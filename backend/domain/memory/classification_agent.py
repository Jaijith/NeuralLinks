"""
Classification Agent — LLM-powered observation extraction.

Replaces the existing extraction + reasoning agent pipeline.
Runs in real-time per event (voice session, post, chat, platform import).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .models import (
    ClassificationResult,
    ClassifiedObservation,
    CoMention,
    EntityType,
    ObservationSubtype,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Memory Classification Agent. You analyze conversations and extract
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
has this attribute/interest/fact, how much would you bet based on this utterance alone?"""


def _build_user_prompt(
    conversation: str,
    existing_data: Optional[Dict[str, Any]] = None,
    source: str = "voice",
) -> str:
    """Build the user prompt for the Classification Agent."""
    entity_types = ", ".join(e.value for e in EntityType)
    subtypes = "\n".join(f"  {s.value}" for s in ObservationSubtype)

    existing_section = ""
    if existing_data:
        existing_section = f"""
EXISTING USER DATA (for detecting corrections/updates):
{json.dumps(existing_data, indent=2, default=str)[:3000]}
"""

    return f"""Analyze the following content from source "{source}" and extract all observations about the USER.

ENTITY TYPES: {entity_types}

OBSERVATION SUBTYPES:
{subtypes}

{existing_section}

CONTENT:
---
{conversation[:6000]}
---

For EACH observation, reason about:
- What exactly was expressed? (quote it if possible)
- What does this tell us about the user?
- How certain is this? Definitive vs hedging, past tense vs present, single event vs pattern
- How much should this count as evidence?
- Does this conflict with existing data?

Return JSON:
{{
  "observations": [
    {{
      "entity_type": "connection|interest|fact|trait|value|preference|experience|demographic",
      "observation_subtype": "one of the subtypes above",
      "label": "concise lowercase label",
      "display_label": "Human Readable",
      "quote": "exact words from content",
      "details": "additional context",
      "confidence": 0.0-1.0,
      "evidence_weight": 0.0-3.0,
      "sentiment": -1.0 to 1.0,
      "observation_type": "new|correction|removal",
      "corrects": "label of entity being corrected, if applicable",
      "reasoning": "1-2 sentences explaining classification and evidence weight"
    }}
  ],
  "co_mentions": [
    {{
      "entity_a": "label",
      "entity_b": "label",
      "relationship_hint": "how they relate in this content"
    }}
  ],
  "classification_notes": "overall observations about this content's informativeness"
}}"""


async def get_existing_context(
    db,
    user_id: str,
    max_nodes: int = 50,
) -> Dict[str, Any]:
    """
    Gather existing user data for correction detection.
    The Classification Agent needs this to detect updates vs. new info.
    """
    context: Dict[str, Any] = {"interests": [], "connections": [], "facts": [], "traits": []}

    try:
        nodes = await db.graph_nodes.find(
            {"user_id": user_id, "status": {"$ne": "fading"}},
            {"_id": 0, "label": 1, "node_type": 1, "display_label": 1}
        ).sort("salience", -1).limit(max_nodes).to_list(max_nodes)

        for n in nodes:
            nt = n.get("node_type", "")
            label = n.get("display_label") or n.get("label", "")
            if nt == "interest":
                context["interests"].append(label)
            elif nt == "connection":
                context["connections"].append(label)
            elif nt in ("fact", "preference", "demographic"):
                context["facts"].append(label)
            elif nt in ("trait", "value"):
                context["traits"].append(label)
    except Exception as e:
        logger.warning(f"Error loading existing context for classification: {e}")

    # Also load connections from users collection
    try:
        user_doc = await db.users.find_one(
            {"id": user_id}, {"connections": 1}
        )
        if user_doc:
            for conn in user_doc.get("connections", []):
                name = conn.get("name", "")
                if name and name not in context["connections"]:
                    context["connections"].append(name)
    except Exception:
        pass

    return context


async def classify_observations(
    openai_client,
    db,
    user_id: str,
    content: str,
    source: str = "voice",
) -> ClassificationResult:
    """
    Run the Classification Agent on content to extract structured observations.

    Returns a ClassificationResult with all observations and co-mentions.
    """
    if not content or not content.strip():
        return ClassificationResult()

    try:
        existing_data = await get_existing_context(db, user_id)

        prompt = _build_user_prompt(
            conversation=content,
            existing_data=existing_data,
            source=source,
        )

        from core.config import call_openai_json

        raw_text = await call_openai_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=prompt,
            client=openai_client,
            temperature=0.1,
        )

        raw = json.loads(raw_text)
        return _parse_result(raw)

    except Exception as e:
        logger.error(f"Classification Agent error: {e}")
        return ClassificationResult()


def _parse_result(raw: Dict[str, Any]) -> ClassificationResult:
    """Parse the raw LLM JSON output into a validated ClassificationResult."""
    observations = []
    for obs_dict in raw.get("observations", []):
        try:
            label = (obs_dict.get("label") or "").strip()
            if not label:
                continue
            observations.append(ClassifiedObservation(
                entity_type=obs_dict.get("entity_type", "interest"),
                observation_subtype=obs_dict.get("observation_subtype", "activity_mention"),
                label=label.lower(),
                display_label=obs_dict.get("display_label", label.title()),
                quote=obs_dict.get("quote", ""),
                details=obs_dict.get("details", ""),
                confidence=max(0.0, min(1.0, float(obs_dict.get("confidence", 0.5)))),
                evidence_weight=max(0.0, min(3.0, float(obs_dict.get("evidence_weight", 0.5)))),
                sentiment=max(-1.0, min(1.0, float(obs_dict.get("sentiment", 0.0)))),
                observation_type=obs_dict.get("observation_type", "new"),
                corrects=obs_dict.get("corrects", ""),
                reasoning=obs_dict.get("reasoning", ""),
            ))
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Skipping malformed observation: {e}")
            continue

    co_mentions = []
    for cm in raw.get("co_mentions", []):
        try:
            a = (cm.get("entity_a") or "").strip().lower()
            b = (cm.get("entity_b") or "").strip().lower()
            if a and b and a != b:
                co_mentions.append(CoMention(
                    entity_a=a,
                    entity_b=b,
                    relationship_hint=cm.get("relationship_hint", ""),
                ))
        except (ValueError, TypeError):
            continue

    return ClassificationResult(
        observations=observations,
        co_mentions=co_mentions,
        classification_notes=raw.get("classification_notes", ""),
    )
