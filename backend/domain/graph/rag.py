"""
Graph RAG Module — Context-Aware Identity Graph Retrieval

Combines insights from:
- ID-RAG (MIT Media Lab): Context-aware priority-based graph querying
- SYNAPSE: Spreading activation with temporal decay
- StepChain GraphRAG: BFS multi-hop traversal with evidence chains
- synapse-ai-memory: compile_context() for LLM-ready narratives

The key shift: instead of flattening the graph to label lists, we traverse
edges to produce connected identity narratives. The LLM receives a structured
understanding of HOW interests, traits, experiences, and connections relate
to each other — not just that they exist.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory graph representation for fast traversal
# ---------------------------------------------------------------------------

@dataclass
class InMemoryGraph:
    """Lightweight in-memory representation of a user's identity graph."""

    user_id: str
    nodes: Dict[str, dict] = field(default_factory=dict)
    edges: List[dict] = field(default_factory=list)
    outgoing: Dict[str, List[dict]] = field(default_factory=dict)
    incoming: Dict[str, List[dict]] = field(default_factory=dict)
    by_type: Dict[str, List[str]] = field(default_factory=dict)
    by_label: Dict[str, str] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def neighbors(self, node_id: str) -> List[dict]:
        """All adjacent edges (both directions) for a node."""
        return self.outgoing.get(node_id, []) + self.incoming.get(node_id, [])

    def node_strength(self, node_id: str) -> float:
        """Extract strength from a node, handling different storage locations."""
        node = self.nodes.get(node_id)
        if not node:
            return 0.0
        s = node.get("strength")
        if s is not None:
            return min(float(s), 1.0)
        return min(float(node.get("properties", {}).get("strength", 0.5)), 1.0)


# ---------------------------------------------------------------------------
# Main GraphRAG class
# ---------------------------------------------------------------------------

class GraphRAG:
    """
    Context-aware identity graph retrieval with multi-hop traversal.

    All existing method signatures are preserved for backwards compatibility.
    Internally, every method now loads the full graph (nodes + edges) into
    memory and uses structured traversal instead of flat label extraction.
    """

    CACHE_TTL = 300  # seconds

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._graph_cache: Dict[str, Tuple[float, InMemoryGraph]] = {}

    # ------------------------------------------------------------------
    # Graph loading with caching
    # ------------------------------------------------------------------

    async def _load_graph(self, user_id: str) -> InMemoryGraph:
        """Load the complete user graph into memory with adjacency lists."""
        now = time.time()
        cached = self._graph_cache.get(user_id)
        if cached and (now - cached[0]) < self.CACHE_TTL:
            return cached[1]

        g = InMemoryGraph(user_id=user_id)

        raw_nodes = await self.db.graph_nodes.find(
            {"user_id": user_id}, {"_id": 0}
        ).to_list(10000)

        for n in raw_nodes:
            nid = n.get("id")
            if not nid:
                continue
            g.nodes[nid] = n
            ntype = n.get("node_type", "interest")
            g.by_type.setdefault(ntype, []).append(nid)
            label = (n.get("label") or "").lower().strip()
            if label:
                g.by_label[label] = nid

        node_ids = list(g.nodes.keys())
        if node_ids:
            raw_edges = await self.db.graph_edges.find(
                {"$or": [
                    {"from_node_id": {"$in": node_ids}},
                    {"to_node_id": {"$in": node_ids}},
                ]},
                {"_id": 0},
            ).to_list(10000)

            for e in raw_edges:
                fid, tid = e.get("from_node_id"), e.get("to_node_id")
                if fid not in g.nodes or tid not in g.nodes:
                    continue
                g.edges.append(e)
                g.outgoing.setdefault(fid, []).append(
                    {"edge": e, "neighbor_id": tid}
                )
                g.incoming.setdefault(tid, []).append(
                    {"edge": e, "neighbor_id": fid}
                )

        self._graph_cache[user_id] = (now, g)
        logger.debug(
            "Loaded graph for %s: %d nodes, %d edges",
            user_id, g.node_count, g.edge_count,
        )
        return g

    def invalidate_cache(self, user_id: str) -> None:
        self._graph_cache.pop(user_id, None)

    # ------------------------------------------------------------------
    # Core algorithms
    # ------------------------------------------------------------------

    @staticmethod
    def _spreading_activation(
        graph: InMemoryGraph,
        seed_activations: Dict[str, float],
        decay: float = 0.5,
        threshold: float = 0.05,
        max_steps: int = 3,
    ) -> Dict[str, float]:
        """
        Propagate activation energy from seed nodes through edges.

        Inspired by SYNAPSE's spreading activation. Each step, a node's
        activation spreads to its neighbors attenuated by edge weight × decay.
        Lateral inhibition is implicit: only the *max* incoming activation
        is kept (prevents runaway accumulation).
        """
        activations = dict(seed_activations)

        for _ in range(max_steps):
            updates: Dict[str, float] = {}
            for nid, act in activations.items():
                for adj in graph.neighbors(nid):
                    neighbor = adj["neighbor_id"]
                    w = min(float(adj["edge"].get("weight", 0.5)), 1.0)
                    spread = act * w * decay
                    if spread > threshold:
                        current = max(
                            updates.get(neighbor, 0.0),
                            activations.get(neighbor, 0.0),
                        )
                        updates[neighbor] = max(current, spread)

            changed = False
            for nid, act in updates.items():
                if nid not in activations or act > activations[nid]:
                    activations[nid] = act
                    changed = True
            if not changed:
                break

        return activations

    @staticmethod
    def _bfs_traverse(
        graph: InMemoryGraph,
        seed_ids: Set[str],
        max_hops: int = 2,
        min_weight: float = 0.2,
    ) -> Tuple[Dict[str, int], List[dict]]:
        """
        Controlled BFS from seed nodes (StepChain pattern).
        Returns (node_id → hop_distance, collected_edges).
        """
        distances: Dict[str, int] = {
            nid: 0 for nid in seed_ids if nid in graph.nodes
        }
        collected_edges: List[dict] = []
        frontier = set(distances.keys())

        for hop in range(1, max_hops + 1):
            next_frontier: Set[str] = set()
            for nid in frontier:
                for adj in graph.neighbors(nid):
                    neighbor = adj["neighbor_id"]
                    w = float(adj["edge"].get("weight", 0.5))
                    if w < min_weight:
                        continue
                    if neighbor not in distances:
                        distances[neighbor] = hop
                        next_frontier.add(neighbor)
                    collected_edges.append(adj["edge"])
            frontier = next_frontier
            if not frontier:
                break

        return distances, collected_edges

    # ------------------------------------------------------------------
    # Seed selection (ID-RAG context-aware strategy)
    # ------------------------------------------------------------------

    @staticmethod
    def _select_seeds(
        graph: InMemoryGraph,
        action_type: str = "general",
        topic: Optional[str] = None,
        mood: Optional[str] = None,
        other_user_interests: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Select seed nodes based on action context.

        Instead of using an LLM to generate a search strategy (as ID-RAG
        does), we use deterministic heuristics — our graphs are small enough
        (<100 nodes) that algorithmic seed selection is both faster and cheaper.
        """
        seeds: Dict[str, float] = {}

        def _weighted_sample(node_ids: List[str], count: int) -> List[Tuple[str, float]]:
            """Weighted random sample without replacement."""
            available = [
                (nid, graph.node_strength(nid)) for nid in node_ids
            ]
            selected = []
            for _ in range(min(count, len(available))):
                if not available:
                    break
                total = sum(w for _, w in available)
                if total <= 0:
                    break
                r = random.random() * total
                cumulative = 0.0
                for i, (nid, w) in enumerate(available):
                    cumulative += w
                    if r <= cumulative:
                        selected.append((nid, w))
                        available.pop(i)
                        break
            return selected

        def _topic_match(topic_text: str) -> Dict[str, float]:
            """Find nodes matching a topic string across labels and details."""
            matches: Dict[str, float] = {}
            words = set(topic_text.lower().split())
            for nid, node in graph.nodes.items():
                label = (node.get("label") or "").lower()
                display = (node.get("display_label") or "").lower()
                details = (node.get("properties", {}).get("details") or "").lower()
                strength = graph.node_strength(nid)

                if topic_text.lower() in label or topic_text.lower() in display:
                    matches[nid] = strength
                elif any(w in label for w in words) or any(w in display for w in words):
                    matches[nid] = strength * 0.7
                elif any(w in details for w in words if len(w) > 3):
                    matches[nid] = strength * 0.5
            return matches

        if action_type == "post_generation":
            if topic:
                seeds.update(_topic_match(topic))
            if not seeds:
                interest_ids = graph.by_type.get("interest", [])
                for nid, w in _weighted_sample(interest_ids, 3):
                    seeds[nid] = w
            for ntype in ("trait", "value"):
                for nid in graph.by_type.get(ntype, []):
                    s = graph.node_strength(nid)
                    if s >= 0.7:
                        seeds.setdefault(nid, s * 0.3)

        elif action_type == "chat_response":
            if other_user_interests:
                for label in other_user_interests:
                    lbl = label.lower().strip()
                    if lbl in graph.by_label:
                        seeds[graph.by_label[lbl]] = 1.0
                    else:
                        for stored_label, nid in graph.by_label.items():
                            if lbl in stored_label or stored_label in lbl:
                                seeds[nid] = 0.7
            for nid in graph.by_type.get("connection", []):
                seeds.setdefault(nid, graph.node_strength(nid) * 0.5)
            for nid in graph.by_type.get("trait", []):
                seeds.setdefault(nid, graph.node_strength(nid) * 0.3)

        elif action_type == "personality_profile":
            for nid in graph.nodes:
                s = graph.node_strength(nid)
                if s >= 0.5:
                    seeds[nid] = s
            for nid in graph.by_type.get("connection", []):
                seeds.setdefault(nid, 0.4)

        elif action_type == "decision":
            for nid in graph.by_type.get("interest", []):
                seeds[nid] = graph.node_strength(nid)

        else:  # "general"
            ranked = sorted(
                graph.nodes.keys(),
                key=lambda nid: graph.node_strength(nid),
                reverse=True,
            )
            for nid in ranked[:20]:
                seeds[nid] = graph.node_strength(nid)

        return seeds

    # ------------------------------------------------------------------
    # Narrative compilation (compile_context)
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_narrative(
        graph: InMemoryGraph,
        activations: Dict[str, float],
        action_type: str = "general",
        max_chars: int = 6000,
    ) -> str:
        """
        Convert activated subgraph into an LLM-ready narrative.

        Instead of dumping comma-separated labels, we follow edges to show
        how different aspects of identity connect. This gives the LLM a
        structural understanding of the person, not just a flat inventory.
        """
        activated = sorted(
            [(nid, activations[nid]) for nid in activations if nid in graph.nodes],
            key=lambda x: x[1],
            reverse=True,
        )

        by_type: Dict[str, List[Tuple[str, dict, float]]] = {}
        for nid, act in activated:
            node = graph.nodes[nid]
            ntype = node.get("node_type", "interest")
            by_type.setdefault(ntype, []).append((nid, node, act))

        sections: List[str] = []
        char_count = 0

        def _add(text: str) -> bool:
            nonlocal char_count
            if char_count + len(text) > max_chars:
                return False
            sections.append(text)
            char_count += len(text)
            return True

        def _display(node: dict) -> str:
            return node.get("display_label") or node.get("label", "?")

        def _details(node: dict) -> str:
            return node.get("properties", {}).get("details", "")

        def _edge_context(nid: str, exclude_types: Set[str] = frozenset()) -> List[str]:
            """Get connected node descriptions for a given node."""
            parts = []
            seen = set()
            for adj in graph.neighbors(nid):
                neighbor = graph.nodes.get(adj["neighbor_id"])
                if not neighbor or adj["neighbor_id"] in seen:
                    continue
                if adj["neighbor_id"] not in activations:
                    continue
                n_type = neighbor.get("node_type", "")
                if n_type in exclude_types:
                    continue
                seen.add(adj["neighbor_id"])
                rel = adj["edge"].get("relationship_type", "related_to")
                parts.append(f"{rel} → {_display(neighbor)}")
            return parts[:4]

        # 1. Demographics — identity core
        demos = by_type.get("demographic", [])
        if demos:
            demo_parts = []
            for nid, node, _ in demos:
                d = _details(node)
                demo_parts.append(d if d else _display(node))
            _add("**Identity:** " + ". ".join(demo_parts[:8]))

        # 2. Connections — people in their life with relationship context
        connections = by_type.get("connection", [])
        if connections:
            conn_lines = []
            for nid, node, _ in connections:
                rel = node.get("properties", {}).get("relationship", "")
                d = _details(node)
                line = _display(node)
                if rel:
                    line += f" ({rel})"
                if d:
                    line += f" — {d}"
                edges = _edge_context(nid, exclude_types={"connection"})
                if edges:
                    line += f" [{', '.join(edges)}]"
                conn_lines.append(line)
            _add("\n**Important people:** " + " | ".join(conn_lines[:6]))

        # 3. Experiences — life events with connected context
        experiences = by_type.get("experience", [])
        if experiences:
            exp_lines = []
            for nid, node, _ in experiences:
                d = _details(node)
                line = _display(node)
                if d:
                    line += f" — {d}"
                edges = _edge_context(nid, exclude_types={"experience"})
                if edges:
                    line += f" [{', '.join(edges)}]"
                exp_lines.append(line)
            _add("\n**Life experiences:** " + " | ".join(exp_lines[:5]))

        # 4. Interests — clustered by graph connectivity
        interests = by_type.get("interest", [])
        if interests:
            interest_ids = [nid for nid, _, _ in interests]
            clusters = GraphRAG._cluster_connected(graph, interest_ids)

            cluster_parts = []
            for cluster in clusters:
                labels = [_display(graph.nodes[nid]) for nid in cluster]
                cross = set()
                for nid in cluster:
                    for adj in graph.neighbors(nid):
                        nb = graph.nodes.get(adj["neighbor_id"])
                        if nb and nb.get("node_type") != "interest" and adj["neighbor_id"] in activations:
                            cross.add(
                                f"{adj['edge'].get('relationship_type', '→')} {_display(nb)}"
                            )
                text = ", ".join(labels)
                if cross:
                    text += f" (→ {', '.join(list(cross)[:3])})"
                cluster_parts.append(text)
            _add("\n**Interests & passions:** " + " | ".join(cluster_parts))

        # 5. Traits
        traits = by_type.get("trait", [])
        if traits:
            trait_parts = []
            for nid, node, _ in traits:
                d = _details(node)
                trait_parts.append(f"{_display(node)} — {d}" if d else _display(node))
            _add("\n**Character traits:** " + ", ".join(trait_parts[:8]))

        # 6. Values
        values = by_type.get("value", [])
        if values:
            val_parts = []
            for nid, node, _ in values:
                d = _details(node)
                val_parts.append(f"{_display(node)} — {d}" if d else _display(node))
            _add("\n**Core values:** " + ", ".join(val_parts[:6]))

        # 7. Preferences
        prefs = by_type.get("preference", [])
        if prefs:
            pref_parts = []
            for nid, node, _ in prefs:
                d = _details(node)
                pref_parts.append(d if d else _display(node))
            _add("\n**Preferences:** " + " | ".join(pref_parts[:5]))

        return "\n".join(sections)

    @staticmethod
    def _cluster_connected(
        graph: InMemoryGraph, node_ids: List[str],
    ) -> List[List[str]]:
        """Group nodes that are directly connected to each other (union-find)."""
        parent = {nid: nid for nid in node_ids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        node_set = set(node_ids)
        for nid in node_ids:
            for adj in graph.neighbors(nid):
                if adj["neighbor_id"] in node_set:
                    union(nid, adj["neighbor_id"])

        clusters: Dict[str, List[str]] = {}
        for nid in node_ids:
            clusters.setdefault(find(nid), []).append(nid)

        return sorted(
            clusters.values(),
            key=lambda c: max(graph.node_strength(nid) for nid in c),
            reverse=True,
        )

    # ==================================================================
    # NEW PUBLIC API — context-aware identity retrieval
    # ==================================================================

    async def get_identity_context(
        self,
        user_id: str,
        action_type: str = "general",
        topic: Optional[str] = None,
        mood: Optional[str] = None,
        other_user_interests: Optional[List[str]] = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        Context-aware identity retrieval with multi-hop traversal.

        This is the primary new method. It:
        1. Selects seed nodes based on the action context (ID-RAG)
        2. Propagates activation through edges (SYNAPSE)
        3. BFS traversal for evidence chains (StepChain)
        4. Compiles a narrative for the LLM (synapse-ai-memory)

        Returns an LLM-ready narrative string.
        """
        graph = await self._load_graph(user_id)
        if not graph.nodes:
            return ""

        seeds = self._select_seeds(
            graph, action_type, topic, mood, other_user_interests,
        )
        if not seeds:
            ranked = sorted(
                graph.nodes.keys(),
                key=lambda nid: graph.node_strength(nid),
                reverse=True,
            )
            seeds = {nid: graph.node_strength(nid) for nid in ranked[:10]}

        use_wider_spread = action_type == "personality_profile"
        activations = self._spreading_activation(
            graph, seeds,
            decay=0.6 if use_wider_spread else 0.5,
            threshold=0.03 if use_wider_spread else 0.05,
            max_steps=3,
        )

        hops = 3 if use_wider_spread else 2
        distances, _ = self._bfs_traverse(
            graph, set(seeds.keys()), max_hops=hops, min_weight=0.2,
        )
        for nid, dist in distances.items():
            if nid not in activations:
                activations[nid] = max(0.1, 0.5 ** dist)

        max_chars = max_tokens * 4
        return self._compile_narrative(graph, activations, action_type, max_chars)

    async def get_identity_subgraph(
        self,
        user_id: str,
        seed_labels: Optional[List[str]] = None,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Get a structured subgraph starting from seed labels.
        Useful for visualization or programmatic consumption.
        """
        graph = await self._load_graph(user_id)

        seed_ids: Set[str] = set()
        if seed_labels:
            for label in seed_labels:
                lbl = label.lower().strip()
                if lbl in graph.by_label:
                    seed_ids.add(graph.by_label[lbl])
                else:
                    for stored, nid in graph.by_label.items():
                        if lbl in stored or stored in lbl:
                            seed_ids.add(nid)
        else:
            seed_ids = set(graph.by_type.get("interest", []))

        distances, edges = self._bfs_traverse(graph, seed_ids, max_hops)

        return {
            "nodes": [graph.nodes[nid] for nid in distances if nid in graph.nodes],
            "edges": edges,
            "seed_count": len(seed_ids),
            "total_reached": len(distances),
        }

    # ==================================================================
    # BACKWARDS-COMPATIBLE API — same signatures, enhanced internals
    # ==================================================================

    async def get_user_context(
        self, user_id: str, max_nodes: int = 20,
    ) -> Dict[str, Any]:
        """
        Get comprehensive user context from knowledge graph.

        Returns structured context for LLM prompts. Same return format as
        before, but each item now includes a ``connected`` list showing
        edge relationships — consumers that use it will benefit, those that
        ignore it won't break.
        """
        graph = await self._load_graph(user_id)

        context: Dict[str, list] = {
            "interests": [],
            "traits": [],
            "values": [],
            "experiences": [],
            "preferences": [],
            "demographics": [],
            "connections": [],
        }

        type_mapping = {
            "interest": "interests",
            "trait": "traits",
            "value": "values",
            "experience": "experiences",
            "preference": "preferences",
            "demographic": "demographics",
            "connection": "connections",
        }

        for nid, node in graph.nodes.items():
            node_type = node.get("node_type", "interest")
            label = node.get("label", "")
            properties = node.get("properties", {})
            strength = graph.node_strength(nid)
            source = properties.get("source", "unknown")

            connected = []
            for adj in graph.neighbors(nid)[:5]:
                nb = graph.nodes.get(adj["neighbor_id"])
                if nb:
                    connected.append({
                        "label": nb.get("label", ""),
                        "type": nb.get("node_type", ""),
                        "relationship": adj["edge"].get("relationship_type", ""),
                        "weight": adj["edge"].get("weight", 0.5),
                    })

            item = {
                "label": label,
                "display_label": node.get("display_label", label),
                "strength": strength,
                "properties": properties,
                "source": source,
                "connected": connected,
            }

            key = type_mapping.get(node_type, "interests")
            context[key].append(item)

        for key in context:
            context[key] = sorted(
                context[key],
                key=lambda x: x.get("strength", 0),
                reverse=True,
            )[:max_nodes]

        return context

    async def get_relevant_context(
        self, user_id: str, query_type: str, topic: Optional[str] = None,
    ) -> Any:
        """
        Get relevant context for specific query types.
        Now powered by graph traversal instead of flat label extraction.
        """
        if query_type == "post_generation":
            return await self.get_identity_context(
                user_id,
                action_type="post_generation",
                topic=topic,
                max_tokens=1500,
            )

        elif query_type == "chat_response":
            return await self.get_identity_context(
                user_id,
                action_type="chat_response",
                max_tokens=1000,
            )

        elif query_type == "matching":
            context = await self.get_user_context(user_id, max_nodes=30)
            return {
                "interests": [i["label"] for i in context.get("interests", [])],
                "values": [v["label"] for v in context.get("values", [])],
                "traits": [t["label"] for t in context.get("traits", [])],
            }

        return ""

    async def get_avatar_personality_profile(self, user_id: str) -> str:
        """
        Generate a personality profile grounded in graph traversal.

        Uses full identity subgraph (personality_profile mode) to produce
        a narrative that reads like a real person — with connected context
        showing how interests, experiences, traits, and relationships
        relate to each other.
        """
        graph = await self._load_graph(user_id)

        user = await self.db.users.find_one(
            {"id": user_id}, {"archetype": 1, "name": 1, "avatar_name": 1}
        )
        archetype = (user.get("archetype", "casual_observer") if user else "casual_observer")

        archetype_behaviors = {
            "social_butterfly": "You're the person who knows everyone and always has plans. You text first, make group chats, and your phone is always buzzing.",
            "thoughtful_contributor": "You don't post just to post. When you share something, it means something. Quality over quantity, always.",
            "casual_observer": "You scroll more than you post, but when something genuinely hits, you share it. No pressure, no performance.",
            "niche_expert": "You go DEEP on what you care about. Your friends come to you for recommendations in your areas. You know your stuff.",
            "enthusiastic_newcomer": "Everything is exciting and new. You're discovering, asking questions, trying things, and not afraid to be a beginner.",
        }
        archetype_desc = archetype_behaviors.get(
            archetype, archetype_behaviors["casual_observer"]
        )

        identity_narrative = await self.get_identity_context(
            user_id,
            action_type="personality_profile",
            max_tokens=2500,
        )

        profile = f"""=== WHO YOU ARE ===

{archetype_desc}

{identity_narrative}

=== HOW YOU TALK ON SOCIAL MEDIA ===
- You're a real person with a real life, not a content creator
- You post about MOMENTS, not topics. Something happens, you share it.
- Your interests blend naturally — you don't isolate them into separate posts
- You have opinions, humor, bad days, inside jokes, random thoughts
- Sometimes you post a whole story. Sometimes just a sentence. Depends on the vibe.
- When something moves you, you share it RAW — not polished, not filtered
- The detail matters. Specific moments say more than generic sentiments.
- You NEVER sound like an AI, a brand, or a motivational poster"""

        return profile

    async def calculate_compatibility(
        self, user1_id: str, user2_id: str,
    ) -> Dict[str, Any]:
        """Calculate compatibility score between two users based on their graphs."""
        g1 = await self._load_graph(user1_id)
        g2 = await self._load_graph(user2_id)

        def _labels(g: InMemoryGraph, ntype: str) -> set:
            return {
                (g.nodes[nid].get("label") or "").lower()
                for nid in g.by_type.get(ntype, [])
            }

        u1_int, u2_int = _labels(g1, "interest"), _labels(g2, "interest")
        u1_val, u2_val = _labels(g1, "value"), _labels(g2, "value")
        u1_tra, u2_tra = _labels(g1, "trait"), _labels(g2, "trait")

        i_score = self._jaccard_similarity(u1_int, u2_int) * 100
        v_score = self._jaccard_similarity(u1_val, u2_val) * 100
        t_score = self._jaccard_similarity(u1_tra, u2_tra) * 100

        return {
            "compatibility_score": round(i_score * 0.5 + v_score * 0.3 + t_score * 0.2, 2),
            "shared_interests": list(u1_int & u2_int),
            "shared_values": list(u1_val & u2_val),
            "shared_traits": list(u1_tra & u2_tra),
            "breakdown": {
                "interests": round(i_score, 2),
                "values": round(v_score, 2),
                "traits": round(t_score, 2),
            },
        }

    async def find_similar_users(
        self, user_id: str, limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find users with similar graph profiles."""
        user_nodes = await self.db.graph_nodes.find(
            {"user_id": user_id}, {"_id": 0}
        ).to_list(1000)
        user_labels = set(
            n["label"] for n in user_nodes
            if n.get("node_type") in ("interest", "value")
        )

        all_users = await self.db.users.find(
            {"id": {"$ne": user_id}}, {"_id": 0, "id": 1}
        ).to_list(1000)

        similarities = []
        for other in all_users[:50]:
            oid = other["id"]
            other_nodes = await self.db.graph_nodes.find(
                {"user_id": oid}, {"_id": 0}
            ).to_list(1000)
            other_labels = set(
                n["label"] for n in other_nodes
                if n.get("node_type") in ("interest", "value")
            )
            sim = self._jaccard_similarity(user_labels, other_labels)
            if sim > 0:
                similarities.append({
                    "user_id": oid,
                    "similarity": sim,
                    "shared_items": list(user_labels & other_labels),
                })

        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:limit]

    async def get_conversation_context(
        self, user_id: str, other_user_id: str,
    ) -> str:
        """Get conversation context between two users for avatar chat."""
        other_ctx = await self.get_user_context(other_user_id, max_nodes=10)
        other_interests = [i["label"] for i in other_ctx.get("interests", [])[:8]]

        narrative = await self.get_identity_context(
            user_id,
            action_type="chat_response",
            other_user_interests=other_interests,
            max_tokens=1200,
        )

        compatibility = await self.calculate_compatibility(user_id, other_user_id)
        shared = compatibility.get("shared_interests", [])

        return f"""{narrative}

Shared interests with this person: {', '.join(shared) if shared else 'discovering common ground'}
Compatibility: {compatibility.get('compatibility_score', 0):.0f}%

Use this context to have natural, engaging conversations that explore shared interests and build connection."""

    @staticmethod
    def _jaccard_similarity(set1: set, set2: set) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
