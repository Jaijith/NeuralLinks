# Dual-Memory Architecture: Short-Term & Long-Term Memory Graphs

## Implementation Plan — NeuralLinks

**Created**: 2026-02-22
**Status**: Plan (pre-implementation)
**Authors**: Jai + AI Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Analysis](#2-current-system-analysis)
3. [Academic Foundations](#3-academic-foundations)
4. [Architecture Overview](#4-architecture-overview)
5. [Short-Term Memory Graph (STM)](#5-short-term-memory-graph-stm)
6. [Long-Term Memory Graph (LTM)](#6-long-term-memory-graph-ltm)
7. [Observation Ontology](#7-observation-ontology)
8. [Agentic Pipeline — Classification Agent](#8-agentic-pipeline--classification-agent)
9. [Agentic Pipeline — Consolidation Agent](#9-agentic-pipeline--consolidation-agent)
10. [Read Path — GraphRAG Enhancement](#10-read-path--graphrag-enhancement)
11. [Write Path Changes](#11-write-path-changes)
12. [Scheduling & Timing](#12-scheduling--timing)
13. [Migration Strategy](#13-migration-strategy)
14. [Implementation Phases](#14-implementation-phases)
15. [Operations & Monitoring](#15-operations--monitoring)
16. [Cost Analysis](#16-cost-analysis)
17. [Design Decisions & Rationale](#17-design-decisions--rationale)

---

## 1. Executive Summary

We are restructuring the NeuralLinks memory system from a single, naively-updated knowledge graph into a **dual-memory architecture** inspired by neuroscience's Complementary Learning Systems (CLS) theory:

- **Short-Term Memory Graph (STM)**: A rolling 2-week buffer of raw, timestamped observations from voice, posts, chat, and platform imports. Fast writes, high granularity, automatic expiry.

- **Long-Term Memory Graph (LTM)**: The existing `graph_nodes` + `graph_edges` collections enhanced with Bayesian belief parameters. Permanent, evidence-accumulating, high-confidence beliefs about the user's identity.

- **Consolidation Pipeline**: A daily batch process where an LLM-powered Consolidation Agent reviews all accumulated STM observations holistically, updates LTM beliefs using Bayesian math, and decides which pending beliefs to promote to active identity.

All classification and consolidation decisions are **agentic** (LLM-driven), not rule-based. The observation ontology (entity types + subtypes) serves as a shared structured vocabulary for the agents, not a rigid rule engine.

---

## 2. Current System Analysis

### 2.1 What Exists Today

| Layer | Collection(s) | Purpose | Location |
|---|---|---|---|
| **Semantic Memory** | `graph_nodes`, `graph_edges` | Interests, traits, values, connections, experiences, preferences, demographics | `backend/domain/graph/rag.py`, `builder.py` |
| **Procedural Memory** | `avatar_action_memory` | Action patterns, success rates | `backend/domain/avatar/memory/action_memory.py` |
| **Episodic Memory** | `avatar_episodic_memory` | Significant experiences with emotional valence | `backend/domain/avatar/memory/episodic_memory.py` |
| **Identity Memory** | `identity_memory` | Raw facts/interests from voice (legacy) | `backend/domain/voice/voice_memory.py` |
| **Conversation Index** | `conversation_index`, S3 transcripts | Lightweight conversation summaries | `backend/domain/voice/conversation_recall.py` |
| **Episodic (voice)** | `episodic_memory` | Richer conversation summaries | `backend/domain/voice/memory_orchestrator.py` |
| **Memory Manager** | Unified interface | Combines graph + action + episodic memory | `backend/domain/avatar/memory/memory_manager.py` |

### 2.2 GraphRAG System

The `GraphRAG` class (`backend/domain/graph/rag.py`) provides context-aware identity retrieval using:

- **InMemoryGraph**: Lightweight in-memory representation with adjacency lists
- **Spreading Activation**: Propagates activation from seed nodes through edges (SYNAPSE-inspired)
- **BFS Multi-Hop Traversal**: Controlled breadth-first search for evidence chains (StepChain-inspired)
- **Context-Aware Seed Selection**: Heuristic-based selection by action type (ID-RAG-inspired)
- **Narrative Compilation**: Converts activated subgraphs into LLM-ready text

Used by: voice prompt generation, post generation, chat responses, personality profiles, decision making.

### 2.3 Current Node Schema

```
graph_nodes:
  id: str (e.g., "interest_userId_label")
  user_id: str
  node_type: "interest" | "trait" | "value" | "connection" | "experience" | "preference" | "demographic"
  label: str (lowercase)
  display_label: str
  strength: float (0.0-1.0)
  mention_count: int
  properties: { source, service, details, confidence, relationship, ... }
  created_at: datetime
  updated_at: datetime
```

### 2.4 Current Edge Schema

```
graph_edges:
  id: str (UUID)
  from_node_id: str
  to_node_id: str
  relationship_type: "co_occurs_with" | "expressed_through" | "motivates" | "shaped_by" | ...
  weight: float (0.0-1.0)
  properties: { source, reasoning, confidence }
  created_at: datetime
```

### 2.5 Critical Problems

| Problem | Details | Impact |
|---|---|---|
| **Naive additive strength** | `+0.05` per voice mention, `+0.5` per post, `+0.3` per interaction — arbitrary increments that saturate at 1.0 | Strength is meaningless after a few mentions |
| **No temporal decay on graph nodes** | Once created at strength 0.8, stays forever | A 6-month-old single mention looks identical to an active daily habit |
| **No evidence tracking** | Can't distinguish 1-observation node from 50-observation node | No uncertainty quantification |
| **Direct LTM writes** | Voice extraction, posts, manual edits all write directly to `graph_nodes` | A single misheard transcript creates permanent incorrect nodes |
| **No consolidation** | No process to aggregate signals into stable beliefs or downweight stale info | Graph accumulates noise over time |
| **No edges from voice** | Memory orchestrator creates nodes from voice but never creates edges | Voice conversations don't build graph structure |
| **No classification nuance** | "I was born in India" and "I went trekking" get same treatment | Facts and activity mentions have identical evidence weight |
| **Three entity types only** | `EntityType` enum has only CONNECTION, INTEREST, FACT | Can't properly classify traits, values, experiences, preferences |

### 2.6 Current Write Paths

| Source | Pipeline | Destination |
|---|---|---|
| Voice conversation | `MemoryOrchestrator` → Extract → Reason → Validate → Execute | `graph_nodes` (direct), `users.connections`, `identity_memory` |
| Voice conversation | `VoiceMemoryService._store_to_graph_nodes()` | `graph_nodes` (direct) |
| Voice conversation | `_personality_extraction_agent()` | `graph_nodes` (direct, traits + values) |
| Post content | `GraphBuilder.enrich_graph_from_post()` | `graph_nodes` (direct) |
| User interaction | `GraphBuilder.enrich_graph_from_interaction()` | `graph_nodes` (direct) |
| Profile creation | `GraphBuilder.build_graph_from_profile()` | `graph_nodes` + `graph_edges` (direct) |
| Platform import | `GraphBuilder.add_external_platform_data()` | `graph_nodes` (direct) |
| Manual API | `graph_routes.py` endpoints | `graph_nodes` (direct) |

**All paths write directly to LTM. There is no staging buffer.**

---

## 3. Academic Foundations

All publications below are real, verifiable works.

### 3.1 Complementary Learning Systems (CLS) Theory

**McClelland, McNaughton & O'Reilly (1995)**. "Why there are complementary learning systems in the hippocampus and neocortex: Insights from the successes and failures of connectionist models of learning and memory." *Psychological Review*, 102(3), 419–457.

**Kumaran, Hassabis & McClelland (2016)**. "What Learning Systems do Intelligent Agents Need? Complementary Learning Systems Theory Updated." *Trends in Cognitive Sciences*, 20(7), 512–534.

**Sun et al. (2023)**. "Organizing memories for generalization in complementary learning systems." *Nature Neuroscience*.

**Relevance**: The brain uses two complementary systems — a fast-learning hippocampal system (our STM) that rapidly encodes new experiences, and a slow-learning neocortical system (our LTM) that gradually consolidates stable knowledge. Memories don't transfer wholesale; only memories that are reinforced and aid generalization consolidate. This directly justifies the STM → periodic consolidation → LTM architecture.

### 3.2 ACT-R Declarative Memory

**Anderson, Bothell, Byrne, Douglass, Lebiere & Qin (2004)**. "An Integrated Theory of the Mind." *Psychological Review*, 111(4), 1036–1060.

**Relevance**: Base-level activation of a memory chunk: `B_i = ln(Σ t_j^{-d})` where `t_j` is time since j-th access, `d ≈ 0.5`. Memory accessibility depends on both **recency** (recent accesses contribute more) and **frequency** (more accesses = higher activation). This gives the mathematical foundation for why the evidence_log must preserve all observation timestamps and why spaced evidence is more valuable than clustered evidence.

### 3.3 Ebbinghaus Forgetting Curve

**Ebbinghaus (1885)**. *Über das Gedächtnis* (Memory: A Contribution to Experimental Psychology).

**Formula**: `R = e^{-t/S}` where R = retention, t = time since learning, S = memory stability. Each successful retrieval increases S. This underpins the salience decay mechanism: salience fades without reinforcement, but each new observation increases stability, making the memory more resistant to future decay.

### 3.4 Beta-Bernoulli Bayesian Updates

**Gelman, Carlin, Stern, Dunson, Vehtari & Rubin (2013)**. *Bayesian Data Analysis*, 3rd Edition, CRC Press.

**Relevance**: For belief accumulation from observations:
- Prior: `Beta(α, β)` where α = positive evidence, β = negative/absent evidence
- Posterior after positive evidence: `Beta(α + w, β)` where w = evidence weight
- Posterior mean (belief strength): `α / (α + β)`
- Posterior variance: `αβ / ((α+β)²(α+β+1))` — encodes uncertainty
- A node with `Beta(2, 1)` has high uncertainty; `Beta(50, 10)` has low uncertainty
- The Beta distribution naturally handles the distinction between "probably likes cooking" (few observations) and "definitely likes cooking" (many observations)

### 3.5 Zep / Graphiti — Temporal Knowledge Graph for Agent Memory

**Preston-Werner, Riedel & Holmgren (2025)**. "Zep: A Temporal Knowledge Graph Architecture for Agent Memory." *arXiv:2501.13956*.

**Relevance**: Episode-based ingestion (each data event = episode node) with bi-temporal edges (database time + real-world time). Validates recording raw observations as timestamped events (STM) while maintaining a separate evolving knowledge layer (LTM). 94.8% on DMR benchmark, up to 18.5% improvement on LongMemEval.

### 3.6 Agentic Memory (AgeMem)

**Xu et al. (2025)**. "Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for Large Language Model Agents." *arXiv:2601.01885*.

**Relevance**: Memory operations (store, retrieve, update, summarize, discard) should be intelligent agent decisions, not mechanical rule execution. Validates making consolidation an LLM-driven reasoning process.

### 3.7 HiMem — Hierarchical Long-Term Memory

**Wang et al. (2025)**. "HiMem: Hierarchical Long-Term Memory for LLM Long-Horizon Agents." *arXiv:2601.06377*.

**Relevance**: Separates Episode Memory (concrete events) from Note Memory (stable abstract knowledge) with conflict-aware reconsolidation. Maps to our STM (episodes) → LTM (consolidated beliefs) with conflict resolution.

### 3.8 BAKE — Bayesian Continual KG Embedding

**(2025)**. "Learning to Evolve: Bayesian-Guided Continual Knowledge Graph Embedding." *arXiv:2508.02426*.

**Relevance**: Treats continual KG evolution as sequential Bayesian inference, preventing catastrophic forgetting. Validates Bayesian updates over naive additive increments.

### 3.9 BIKG — Bayesian Inference with Complex KG Evidence

**Toroghi et al. (2024)**. "Bayesian Inference with Complex Knowledge Graph Evidence." *OpenReview*.

**Relevance**: Bayesian filtering for belief tracking over KG entities with incremental evidence. Applicable to updating node beliefs from multiple evidence sources.

### 3.10 M2A — Multimodal Memory Agent

**(2025)**. "M2A: Multimodal Memory Agent with Dual-Layer Hybrid Memory for Long-Term Personalized Interactions." *arXiv:2602.07624*.

**Relevance**: Dual-layer memory: RawMessageStore (immutable log) + SemanticMemoryStore (high-level observations). Validates our STM (raw observations) + LTM (semantic beliefs) separation.

### 3.11 MemGPT / Letta

**Packer et al. (2023)**. "MemGPT: Towards LLMs as Operating Systems."

**Relevance**: Virtual context management with tiered memory (in-context core memory vs. out-of-context archival). Demonstrates the value of separating active/working memory from long-term storage.

---

## 4. Architecture Overview

### 4.1 High-Level Design

```
                    ┌───────────────────────────────────────────┐
    Voice ──────┐   │     SHORT-TERM MEMORY GRAPH (STM)         │
    Posts ──────┤   │     Collections: stm_observations,         │
    Chat  ──────┤──▶│                  stm_edges                │
    Actions ────┤   │     Rolling 2-week window (TTL)           │
    Platforms ──┘   │     Raw, timestamped, per-observation     │
                    │     Written REAL-TIME by Classification    │
                    │     Agent after each event                │
                    └──────────────┬────────────────────────────┘
                                   │
                     ── ── ── ── ──┤── ── ── ── ── ── ── ── ──
                     Async batch   │  Every 24-48 hours
                     (not per      │  (scheduled Lambda)
                      conversation)│
                                   │
                    ┌──────────────▼────────────────────────────┐
                    │     CONSOLIDATION AGENT (LLM)             │
                    │                                           │
                    │  Sees ALL accumulated STM for the user    │
                    │  across all conversations and sources.    │
                    │  Makes holistic decisions about:          │
                    │  • Bayesian belief updates (α, β)         │
                    │  • Salience and stability                 │
                    │  • Pending → active promotion             │
                    │  • Narrative descriptors                  │
                    │  • Cross-entity patterns                  │
                    │  • Conflict resolution                    │
                    └──────────────┬────────────────────────────┘
                                   │
                    ┌──────────────▼────────────────────────────┐
                    │     LONG-TERM MEMORY GRAPH (LTM)          │
                    │     Collections: graph_nodes (enhanced),   │
                    │                  graph_edges (enhanced)    │
                    │     Permanent Bayesian beliefs             │
                    │     Evidence log (never deleted)           │
                    │     Belief ≠ Salience separation           │
                    └───────────────────────────────────────────┘
```

### 4.2 Key Principles

1. **STM is a buffer, not a store**: Raw observations accumulate in STM. They are NOT the source of truth. They expire after 14 days via TTL.

2. **LTM is the source of truth**: All permanent knowledge lives in LTM. LTM nodes are only modified by the Consolidation Agent (or direct user edits via API).

3. **Belief ≠ Salience**: `belief_strength` (α/(α+β)) is permanent — it only changes with new evidence, never decays. `salience` is temporal — it decays without reinforcement, representing "how relevant is this right now?"

4. **Evidence is permanent**: The `evidence_log` on each LTM node is append-only. We never lose information about past observations. This is how the 6-month trekking gap works — the first observation is preserved in evidence_log even after the STM observation expires.

5. **All decisions are agentic**: Classification (at extraction time) and consolidation (at batch time) are LLM-driven. The observation ontology is a shared vocabulary, not a rule engine.

6. **Consolidation is batch, not per-event**: The Consolidation Agent runs once every 24-48 hours, seeing ALL accumulated evidence across conversations and sources. This enables cross-channel and cross-conversation reasoning.

7. **Backwards compatible**: New Bayesian fields are additive. `belief_strength` is dual-written to `strength`. `edge_strength` is dual-written to `weight`. Existing code continues to work.

---

## 5. Short-Term Memory Graph (STM)

**Cognitive analogy**: Hippocampus — fast encoding of individual experiences.

### 5.1 Collection: `stm_observations`

```python
{
    "id": str,                        # UUID
    "user_id": str,
    "avatar_id": str,

    # What was observed
    "entity_label": str,              # e.g., "trekking", "born in india", "sarah"
    "entity_type": str,               # From EntityType enum
    "display_label": str,             # Human-readable form
    "observation_subtype": str,       # From ObservationSubtype enum — THE key classification

    # Observation metadata
    "observation_type": str,          # "new" | "correction" | "removal"
    "source": str,                    # "voice" | "post" | "chat" | "platform_spotify" | "manual"
    "session_id": str,                # Links to specific conversation/session
    "raw_evidence": str,              # Exact quote from conversation
    "details": str,                   # Additional context

    # Agent-determined signals
    "confidence": float,              # 0.0-1.0, calibrated by Classification Agent
    "evidence_weight": float,         # 0.0-3.0, determined by Classification Agent (NOT a lookup)
    "sentiment": float,               # -1.0 to 1.0
    "reasoning": str,                 # Agent's reasoning for this classification

    # Correction metadata (if applicable)
    "corrects": str,                  # Label of entity being corrected

    # Temporal
    "observed_at": datetime,          # When this was observed
    "expires_at": datetime,           # observed_at + 14 days (MongoDB TTL index)

    # Consolidation tracking
    "consolidated": bool,             # Has this been processed by consolidation?
    "consolidated_at": datetime,      # When
}
```

### 5.2 Collection: `stm_edges`

```python
{
    "id": str,                        # UUID
    "user_id": str,
    "from_entity_label": str,         # Label-based (not node ID — STM is decoupled from LTM)
    "to_entity_label": str,
    "relationship_hint": str,         # From Classification Agent's co_mentions output
    "source": str,
    "session_id": str,
    "observed_at": datetime,
    "expires_at": datetime,           # TTL
    "consolidated": bool,
}
```

### 5.3 Design Decisions

- **Label-based, not ID-based**: STM observations reference entities by label, not by `graph_node` ID. This decouples STM from LTM. The Consolidation Agent handles entity resolution (matching STM labels to existing LTM nodes).

- **TTL index on `expires_at`**: MongoDB automatically removes documents after 14 days. No manual cleanup.

- **One observation per extraction**: If a user mentions "cooking" twice in one conversation, the Classification Agent may produce one or two observations depending on context. Each observation has its own evidence_weight.

- **`evidence_weight` is LLM-determined**: The Classification Agent reasons about how informative each utterance is. "I was born in India" gets ~2.8. "I went trekking" gets ~0.3. This is NOT a lookup table — the agent considers the full conversational context.

### 5.4 MongoDB Indexes

```javascript
// TTL index for automatic cleanup
db.stm_observations.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })

// Query: unconsolidated observations for a user
db.stm_observations.createIndex({ "user_id": 1, "consolidated": 1, "observed_at": -1 })

// Query: recent observations for GraphRAG recency boost
db.stm_observations.createIndex({ "user_id": 1, "entity_label": 1, "observed_at": -1 })

// TTL for edges
db.stm_edges.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
db.stm_edges.createIndex({ "user_id": 1, "consolidated": 1 })
```

---

## 6. Long-Term Memory Graph (LTM)

**Cognitive analogy**: Neocortex — slow, stable, generalized knowledge.

### 6.1 Enhanced `graph_nodes` Schema

All existing fields are preserved. New fields are additive (backwards compatible):

```python
{
    # ─── EXISTING FIELDS (unchanged) ───
    "id": str,
    "user_id": str,
    "node_type": str,                 # interest, trait, value, connection, experience, preference, demographic
    "label": str,
    "display_label": str,
    "strength": float,                # KEPT for backwards compat — mirrors belief_strength
    "mention_count": int,             # KEPT — mirrors evidence_count
    "properties": dict,
    "created_at": datetime,
    "updated_at": datetime,

    # ─── NEW: Bayesian Belief Parameters ───
    "belief_alpha": float,            # Positive evidence (default: 1.0, uninformative prior)
    "belief_beta": float,             # Negative/absent evidence (default: 1.0)
    "belief_strength": float,         # = α/(α+β) — the system's conviction this is true/relevant
    "belief_variance": float,         # = αβ/((α+β)²(α+β+1)) — uncertainty measure
    "belief_confidence": float,       # Derived: 1 - normalized variance

    # ─── NEW: Evidence Tracking (permanent, never deleted) ───
    "evidence_count": int,            # Total observations ever consolidated
    "evidence_log": [                 # Compact append-only log
        {
            "at": datetime,           # When observed
            "source": str,            # voice, post, chat, etc.
            "weight": float,          # evidence_weight from Classification Agent
            "subtype": str,           # observation_subtype
            "session_id": str,        # Traceability
        }
    ],
    "evidence_sources": [str],        # Unique sources: ["voice", "post", "spotify"]
    "first_evidence_at": datetime,
    "last_evidence_at": datetime,

    # ─── NEW: Frequency Metrics (recomputed at each consolidation) ───
    "mention_frequency": float,       # Observations per 30-day period
    "evidence_span_days": int,        # Days between first and last evidence
    "evidence_pattern": str,          # "single_mention" | "recent_burst" | "regular_interest" |
                                      # "enduring_sporadic" | "active_habit" | "fading"
    "narrative_descriptor": str,      # Natural language: "passionate about", "enjoys occasionally"

    # ─── NEW: Temporal Salience (decays, separate from belief) ───
    "salience": float,                # 0.0-1.0, how prominent RIGHT NOW (decays over time)
    "salience_stability": float,      # S in R=e^{-t/S}, days. Grows with spaced evidence.
    "salience_last_computed": datetime,

    # ─── NEW: Status ───
    "status": str,                    # "pending" | "active" | "fading"
}
```

### 6.2 Critical Design: Belief ≠ Salience

These are two fundamentally different signals:

| | Belief (`belief_strength`) | Salience (`salience`) |
|---|---|---|
| **Question it answers** | "Do we believe this is true about this person?" | "How relevant is this to what's happening right now?" |
| **Changes with** | Only new evidence (Bayesian updates by Consolidation Agent) | Time (exponential decay) and new evidence (reactivation) |
| **Decays?** | **NEVER**. α and β are permanent. | Yes. `salience *= exp(-elapsed / salience_stability)` |
| **Example: "Born in India"** | 0.79 forever (single high-weight observation) | 0.70 initially → decays very slowly (stability=365 days) → still 0.65 after 30 days |
| **Example: "Trekking" (1 mention, 6mo ago)** | 0.57 (unchanged since first observation) | 0.001 (effectively zero — faded from salience) |
| **Example: "Trekking" (mentioned again after 6mo)** | 0.67 (increased with new evidence) | 0.65 (reactivated by new observation) |
| **Used for** | Narrative compilation ("what do we know about this person") | Seed selection in GraphRAG ("what's active/relevant now") |

### 6.3 Enhanced `graph_edges` Schema

```python
{
    # ─── EXISTING FIELDS ───
    "id": str,
    "from_node_id": str,
    "to_node_id": str,
    "relationship_type": str,
    "weight": float,                  # KEPT — mirrors edge_strength
    "properties": dict,
    "created_at": datetime,

    # ─── NEW ───
    "belief_alpha": float,
    "belief_beta": float,
    "edge_strength": float,           # = α/(α+β)
    "valid_from": datetime,           # Bi-temporal (Graphiti-inspired)
    "valid_until": datetime,          # null = still true
    "last_evidence_at": datetime,
    "evidence_count": int,
    "user_id": str,                   # For user-scoped edge queries
}
```

### 6.4 Enhanced Indexes

```javascript
db.graph_nodes.createIndex({ "user_id": 1, "belief_strength": -1 })
db.graph_nodes.createIndex({ "user_id": 1, "status": 1, "salience": -1 })
db.graph_nodes.createIndex({ "user_id": 1, "last_evidence_at": 1 })
db.graph_nodes.createIndex({ "user_id": 1, "node_type": 1, "status": 1 })
```

---

## 7. Observation Ontology

The ontology is a **shared vocabulary** for the Classification and Consolidation agents. It is NOT a rule engine — agents use it as a structured output format while reasoning about each observation individually.

### 7.1 Entity Types

```python
class EntityType(Enum):
    CONNECTION = "connection"       # People in the user's life
    INTEREST = "interest"           # Hobbies, topics, activities
    FACT = "fact"                   # Biographical / identity facts
    TRAIT = "trait"                 # Personality traits
    VALUE = "value"                 # Core values / beliefs
    PREFERENCE = "preference"      # Preferences and opinions
    EXPERIENCE = "experience"      # Life events and experiences
    DEMOGRAPHIC = "demographic"    # Age, location, gender, etc.
```

### 7.2 Observation Subtypes

```python
class ObservationSubtype(Enum):
    # Facts & Identity
    FACT_DECLARATIVE = "fact_declarative"
    # "I was born in India", "I have two kids", "My name is Jai"
    # Permanent identity. Single confident mention is fully sufficient.

    FACT_BIOGRAPHICAL = "fact_biographical"
    # "I work at Google", "I live in San Francisco"
    # Definitive when stated, but can change over time.

    FACT_TEMPORAL = "fact_temporal"
    # "I just moved to NYC", "I started a new job"
    # True at time of statement. May become stale.

    # Connections
    CONNECTION_DEFINITIVE = "connection_definitive"
    # "Sarah is my sister", "My wife Priya"
    # Clear relationship declaration.

    CONNECTION_MENTIONED = "connection_mentioned"
    # "I was talking to John", "Met up with a friend named Rohan"
    # Person exists in their world, relationship unclear.

    # Interests
    INTEREST_EXPLICIT = "interest_explicit"
    # "I love cooking", "Trekking is my passion", "I'm really into chess"
    # Explicit declaration of interest.

    INTEREST_IMPLICIT = "interest_implicit"
    # "I've been cooking a lot lately", "Been reading about AI"
    # Implied through behavior or frequency, not directly declared.

    ACTIVITY_MENTION = "activity_mention"
    # "I went trekking last weekend", "Had sushi for dinner"
    # Single behavioral event. NOT the same as an interest.
    # THE most important distinction in the ontology.

    # Traits
    TRAIT_SELF_DECLARED = "trait_self_declared"
    # "I'm pretty introverted", "I tend to overthink things"
    # User self-labels.

    TRAIT_BEHAVIORAL = "trait_behavioral"
    # Inferred from conversation patterns (observed, not stated).
    # e.g., uses humor frequently → "humorous"

    # Values
    VALUE_EXPLICIT = "value_explicit"
    # "Family means everything to me", "I believe in honesty"
    # Direct value declaration.

    VALUE_IMPLICIT = "value_implicit"
    # Inferred from choices/priorities shown in conversation.
    # "I turned down the promotion to spend more time with kids" → values family

    # Preferences
    PREFERENCE_STATED = "preference_stated"
    # "I prefer window seats", "I don't drink coffee"
    # Explicit preference declaration.

    SENTIMENT_EXPRESSION = "sentiment_expression"
    # "I hate winter", "Mondays are the worst"
    # Emotional opinion, may be transient.

    # Experiences
    EXPERIENCE_SIGNIFICANT = "experience_significant"
    # "I lived in Japan for 3 years", "I survived cancer"
    # Major life events. Single mention is typically sufficient.

    EXPERIENCE_EPISODIC = "experience_episodic"
    # "We went to Goa last summer", "Had a great time at the concert"
    # Specific episodes.

    # Meta
    CORRECTION = "correction"
    # "Not cooking, I meant baking", "Actually I work at Meta, not Google"
    # Explicit correction of previously stored information.

    REMOVAL = "removal"
    # "I don't do that anymore", "I quit smoking"
    # Explicit negation of a previously held attribute.
```

### 7.3 How The Ontology Is Used

The ontology appears in three places:

1. **Classification Agent output**: The agent classifies each observation into entity_type + observation_subtype and determines evidence_weight through reasoning.

2. **STM storage**: `stm_observations.observation_subtype` stores the classification.

3. **Consolidation Agent input**: The agent sees the subtype as context when deciding how to update LTM beliefs. The subtype informs but does not dictate the agent's decision.

The agents are free to reason beyond the ontology. For example, the Classification Agent might note: *"Although this is technically an activity_mention, the user's tone and the word 'again' suggest this is becoming a pattern. I'm giving it a higher evidence_weight than a typical activity_mention."*

---

## 8. Agentic Pipeline — Classification Agent

### 8.1 When It Runs

**Real-time, per event.** After every voice session, post creation, chat batch, or platform import. This replaces the current Extraction Agent + Reasoning Agent.

### 8.2 System Prompt

```
You are a Memory Classification Agent. You analyze conversations and extract
observations about the user, classifying each one precisely.

You understand that different kinds of knowledge carry different epistemological weight:

- A biographical fact stated once ("I was born in India") is near-certain from a
  single utterance.
- An activity mentioned once ("I went trekking") is a behavioral data point, NOT a
  confirmed interest.
- An explicit passion ("I love cooking, it's my life") carries strong interest
  evidence in a single statement.
- A hedged statement ("I think maybe I like hiking") is low-confidence.
- A habitual pattern ("I go running every morning") reveals a committed interest.
- A hypothetical ("I should try yoga someday") is NOT an observation — the user
  hasn't done or committed to anything.

Your job is to reason about EACH extracted entity and produce:
1. The correct entity_type and observation_subtype
2. A calibrated confidence score reflecting linguistic certainty
3. An evidence_weight: YOUR judgment of how much this observation should count
   toward building a long-term belief. This is your assessment of how informative
   this utterance is, not a formula.
4. Brief reasoning explaining your classification

Think about it this way: if you had to bet money on whether this person genuinely
has this attribute/interest/fact, how much would you bet based on this utterance alone?
```

### 8.3 User Prompt Template

```
Analyze this conversation and extract all observations about the USER.

ENTITY TYPES: connection, interest, fact, trait, value, preference, experience, demographic

OBSERVATION SUBTYPES:
[full subtype list with descriptions and examples — see Section 7.2]

EXISTING USER DATA (for detecting corrections/updates):
{existing_data}

CONVERSATION:
---
{conversation}
---

For EACH observation, reason about:
- What exactly did the user say? (quote it)
- What does this tell us about them?
- How certain is this? Definitive vs hedging, past tense vs present, single event vs pattern
- How much should this count as evidence?
- Does this conflict with existing data?

Return JSON:
{
  "observations": [
    {
      "entity_type": "...",
      "observation_subtype": "...",
      "label": "concise lowercase label",
      "display_label": "Human Readable",
      "quote": "exact words from conversation",
      "details": "additional context",
      "confidence": 0.0-1.0,
      "evidence_weight": 0.0-3.0,
      "sentiment": -1.0 to 1.0,
      "observation_type": "new|correction|removal",
      "corrects": "label of entity being corrected, if applicable",
      "reasoning": "1-2 sentences explaining classification and evidence weight"
    }
  ],
  "co_mentions": [
    {
      "entity_a": "label",
      "entity_b": "label",
      "relationship_hint": "how they relate in this conversation"
    }
  ],
  "classification_notes": "overall observations about this conversation's informativeness"
}
```

### 8.4 Model & Parameters

- **Model**: `gpt-4o-mini` (fast, cheap, sufficient for classification)
- **Temperature**: 0.1 (precise classification, not creative)
- **Response format**: `json_object`
- **Single call per event**: Extracts ALL observations from one conversation in one call

### 8.5 Illustrative Examples

**Input**: *"You know, I was born in India, grew up in Kerala actually. I went trekking last weekend with some college friends. Oh and Sarah — she's my sister — she just had a baby!"*

**Output**:
```json
{
  "observations": [
    {
      "entity_type": "fact",
      "observation_subtype": "fact_declarative",
      "label": "born in india",
      "display_label": "Born in India",
      "quote": "I was born in India",
      "confidence": 0.95,
      "evidence_weight": 2.8,
      "observation_type": "new",
      "reasoning": "Definitive birthplace statement. Immutable identity fact — single utterance is complete evidence."
    },
    {
      "entity_type": "fact",
      "observation_subtype": "fact_declarative",
      "label": "grew up in kerala",
      "display_label": "Grew Up in Kerala",
      "quote": "grew up in Kerala actually",
      "confidence": 0.95,
      "evidence_weight": 2.7,
      "reasoning": "Childhood origin. Permanent biographical fact with confident declarative phrasing."
    },
    {
      "entity_type": "interest",
      "observation_subtype": "activity_mention",
      "label": "trekking",
      "display_label": "Trekking",
      "quote": "I went trekking last weekend with some college friends",
      "confidence": 0.8,
      "evidence_weight": 0.3,
      "observation_type": "new",
      "reasoning": "Single past-tense activity with friends. No frequency signal, no enthusiasm declaration. Could be a one-off social activity. Low evidence weight — needs more data to classify as interest."
    },
    {
      "entity_type": "connection",
      "observation_subtype": "connection_definitive",
      "label": "sarah",
      "display_label": "Sarah",
      "details": "Sister, just had a baby",
      "quote": "Sarah — she's my sister — she just had a baby",
      "confidence": 0.95,
      "evidence_weight": 2.5,
      "observation_type": "new",
      "reasoning": "Definitive family relationship with life event detail. High confidence, high weight."
    }
  ],
  "co_mentions": [
    {
      "entity_a": "born in india",
      "entity_b": "grew up in kerala",
      "relationship_hint": "geographic origin — born in India, specifically Kerala"
    },
    {
      "entity_a": "trekking",
      "entity_b": "sarah",
      "relationship_hint": "none — mentioned separately in conversation"
    }
  ]
}
```

---

## 9. Agentic Pipeline — Consolidation Agent

### 9.1 When It Runs

**Batch, every 24-48 hours.** NOT per conversation. Scheduled as a background job.

The Consolidation Agent sees ALL accumulated STM observations for a user across all conversations and sources from the period, enabling cross-channel and cross-conversation reasoning.

### 9.2 System Prompt

```
You are a Memory Consolidation Agent. You are reviewing ALL observations about a user
that accumulated over the past period. This is like "sleeping on it" — you see the full
picture of recent activity, not just a single conversation.

You understand the Bayesian framework:
- Each belief has alpha (positive evidence) and beta (negative evidence)
- belief_strength = alpha / (alpha + beta)
- More evidence = more certainty, but quality matters more than quantity
- Spaced evidence (observations far apart in time) is MORE valuable than clustered evidence
- Belief is PERMANENT — only changes with new evidence
- Salience is TEMPORAL — represents current relevance, fades without reinforcement

You make key decisions for each entity:
1. BELIEF UPDATE: How much to change alpha/beta based on new evidence quality
2. SALIENCE: How prominent should this be right now, and how resistant to fading
3. STATUS: Should "pending" nodes promote to "active" (included in identity narrative)?
4. NARRATIVE: How should this entity be described in the person's identity story?
5. CONFLICT: Does new evidence contradict existing beliefs?

You also look for cross-entity patterns — life changes, shifting interests, emerging themes.
```

### 9.3 User Prompt Template

```
Process all new observations for this user and update their long-term memory.

USER: {user_name} ({user_id})
PERIOD: {period_start} to {period_end}
TOTAL NEW OBSERVATIONS: {total_count}
SOURCES THIS PERIOD: {sources_summary}

Below are all entities with new STM observations, plus active entities with NO new
observations (for salience decay review).

For each entity, you have:
- Current LTM state (null if new entity)
- All new observations from this consolidation period
- Full evidence history across ALL TIME

─────────────────────────────────────
ENTITY: "{label}" (type: {entity_type})

Current LTM:
{ltm_node_json_or_null}

New observations this period ({count}):
{observations_list}

Full evidence history:
{evidence_log}
─────────────────────────────────────

[... repeat for each entity ...]

ACTIVE ENTITIES WITH NO NEW OBSERVATIONS:
(Review these for salience decay or status changes)
{stale_entities_list}

─────────────────────────────────────

For EACH entity, provide your consolidation decision.

Return JSON:
{
  "consolidation_decisions": [
    {
      "entity_label": "...",
      "belief_update": {
        "delta_alpha": float,
        "delta_beta": float,
        "reasoning": "..."
      },
      "salience_update": {
        "new_salience": float,
        "new_stability_days": float,
        "reasoning": "..."
      },
      "status_decision": {
        "new_status": "pending|active|fading",
        "reasoning": "..."
      },
      "frequency_assessment": {
        "evidence_pattern": "single_mention|recent_burst|regular_interest|enduring_sporadic|active_habit|fading",
        "narrative_descriptor": "natural language phrase for narratives",
        "mention_frequency_per_month": float
      },
      "conflict_resolution": {
        "has_conflict": bool,
        "resolution": "..."
      }
    }
  ],
  "cross_entity_observations": "Patterns across entities (life changes, shifting interests, emerging themes)",
  "new_edges_suggested": [
    {
      "from_label": "...",
      "to_label": "...",
      "relationship_type": "...",
      "reasoning": "..."
    }
  ]
}
```

### 9.4 Model & Parameters

- **Model**: `gpt-4o-mini` for routine consolidation
- **Temperature**: 0.2 (thoughtful but not too creative)
- **Response format**: `json_object`
- **Single call per user per consolidation cycle**: All entities batched into one prompt

### 9.5 Consolidation Executor

After the agent returns decisions, a Python executor applies them:

```python
async def apply_consolidation_decisions(self, user_id, decisions):
    """Apply Consolidation Agent's decisions to LTM."""
    now = datetime.now(timezone.utc)

    for decision in decisions["consolidation_decisions"]:
        label = decision["entity_label"]

        # Find or create LTM node
        node = await self.db.graph_nodes.find_one({
            "user_id": user_id, "label": label
        })

        if node:
            # Update existing node
            alpha = node.get("belief_alpha", 1.0) + decision["belief_update"]["delta_alpha"]
            beta = node.get("belief_beta", 1.0) + decision["belief_update"]["delta_beta"]
            belief_strength = alpha / (alpha + beta)
            belief_variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))

            # Append to evidence log
            # (new observations from this consolidation cycle)

            update = {
                "$set": {
                    "belief_alpha": alpha,
                    "belief_beta": beta,
                    "belief_strength": belief_strength,
                    "belief_variance": belief_variance,
                    "belief_confidence": 1.0 - min(1.0, belief_variance * 4),
                    "strength": belief_strength,                  # Backwards compat
                    "salience": decision["salience_update"]["new_salience"],
                    "salience_stability": decision["salience_update"]["new_stability_days"],
                    "salience_last_computed": now,
                    "status": decision["status_decision"]["new_status"],
                    "evidence_pattern": decision["frequency_assessment"]["evidence_pattern"],
                    "narrative_descriptor": decision["frequency_assessment"]["narrative_descriptor"],
                    "mention_frequency": decision["frequency_assessment"]["mention_frequency_per_month"],
                    "last_evidence_at": now,
                    "updated_at": now,
                },
                "$push": {
                    "evidence_log": { "$each": new_evidence_entries }
                },
                "$inc": {
                    "evidence_count": len(new_observations_for_this_entity),
                    "mention_count": len(new_observations_for_this_entity),  # Backwards compat
                }
            }
            await self.db.graph_nodes.update_one({"_id": node["_id"]}, update)

        else:
            # Create new LTM node (pending or active based on agent decision)
            # ... (initial node creation with Bayesian parameters)

    # Apply suggested edges
    for edge_suggestion in decisions.get("new_edges_suggested", []):
        # ... (create graph_edges)

    # Mark STM observations as consolidated
    await self.db.stm_observations.update_many(
        {"user_id": user_id, "consolidated": False},
        {"$set": {"consolidated": True, "consolidated_at": now}}
    )

    # Invalidate caches
    graph_rag = GraphRAG(self.db)
    graph_rag.invalidate_cache(user_id)
```

### 9.6 Salience Decay (Pure Math, No LLM)

Separate from the Consolidation Agent, a lightweight daily job applies temporal decay to salience:

```python
async def apply_salience_decay(self, user_id):
    """Pure math — exponential decay of salience for all active LTM nodes."""
    now = datetime.now(timezone.utc)
    active_nodes = await self.db.graph_nodes.find({
        "user_id": user_id,
        "status": {"$in": ["active", "pending"]},
        "salience": {"$gt": 0.01}
    }).to_list(10000)

    for node in active_nodes:
        last_computed = node.get("salience_last_computed", node.get("updated_at", now))
        elapsed_days = (now - last_computed).total_seconds() / 86400
        stability = node.get("salience_stability", 14.0)
        old_salience = node.get("salience", 0.5)

        # Ebbinghaus-inspired exponential decay
        new_salience = old_salience * math.exp(-elapsed_days / stability)

        await self.db.graph_nodes.update_one(
            {"_id": node["_id"]},
            {"$set": {
                "salience": new_salience,
                "salience_last_computed": now,
            }}
        )
```

This runs daily, is extremely fast (no LLM), and keeps salience current between consolidation cycles.

---

## 10. Read Path — GraphRAG Enhancement

### 10.1 STM Recency Boost

The GraphRAG `get_identity_context()` method reads from **both** LTM and STM:

```python
async def get_identity_context(self, user_id, action_type, ...):
    # Load LTM graph (existing)
    ltm_graph = await self._load_graph(user_id)

    # NEW: Load recent STM observations (last 3 days) for recency signal
    stm_recent = await self._load_recent_stm(user_id, days=3)

    # Select seeds from LTM (existing behavior)
    seeds = self._select_seeds(ltm_graph, action_type, ...)

    # NEW: Boost seeds that have recent STM activity
    for obs in stm_recent:
        label = obs["entity_label"]
        if label in ltm_graph.by_label:
            node_id = ltm_graph.by_label[label]
            recency_hours = (now - obs["observed_at"]).total_seconds() / 3600
            boost = 0.3 * math.exp(-recency_hours / 48)  # 48-hour half-life
            seeds[node_id] = max(
                seeds.get(node_id, 0),
                boost + ltm_graph.node_strength(node_id)
            )

    # Rest of pipeline: spreading activation → BFS → narrative compilation
    # ... (unchanged)
```

This ensures that if someone mentioned "trekking" 2 hours ago in a voice session, it will be prominent in the next voice session's prompt — even before the nightly consolidation runs.

### 10.2 node_strength() Enhancement

```python
def node_strength(self, node_id: str) -> float:
    """Use salience-weighted belief for retrieval prioritization."""
    node = self.nodes.get(node_id)
    if not node:
        return 0.0
    # Prefer salience for retrieval (what's active now)
    salience = node.get("salience")
    if salience is not None:
        return min(float(salience), 1.0)
    # Fall back to belief_strength, then legacy strength
    bs = node.get("belief_strength")
    if bs is not None:
        return min(float(bs), 1.0)
    s = node.get("strength")
    if s is not None:
        return min(float(s), 1.0)
    return min(float(node.get("properties", {}).get("strength", 0.5)), 1.0)
```

### 10.3 Narrative Compilation Enhancement

The `_compile_narrative` method uses `narrative_descriptor` when available:

```python
# In the interests section, instead of just listing labels:

# OLD: "Interests: cooking, trekking, chess, reading"

# NEW (using narrative_descriptor from Consolidation Agent):
for nid, node, act in interests:
    descriptor = node.get("narrative_descriptor", "")
    if descriptor:
        interest_parts.append(descriptor)
    else:
        interest_parts.append(_display(node))

# Result: "passionate about cooking | enjoys trekking occasionally |
#          recently got into chess | long-time reader"
```

### 10.4 Two-Tier Narrative Inclusion

```python
# Tier 1: High-salience nodes — always included (currently active)
# Tier 2: High-belief, low-salience nodes — included if space permits (known but dormant)
# Excluded: pending nodes (insufficient evidence) and fading nodes

for nid, node in graph.nodes.items():
    status = node.get("status", "active")
    if status == "pending":
        continue  # Not enough evidence for narratives
    salience = node.get("salience", 0.5)
    belief = node.get("belief_strength", node.get("strength", 0.5))

    if salience > 0.2:
        tier1.append(nid)    # Currently relevant
    elif belief > 0.5 and status == "active":
        tier2.append(nid)    # Known but dormant
```

---

## 11. Write Path Changes

### 11.1 Voice Memory Pipeline

**Current**: `MemoryOrchestrator` → Extract → Reason → Validate → Execute → writes to `graph_nodes`

**New**: `MemoryOrchestrator` → Classification Agent → Validation → writes to `stm_observations`

Files to modify:
- `backend/domain/voice/memory_orchestrator.py` — Replace `_extraction_agent` + `_reasoning_agent` with Classification Agent; replace `_execute_*` methods with STM writer
- `backend/domain/voice/voice_memory.py` — Replace `_store_to_graph_nodes()` with STM writes

### 11.2 Voice Personality Extraction

**Current**: `_personality_extraction_agent()` writes traits/values directly to `graph_nodes`

**New**: Writes to `stm_observations` with subtypes `trait_behavioral`, `value_implicit`

File: `backend/domain/voice/memory_orchestrator.py`

### 11.3 Post Enrichment

**Current**: `GraphBuilder.enrich_graph_from_post()` writes directly to `graph_nodes`

**New**: Calls Classification Agent on post content → writes to `stm_observations`

File: `backend/domain/graph/builder.py`

### 11.4 Interaction Enrichment

**Current**: `GraphBuilder.enrich_graph_from_interaction()` writes directly to `graph_nodes`

**New**: Writes to `stm_observations`

File: `backend/domain/graph/builder.py`

### 11.5 Profile Creation (EXCEPTION)

**UNCHANGED**: `GraphBuilder.build_graph_from_profile()` continues to write directly to LTM. Profile data is user-verified and doesn't need the STM buffer. New nodes created this way get initial Bayesian parameters: `belief_alpha=3.0`, `belief_beta=1.0`, `status="active"`.

### 11.6 Manual API (EXCEPTION)

**UNCHANGED**: Manual CRUD via `graph_routes.py` continues to write directly to LTM. User-initiated edits are intentional and don't need consolidation review.

### 11.7 Platform Imports

**Current**: `GraphBuilder.add_external_platform_data()` writes directly to `graph_nodes`

**New**: Calls Classification Agent on platform data → writes to `stm_observations`

File: `backend/domain/graph/builder.py`

---

## 12. Scheduling & Timing

### 12.1 Event Timeline

```
    Day 1                       Day 2                       Day 3
    ───────────────────         ───────────────────         ──────────
    Voice session 1 → STM       Voice session 3 → STM
    Post created    → STM       Chat messages   → STM
    Voice session 2 → STM       Platform import → STM       🌙 3:00 AM UTC
                                                             CONSOLIDATION
                                                             (all STM from
                                                              Day 1-3)
                                                             +
                                                             SALIENCE DECAY
                                                             (all active LTM)
```

### 12.2 What Runs When

| Event | Trigger | What Happens | LLM Call? | Latency |
|---|---|---|---|---|
| Voice session ends | `save_transcript` endpoint | Classification Agent → STM write | Yes (gpt-4o-mini) | ~2s async |
| Post created | Post creation hook | Classification Agent → STM write | Yes (gpt-4o-mini) | ~1s async |
| Chat batch | Periodic or on session end | Lightweight classification → STM write | Yes (gpt-4o-mini) | ~1s async |
| Platform import | User connects platform | Classification Agent → STM write | Yes (gpt-4o-mini) | ~2s async |
| **Consolidation** | **Scheduled: daily at 3am UTC** | **Consolidation Agent → LTM updates** | **Yes (gpt-4o-mini)** | **~3-5s per user** |
| **Salience decay** | **Scheduled: daily at 3am UTC** | **Pure math decay on all active nodes** | **No** | **<100ms per user** |
| **Maintenance** | Scheduled: weekly | Archive fading nodes, prune orphan edges | No | ~1s per user |

### 12.3 Consolidation Triggers

```python
# Primary: Scheduled (EventBridge → Lambda)
# Every 24 hours at 3am UTC for all users with unconsolidated STM observations

# Secondary: High-activity threshold (optional)
# If a user accumulates >50 unconsolidated STM observations, trigger early

# Manual: Admin endpoint for testing
# POST /api/admin/consolidate/{user_id}

# NEVER: Per-conversation (this defeats the purpose of the batch design)
```

---

## 13. Migration Strategy

### 13.1 Migrate Existing Nodes to Bayesian Parameters

For each existing `graph_node`, compute initial Bayesian parameters from current data:

```python
async def migrate_node_to_bayesian(node):
    now = datetime.now(timezone.utc)
    strength = node.get("strength", 0.5)
    mention_count = node.get("mention_count", 1)
    node_type = node.get("node_type", "interest")

    # Reconstruct approximate alpha/beta
    total_evidence = max(mention_count, 1)
    alpha = 1.0 + total_evidence * strength
    beta = 1.0 + total_evidence * (1.0 - strength) * 0.5

    # Calculate stability from age and evidence
    created_at = node.get("created_at", now)
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    age_days = max(0, (now - created_at).days)
    stability = min(365.0, 7.0 + total_evidence * 3.0 + age_days * 0.1)

    belief_strength = alpha / (alpha + beta)
    belief_variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))

    return {
        "belief_alpha": alpha,
        "belief_beta": beta,
        "belief_strength": belief_strength,
        "belief_variance": belief_variance,
        "belief_confidence": 1.0 - min(1.0, belief_variance * 4),
        "evidence_count": total_evidence,
        "evidence_log": [{
            "at": node.get("created_at", now),
            "source": node.get("properties", {}).get("source", "migration"),
            "weight": strength,
            "subtype": "migration_initial",
        }],
        "evidence_sources": [node.get("properties", {}).get("source", "unknown")],
        "first_evidence_at": node.get("created_at", now),
        "last_evidence_at": node.get("updated_at", now),
        "mention_frequency": 0,
        "evidence_span_days": age_days,
        "evidence_pattern": "migration",
        "narrative_descriptor": "",      # Will be set by first consolidation
        "salience": belief_strength,     # Initially same as belief
        "salience_stability": stability,
        "salience_last_computed": now,
        "status": "active",             # Existing nodes are considered active
        "strength": belief_strength,     # Backwards compat
    }
```

### 13.2 Migration Script

```python
# backend/scripts/migrate_to_bayesian.py
# Runs once, idempotent (checks for existing belief_alpha before updating)

async def migrate_all_users():
    users = await db.graph_nodes.distinct("user_id")
    for user_id in users:
        nodes = await db.graph_nodes.find(
            {"user_id": user_id, "belief_alpha": {"$exists": False}}
        ).to_list(10000)

        for node in nodes:
            bayesian_fields = await migrate_node_to_bayesian(node)
            await db.graph_nodes.update_one(
                {"_id": node["_id"]},
                {"$set": bayesian_fields}
            )

        print(f"Migrated {len(nodes)} nodes for {user_id}")
```

### 13.3 Edge Migration

```python
# Similar approach for graph_edges — add belief_alpha, belief_beta, edge_strength
async def migrate_edge_to_bayesian(edge):
    weight = edge.get("weight", 0.5)
    return {
        "belief_alpha": 1.0 + weight * 2,
        "belief_beta": 1.0,
        "edge_strength": (1.0 + weight * 2) / (2.0 + weight * 2),
        "valid_from": edge.get("created_at"),
        "valid_until": None,
        "last_evidence_at": edge.get("created_at"),
        "evidence_count": 1,
        "user_id": None,  # Will be inferred from connected nodes
    }
```

### 13.4 Create Collections and Indexes

```javascript
// Create STM collections with TTL indexes
db.createCollection("stm_observations")
db.createCollection("stm_edges")

// All indexes from Sections 5.4 and 6.4
// Run as part of migration script
```

---

## 14. Implementation Phases

### Phase 1: Foundation (Week 1)

| # | Task | Files | Description |
|---|---|---|---|
| 1.1 | Data models | `backend/domain/memory/models.py` (new) | Pydantic models: `STMObservation`, `STMEdge`, `EntityType`, `ObservationSubtype`, `ConsolidationDecision` |
| 1.2 | Schema updates | `backend/api/models.py` | Add Bayesian fields to `GraphNode` and `GraphEdge` Pydantic models |
| 1.3 | GraphRAG node_strength | `backend/domain/graph/rag.py` | Update `node_strength()` to use `salience` → `belief_strength` → `strength` fallback chain |
| 1.4 | Migration script | `backend/scripts/migrate_to_bayesian.py` (new) | Migrate all existing nodes/edges to Bayesian parameters |
| 1.5 | MongoDB indexes | Migration script | Create TTL and query indexes for STM + enhanced LTM indexes |

### Phase 2: Classification Agent (Week 1-2)

| # | Task | Files | Description |
|---|---|---|---|
| 2.1 | Classification Agent | `backend/domain/memory/classification_agent.py` (new) | LLM-powered classification with ontology-structured output |
| 2.2 | STM Writer | `backend/domain/memory/stm_writer.py` (new) | Writes validated observations to `stm_observations` and co-mentions to `stm_edges` |
| 2.3 | Validation layer | `backend/domain/memory/validation.py` (new) | Structural validation (required fields, confidence floor, deletion safety) |
| 2.4 | Voice integration | `backend/domain/voice/memory_orchestrator.py` | Replace extraction + reasoning + execution pipeline with Classification Agent → STM write |
| 2.5 | Voice memory integration | `backend/domain/voice/voice_memory.py` | Replace `_store_to_graph_nodes()` with STM write |
| 2.6 | Personality extraction integration | `backend/domain/voice/memory_orchestrator.py` | `_personality_extraction_agent` → STM write with `trait_behavioral` / `value_implicit` |
| 2.7 | Post enrichment integration | `backend/domain/graph/builder.py` | `enrich_graph_from_post()` → Classification Agent → STM |
| 2.8 | Interaction integration | `backend/domain/graph/builder.py` | `enrich_graph_from_interaction()` → STM |

### Phase 3: Consolidation Agent (Week 2-3)

| # | Task | Files | Description |
|---|---|---|---|
| 3.1 | Consolidation Agent | `backend/domain/memory/consolidation_agent.py` (new) | LLM-powered batch consolidation with full evidence context |
| 3.2 | Entity Resolver | `backend/domain/memory/entity_resolver.py` (new) | Match STM labels to existing LTM nodes (exact + fuzzy) |
| 3.3 | Consolidation Executor | `backend/domain/memory/consolidation_executor.py` (new) | Apply agent decisions to LTM (Bayesian updates, status changes, edge creation) |
| 3.4 | Consolidation Pipeline | `backend/domain/memory/consolidation_pipeline.py` (new) | Orchestrates: gather STM → group → resolve → agent call → execute → mark consolidated → invalidate caches |
| 3.5 | Salience Decay Service | `backend/domain/memory/salience_decay.py` (new) | Pure math daily decay job |
| 3.6 | Scheduler | `backend/domain/memory/consolidation_scheduler.py` (new) | Scheduling logic for daily batch + high-activity threshold |

### Phase 4: Read Path Enhancement (Week 3)

| # | Task | Files | Description |
|---|---|---|---|
| 4.1 | STM recency boost | `backend/domain/graph/rag.py` | Add `_load_recent_stm()`, boost seeds with recent STM activity |
| 4.2 | Narrative compilation | `backend/domain/graph/rag.py` | Use `narrative_descriptor`, two-tier inclusion (salience vs belief), exclude pending |
| 4.3 | Spreading activation | `backend/domain/graph/rag.py` | Use `salience` for seed activation, `belief_confidence` for edge traversal |
| 4.4 | Graph service | `backend/services/graph_service.py` | Expose STM visualization data (recent observations timeline) |

### Phase 5: Infrastructure (Week 3-4)

| # | Task | Files | Description |
|---|---|---|---|
| 5.1 | Lambda trigger | Infrastructure (CDK / EventBridge) | Schedule daily consolidation + decay as EventBridge → Lambda |
| 5.2 | Admin endpoints | `backend/api/admin_routes.py` or similar | `POST /api/admin/consolidate/{user_id}`, `GET /api/admin/stm/{user_id}` |
| 5.3 | Maintenance job | `backend/domain/memory/maintenance.py` (new) | Weekly: archive fading nodes, prune orphan edges |

### Phase 6: Testing & Validation (Week 4)

| # | Task | Files | Description |
|---|---|---|---|
| 6.1 | Unit tests | `backend/scripts/test_bayesian_math.py` (new) | Beta update math, salience decay curves |
| 6.2 | Classification tests | `backend/scripts/test_classification_agent.py` (new) | Verify agent correctly classifies: facts vs activities vs interests vs hypotheticals |
| 6.3 | Consolidation tests | `backend/scripts/test_consolidation_pipeline.py` (new) | STM → consolidation → LTM update → verify state |
| 6.4 | End-to-end test | `backend/scripts/test_dual_memory_e2e.py` (new) | Voice conversation → STM → consolidation → GraphRAG reads correct context |
| 6.5 | Migration dry-run | `backend/scripts/migrate_to_bayesian.py` | Run with `--dry-run` flag to verify migration output |
| 6.6 | Regression tests | Existing test suite | Verify all existing functionality (voice prompt, posts, chat) works with new schema |

---

## 15. Operations & Monitoring

### 15.1 Metrics to Track

| Metric | What It Tells Us | Alert Threshold |
|---|---|---|
| `stm_observations_per_user_per_day` | Write volume | >200 (investigate) |
| `consolidation_duration_seconds` | Pipeline performance | >30s per user |
| `consolidation_success_rate` | Reliability | <95% |
| `nodes_promoted_per_consolidation` | How fast graph grows | Context-dependent |
| `nodes_fading_per_week` | How aggressively we forget | Context-dependent |
| `avg_belief_strength_by_type` | Distribution health | Drift from expected ranges |
| `avg_salience_by_type` | Salience decay working correctly | All near-zero = problem |
| `stm_to_ltm_promotion_rate` | What % of STM observations create/update LTM | <10% or >90% = investigate |
| `entity_resolution_match_rate` | Fuzzy matching quality | <70% = improve resolver |
| `classification_agent_latency_ms` | Real-time path performance | >5000ms |
| `consolidation_agent_latency_ms` | Batch path performance | >15000ms per user |
| `stm_collection_size_per_user` | Storage | >10000 docs |

### 15.2 Logging

Each agent call should log:
- Input token count
- Output token count
- Latency
- Number of observations extracted/decisions made
- Any classification reasoning that seems unusual

### 15.3 Observability Endpoints

```
GET /api/admin/memory/{user_id}/overview
  → { stm_count, ltm_active_count, ltm_pending_count, last_consolidation, ... }

GET /api/admin/memory/{user_id}/stm
  → Recent STM observations with classifications

GET /api/admin/memory/{user_id}/evidence/{label}
  → Full evidence log for a specific entity

POST /api/admin/memory/{user_id}/consolidate
  → Trigger manual consolidation

GET /api/admin/memory/{user_id}/consolidation-log
  → Last consolidation agent output (for debugging)
```

---

## 16. Cost Analysis

### 16.1 Per-Event Cost (Classification Agent)

| Parameter | Value |
|---|---|
| Model | gpt-4o-mini |
| Avg input tokens (system + prompt + conversation) | ~2000 |
| Avg output tokens | ~800 |
| Cost per call | ~$0.0005 |
| Calls per active user per day | ~3-5 (voice sessions + posts) |
| **Daily cost per active user** | **~$0.002** |

### 16.2 Per-Consolidation Cost (Consolidation Agent)

| Parameter | Value |
|---|---|
| Model | gpt-4o-mini |
| Avg input tokens (system + all entities + evidence) | ~4000 |
| Avg output tokens | ~1500 |
| Cost per call | ~$0.001 |
| Calls per active user per day | 1 |
| **Daily cost per active user** | **~$0.001** |

### 16.3 Total Daily Cost

| Component | Per User | 1000 Users |
|---|---|---|
| Classification Agent | $0.002 | $2.00 |
| Consolidation Agent | $0.001 | $1.00 |
| Salience Decay | $0.000 | $0.00 |
| MongoDB (STM reads/writes) | $0.001 | $1.00 |
| **Total** | **$0.004** | **$4.00/day** |

Compared to current system: no meaningful cost increase. The Classification Agent replaces the existing Extraction + Reasoning agents (same model, similar token count). The Consolidation Agent is a new cost but runs once/day.

---

## 17. Design Decisions & Rationale

### 17.1 Why Beta Distribution?

**Alternative**: Simple frequency counting (`mention_count / total_sessions`).

**Why Beta is better**: A node mentioned 1 time in 1 session has frequency 1.0, same as a node mentioned 100 times in 100 sessions. But the first has much higher uncertainty. Beta(2, 1) has mean 0.67 with high variance; Beta(101, 1) has mean 0.99 with near-zero variance. The Beta distribution naturally encodes both the estimate and the uncertainty.

### 17.2 Why Separate STM from LTM?

**Alternative**: Immediately update LTM via Bayesian update on every observation.

**Why separate is better** (CLS theory):
- **Error isolation**: Misheard transcript → temporary STM observation, not permanent LTM corruption
- **Batch efficiency**: One consolidation LLM call per day vs per-event
- **Holistic reasoning**: Consolidation Agent sees cross-conversation patterns
- **Recency signal**: STM provides temporal recency that LTM alone cannot
- **Provenance**: STM links to specific sessions/transcripts

### 17.3 Why 14-Day STM Window?

Based on Ebbinghaus: ~79% of unreinforced info forgotten after 31 days. 14 days captures the most informative recent period while keeping collection small (~100-200 observations per active user). MongoDB TTL handles cleanup.

### 17.4 Why Belief Never Decays?

**Alternative**: Decay alpha/beta over time (original plan).

**Why permanent belief is better**: If someone mentioned trekking once, that's a permanent data point. Decaying alpha loses the information — after 3 months, the system "forgets" the first mention. When they mention it again 6 months later, it treats it as fresh. By keeping alpha permanent and only decaying salience, we preserve the full evidence history while still modeling "what's relevant right now."

### 17.5 Why Daily Consolidation (Not Per-Conversation)?

**Alternative**: Run Consolidation Agent after every voice session.

**Why daily batch is better**:
- Sees cross-conversation patterns ("mentioned cooking in voice, posted food photo, asked about recipe in chat")
- One LLM call per day, not 3-5
- More context per call = better reasoning
- Matches the CLS "sleep consolidation" model

### 17.6 Why Agentic (Not Rule-Based)?

**Alternative**: Hardcoded evidence weights and promotion thresholds per subtype.

**Why agentic is better**: "I went trekking" and "I went trekking again, been doing it every month for a year" are both technically `activity_mention` / `interest_implicit` — but carry radically different evidence weight. An LLM can read the full context and calibrate. Rules cannot handle the combinatorial explosion of linguistic nuance.

### 17.7 What Happens to `identity_memory` Collection?

Gradually superseded by LTM `graph_nodes` (which already stores interests and facts). Keep for backwards compatibility during transition, then deprecate. The data should be migrated to `graph_nodes` as part of Phase 1.

### 17.8 What Happens to `avatar_episodic_memory` and `avatar_action_memory`?

**Unchanged.** These track avatar-level experiences and action patterns, not user-level beliefs. Different purpose, different lifecycle. The `MemoryManager` continues to combine all three memory systems.

### 17.9 Voice Response Latency Impact

**Read path**: One additional MongoDB query (~20-50 STM docs, <5ms). Negligible vs existing 4.5s timeout.

**Write path**: Classification Agent writes to STM (inserts, no upsert checks) — actually faster than current direct graph writes. Consolidation is fully async.

---

## Appendix A: File Inventory

### New Files to Create

| File | Purpose |
|---|---|
| `backend/domain/memory/__init__.py` | Package init |
| `backend/domain/memory/models.py` | Pydantic models for STM, consolidation |
| `backend/domain/memory/classification_agent.py` | Classification Agent (extraction-time LLM) |
| `backend/domain/memory/stm_writer.py` | STM observation writer |
| `backend/domain/memory/validation.py` | Structural validation |
| `backend/domain/memory/consolidation_agent.py` | Consolidation Agent (batch LLM) |
| `backend/domain/memory/consolidation_executor.py` | Apply consolidation decisions to LTM |
| `backend/domain/memory/consolidation_pipeline.py` | Full pipeline orchestration |
| `backend/domain/memory/consolidation_scheduler.py` | Scheduling logic |
| `backend/domain/memory/entity_resolver.py` | STM label → LTM node matching |
| `backend/domain/memory/salience_decay.py` | Pure math decay service |
| `backend/domain/memory/maintenance.py` | Weekly maintenance (archive, prune) |
| `backend/scripts/migrate_to_bayesian.py` | One-time migration script |
| `backend/scripts/test_bayesian_math.py` | Unit tests |
| `backend/scripts/test_classification_agent.py` | Classification tests |
| `backend/scripts/test_consolidation_pipeline.py` | Consolidation tests |
| `backend/scripts/test_dual_memory_e2e.py` | End-to-end tests |

### Files to Modify

| File | Changes |
|---|---|
| `backend/api/models.py` | Add Bayesian fields to GraphNode, GraphEdge models |
| `backend/domain/graph/rag.py` | STM recency boost, node_strength fallback, narrative descriptors, two-tier inclusion |
| `backend/domain/graph/builder.py` | `enrich_graph_from_post()` and `enrich_graph_from_interaction()` → STM writes |
| `backend/domain/voice/memory_orchestrator.py` | Replace extraction/reasoning/execution with Classification Agent → STM |
| `backend/domain/voice/voice_memory.py` | Replace `_store_to_graph_nodes()` with STM write |
| `backend/services/graph_service.py` | Add STM visualization endpoint |
| `backend/api/voice_routes.py` | Remove per-conversation consolidation trigger (if any) |

### Files Unchanged

| File | Reason |
|---|---|
| `backend/domain/avatar/memory/memory_manager.py` | Still combines graph + action + episodic. Reads from enhanced LTM. |
| `backend/domain/avatar/memory/action_memory.py` | Avatar-level procedural memory, separate concern |
| `backend/domain/avatar/memory/episodic_memory.py` | Avatar-level experiential memory, separate concern |
| `backend/domain/voice/prompt_generator.py` | Calls `graph_rag.get_identity_context()` which handles everything |
| `backend/domain/avatar/orchestration/post_orchestrator.py` | Calls `graph_rag.get_identity_context()` |
| `backend/domain/voice/voice_config.py` | MCP tools unchanged |
| `backend/domain/voice/conversation_recall.py` | Conversation recall unchanged |
| `backend/api/graph_routes.py` | Manual CRUD still writes directly to LTM (intentional user edits) |

---

## Appendix B: The Trekking Saga (Complete Walk-Through)

This traces a single entity ("trekking") through the full lifecycle across 6 months to demonstrate every component working together.

### Day 0: Voice Session

**User says**: *"I went trekking last weekend with some college friends"*

**Classification Agent** extracts:
```
entity_type: interest
observation_subtype: activity_mention
label: "trekking"
confidence: 0.8
evidence_weight: 0.3
reasoning: "Single past-tense activity mention. No frequency signal, no enthusiasm.
            Low evidence weight — could be a one-off."
```

**STM Write**: One `stm_observations` document created. `expires_at` = Day 14.

### Day 1: Nightly Consolidation

**Consolidation Agent** sees:
- Entity "trekking": 1 new observation, no existing LTM node
- Evidence weight: 0.3

**Agent decides**:
```
belief_update: delta_alpha=0.3, delta_beta=0.0
  → LTM node: Beta(1.3, 1.0), belief_strength=0.565
salience: 0.4, stability=10 days
status: "pending"
  reasoning: "One activity mention insufficient for identity. Need explicit declaration
              or repeated mentions."
evidence_pattern: "single_mention"
narrative_descriptor: "" (not in narratives — pending)
```

**LTM node created** with `status: "pending"`. Not included in any identity narratives.

### Day 14: STM Expires

STM observation auto-deleted by TTL index. **LTM node persists** with `evidence_log` intact.

### Days 15-179: Salience Decays

Daily salience decay: `salience *= exp(-1/10)`. By Day 30: ~0.05. By Day 60: ~0.001.

`belief_alpha` (1.3) and `belief_beta` (1.0) are **unchanged**. `evidence_log` still has the Day 0 entry.

### Day 180: Voice Session

**User says**: *"Went trekking again this weekend, the trail was beautiful"*

**Classification Agent** extracts:
```
entity_type: interest
observation_subtype: activity_mention
label: "trekking"
confidence: 0.8
evidence_weight: 0.6
reasoning: "The word 'again' is a frequency signal — indicates recurrence. Plus emotional
            color ('beautiful'). Higher weight than a pure one-off mention."
```

### Day 181: Nightly Consolidation

**Consolidation Agent** sees:
- Entity "trekking": 1 new observation (Day 180)
- Existing LTM: `pending`, `belief_alpha=1.3`, `evidence_count=1`
- Evidence log: `[{Day 0, voice, 0.3, activity_mention}]`
- Evidence span: 180 days

**Agent decides**:
```
belief_update: delta_alpha=0.8, delta_beta=0.0
  reasoning: "Second observation after 6-month gap. The word 'again' confirms
              recurring activity. The 180-day span between observations is MORE
              valuable than two mentions in the same week — evidence of genuine
              persistence. Giving higher delta than raw weight."
  → LTM node: Beta(2.1, 1.0), belief_strength=0.677

salience: 0.65, stability=50 days
  reasoning: "Just mentioned so fully reactivated. The 6-month evidence span earns
              substantial stability — this persisted across seasons."

status: "active"
  reasoning: "Two activity mentions spanning 6 months with 'again' signal = sufficient
              evidence of genuine recurring interest. Promoting to active identity."

evidence_pattern: "enduring_sporadic"
narrative_descriptor: "enjoys trekking occasionally"
```

**LTM node updated** to `status: "active"`. Now appears in identity narratives.

### Contrast: "I was born in India" (Day 0)

**Classification Agent**: `evidence_weight: 2.8, observation_subtype: fact_declarative`

**Consolidation Agent**: `delta_alpha=2.8 → Beta(3.8, 1.0), belief_strength=0.79, status=active, stability=365 days, narrative_descriptor="born in India"`

**Immediate promotion.** In identity narratives from Day 1. Salience barely decays over a full year.

---

## Appendix C: Complete Collection Audit & Integration Map

This section maps EVERY memory-related MongoDB collection in NeuralLinks to its role in the dual-memory architecture: what changes, what stays, what gets deprecated, and what gets unified.

### C.1 The Full Collection Landscape

There are **22 memory/state collections** in the system. They fall into five categories:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IDENTITY KNOWLEDGE (about the user)              │
│                                                                     │
│   graph_nodes ──────── THE LTM (enhanced with Bayesian params)     │
│   graph_edges ──────── THE LTM (enhanced)                          │
│   knowledge_graph ──── PARALLEL GRAPH (MCP tools) ⚠️ MUST UNIFY   │
│   identity_memory ──── LEGACY STORE ⚠️ DEPRECATE                   │
│   users.connections ── DUPLICATE ⚠️ CLARIFY                        │
│                                                                     │
│   NEW: stm_observations ── THE STM                                 │
│   NEW: stm_edges ────────── THE STM                                │
├─────────────────────────────────────────────────────────────────────┤
│                    CONVERSATION MEMORY (what was said)              │
│                                                                     │
│   episodic_memory ──────── Voice conversation summaries            │
│   conversation_index ───── Lightweight index + S3 keys             │
│   voice_transcripts ────── Session metadata + processing status    │
│   S3 transcripts ───────── Full conversation text (external)       │
├─────────────────────────────────────────────────────────────────────┤
│                    AVATAR STATE (how the avatar behaves)            │
│                                                                     │
│   avatar_episodic_memory ── Avatar experiences & emotions          │
│   avatar_action_memory ──── Action patterns & outcomes             │
│   avatar_state_history ──── State machine transitions              │
│   avatar_personality_prompts ── Cached personality (24h TTL)       │
│   avatar_style_profiles ──── Writing style learned from posts      │
├─────────────────────────────────────────────────────────────────────┤
│                    RELATIONSHIP STATE (user ↔ avatar bond)         │
│                                                                     │
│   bonding_states ────────── Bond strength, trust, satisfaction     │
│   bonding_sessions ──────── Session-level bonding records          │
│   bond_moments ──────────── Significant closeness events           │
│   reflection_logs ───────── Avatar learnings & reflections         │
├─────────────────────────────────────────────────────────────────────┤
│                    INTELLIGENCE SYSTEMS (what to ask/surface)       │
│                                                                     │
│   avatar_knowledge_gaps ──── Coverage tracking & question queue    │
│   avatar_post_insights ───── Post-derived conversation threads     │
└─────────────────────────────────────────────────────────────────────┘
```

### C.2 Critical Issue: The `knowledge_graph` Parallel Store

**Discovery**: The MCP tools (`memory_tools.py`, `tools.py`, `discovery_tools.py`) and workflow engines (`matchfinding_engine.py`) read and write a collection called `knowledge_graph` — this is a **completely separate collection** from `graph_nodes`.

**The problem**: Two parallel graph stores with different schemas:

| | `graph_nodes` (identity graph) | `knowledge_graph` (MCP/workflow) |
|---|---|---|
| **Schema field for type** | `node_type` | `type` |
| **Written by** | Voice memory, Graph builder, Memory orchestrator, Manual API | MCP memory tools (chat-based) |
| **Read by** | GraphRAG, Voice prompt, Post/Chat orchestrators, Graph visualization | MCP tools, Discovery tools, Matchfinding engine, Serendipity engine |
| **Used in** | Identity narratives, personality profiles | Workflow context, compatibility matching |

**Additionally**, `serendipity_engine.py` and `recap_generator.py` read from `knowledge_graph_nodes` (with `node_type` field) — this appears to be yet another name, possibly intended to be `graph_nodes` but pointing to a different collection due to a naming inconsistency.

**Impact**: When the voice system learns that a user likes "cooking" and writes it to `graph_nodes`, the MCP tools that read from `knowledge_graph` don't see it. When the MCP chat tool learns about a user's interest and writes to `knowledge_graph`, the voice system's GraphRAG doesn't see it. **Knowledge is siloed.**

**Resolution in dual-memory architecture**:

1. **All write paths → STM**: Both the voice pipeline AND the MCP memory tools should write to `stm_observations`. The Classification Agent handles both voice transcripts and MCP chat interactions.

2. **Consolidation → `graph_nodes` only**: The single LTM is `graph_nodes`. There is no `knowledge_graph` in the new architecture.

3. **Migration**: Merge existing `knowledge_graph` documents into `graph_nodes` (mapping `type` → `node_type`). Then update all MCP tool code to read from `graph_nodes` instead.

4. **`knowledge_graph_nodes` references**: Update `serendipity_engine.py` and `recap_generator.py` to read from `graph_nodes`.

**Implementation tasks to add to Phase 2**:

| # | Task | Files |
|---|---|---|
| 2.9 | Merge `knowledge_graph` → `graph_nodes` | Migration script |
| 2.10 | Update MCP memory tools to write to STM | `backend/domain/workflow/mcp/memory_tools.py` |
| 2.11 | Update MCP read tools to query `graph_nodes` | `backend/domain/workflow/mcp/tools.py`, `discovery_tools.py` |
| 2.12 | Update workflow engines to query `graph_nodes` | `backend/domain/workflow/engines/matchfinding_engine.py` |
| 2.13 | Fix `knowledge_graph_nodes` references | `backend/domain/workflow/services/serendipity_engine.py`, `recap_generator.py` |

### C.3 `identity_memory` — Deprecation Path

**Current role**: Stores raw facts and interests extracted from voice conversations. Written by `voice_memory._store_identity_memory()`. Read by `voice_memory._get_identity_memory()` and `personality_prompt._get_identity_memory()`.

**Problem**: Duplicates data already in `graph_nodes`. The same voice extraction writes to both `identity_memory` AND `graph_nodes` via `_store_to_graph_nodes()`.

**Deprecation plan**:

| Phase | Action |
|---|---|
| Phase 1 | Migration script: for any facts/interests in `identity_memory` that don't have corresponding `graph_nodes` entries, create them |
| Phase 2 | Stop writes: `_store_identity_memory()` becomes a no-op (voice pipeline writes to STM only) |
| Phase 2 | Update readers: `voice_memory._get_identity_memory()` and `personality_prompt._get_identity_memory()` → read from `graph_nodes` instead (they already largely do, but with fallback to `identity_memory`) |
| Phase 6 | Verification: confirm no code reads from `identity_memory` |
| Post-launch | Drop collection |

### C.4 `users.connections` — Duplication Resolution

**Current role**: The `connections` array inside the `users` document stores people mentioned in voice conversations. The memory orchestrator writes to BOTH `users.connections` AND `graph_nodes` (as `node_type: "connection"`).

**Problem**: Two sources of truth for the same data. The `users.connections` array has fields like `mentioned_count`, `last_mentioned`, `context` that are not in `graph_nodes`.

**Resolution**:

| Phase | Action |
|---|---|
| Phase 2 | Voice pipeline writes connection observations to STM only (not to `users.connections` directly) |
| Phase 3 | Consolidation Agent creates/updates connection nodes in `graph_nodes` (LTM) with all metadata (relationship, details, mention context) |
| Phase 2 | Migration: Ensure all `users.connections` entries have corresponding `graph_nodes` entries |
| Ongoing | `users.connections` is kept as a **read-optimized denormalization** — the consolidation executor writes to both `graph_nodes` (source of truth) and `users.connections` (for quick access by social features). This is a deliberate dual-write, not an accidental duplication. |

### C.5 Conversation Memory — Evidence Sources for Consolidation

These collections don't change, but they serve as **additional evidence sources** that the Consolidation Agent can read for context:

| Collection | Role in Consolidation |
|---|---|
| `episodic_memory` | The Consolidation Agent can read recent conversation summaries to understand the context in which entities were mentioned. This is richer than the raw STM observations alone. |
| `conversation_index` | Provides topic lists and emotional tone per conversation, helping the agent assess whether a topic was discussed enthusiastically or in passing. |
| `S3 transcripts` | For conflict resolution: if the agent detects contradictory observations, it can request specific transcript snippets (via `s3_key` in `conversation_index` or `episodic_memory`) to resolve ambiguity. This is a rare, on-demand operation. |

**Implementation**: The Consolidation Pipeline (Phase 3) should optionally load recent `episodic_memory` entries for the user and include them as context in the Consolidation Agent prompt:

```python
# In consolidation_pipeline.py, add to the agent context:
recent_conversations = await db.episodic_memory.find(
    {"user_id": user_id},
    {"_id": 0, "summary": 1, "topics": 1, "emotional_tone": 1, "timestamp": 1}
).sort("timestamp", -1).limit(10).to_list(10)

# Include in the consolidation prompt as:
# RECENT CONVERSATIONS (for context):
# [Day 1] "Discussed cooking and family. Tone: warm, animated."
# [Day 2] "Talked about work stress and upcoming vacation. Tone: mixed."
```

This gives the Consolidation Agent the narrative arc of recent interactions, not just isolated entity observations.

### C.6 Avatar State Collections — Relationship to Dual-Memory

These collections are about how the **avatar** behaves, not about what we **know about the user**. They are separate concerns and remain unchanged:

| Collection | Why It Stays Unchanged |
|---|---|
| `avatar_episodic_memory` | Tracks what the *avatar* experienced (e.g., "posted about cooking and got 5 likes"). This is the avatar's procedural/experiential learning, not user identity knowledge. The `MemoryManager` continues to combine this with the enhanced LTM. |
| `avatar_action_memory` | Tracks action patterns and success rates for the avatar's decision engine. Separate from user identity. |
| `avatar_state_history` | Records avatar state machine transitions (mood, energy, social desire). Not identity knowledge. |
| `avatar_style_profiles` | Writing style learned from user's posts. Already a "consolidated" artifact. Not affected by STM/LTM split. |

### C.7 `avatar_personality_prompts` — Cache Invalidation

**Current**: Cached personality prompt per user with 24-hour TTL. Built from `graph_nodes`, `identity_memory`, `users.connections`, posts, episodic summary, and style profile.

**Change needed**: After the nightly consolidation updates LTM nodes, the personality prompt cache must be invalidated so the next voice session / post generation picks up the updated identity.

**Implementation**: Add to the consolidation executor's post-update step:

```python
# After applying all consolidation decisions for a user:
await self.db.avatar_personality_prompts.delete_one({"user_id": user_id})
```

This forces regeneration on next use with fresh LTM data. Since consolidation runs at 3am and personality prompts are typically needed during user activity hours, the regeneration happens naturally before the next use.

### C.8 `avatar_knowledge_gaps` — Consolidation Feedback Loop

**Current**: Tracks coverage scores across 8 categories and surfaces questions in voice. Updated by `_update_knowledge_gaps()` in the memory orchestrator using keyword matching.

**Enhancement opportunity**: The Consolidation Agent has a holistic view of what was learned about the user in the past 24-48 hours. It can provide a more accurate coverage update than keyword matching.

**Implementation**: Add to the Consolidation Agent's output:

```json
{
  "consolidation_decisions": [...],
  "coverage_updates": {
    "life_narrative": 0.05,
    "values_beliefs": 0.0,
    "interests_passions": 0.10,
    "social_patterns": 0.03,
    ...
  },
  "coverage_reasoning": "User shared significant details about trekking interest
    and family connection (Sarah). Interests and social patterns coverage improved."
}
```

The consolidation executor then applies these coverage updates to `avatar_knowledge_gaps`. This is more accurate than keyword matching because the agent has already deeply reasoned about what was learned.

**Implementation task to add to Phase 3**:

| # | Task | Files |
|---|---|---|
| 3.7 | Add coverage_updates to Consolidation Agent output | `consolidation_agent.py` |
| 3.8 | Apply coverage updates to `avatar_knowledge_gaps` | `consolidation_executor.py` |

### C.9 Relationship State Collections — Future Integration (Not in Scope)

The bonding collections (`bonding_states`, `bonding_sessions`, `bond_moments`, `reflection_logs`) are about the avatar-user relationship dynamic, not user identity. However, there is a future integration opportunity:

- **Bonding → STM evidence**: When `bonding_states.metrics.bond_strength` increases significantly after a conversation about a topic, that's evidence the topic is important to the user. A future enhancement could have the bonding engine write STM observations like `{entity_label: "cooking", observation_subtype: "sentiment_expression", evidence_weight: 0.3, source: "bonding_signal"}`.

- **Reflection logs → Consolidation context**: The avatar's reflections about the user could inform the Consolidation Agent's reasoning. If the avatar reflected "User seems to really care about family," that's a corroborating signal for family-related nodes.

These are not in scope for the initial implementation but represent a natural evolution path.

### C.10 Complete Collection Disposition Table

| Collection | Category | Disposition | Phase |
|---|---|---|---|
| `graph_nodes` | Identity | **ENHANCED** — Bayesian params, evidence log, salience | Phase 1 |
| `graph_edges` | Identity | **ENHANCED** — Bayesian params, temporal awareness | Phase 1 |
| `knowledge_graph` | Identity | **UNIFIED** — Merge into `graph_nodes`, update all readers/writers | Phase 2 |
| `knowledge_graph_nodes` | Identity | **FIX** — Update references to use `graph_nodes` | Phase 2 |
| `identity_memory` | Identity | **DEPRECATE** — Migrate data, stop writes, then drop | Phase 1-2 |
| `users.connections` | Identity | **KEPT AS DENORMALIZATION** — Consolidation dual-writes to both `graph_nodes` and `users.connections` | Phase 3 |
| `stm_observations` | Identity | **NEW** — Short-term memory buffer | Phase 1 |
| `stm_edges` | Identity | **NEW** — Short-term co-occurrence edges | Phase 1 |
| `episodic_memory` | Conversation | **UNCHANGED** — Additional context source for Consolidation Agent | — |
| `conversation_index` | Conversation | **UNCHANGED** — Additional context source for Consolidation Agent | — |
| `voice_transcripts` | Conversation | **UNCHANGED** | — |
| `avatar_episodic_memory` | Avatar State | **UNCHANGED** | — |
| `avatar_action_memory` | Avatar State | **UNCHANGED** | — |
| `avatar_state_history` | Avatar State | **UNCHANGED** | — |
| `avatar_personality_prompts` | Avatar State | **CACHE INVALIDATION** added after consolidation | Phase 3 |
| `avatar_style_profiles` | Avatar State | **UNCHANGED** | — |
| `bonding_states` | Relationship | **UNCHANGED** (future integration opportunity) | — |
| `bonding_sessions` | Relationship | **UNCHANGED** | — |
| `bond_moments` | Relationship | **UNCHANGED** | — |
| `reflection_logs` | Relationship | **UNCHANGED** | — |
| `avatar_knowledge_gaps` | Intelligence | **ENHANCED** — Consolidation Agent provides coverage updates | Phase 3 |
| `avatar_post_insights` | Intelligence | **UNCHANGED** | — |

### C.11 Updated Implementation Phase Tasks

The following tasks are **added** to the implementation phases defined in Section 14:

**Phase 1 (Foundation)** — add:

| # | Task | Files | Description |
|---|---|---|---|
| 1.6 | Migrate `identity_memory` data | `backend/scripts/migrate_to_bayesian.py` | Ensure all facts/interests in `identity_memory` have corresponding `graph_nodes` entries |
| 1.7 | Merge `knowledge_graph` → `graph_nodes` | `backend/scripts/migrate_to_bayesian.py` | Map `type` → `node_type`, merge nodes, deduplicate |

**Phase 2 (Classification Agent)** — add:

| # | Task | Files | Description |
|---|---|---|---|
| 2.9 | Update MCP memory tools write path | `backend/domain/workflow/mcp/memory_tools.py` | Write to STM instead of `knowledge_graph` |
| 2.10 | Update MCP read tools | `backend/domain/workflow/mcp/tools.py`, `discovery_tools.py` | Read from `graph_nodes` instead of `knowledge_graph` |
| 2.11 | Update workflow engines | `backend/domain/workflow/engines/matchfinding_engine.py` | Read from `graph_nodes` |
| 2.12 | Fix `knowledge_graph_nodes` refs | `backend/domain/workflow/services/serendipity_engine.py`, `recap_generator.py` | Point to `graph_nodes` |
| 2.13 | Stop `identity_memory` writes | `backend/domain/voice/voice_memory.py` | `_store_identity_memory()` → no-op or STM write |
| 2.14 | Update `identity_memory` readers | `backend/domain/voice/voice_memory.py`, `backend/domain/avatar/personality/personality_prompt.py` | Read from `graph_nodes` only |

**Phase 3 (Consolidation Agent)** — add:

| # | Task | Files | Description |
|---|---|---|---|
| 3.7 | Coverage updates in consolidation | `backend/domain/memory/consolidation_agent.py` | Add `coverage_updates` to Consolidation Agent output schema |
| 3.8 | Apply coverage to knowledge gaps | `backend/domain/memory/consolidation_executor.py` | Update `avatar_knowledge_gaps` after consolidation |
| 3.9 | Cache invalidation | `backend/domain/memory/consolidation_executor.py` | Delete `avatar_personality_prompts` for user after consolidation |
| 3.10 | Dual-write `users.connections` | `backend/domain/memory/consolidation_executor.py` | When consolidating connection nodes, also update `users.connections` |
| 3.11 | Conversation context for consolidation | `backend/domain/memory/consolidation_pipeline.py` | Load recent `episodic_memory` entries as context for Consolidation Agent |

**Phase 5 (Infrastructure)** — add:

| # | Task | Files | Description |
|---|---|---|---|
| 5.4 | Drop `knowledge_graph` collection | Post-migration verification | After confirming all code reads from `graph_nodes` |
| 5.5 | Drop `identity_memory` collection | Post-migration verification | After confirming no code reads from it |

### C.12 Updated Files to Modify

Adding to Appendix A:

| File | Changes |
|---|---|
| `backend/domain/workflow/mcp/memory_tools.py` | Write to STM instead of `knowledge_graph` |
| `backend/domain/workflow/mcp/tools.py` | Read from `graph_nodes` instead of `knowledge_graph` |
| `backend/domain/workflow/mcp/discovery_tools.py` | Read from `graph_nodes` instead of `knowledge_graph` |
| `backend/domain/workflow/engines/matchfinding_engine.py` | Read from `graph_nodes` instead of `knowledge_graph` |
| `backend/domain/workflow/services/serendipity_engine.py` | Fix `knowledge_graph_nodes` → `graph_nodes` |
| `backend/domain/workflow/services/recap_generator.py` | Fix `knowledge_graph_nodes` → `graph_nodes` |
| `backend/domain/avatar/personality/personality_prompt.py` | Read identity data from `graph_nodes` only (not `identity_memory`) |

### C.13 Data Flow After Full Implementation

```
                         WRITE SOURCES
    ┌─────────────────────────────────────────────────┐
    │  Voice sessions (MemoryOrchestrator)            │
    │  Voice personality extraction                    │
    │  MCP chat memory tools                          │
    │  Post content (GraphBuilder)                    │
    │  User interactions                               │
    │  Platform imports (Spotify, YouTube, etc.)       │
    └─────────────────┬───────────────────────────────┘
                      │ ALL → Classification Agent → STM
                      ▼
    ┌─────────────────────────────────────────────────┐
    │  stm_observations  +  stm_edges                 │
    │  (14-day TTL, raw observations)                 │
    └─────────────────┬───────────────────────────────┘
                      │ Daily batch consolidation
                      ▼
    ┌─────────────────────────────────────────────────┐
    │  Consolidation Agent                            │
    │  Context from: episodic_memory,                 │
    │  conversation_index, evidence_log               │
    └──┬──────────────────────────────────────────────┘
       │
       ├──▶ graph_nodes (LTM — Bayesian, single source of truth)
       ├──▶ graph_edges (LTM — Bayesian, temporal)
       ├──▶ users.connections (denormalized copy for social features)
       ├──▶ avatar_knowledge_gaps (coverage score updates)
       └──▶ avatar_personality_prompts (cache invalidation)

                         READ CONSUMERS
    ┌─────────────────────────────────────────────────┐
    │  GraphRAG (voice, posts, chat, decisions)       │ ← graph_nodes + stm_observations (recency)
    │  MCP tools (workflow, discovery, matching)       │ ← graph_nodes (unified)
    │  Personality prompt generator                    │ ← graph_nodes (via avatar_personality_prompts cache)
    │  Serendipity engine, recap generator            │ ← graph_nodes (fixed references)
    │  Graph visualization (frontend)                 │ ← graph_nodes + graph_edges
    │  Conversation recall                            │ ← episodic_memory + conversation_index (unchanged)
    │  Memory manager (decision engine)               │ ← graph_nodes + avatar_action_memory + avatar_episodic_memory
    └─────────────────────────────────────────────────┘
```

---

## Appendix D: Critical Audit Findings & Corrections

This appendix documents findings from a full code audit of every upstream and downstream dependency of the graph system. Each finding is an inaccuracy, gap, or potential breakage in the plan above, along with the correction.

---

### D.1 FINDING: `integration_routes.py` is a Massive Direct Writer — Missing from Plan

**Severity**: HIGH — Breaks if not addressed.

**Discovery**: `backend/api/integration_routes.py` contains extensive `graph_nodes` write paths for LinkedIn, YouTube (3 separate sync flows), and generic platform imports. These write paths are **completely independent** of `GraphBuilder.add_external_platform_data()`.

**What the plan says**: Section 11.7 lists only `GraphBuilder.add_external_platform_data()` as the platform import write path.

**What actually exists**:

| Write Path in `integration_routes.py` | Node Types Created | Approximate Write Operations |
|---|---|---|
| LinkedIn sync (`sync_linkedin_data`) | `preference` (profession), `experience` (work/education), LLM-extracted entities | ~5-20 inserts per sync |
| YouTube LLM analysis (`sync_youtube_data`) | `interest` (topics), `value`, `trait` from LLM analysis | ~5-15 inserts |
| YouTube watch history upload | `interest` (channels, categories, tags), `preference` (playlists) | ~20-50 inserts per upload |
| YouTube subscriptions | `interest` (channels) | ~10-30 inserts |
| YouTube liked video aggregation | `interest` (categories, tags) | ~10-20 inserts |
| Generic platform import | LLM-extracted entities | Varies |

All of these write directly to `graph_nodes` via `db.graph_nodes.insert_one()` / `update_one()` — bypassing `GraphBuilder` entirely.

**Correction**: Add `integration_routes.py` to the plan:

- **Phase 2**: Redirect all `integration_routes.py` graph writes to use the Classification Agent → STM pipeline. Create a shared utility function like `classify_and_write_to_stm(entities, user_id, avatar_id, source)` that both `GraphBuilder` and `integration_routes.py` call.
- This is actually a significant improvement: currently, YouTube imports create nodes with arbitrary strength values (e.g., `min(count / 10.0, 1.0)`) which pollute the graph. Routing through the Classification Agent gives them proper evidence weights.

**Add to Phase 2 tasks**:

| # | Task | Files | Description |
|---|---|---|---|
| 2.15 | Redirect LinkedIn sync writes to STM | `backend/api/integration_routes.py` | LinkedIn sync → Classification Agent → STM |
| 2.16 | Redirect YouTube sync writes to STM | `backend/api/integration_routes.py` | YouTube sync (all 3 flows) → Classification Agent → STM |
| 2.17 | Redirect generic platform writes to STM | `backend/api/integration_routes.py` | Generic platform import → Classification Agent → STM |
| 2.18 | Create shared STM ingestion utility | `backend/domain/memory/ingestion.py` (new) | Shared `classify_and_ingest(data, user_id, avatar_id, source)` callable from any write path |

**Add to Appendix A — Files to Modify**:

| File | Changes |
|---|---|
| `backend/api/integration_routes.py` | Redirect all `graph_nodes` writes to STM via shared ingestion utility |

---

### D.2 FINDING: Node ID Format Inconsistency

**Severity**: MEDIUM — Affects entity resolution.

**Discovery**: Different write paths generate node IDs in incompatible formats:

| Source | ID Format | Example |
|---|---|---|
| `builder.py` | `uuid4()` | `"a1b2c3d4-e5f6-..."` |
| `graph_routes.py` | `{type}_{user_id}_{label}` | `"interest_abc123_cooking"` |
| `memory_orchestrator.py` | `{type}_{user_id}_{label}` | `"connection_abc123_sarah"` |
| `voice_memory.py` | `{type}_{user_id}_{label}` | `"preference_abc123_born_in"` |
| `integration_routes.py` | Various compound keys | `"interest:youtube_channel_mkbhd"` |
| `apply_verified_graph*.py` | Manually defined per user | Varies |

**Impact on dual-memory**: The Entity Resolver (Section 3.2 in Phase 3) matches STM labels to existing LTM nodes. Since the plan uses **label-based matching** (STM stores `entity_label`, not node IDs), the node ID inconsistency doesn't break entity resolution. However:

1. The Consolidation Executor creates new LTM nodes. It must decide what ID format to use.
2. Duplicate nodes can exist with the same label but different IDs from different sources.

**Correction**: Add to Entity Resolver design:

- Entity Resolver matches by `(user_id, node_type, label)` — not by `id`. This is already how most read-before-write logic works in the codebase.
- When creating new LTM nodes, the Consolidation Executor uses the `{type}_{user_id}_{label}` format (consistent with the majority of write paths).
- As part of Phase 1 migration, deduplicate nodes that share `(user_id, node_type, label)` but have different IDs. Keep the one with the most evidence.

---

### D.3 FINDING: GraphRAG Cache Invalidation Won't Work from Lambda

**Severity**: HIGH — Consolidation results not visible until cache expires.

**Discovery**: GraphRAG has an in-memory cache (`_graph_cache`) with 300-second TTL. The plan's consolidation executor calls `graph_rag.invalidate_cache(user_id)` (Section 9.5). But:

- Consolidation runs as a **scheduled Lambda** (Section 12).
- The backend API server runs as a **separate process** (ECS or another Lambda).
- `invalidate_cache()` only clears the local in-memory dict — it cannot reach the API server's cache.

**What breaks**: After nightly consolidation updates LTM nodes (e.g., promoting "trekking" to `status: "active"`), the API server's GraphRAG cache continues serving stale data for up to 5 minutes.

**Correction**: Three options (pick one):

1. **Reduce cache TTL to 60s** — Simplest. After consolidation runs at 3am, the cache expires naturally before the user's next session. The 5-minute window only matters if the user is active right when consolidation runs.

2. **Add a cache-bust signal** — After consolidation, write a timestamp to a fast-read store (e.g., a `graph_cache_bust` collection). GraphRAG checks this timestamp before serving cached data:
   ```python
   bust_doc = await self.db.graph_cache_bust.find_one({"user_id": user_id})
   if bust_doc and bust_doc["busted_at"] > cached_timestamp:
       self._graph_cache.pop(user_id, None)
   ```

3. **Accept the delay** — Since consolidation runs at 3am UTC (Section 12.1), most users are asleep. The cache expires naturally before their next session.

**Recommendation**: Option 3 (accept the delay) with Option 1 as a safety net. The current 300s TTL is already fine for nightly consolidation. The plan should remove the direct `invalidate_cache()` call from the consolidation executor and instead document this as an accepted latency.

**Update to Section 9.5**: Replace `graph_rag.invalidate_cache(user_id)` with:
```python
# Cache invalidation signal for GraphRAG
# GraphRAG has a 300s in-memory cache. Since consolidation runs at 3am,
# the cache naturally expires before the user's next session.
# For the high-activity early-trigger case, we write a bust signal.
await self.db.graph_cache_bust.update_one(
    {"user_id": user_id},
    {"$set": {"busted_at": now}},
    upsert=True
)
```

---

### D.4 FINDING: `voice_memory._store_to_graph_nodes()` Stores Facts as `node_type: "preference"`

**Severity**: LOW — But Classification Agent must handle this for backwards compatibility.

**Discovery**: In `voice_memory.py` lines 928-1008, facts extracted from voice conversations are stored as `node_type: "preference"` (not `"fact"`). The label is generated by taking the first 4 words of the fact text: `label = " ".join(fact_text.split()[:4]).lower()`.

**Impact**: The Observation Ontology (Section 7) defines `FACT_DECLARATIVE`, `FACT_BIOGRAPHICAL`, etc. as entity types that map to `entity_type: "fact"`. But existing LTM nodes for facts are stored as `"preference"`. The Entity Resolver must handle this mismatch.

**Correction**:

1. The Entity Resolver should map `entity_type: "fact"` observations to LTM nodes with EITHER `node_type: "fact"` OR `node_type: "preference"` (for legacy compatibility).
2. The Phase 1 migration script should re-classify existing `"preference"` nodes that are actually facts (identifiable by `properties.source: "conversation"` and label patterns like "born in", "works at", etc.).
3. Going forward, the Consolidation Executor creates new fact nodes as `node_type: "fact"` (not `"preference"`).

---

### D.5 FINDING: `PerceptionEngine` Directly Reads `graph_nodes` — Not Via GraphRAG

**Severity**: MEDIUM — Not listed in plan, may show stale data.

**Discovery**: `backend/domain/avatar/perception/engine.py` reads `graph_nodes` directly (lines 180-183):

```python
nodes = await self.db.graph_nodes.find(
    {"user_id": avatar_id, "node_type": "interest"},
    {"_id": 0, "label": 1, "properties": 1}
).sort("properties.strength", -1).limit(20).to_list(20)
```

This sorts by `properties.strength` and returns only `label` and `properties`. It also reads friend interest nodes the same way (lines 309-312).

**What the plan says**: Not mentioned. Not in "Files to Modify" or "Files Unchanged" in Appendix A.

**Impact**: After migration, `properties.strength` won't be the right field for sorting. New Bayesian nodes have `strength` (top-level, mirroring `belief_strength`) and `salience`. Sorting by `properties.strength` returns arbitrary/stale values.

**Correction**: Add to Phase 4 (Read Path Enhancement):

| # | Task | Files | Description |
|---|---|---|---|
| 4.5 | Update PerceptionEngine interest sort | `backend/domain/avatar/perception/engine.py` | Sort by `salience` (or `strength` top-level) instead of `properties.strength`. Filter out `status: "pending"` nodes. |

PerceptionEngine also has its own 10-minute interests cache (`_interests_cache`), separate from GraphRAG's cache.

---

### D.6 FINDING: Orchestrator Steps 6-8 Must Continue Running

**Severity**: MEDIUM — Ambiguity in plan.

**Discovery**: The memory_orchestrator runs 8 steps. Steps 1-4 (extraction, reasoning, validation, execution) and step 5 (personality extraction) are replaced by the Classification Agent → STM pipeline. But steps 6, 7, and 8 are:

| Step | What It Does | Collection Written |
|---|---|---|
| 6 | Index conversation for recall | `conversation_index` |
| 7 | Update knowledge gap coverage | `avatar_knowledge_gaps` |
| 8 | Update post insight thread statuses | `avatar_post_insights` |

**What the plan says**: Section 11.1 says to replace the extraction/reasoning/execution pipeline but doesn't explicitly state what happens to steps 6-8.

**Correction**: Steps 6, 7, and 8 MUST continue to run unchanged. They serve different purposes from the identity graph and are not part of the STM/LTM pipeline:

- **Step 6** (conversation indexing): Required for conversation recall. Independent of identity memory.
- **Step 7** (knowledge gaps): Required for voice question selection. Coverage update moves to consolidation (C.8) but the `increment_conversation_count` must still happen per-conversation.
- **Step 8** (post insight threads): Required for proactive voice topics. Independent of identity memory.

**Updated memory_orchestrator pipeline post-migration**:

```
Step 1: Classification Agent (replaces extraction + reasoning)     → STM
Step 2: STM Writer (replaces validation + execution)               → stm_observations, stm_edges
Step 3: Personality extraction → Classification Agent → STM        → stm_observations
Step 4: Conversation indexing (UNCHANGED)                          → conversation_index
Step 5: Knowledge gap increment (UNCHANGED, per-conversation)     → avatar_knowledge_gaps
Step 6: Post insight thread update (UNCHANGED)                     → avatar_post_insights
```

Note that the number of steps reduces from 8 to 6 because extraction+reasoning+validation+execution collapse into Classification Agent + STM Writer.

---

### D.7 FINDING: `apply_verified_graph*.py` Scripts Need Migration Awareness

**Severity**: LOW — Admin scripts, not production paths. But will break if run post-migration.

**Discovery**: The `apply_verified_graph*.py` scripts do `delete_many` + `insert_many` on `graph_nodes`. They insert manually curated nodes with specific fields. After migration, these nodes would lack Bayesian fields (`belief_alpha`, `belief_beta`, `salience`, `status`, etc.).

**Correction**: Two options:

1. **Update scripts**: When inserting verified nodes, include Bayesian fields with strong priors (e.g., `belief_alpha=5.0, belief_beta=1.0, status="active", salience=0.8`). These are human-verified, so they deserve high initial belief.

2. **Post-insert migration**: After running the script, run the Phase 1 migration script on the affected user to populate Bayesian fields.

**Recommendation**: Option 1. Add a utility function `add_bayesian_defaults(node)` that enriches any node dict with proper Bayesian fields. Use it in both the migration script and the verified graph scripts.

**Add to Phase 1 tasks**:

| # | Task | Description |
|---|---|---|
| 1.8 | Create `add_bayesian_defaults()` utility | Reusable function to add Bayesian fields to any node dict, with configurable priors for verified vs. inferred data |

---

### D.8 FINDING: `graph_routes.py` Connection CRUD Dual-Writes to `users.connections` — Plan Needs Explicit Decision

**Severity**: LOW — Plan says "UNCHANGED" which is correct, but reasoning should be explicit.

**Discovery**: `graph_routes.py` (manual API) writes to BOTH `graph_nodes` AND `users.connections` when adding/updating/deleting connections. This is the same dual-write pattern as `memory_orchestrator._execute_connection_action`.

**What the plan says**: Section 11.6 says "Manual API — UNCHANGED." Appendix A says `graph_routes.py` is unchanged.

**Clarification**: This is correct. Manual edits from the user (via the frontend UI) bypass STM because they are **intentional, user-initiated, verified actions**. They should write directly to LTM and to `users.connections`. However:

1. These manual writes should ALSO populate Bayesian fields on the new/updated nodes. Currently they don't include `belief_alpha`, `salience`, etc.
2. Manual additions should get strong priors: `belief_alpha=3.0, belief_beta=1.0, status="active"`.

**Correction**: Add to Phase 1:

| # | Task | Files | Description |
|---|---|---|---|
| 1.9 | Update `graph_routes.py` node writes with Bayesian defaults | `backend/api/graph_routes.py` | All insert/update operations include Bayesian fields. Manual additions get `belief_alpha=3.0, status="active"`. |

---

### D.9 FINDING: Classification Agent Needs Existing Data for Correction Detection

**Severity**: MEDIUM — Functional gap.

**Discovery**: The current `_reasoning_agent` (Step 2 of the orchestrator) calls `_get_existing_data(user_id)` which reads `users.connections` and `graph_nodes` to compare extracted entities against existing data. This is how it detects corrections ("not cooking, I meant baking") and updates vs. new entities.

**What the plan says**: Section 8.3 shows `{existing_data}` in the Classification Agent prompt template, but doesn't specify how this data is gathered.

**Correction**: The Classification Agent must receive existing user data to detect corrections. This means the classification pipeline needs a pre-step:

```python
async def classify_observations(self, user_id, avatar_id, conversation, source):
    # Step 1: Gather existing data for correction detection
    existing = await self._get_existing_context(user_id)
    # Includes: top graph_nodes labels, users.connections names
    
    # Step 2: Call Classification Agent with existing data
    result = await self._call_classification_agent(
        conversation, existing, source
    )
    
    # Step 3: Write to STM
    await self.stm_writer.write(user_id, avatar_id, result, source)
```

This is already implied by the plan's prompt template (`EXISTING USER DATA: {existing_data}`) but should be explicit in the pipeline description. The data should come from `graph_nodes` (active LTM nodes) — NOT from `identity_memory` (which is being deprecated).

---

### D.10 FINDING: `knowledge_graph_nodes` vs `graph_nodes` in Serendipity/Recap — May Be the Same Collection

**Severity**: MEDIUM — Need to verify before planning migration.

**Discovery**: `serendipity_engine.py` and `recap_generator.py` access `self.db.knowledge_graph_nodes` with a `node_type` field (same as `graph_nodes`). This could be:

1. A different collection that happens to use the same schema, OR
2. The same collection accessed via a different name (MongoDB allows accessing the same collection by different names only if explicitly aliased — this is unlikely)

**Most likely**: These are separate collections. `knowledge_graph_nodes` was probably created early in development alongside `graph_nodes`, and these services were never updated.

**Verification needed**: Before migration, run:
```javascript
db.knowledge_graph_nodes.countDocuments({})
db.graph_nodes.countDocuments({})
```
If `knowledge_graph_nodes` is empty or has stale data, the serendipity engine and recap generator are already broken (returning no results). If it has data, it needs to be merged into `graph_nodes`.

**Correction**: Added verification step to Phase 1 migration.

---

### D.11 FINDING: The `strength` Field Dual-Location Pattern Must Be Preserved

**Severity**: MEDIUM — Subtle backwards compatibility issue.

**Discovery**: GraphRAG's `node_strength()` reads `strength` from TWO locations in order:
1. `node["strength"]` (top-level)
2. `node["properties"]["strength"]` (nested, default 0.5)

Different writers store strength differently:

| Writer | `node.strength` | `node.properties.strength` |
|---|---|---|
| `graph_routes.py` | Yes | No |
| `memory_orchestrator.py` | Yes (some paths) | Yes (some paths) |
| `voice_memory.py` | Yes | No |
| `builder.py` | No | Yes |
| `integration_routes.py` | No | Yes |

The plan's Consolidation Executor (Section 9.5) writes `"strength": belief_strength` (top-level only, for backwards compat). This is correct — GraphRAG checks top-level first.

**Potential issue**: For existing nodes created by `builder.py` or `integration_routes.py` that only have `properties.strength`, the migration script must set `strength` (top-level) too. The current migration script (Section 13.1) computes `belief_strength` and sets `"strength": belief_strength` — this is correct.

**No code change needed** — just documenting that the migration correctly handles this.

---

### D.12 FINDING: Missing File in "Files to Modify" — `perception/engine.py`

**Severity**: LOW — But without it, perception results will sort incorrectly post-migration.

**Correction**: Add to Appendix A "Files to Modify":

| File | Changes |
|---|---|
| `backend/domain/avatar/perception/engine.py` | Sort interests by `strength` (top-level, not `properties.strength`). Filter out `status: "pending"` nodes. |

---

### D.13 Summary: Complete Updated File Inventory

After all findings, here is the **corrected, complete** list of files that need changes:

#### Files to Create (17 files — same as original plan)

No changes to the new files list.

#### Files to Modify (14 files — was 7, adding 7 more)

| # | File | Changes | Finding |
|---|---|---|---|
| 1 | `backend/api/models.py` | Add Bayesian fields to GraphNode, GraphEdge models | Original |
| 2 | `backend/domain/graph/rag.py` | STM recency boost, node_strength fallback, narrative descriptors, two-tier inclusion, cache-bust check | Original + D.3 |
| 3 | `backend/domain/graph/builder.py` | `enrich_graph_from_post()` and `enrich_graph_from_interaction()` → STM writes | Original |
| 4 | `backend/domain/voice/memory_orchestrator.py` | Replace steps 1-5 with Classification Agent → STM; keep steps 6-8 unchanged | Original + D.6 |
| 5 | `backend/domain/voice/voice_memory.py` | Replace `_store_to_graph_nodes()` and `_store_identity_memory()` with STM write | Original |
| 6 | `backend/services/graph_service.py` | Add STM visualization endpoint | Original |
| 7 | `backend/api/voice_routes.py` | Remove per-conversation consolidation trigger (if any) | Original |
| **8** | **`backend/api/integration_routes.py`** | **Redirect ALL platform sync writes to STM** | **D.1** |
| **9** | **`backend/api/graph_routes.py`** | **Add Bayesian defaults to all insert/update operations** | **D.8** |
| **10** | **`backend/domain/avatar/perception/engine.py`** | **Sort by `strength` (top-level), filter `status: "pending"`** | **D.5** |
| **11** | **`backend/domain/workflow/mcp/memory_tools.py`** | **Write to STM instead of `knowledge_graph`** | **C.2** |
| **12** | **`backend/domain/workflow/mcp/tools.py`** | **Read from `graph_nodes` instead of `knowledge_graph`** | **C.2** |
| **13** | **`backend/domain/workflow/mcp/discovery_tools.py`** | **Read from `graph_nodes` instead of `knowledge_graph`** | **C.2** |
| **14** | **`backend/domain/workflow/engines/matchfinding_engine.py`** | **Read from `graph_nodes` instead of `knowledge_graph`** | **C.2** |
| **15** | **`backend/domain/workflow/services/serendipity_engine.py`** | **Fix `knowledge_graph_nodes` → `graph_nodes`** | **C.2 / D.10** |
| **16** | **`backend/domain/workflow/services/recap_generator.py`** | **Fix `knowledge_graph_nodes` → `graph_nodes`** | **C.2 / D.10** |
| **17** | **`backend/domain/avatar/personality/personality_prompt.py`** | **Read identity data from `graph_nodes` only (not `identity_memory`)** | **C.3** |

#### Files Unchanged (corrected — removed `graph_routes.py` and `perception/engine.py` from this list)

| File | Reason |
|---|---|
| `backend/domain/avatar/memory/memory_manager.py` | Still combines graph + action + episodic. Reads from enhanced LTM via GraphRAG. |
| `backend/domain/avatar/memory/action_memory.py` | Avatar-level procedural memory, separate concern |
| `backend/domain/avatar/memory/episodic_memory.py` | Avatar-level experiential memory, separate concern |
| `backend/domain/voice/prompt_generator.py` | Calls `graph_rag.get_identity_context()` which handles everything |
| `backend/domain/avatar/orchestration/post_orchestrator.py` | Calls `graph_rag.get_identity_context()` |
| `backend/domain/avatar/orchestration/message_orchestrator.py` | Calls `graph_rag.get_identity_context()` |
| `backend/domain/voice/voice_config.py` | MCP config unchanged |
| `backend/domain/voice/conversation_recall.py` | Conversation recall unchanged |

---

### D.14 Updated Phase Task Summary (All Additions Consolidated)

All tasks added by Appendix C and Appendix D combined:

**Phase 1 (Foundation)** — additional tasks:

| # | Task | Source |
|---|---|---|
| 1.6 | Migrate `identity_memory` data to `graph_nodes` | C.3 |
| 1.7 | Merge `knowledge_graph` → `graph_nodes` | C.2 |
| 1.8 | Create `add_bayesian_defaults()` utility | D.7 |
| 1.9 | Update `graph_routes.py` node writes with Bayesian defaults | D.8 |
| 1.10 | Verify `knowledge_graph_nodes` collection status | D.10 |
| 1.11 | Deduplicate nodes sharing `(user_id, node_type, label)` | D.2 |
| 1.12 | Re-classify `preference` nodes that are actually `fact` | D.4 |

**Phase 2 (Classification Agent)** — additional tasks:

| # | Task | Source |
|---|---|---|
| 2.9 | Update MCP memory tools write path → STM | C.2 |
| 2.10 | Update MCP read tools → `graph_nodes` | C.2 |
| 2.11 | Update workflow engines → `graph_nodes` | C.2 |
| 2.12 | Fix `knowledge_graph_nodes` references | C.2 |
| 2.13 | Stop `identity_memory` writes | C.3 |
| 2.14 | Update `identity_memory` readers in personality_prompt | C.3 |
| 2.15 | Redirect LinkedIn sync writes to STM | D.1 |
| 2.16 | Redirect YouTube sync writes to STM | D.1 |
| 2.17 | Redirect generic platform writes to STM | D.1 |
| 2.18 | Create shared STM ingestion utility | D.1 |
| 2.19 | Add existing data gathering for Classification Agent | D.9 |

**Phase 3 (Consolidation Agent)** — additional tasks:

| # | Task | Source |
|---|---|---|
| 3.7 | Add coverage_updates to Consolidation Agent output | C.8 |
| 3.8 | Apply coverage to knowledge gaps | C.8 |
| 3.9 | Cache invalidation via `graph_cache_bust` collection | C.7 / D.3 |
| 3.10 | Dual-write `users.connections` for connection nodes | C.4 |
| 3.11 | Conversation context for consolidation | C.5 |
| 3.12 | Entity Resolver handles `preference` → `fact` mapping | D.4 |

**Phase 4 (Read Path)** — additional tasks:

| # | Task | Source |
|---|---|---|
| 4.5 | Update PerceptionEngine interest sort and filtering | D.5 |
| 4.6 | Add cache-bust check to GraphRAG `_load_graph()` | D.3 |

**Phase 5 (Infrastructure)** — additional tasks:

| # | Task | Source |
|---|---|---|
| 5.4 | Drop `knowledge_graph` collection (post-verification) | C.2 |
| 5.5 | Drop `identity_memory` collection (post-verification) | C.3 |

---

### D.15 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `integration_routes.py` writes bypass STM | Certain (if not addressed) | HIGH — platform data skips consolidation | D.1: Redirect all writes |
| GraphRAG cache serves stale data post-consolidation | Medium (only if user active at 3am) | LOW — 5-min delay at worst | D.3: Accept + cache-bust signal |
| `PerceptionEngine` sorts by wrong field | Certain (post-migration) | MEDIUM — wrong interest order for decision engine | D.5: Update sort field |
| Entity resolution fails on `preference`/`fact` mismatch | Medium | MEDIUM — duplicate LTM nodes | D.4: Entity Resolver handles both types |
| `knowledge_graph_nodes` has data that gets lost | Low-Medium | MEDIUM — serendipity engine loses context | D.10: Verify and merge |
| `apply_verified_graph*.py` creates nodes without Bayesian fields | Low (admin scripts, rare) | LOW — nodes lack salience/belief | D.7: Update scripts |
| Orchestrator steps 6-8 accidentally removed | Medium (misreading plan) | HIGH — no conversation recall, no knowledge gaps | D.6: Explicitly preserved |

---

*End of Plan*
