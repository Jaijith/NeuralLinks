"""
Validation layer for STM observations.

Structural validation between the Classification Agent output and the STM write.
Filters out empty labels, clamps numeric fields, enforces required fields.
"""

import logging
from typing import List

from .models import ClassifiedObservation, EntityType, ObservationSubtype

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {e.value for e in EntityType}
VALID_SUBTYPES = {s.value for s in ObservationSubtype}
MIN_LABEL_LENGTH = 2
MAX_LABEL_LENGTH = 200
MIN_CONFIDENCE = 0.1


def validate_observations(
    observations: List[ClassifiedObservation],
) -> List[ClassifiedObservation]:
    """
    Filter and clean observations before writing to STM.
    Returns only observations that pass validation.
    """
    valid = []
    for obs in observations:
        label = (obs.label or "").strip().lower()

        if len(label) < MIN_LABEL_LENGTH:
            logger.debug(f"Skipping observation: label too short '{label}'")
            continue
        if len(label) > MAX_LABEL_LENGTH:
            label = label[:MAX_LABEL_LENGTH]

        if obs.entity_type not in VALID_ENTITY_TYPES:
            logger.warning(
                f"Unknown entity_type '{obs.entity_type}' for '{label}' — "
                f"defaulting to 'interest'"
            )
            obs.entity_type = EntityType.INTEREST.value

        if obs.observation_subtype not in VALID_SUBTYPES:
            logger.warning(
                f"Unknown subtype '{obs.observation_subtype}' for '{label}' — "
                f"defaulting to 'activity_mention'"
            )
            obs.observation_subtype = ObservationSubtype.ACTIVITY_MENTION.value

        if obs.confidence < MIN_CONFIDENCE:
            logger.debug(
                f"Skipping observation: confidence {obs.confidence} below "
                f"threshold for '{label}'"
            )
            continue

        obs.label = label
        if not obs.display_label:
            obs.display_label = label.title()

        obs.confidence = max(0.0, min(1.0, obs.confidence))
        obs.evidence_weight = max(0.0, min(3.0, obs.evidence_weight))
        obs.sentiment = max(-1.0, min(1.0, obs.sentiment))

        valid.append(obs)

    dropped = len(observations) - len(valid)
    if dropped:
        logger.info(f"Validation: {len(valid)} passed, {dropped} dropped")

    return valid
