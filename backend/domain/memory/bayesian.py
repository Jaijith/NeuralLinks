"""
Bayesian utility functions for the Dual-Memory Architecture.

Provides:
- Default Bayesian field generation for new LTM nodes/edges
- Belief strength / variance / confidence calculations
- Salience decay math (Ebbinghaus-inspired)
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import EvidencePattern, NodeStatus


# ---------------------------------------------------------------------------
# Bayesian math helpers
# ---------------------------------------------------------------------------

def compute_belief_strength(alpha: float, beta: float) -> float:
    """Mean of Beta(alpha, beta) distribution."""
    total = alpha + beta
    if total <= 0:
        return 0.5
    return alpha / total


def compute_belief_variance(alpha: float, beta: float) -> float:
    """Variance of Beta(alpha, beta) distribution."""
    total = alpha + beta
    if total <= 0:
        return 0.25
    return (alpha * beta) / (total ** 2 * (total + 1))


def compute_belief_confidence(alpha: float, beta: float) -> float:
    """
    Confidence score derived from variance.
    Higher alpha+beta → lower variance → higher confidence.
    Returns 0.0 – 1.0 where 1.0 = maximally certain.
    """
    variance = compute_belief_variance(alpha, beta)
    return max(0.0, min(1.0, 1.0 - variance * 4))


def compute_salience_decay(
    old_salience: float,
    elapsed_days: float,
    stability_days: float,
) -> float:
    """
    Ebbinghaus-inspired exponential salience decay.
    R = old_salience * exp(-elapsed / stability)
    """
    if stability_days <= 0:
        stability_days = 1.0
    return old_salience * math.exp(-elapsed_days / stability_days)


# ---------------------------------------------------------------------------
# Default Bayesian fields for new LTM nodes
# ---------------------------------------------------------------------------

# Prior strengths for different creation contexts
UNINFORMATIVE_PRIOR_ALPHA = 1.0
UNINFORMATIVE_PRIOR_BETA = 1.0
VERIFIED_PRIOR_ALPHA = 3.0     # User-verified data (profile, manual edits)
VERIFIED_PRIOR_BETA = 1.0
STRONG_PRIOR_ALPHA = 5.0       # Human-curated data (apply_verified_graph scripts)
STRONG_PRIOR_BETA = 1.0


def add_bayesian_defaults(
    node: Dict[str, Any],
    *,
    prior: str = "uninformative",
    initial_salience: Optional[float] = None,
    initial_stability: float = 14.0,
    status: str = NodeStatus.ACTIVE.value,
    source: str = "unknown",
) -> Dict[str, Any]:
    """
    Enrich a graph_nodes document dict with Bayesian fields.

    This is safe to call on nodes that already have Bayesian fields — it will
    not overwrite existing values.

    Args:
        node: The node document dict.
        prior: "uninformative" (default, from consolidation),
               "verified" (user-verified, profile/manual),
               "strong" (human-curated scripts).
        initial_salience: Override for starting salience.  If None, derived
                          from belief_strength.
        initial_stability: Salience stability in days.
        status: Initial NodeStatus value.
        source: Evidence source label.
    """
    now = datetime.now(timezone.utc)

    if prior == "verified":
        alpha = VERIFIED_PRIOR_ALPHA
        beta = VERIFIED_PRIOR_BETA
    elif prior == "strong":
        alpha = STRONG_PRIOR_ALPHA
        beta = STRONG_PRIOR_BETA
    else:
        alpha = UNINFORMATIVE_PRIOR_ALPHA
        beta = UNINFORMATIVE_PRIOR_BETA

    # Only set fields that don't already exist
    defaults = {}

    if "belief_alpha" not in node:
        defaults["belief_alpha"] = alpha
    if "belief_beta" not in node:
        defaults["belief_beta"] = beta

    eff_alpha = node.get("belief_alpha", defaults.get("belief_alpha", alpha))
    eff_beta = node.get("belief_beta", defaults.get("belief_beta", beta))

    bs = compute_belief_strength(eff_alpha, eff_beta)
    bv = compute_belief_variance(eff_alpha, eff_beta)
    bc = compute_belief_confidence(eff_alpha, eff_beta)

    if "belief_strength" not in node:
        defaults["belief_strength"] = bs
    if "belief_variance" not in node:
        defaults["belief_variance"] = bv
    if "belief_confidence" not in node:
        defaults["belief_confidence"] = bc

    if "evidence_count" not in node:
        defaults["evidence_count"] = node.get("mention_count", 1)
    if "evidence_log" not in node:
        created_at = node.get("created_at", now)
        defaults["evidence_log"] = [{
            "at": created_at if isinstance(created_at, datetime) else now,
            "source": source,
            "weight": node.get("strength", bs),
            "subtype": "migration_initial",
            "session_id": "",
        }]
    if "evidence_sources" not in node:
        defaults["evidence_sources"] = [source]
    if "first_evidence_at" not in node:
        defaults["first_evidence_at"] = node.get("created_at", now)
    if "last_evidence_at" not in node:
        defaults["last_evidence_at"] = node.get("updated_at", now)

    if "mention_frequency" not in node:
        defaults["mention_frequency"] = 0.0
    if "evidence_span_days" not in node:
        defaults["evidence_span_days"] = 0
    if "evidence_pattern" not in node:
        defaults["evidence_pattern"] = EvidencePattern.MIGRATION.value
    if "narrative_descriptor" not in node:
        defaults["narrative_descriptor"] = ""

    sal = initial_salience if initial_salience is not None else bs
    if "salience" not in node:
        defaults["salience"] = sal
    if "salience_stability" not in node:
        defaults["salience_stability"] = initial_stability
    if "salience_last_computed" not in node:
        defaults["salience_last_computed"] = now

    if "status" not in node:
        defaults["status"] = status

    # Backwards compat: mirror belief_strength → strength
    if "strength" not in node:
        defaults["strength"] = bs

    node.update(defaults)
    return node


def add_bayesian_edge_defaults(
    edge: Dict[str, Any],
    *,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enrich a graph_edges document dict with Bayesian fields.
    Safe to call on edges that already have these fields.
    """
    now = datetime.now(timezone.utc)
    weight = edge.get("weight", 0.5)

    defaults = {}
    if "belief_alpha" not in edge:
        defaults["belief_alpha"] = 1.0 + weight * 2
    if "belief_beta" not in edge:
        defaults["belief_beta"] = 1.0

    eff_alpha = edge.get("belief_alpha", defaults.get("belief_alpha", 2.0))
    eff_beta = edge.get("belief_beta", defaults.get("belief_beta", 1.0))

    if "edge_strength" not in edge:
        defaults["edge_strength"] = compute_belief_strength(eff_alpha, eff_beta)
    if "valid_from" not in edge:
        defaults["valid_from"] = edge.get("created_at", now)
    if "valid_until" not in edge:
        defaults["valid_until"] = None
    if "last_evidence_at" not in edge:
        defaults["last_evidence_at"] = edge.get("created_at", now)
    if "evidence_count" not in edge:
        defaults["evidence_count"] = 1
    if "user_id" not in edge and user_id:
        defaults["user_id"] = user_id

    edge.update(defaults)
    return edge
