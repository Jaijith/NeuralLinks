"""
Graph Builder Module
Handles knowledge graph construction and enrichment from user data
"""

import re
from typing import List, Dict, Any, Tuple, Union
from datetime import datetime, timezone
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import AsyncOpenAI, AsyncAzureOpenAI
import json
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds and enriches knowledge graphs from user data"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client: Union[AsyncOpenAI, AsyncAzureOpenAI, None], model: str = "gpt-5-nano-2025-08-07"):
        self.db = db
        self.llm_client = llm_client
        self.model = model  # Model name for OpenAI or deployment name for Azure
        self.deployment = model  # Alias for backwards compatibility
        # Check if using gpt-5 models which require responses API
        self._use_responses_api = "gpt-5" in self.model.lower()
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with appropriate API based on model type.
        - For gpt-5 models: uses responses.create() API
        - For other models: uses chat.completions.create() API
        """
        if self._use_responses_api:
            # Use new responses API for gpt-5 models
            response = await self.llm_client.responses.create(
                model=self.model,
                input=prompt
            )
            return response.output_text.strip() if response.output_text else ""
        else:
            # Use traditional chat completions API
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    
    async def extract_entities_from_text(self, text: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract entities (interests, traits, values) from text
        """
        if not self.llm_client or not text:
            return []
        
        try:
            prompt = f"""Extract key entities from this text for a dating profile knowledge graph.
Return ONLY a JSON array with entities in this exact format:
[
  {{"type": "interest", "label": "hiking", "properties": {{"intensity": "high"}}}},
  {{"type": "trait", "label": "adventurous", "properties": {{"confidence": 0.8}}}},
  {{"type": "value", "label": "authenticity", "properties": {{"importance": "high"}}}}
]

Entity types: interest, trait, value, experience, preference
Text: {text}

Return ONLY the JSON array, no explanation."""

            content = await self._call_llm(prompt)
            logger.info(f"Successfully extracted entities using {self.model}")
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            entities = json.loads(content)
            
            # Create graph nodes
            nodes = []
            for entity in entities:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": entity.get("type", "interest"),
                    "label": entity.get("label", "").lower(),
                    "properties": entity.get("properties", {}),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            print(f"Entity extraction error: {str(e)}")
            return []
    
    async def build_graph_from_profile(self, user_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Build initial knowledge graph from user profile data
        Returns count of nodes and edges created
        """
        user_id = user_data['id']
        nodes_created = 0
        edges_created = 0
        
        # 1. Create nodes from interests (explicit)
        interests = user_data.get('interests', [])
        interest_node_ids = []
        
        for interest in interests:
            node = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "node_type": "interest",
                "label": interest.lower(),
                "properties": {"source": "explicit", "strength": 1.0},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if node already exists
            existing = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": interest.lower()
            })
            
            if not existing:
                from domain.memory.bayesian import add_bayesian_defaults as _abd
                _abd(node, prior="verified", source="profile")
                await self.db.graph_nodes.insert_one(node)
                interest_node_ids.append(node["id"])
                nodes_created += 1
            else:
                interest_node_ids.append(existing["id"])
        
        # 2. Extract entities from bio using LLM
        bio = user_data.get('bio', '')
        if bio:
            bio_nodes = await self.extract_entities_from_text(bio, user_id)
            for node in bio_nodes:
                node["properties"]["source"] = "bio"
                
                # Check if similar node exists
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": node["node_type"],
                    "label": node["label"]
                })
                
                if not existing:
                    from domain.memory.bayesian import add_bayesian_defaults as _abd
                    _abd(node, prior="verified", source="bio")
                    await self.db.graph_nodes.insert_one(node)
                    nodes_created += 1
        
        # 3. Create demographic nodes
        demographic_data = [
            ("age_group", self._get_age_group(user_data.get('age'))),
            ("gender", user_data.get('gender')),
            ("location", user_data.get('location'))
        ]
        
        for node_type, value in demographic_data:
            if value:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "demographic",
                    "label": f"{node_type}:{value}",
                    "properties": {"category": node_type, "value": value},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "demographic",
                    "label": node["label"]
                })
                
                if not existing:
                    from domain.memory.bayesian import add_bayesian_defaults as _abd
                    _abd(node, prior="verified", source="profile")
                    await self.db.graph_nodes.insert_one(node)
                    nodes_created += 1
        
        # 4. Create edges between related interests (co-occurrence)
        if len(interest_node_ids) > 1:
            for i in range(len(interest_node_ids)):
                for j in range(i + 1, len(interest_node_ids)):
                    edge = {
                        "id": str(uuid.uuid4()),
                        "from_node_id": interest_node_ids[i],
                        "to_node_id": interest_node_ids[j],
                        "relationship_type": "co_occurs_with",
                        "weight": 1.0,
                        "properties": {"source": "interests"},
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    existing = await self.db.graph_edges.find_one({
                        "from_node_id": interest_node_ids[i],
                        "to_node_id": interest_node_ids[j]
                    })
                    
                    if not existing:
                        await self.db.graph_edges.insert_one(edge)
                        edges_created += 1
        
        return {"nodes_created": nodes_created, "edges_created": edges_created}
    
    async def enrich_graph_from_post(self, post_content: str, user_id: str) -> Dict[str, int]:
        """
        Enrich knowledge graph from user post content.

        Dual-Memory Architecture: Routes through Classification Agent → STM
        instead of writing directly to graph_nodes.
        """
        from domain.memory.ingestion import classify_and_ingest

        # Derive avatar_id from user_id (avatars collection)
        avatar_id = await self._get_avatar_id(user_id)

        obs_count = await classify_and_ingest(
            openai_client=self.llm_client,
            db=self.db,
            user_id=user_id,
            avatar_id=avatar_id,
            content=post_content,
            source="post",
        )

        return {"stm_observations_written": obs_count, "nodes_created": 0, "edges_created": 0}
    
    async def enrich_graph_from_interaction(self, user_id: str, target_user_id: str, 
                                           interaction_type: str) -> Dict[str, int]:
        """
        Enrich graph from user interactions (likes, matches, messages).

        This is a direct LTM reinforcement — shared interests with matched
        users are confirmed by behavioral evidence (interaction = implicit
        interest signal), so we update belief directly.
        """
        from domain.memory.bayesian import compute_belief_strength

        target_user = await self.db.users.find_one({"id": target_user_id})
        if not target_user:
            return {"nodes_created": 0, "edges_created": 0}

        target_nodes = await self.db.graph_nodes.find(
            {"user_id": target_user_id, "node_type": "interest"},
            {"_id": 0}
        ).limit(5).to_list(5)

        now = datetime.now(timezone.utc)
        nodes_updated = 0

        for target_node in target_nodes:
            user_node = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "label": target_node["label"]
            })
            if not user_node:
                continue

            # Evidence weight: match is stronger confirmation than a like
            delta_alpha = 0.5 if interaction_type == "match" else 0.2

            update = {
                "$inc": {"belief_alpha": delta_alpha, "evidence_count": 1},
                "$push": {"evidence_log": {
                    "at": now,
                    "source": f"interaction_{interaction_type}",
                    "weight": delta_alpha,
                    "subtype": "interest_implicit",
                    "session_id": "",
                }},
                "$set": {
                    "last_evidence_at": now,
                    "updated_at": now,
                },
            }

            # Recompute derived fields
            alpha = user_node.get("belief_alpha", 2.0) + delta_alpha
            beta = user_node.get("belief_beta", 1.0)
            bs = compute_belief_strength(alpha, beta)
            update["$set"]["belief_strength"] = bs
            update["$set"]["strength"] = bs
            update["$set"]["salience"] = max(user_node.get("salience", 0.5), bs)

            await self.db.graph_nodes.update_one(
                {"_id": user_node["_id"]},
                update,
            )
            nodes_updated += 1

        return {"nodes_created": 0, "nodes_updated": nodes_updated, "edges_created": 0}
    
    async def add_external_platform_data(self, user_id: str, platform: str, 
                                        data: Dict[str, Any]) -> Dict[str, int]:
        """
        Add data from external platforms to knowledge graph via STM pipeline.

        Converts platform-specific structured data into a text summary,
        then routes through Classification Agent → STM.
        """
        parts = []

        if platform == "spotify":
            for artist in data.get("top_artists", [])[:5]:
                parts.append(f"User listens to {artist} on Spotify (top artist).")
            for genre in data.get("top_genres", [])[:5]:
                parts.append(f"User likes {genre} music (Spotify genre).")

        elif platform == "youtube":
            for topic in data.get("favorite_topics", [])[:5]:
                parts.append(f"User watches {topic} content on YouTube (favorite topic).")

        elif platform in ("facebook", "instagram"):
            for interest in data.get("interests", [])[:10]:
                parts.append(f"User is interested in {interest} ({platform}).")

        elif platform == "twitter":
            for topic in data.get("topics_followed", [])[:5]:
                parts.append(f"User follows {topic} on Twitter.")

        elif platform == "linkedin":
            for skill in data.get("skills", [])[:5]:
                parts.append(f"User has {skill} as a professional skill (LinkedIn).")

        else:
            for interest in data.get("interests", [])[:10]:
                parts.append(f"User has interest: {interest} ({platform}).")
            for sub in data.get("subreddits", [])[:5]:
                topic = sub.replace("r/", "")
                parts.append(f"User follows r/{topic} on Reddit.")
            for genre in data.get("top_genres", data.get("genres", []))[:5]:
                parts.append(f"User listens to {genre} genre ({platform}).")
            for topic in data.get("courses_taken", data.get("topics", []))[:5]:
                parts.append(f"User is studying {topic} ({platform}).")

        if not parts:
            return {"stm_observations_written": 0, "nodes_created": 0, "edges_created": 0}

        from domain.memory.ingestion import classify_and_ingest

        avatar_id = await self._get_avatar_id(user_id)
        summary = "\n".join(parts)

        obs_count = await classify_and_ingest(
            openai_client=self.llm_client,
            db=self.db,
            user_id=user_id,
            avatar_id=avatar_id,
            content=summary,
            source=f"platform_{platform}",
        )

        return {"stm_observations_written": obs_count, "nodes_created": 0, "edges_created": 0}
    
    async def _get_avatar_id(self, user_id: str) -> str:
        """Resolve avatar_id from user_id."""
        try:
            avatar = await self.db.avatars.find_one(
                {"user_id": user_id}, {"_id": 0, "id": 1}
            )
            return avatar.get("id", user_id) if avatar else user_id
        except Exception:
            return user_id

    def _get_age_group(self, age: int) -> str:
        """Categorize age into groups"""
        if not age:
            return None
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55+"
