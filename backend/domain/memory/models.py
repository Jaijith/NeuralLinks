"""
Pydantic models for the Dual-Memory Architecture.

STM (Short-Term Memory): Raw observations with 14-day TTL.
LTM (Long-Term Memory): Bayesian-enhanced graph_nodes / graph_edges.
Consolidation: Agent decisions that transfer STM → LTM.
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict
import uuid


# ---------------------------------------------------------------------------
# Observation Ontology
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """High-level categories for knowledge about a user."""
    CONNECTION = "connection"
    INTEREST = "interest"
    FACT = "fact"
    TRAIT = "trait"
    VALUE = "value"
    PREFERENCE = "preference"
    EXPERIENCE = "experience"
    DEMOGRAPHIC = "demographic"


class ObservationSubtype(str, Enum):
    """
    Fine-grained classification of observations.

    The Classification Agent uses these as structured output categories while
    reasoning about each observation individually. They are a shared vocabulary,
    not a rule engine.
    """
    # Facts & Identity
    FACT_DECLARATIVE = "fact_declarative"
    FACT_BIOGRAPHICAL = "fact_biographical"
    FACT_TEMPORAL = "fact_temporal"

    # Connections
    CONNECTION_DEFINITIVE = "connection_definitive"
    CONNECTION_MENTIONED = "connection_mentioned"

    # Interests
    INTEREST_EXPLICIT = "interest_explicit"
    INTEREST_IMPLICIT = "interest_implicit"
    ACTIVITY_MENTION = "activity_mention"

    # Traits
    TRAIT_SELF_DECLARED = "trait_self_declared"
    TRAIT_BEHAVIORAL = "trait_behavioral"

    # Values
    VALUE_EXPLICIT = "value_explicit"
    VALUE_IMPLICIT = "value_implicit"

    # Preferences
    PREFERENCE_STATED = "preference_stated"
    SENTIMENT_EXPRESSION = "sentiment_expression"

    # Experiences
    EXPERIENCE_SIGNIFICANT = "experience_significant"
    EXPERIENCE_EPISODIC = "experience_episodic"

    # Meta
    CORRECTION = "correction"
    REMOVAL = "removal"


class ObservationType(str, Enum):
    """Whether this observation is new info, a correction, or a removal."""
    NEW = "new"
    CORRECTION = "correction"
    REMOVAL = "removal"


class NodeStatus(str, Enum):
    """LTM node lifecycle status."""
    PENDING = "pending"    # Insufficient evidence for identity narratives
    ACTIVE = "active"      # Confirmed belief, appears in narratives
    FADING = "fading"      # Low salience + low evidence, candidate for archival


class EvidencePattern(str, Enum):
    """How evidence is distributed over time for a given entity."""
    SINGLE_MENTION = "single_mention"
    RECENT_BURST = "recent_burst"
    REGULAR_INTEREST = "regular_interest"
    ENDURING_SPORADIC = "enduring_sporadic"
    ACTIVE_HABIT = "active_habit"
    FADING = "fading"
    MIGRATION = "migration"


# ---------------------------------------------------------------------------
# STM Models
# ---------------------------------------------------------------------------

STM_TTL_DAYS = 14


def _stm_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=STM_TTL_DAYS)


class STMObservation(BaseModel):
    """A single raw observation in Short-Term Memory."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    avatar_id: str

    # What was observed
    entity_label: str
    entity_type: str  # EntityType value
    display_label: Optional[str] = ""
    observation_subtype: str = ""  # ObservationSubtype value

    # Observation metadata
    observation_type: Optional[str] = ObservationType.NEW.value
    source: str  # "voice" | "post" | "chat" | "platform_*" | "manual"
    session_id: Optional[str] = ""
    raw_evidence: Optional[str] = ""
    details: Optional[str] = ""

    # Agent-determined signals
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.5, ge=0.0, le=3.0)
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)
    reasoning: Optional[str] = ""

    # Correction metadata
    corrects: Optional[str] = ""

    # Temporal
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime = Field(default_factory=_stm_expires_at)

    # Consolidation tracking
    consolidated: bool = False
    consolidated_at: Optional[datetime] = None

    def to_mongo(self) -> Dict[str, Any]:
        """Serialize to a MongoDB-ready dict."""
        d = self.model_dump()
        d["entity_label"] = d["entity_label"].lower().strip()
        return d


class STMEdge(BaseModel):
    """A co-mention edge in Short-Term Memory."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    from_entity_label: str
    to_entity_label: str
    relationship_hint: str = ""
    source: str = ""
    session_id: str = ""
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime = Field(default_factory=_stm_expires_at)
    consolidated: bool = False

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["from_entity_label"] = d["from_entity_label"].lower().strip()
        d["to_entity_label"] = d["to_entity_label"].lower().strip()
        return d


# ---------------------------------------------------------------------------
# Evidence Log Entry (embedded in LTM nodes)
# ---------------------------------------------------------------------------

class EvidenceLogEntry(BaseModel):
    """A single entry in the append-only evidence log on an LTM node."""
    at: datetime
    source: str
    weight: float
    subtype: str
    session_id: str = ""


# ---------------------------------------------------------------------------
# Consolidation Models
# ---------------------------------------------------------------------------

class BeliefUpdate(BaseModel):
    """Consolidation Agent's decision on belief parameters."""
    delta_alpha: float = 0.0
    delta_beta: float = 0.0
    reasoning: str = ""


class SalienceUpdate(BaseModel):
    """Consolidation Agent's decision on temporal salience."""
    new_salience: float = 0.5
    new_stability_days: float = 14.0
    reasoning: str = ""


class StatusDecision(BaseModel):
    """Consolidation Agent's decision on node status."""
    new_status: str = NodeStatus.PENDING.value
    reasoning: str = ""


class FrequencyAssessment(BaseModel):
    """Consolidation Agent's assessment of evidence distribution."""
    evidence_pattern: str = EvidencePattern.SINGLE_MENTION.value
    narrative_descriptor: str = ""
    mention_frequency_per_month: float = 0.0


class ConflictResolution(BaseModel):
    """Consolidation Agent's conflict detection output."""
    has_conflict: bool = False
    resolution: str = ""


class ConsolidationDecision(BaseModel):
    """Full consolidation decision for a single entity."""
    entity_label: str
    entity_type: str = ""
    belief_update: BeliefUpdate = Field(default_factory=BeliefUpdate)
    salience_update: SalienceUpdate = Field(default_factory=SalienceUpdate)
    status_decision: StatusDecision = Field(default_factory=StatusDecision)
    frequency_assessment: FrequencyAssessment = Field(
        default_factory=FrequencyAssessment
    )
    conflict_resolution: ConflictResolution = Field(
        default_factory=ConflictResolution
    )


class EdgeSuggestion(BaseModel):
    """A new edge proposed by the Consolidation Agent."""
    from_label: str
    to_label: str
    relationship_type: str
    reasoning: str = ""


class CoverageUpdate(BaseModel):
    """Knowledge gap coverage deltas from consolidation."""
    life_narrative: float = 0.0
    values_beliefs: float = 0.0
    communication_style: float = 0.0
    social_patterns: float = 0.0
    interests_passions: float = 0.0
    emotional_patterns: float = 0.0
    daily_life: float = 0.0
    humor_personality: float = 0.0


class ConsolidationResult(BaseModel):
    """Full output from the Consolidation Agent for one user."""
    consolidation_decisions: List[ConsolidationDecision] = Field(
        default_factory=list
    )
    cross_entity_observations: str = ""
    new_edges_suggested: List[EdgeSuggestion] = Field(default_factory=list)
    coverage_updates: CoverageUpdate = Field(default_factory=CoverageUpdate)
    coverage_reasoning: str = ""


# ---------------------------------------------------------------------------
# Classification Agent Output
# ---------------------------------------------------------------------------

class ClassifiedObservation(BaseModel):
    """A single observation as output from the Classification Agent."""
    model_config = ConfigDict(extra="ignore")

    entity_type: str
    observation_subtype: str = ""
    label: str
    display_label: Optional[str] = ""
    quote: Optional[str] = ""
    details: Optional[str] = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.5, ge=0.0, le=3.0)
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)
    observation_type: Optional[str] = ObservationType.NEW.value
    corrects: Optional[str] = ""
    reasoning: Optional[str] = ""


class CoMention(BaseModel):
    """A co-occurrence relationship between two entities."""
    entity_a: str
    entity_b: str
    relationship_hint: Optional[str] = ""


class ClassificationResult(BaseModel):
    """Full output from the Classification Agent."""
    observations: List[ClassifiedObservation] = Field(default_factory=list)
    co_mentions: List[CoMention] = Field(default_factory=list)
    classification_notes: str = ""
