"""
Memory domain — Dual-Memory Architecture (STM + LTM)

Short-Term Memory (STM): Rolling 2-week buffer of raw observations.
Long-Term Memory (LTM): Bayesian-enhanced knowledge graph (graph_nodes/graph_edges).
Consolidation Pipeline: Daily batch LLM-driven transfer from STM → LTM.
Salience Decay: Ebbinghaus-inspired exponential decay (no LLM).
Maintenance: Weekly archive fading nodes, prune orphan edges.
"""

from .models import (
    EntityType,
    ObservationSubtype,
    ObservationType,
    NodeStatus,
    EvidencePattern,
    STMObservation,
    STMEdge,
    ClassificationResult,
    ConsolidationResult,
)

from .bayesian import (
    add_bayesian_defaults,
    add_bayesian_edge_defaults,
    compute_belief_strength,
    compute_belief_variance,
    compute_belief_confidence,
    compute_salience_decay,
)

from .ingestion import classify_and_ingest
from .salience_decay import SalienceDecayService
from .consolidation_scheduler import ConsolidationScheduler
from .maintenance import MemoryMaintenance

__all__ = [
    "EntityType",
    "ObservationSubtype",
    "ObservationType",
    "NodeStatus",
    "EvidencePattern",
    "STMObservation",
    "STMEdge",
    "ClassificationResult",
    "ConsolidationResult",
    "add_bayesian_defaults",
    "add_bayesian_edge_defaults",
    "compute_belief_strength",
    "compute_belief_variance",
    "compute_belief_confidence",
    "compute_salience_decay",
    "classify_and_ingest",
    "SalienceDecayService",
    "ConsolidationScheduler",
    "MemoryMaintenance",
]
