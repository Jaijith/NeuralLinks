"""
Consolidation Agent — LLM-driven daily batch transfer from STM → LTM.

Runs as a scheduled job (daily / every 2 days). For each user:
1. Gather all unconsolidated STM observations
2. Load current LTM state
3. Ask the LLM to reason holistically about belief updates,
   salience, status transitions, and conflict resolution
4. Return structured ConsolidationResult for the Executor
"""

import json
import logging
from typing import Any, Dict, List

from .models import (
    ConsolidationResult,
    ConsolidationDecision,
    BeliefUpdate,
    SalienceUpdate,
    StatusDecision,
    FrequencyAssessment,
    ConflictResolution,
    EdgeSuggestion,
    CoverageUpdate,
    EntityType,
    ObservationSubtype,
    EvidencePattern,
    NodeStatus,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Memory Consolidation Agent. You work with a dual-memory system:
- Short-Term Memory (STM): Raw observations from the last 14 days
- Long-Term Memory (LTM): Permanent Bayesian knowledge graph

Your job is to analyze ALL recent STM observations for a user and decide how they
should update the LTM. You are performing memory consolidation — the same process
the human brain does during sleep (Complementary Learning Systems theory).

For EACH entity mentioned in the observations, you must decide:

1. BELIEF UPDATE (Bayesian)
   - delta_alpha: How much to increase the "positive evidence" parameter.
     Higher = stronger belief. Range: 0.0 to 3.0.
     A definitive fact like "born in India" deserves delta_alpha=2.5+.
     A single activity mention like "went trekking" deserves delta_alpha=0.2-0.5.
     Repeated mentions with enthusiasm deserve cumulative weight.
   - delta_beta: How much to increase "negative evidence" (usually 0, unless
     there's contradictory information or the observation is very uncertain).
   - Think of it as: alpha / (alpha + beta) = how strongly we believe this.

2. SALIENCE UPDATE
   - new_salience: 0.0-1.0, how "active" and "top of mind" this entity is.
     Recent mentions → high salience. Old, one-time mentions → low salience.
   - new_stability_days: How slowly salience should decay.
     Enduring interests → 180-365 days. Fleeting mentions → 7-30 days.
     Facts → very high stability (365+). Spaced repetition bonus: if evidence
     arrived after a long gap, INCREASE stability significantly.

3. STATUS DECISION
   - "active": Sufficient evidence for identity narratives
   - "pending": Insufficient evidence — not yet ready for narratives
   - "fading": Low salience and low evidence — candidate for archival
   Rules of thumb:
     Facts: active after 1 mention with high confidence
     Interests: active after 2+ mentions or 1 strong explicit mention
     Traits: active after 2+ behavioral signals
     Connections: active after 1 definitive mention

4. FREQUENCY ASSESSMENT
   - evidence_pattern: single_mention | recent_burst | regular_interest |
     enduring_sporadic | active_habit | fading
   - narrative_descriptor: A short phrase for the LLM identity narrative,
     e.g., "passionate trekker", "born in India", "occasional cook"
   - mention_frequency_per_month: estimated monthly mention rate

5. CONFLICT RESOLUTION
   - Detect if observations contradict existing LTM data
   - If yes, explain how to resolve (keep newer, keep both, etc.)

Think holistically: consider cross-entity patterns, not just individual items."""


def _build_consolidation_prompt(
    stm_observations: List[Dict[str, Any]],
    ltm_nodes: List[Dict[str, Any]],
) -> str:
    """Build the user prompt for the Consolidation Agent."""
    entity_types = ", ".join(e.value for e in EntityType)
    patterns = ", ".join(e.value for e in EvidencePattern)

    obs_text = json.dumps(stm_observations[:100], indent=2, default=str)[:8000]
    ltm_text = json.dumps(ltm_nodes[:80], indent=2, default=str)[:6000]

    return f"""Analyze the following STM observations and current LTM state to produce consolidation decisions.

ENTITY TYPES: {entity_types}
EVIDENCE PATTERNS: {patterns}

CURRENT LTM NODES (existing long-term memory):
{ltm_text}

STM OBSERVATIONS (recent short-term observations to consolidate):
{obs_text}

For EACH entity mentioned in the STM observations, provide a consolidation decision.
Also note any NEW entities that don't yet exist in LTM.
Suggest new edges where entities are frequently co-mentioned.

Return JSON:
{{
  "consolidation_decisions": [
    {{
      "entity_label": "lowercase label",
      "entity_type": "connection|interest|fact|trait|value|preference|experience|demographic",
      "belief_update": {{
        "delta_alpha": 0.0-3.0,
        "delta_beta": 0.0-1.0,
        "reasoning": "why this much evidence weight"
      }},
      "salience_update": {{
        "new_salience": 0.0-1.0,
        "new_stability_days": 7.0-365.0,
        "reasoning": "why this salience and stability"
      }},
      "status_decision": {{
        "new_status": "active|pending|fading",
        "reasoning": "why this status"
      }},
      "frequency_assessment": {{
        "evidence_pattern": "single_mention|recent_burst|regular_interest|enduring_sporadic|active_habit|fading",
        "narrative_descriptor": "short phrase for identity narratives",
        "mention_frequency_per_month": 0.0
      }},
      "conflict_resolution": {{
        "has_conflict": false,
        "resolution": ""
      }}
    }}
  ],
  "cross_entity_observations": "holistic observations about this user's patterns",
  "new_edges_suggested": [
    {{
      "from_label": "entity_a",
      "to_label": "entity_b",
      "relationship_type": "co_interest|part_of|related_to",
      "reasoning": "why this edge"
    }}
  ],
  "coverage_updates": {{
    "life_narrative": 0.0,
    "values_beliefs": 0.0,
    "communication_style": 0.0,
    "social_patterns": 0.0,
    "interests_passions": 0.0,
    "emotional_patterns": 0.0,
    "daily_life": 0.0,
    "humor_personality": 0.0
  }},
  "coverage_reasoning": "what new dimensions of the user were revealed"
}}"""


async def run_consolidation_agent(
    openai_client,
    stm_observations: List[Dict[str, Any]],
    ltm_nodes: List[Dict[str, Any]],
) -> ConsolidationResult:
    """
    Run the Consolidation Agent LLM to produce consolidation decisions.
    """
    if not stm_observations:
        return ConsolidationResult()

    try:
        prompt = _build_consolidation_prompt(stm_observations, ltm_nodes)

        from core.config import call_openai_json

        raw_text = await call_openai_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            client=openai_client,
            temperature=0.1,
        )

        raw = json.loads(raw_text)
        return _parse_consolidation_result(raw)

    except Exception as e:
        logger.error(f"Consolidation Agent error: {e}")
        return ConsolidationResult()


def _parse_consolidation_result(raw: Dict[str, Any]) -> ConsolidationResult:
    """Parse the raw LLM JSON output into a validated ConsolidationResult."""
    decisions = []
    for d in raw.get("consolidation_decisions", []):
        try:
            label = (d.get("entity_label") or "").strip().lower()
            if not label:
                continue

            bu = d.get("belief_update") or {}
            su = d.get("salience_update") or {}
            sd = d.get("status_decision") or {}
            fa = d.get("frequency_assessment") or {}
            cr = d.get("conflict_resolution") or {}

            if not isinstance(bu, dict):
                bu = {}
            if not isinstance(su, dict):
                su = {}
            if not isinstance(sd, dict):
                sd = {}
            if not isinstance(fa, dict):
                fa = {}
            if not isinstance(cr, dict):
                cr = {}

            decisions.append(ConsolidationDecision(
                entity_label=label,
                entity_type=d.get("entity_type", "interest"),
                belief_update=BeliefUpdate(
                    delta_alpha=max(0.0, min(3.0, float(bu.get("delta_alpha", 0)))),
                    delta_beta=max(0.0, min(1.0, float(bu.get("delta_beta", 0)))),
                    reasoning=bu.get("reasoning", ""),
                ),
                salience_update=SalienceUpdate(
                    new_salience=max(0.0, min(1.0, float(su.get("new_salience", 0.5)))),
                    new_stability_days=max(1.0, min(365.0, float(su.get("new_stability_days", 14)))),
                    reasoning=su.get("reasoning", ""),
                ),
                status_decision=StatusDecision(
                    new_status=sd.get("new_status", NodeStatus.PENDING.value),
                    reasoning=sd.get("reasoning", ""),
                ),
                frequency_assessment=FrequencyAssessment(
                    evidence_pattern=fa.get("evidence_pattern", EvidencePattern.SINGLE_MENTION.value),
                    narrative_descriptor=fa.get("narrative_descriptor", ""),
                    mention_frequency_per_month=max(0.0, float(fa.get("mention_frequency_per_month", 0))),
                ),
                conflict_resolution=ConflictResolution(
                    has_conflict=bool(cr.get("has_conflict", False)),
                    resolution=cr.get("resolution", ""),
                ),
            ))
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Skipping malformed consolidation decision: {e}")
            continue

    new_edges = []
    for e in raw.get("new_edges_suggested", []):
        try:
            fl = (e.get("from_label") or "").strip().lower()
            tl = (e.get("to_label") or "").strip().lower()
            if fl and tl and fl != tl:
                new_edges.append(EdgeSuggestion(
                    from_label=fl,
                    to_label=tl,
                    relationship_type=e.get("relationship_type", "related_to"),
                    reasoning=e.get("reasoning", ""),
                ))
        except (ValueError, TypeError):
            continue

    cu_raw = raw.get("coverage_updates", {})
    coverage = CoverageUpdate(
        life_narrative=float(cu_raw.get("life_narrative", 0)),
        values_beliefs=float(cu_raw.get("values_beliefs", 0)),
        communication_style=float(cu_raw.get("communication_style", 0)),
        social_patterns=float(cu_raw.get("social_patterns", 0)),
        interests_passions=float(cu_raw.get("interests_passions", 0)),
        emotional_patterns=float(cu_raw.get("emotional_patterns", 0)),
        daily_life=float(cu_raw.get("daily_life", 0)),
        humor_personality=float(cu_raw.get("humor_personality", 0)),
    )

    return ConsolidationResult(
        consolidation_decisions=decisions,
        cross_entity_observations=raw.get("cross_entity_observations", ""),
        new_edges_suggested=new_edges,
        coverage_updates=coverage,
        coverage_reasoning=raw.get("coverage_reasoning", ""),
    )
