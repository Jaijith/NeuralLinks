#!/usr/bin/env python3
"""
Classification Agent tests — Phase 6.2

Tests the non-LLM parts of the classification pipeline:
- _parse_result: LLM JSON → ClassificationResult
- _build_user_prompt: generates correct prompt structure
- validation layer: filtering, clamping, edge cases

Usage:
    python -m scripts.test_classification_agent
"""

import sys
import unittest

sys.path.insert(0, ".")

from domain.memory.classification_agent import _parse_result, _build_user_prompt
from domain.memory.validation import validate_observations
from domain.memory.models import (
    ClassifiedObservation,
    EntityType,
    ObservationSubtype,
)


class TestParseResult(unittest.TestCase):
    """Test that _parse_result correctly converts raw LLM JSON."""

    def test_well_formed_observations(self):
        raw = {
            "observations": [
                {
                    "entity_type": "interest",
                    "observation_subtype": "interest_explicit",
                    "label": "cooking",
                    "display_label": "Cooking",
                    "quote": "I love cooking",
                    "details": "mentioned passionately",
                    "confidence": 0.9,
                    "evidence_weight": 2.0,
                    "sentiment": 0.8,
                    "observation_type": "new",
                    "corrects": "",
                    "reasoning": "Explicit passionate statement",
                },
                {
                    "entity_type": "fact",
                    "observation_subtype": "fact_biographical",
                    "label": "born in india",
                    "display_label": "Born in India",
                    "confidence": 0.95,
                    "evidence_weight": 2.5,
                    "sentiment": 0.0,
                    "observation_type": "new",
                    "reasoning": "Direct factual statement",
                },
            ],
            "co_mentions": [
                {
                    "entity_a": "cooking",
                    "entity_b": "india",
                    "relationship_hint": "cultural cuisine",
                }
            ],
            "classification_notes": "User shared personal facts and interests.",
        }

        result = _parse_result(raw)
        self.assertEqual(len(result.observations), 2)
        self.assertEqual(result.observations[0].label, "cooking")
        self.assertEqual(result.observations[0].entity_type, "interest")
        self.assertEqual(result.observations[1].label, "born in india")
        self.assertEqual(len(result.co_mentions), 1)
        self.assertEqual(result.co_mentions[0].entity_a, "cooking")
        self.assertIn("personal facts", result.classification_notes)

    def test_empty_observations(self):
        result = _parse_result({"observations": [], "co_mentions": []})
        self.assertEqual(len(result.observations), 0)

    def test_empty_dict(self):
        result = _parse_result({})
        self.assertEqual(len(result.observations), 0)
        self.assertEqual(len(result.co_mentions), 0)

    def test_missing_label_skipped(self):
        raw = {
            "observations": [
                {"entity_type": "interest", "label": "", "confidence": 0.9},
                {"entity_type": "interest", "label": "chess", "confidence": 0.8},
            ]
        }
        result = _parse_result(raw)
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(result.observations[0].label, "chess")

    def test_confidence_clamping(self):
        raw = {
            "observations": [
                {"entity_type": "interest", "label": "hiking", "confidence": 5.0},
                {"entity_type": "fact", "label": "name is jai", "confidence": -0.5},
            ]
        }
        result = _parse_result(raw)
        self.assertLessEqual(result.observations[0].confidence, 1.0)
        self.assertGreaterEqual(result.observations[1].confidence, 0.0)

    def test_evidence_weight_clamping(self):
        raw = {
            "observations": [
                {"entity_type": "interest", "label": "yoga", "evidence_weight": 10.0},
            ]
        }
        result = _parse_result(raw)
        self.assertLessEqual(result.observations[0].evidence_weight, 3.0)

    def test_co_mention_dedup(self):
        """Identical entity_a and entity_b should be skipped."""
        raw = {
            "observations": [],
            "co_mentions": [
                {"entity_a": "cooking", "entity_b": "cooking", "relationship_hint": "self"},
                {"entity_a": "cooking", "entity_b": "baking", "relationship_hint": "related"},
            ],
        }
        result = _parse_result(raw)
        self.assertEqual(len(result.co_mentions), 1)
        self.assertEqual(result.co_mentions[0].entity_b, "baking")

    def test_malformed_observation_skipped(self):
        raw = {
            "observations": [
                {"entity_type": "interest", "label": "chess", "confidence": "not_a_number"},
                {"entity_type": "interest", "label": "yoga", "confidence": 0.7},
            ]
        }
        result = _parse_result(raw)
        # The malformed one should be skipped gracefully
        self.assertGreaterEqual(len(result.observations), 1)


class TestBuildUserPrompt(unittest.TestCase):
    """Test prompt construction."""

    def test_basic_prompt_structure(self):
        prompt = _build_user_prompt("I love cooking and yoga", source="voice")
        self.assertIn("voice", prompt)
        self.assertIn("I love cooking and yoga", prompt)
        self.assertIn("ENTITY TYPES", prompt)
        self.assertIn("OBSERVATION SUBTYPES", prompt)
        self.assertIn("Return JSON", prompt)

    def test_existing_data_included(self):
        prompt = _build_user_prompt(
            "I went trekking",
            existing_data={"interests": ["cooking", "yoga"]},
            source="post",
        )
        self.assertIn("EXISTING USER DATA", prompt)
        self.assertIn("cooking", prompt)

    def test_no_existing_data(self):
        prompt = _build_user_prompt("hello", source="chat")
        self.assertNotIn("EXISTING USER DATA", prompt)


class TestValidation(unittest.TestCase):
    """Test the validation layer."""

    def _make_obs(self, **kwargs):
        defaults = {
            "entity_type": "interest",
            "observation_subtype": "activity_mention",
            "label": "cooking",
            "display_label": "Cooking",
            "quote": "",
            "details": "",
            "confidence": 0.7,
            "evidence_weight": 0.5,
            "sentiment": 0.0,
            "observation_type": "new",
            "corrects": "",
            "reasoning": "",
        }
        defaults.update(kwargs)
        return ClassifiedObservation(**defaults)

    def test_valid_observation_passes(self):
        obs = self._make_obs(label="cooking", confidence=0.8)
        result = validate_observations([obs])
        self.assertEqual(len(result), 1)

    def test_empty_label_rejected(self):
        obs = self._make_obs(label="", confidence=0.8)
        result = validate_observations([obs])
        self.assertEqual(len(result), 0)

    def test_short_label_rejected(self):
        obs = self._make_obs(label="x", confidence=0.8)
        result = validate_observations([obs])
        self.assertEqual(len(result), 0)

    def test_low_confidence_rejected(self):
        obs = self._make_obs(label="maybe yoga", confidence=0.05)
        result = validate_observations([obs])
        self.assertEqual(len(result), 0)

    def test_unknown_entity_type_defaults(self):
        obs = self._make_obs(entity_type="nonexistent", label="test")
        result = validate_observations([obs])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].entity_type, EntityType.INTEREST.value)

    def test_unknown_subtype_defaults(self):
        obs = self._make_obs(observation_subtype="nonexistent", label="test")
        result = validate_observations([obs])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].observation_subtype, ObservationSubtype.ACTIVITY_MENTION.value)

    def test_label_lowercased(self):
        obs = self._make_obs(label="  COOKING  ")
        result = validate_observations([obs])
        self.assertEqual(result[0].label, "cooking")

    def test_long_label_truncated(self):
        obs = self._make_obs(label="a" * 500)
        result = validate_observations([obs])
        self.assertLessEqual(len(result[0].label), 200)

    def test_display_label_fallback(self):
        obs = self._make_obs(label="trekking", display_label="")
        result = validate_observations([obs])
        self.assertEqual(result[0].display_label, "Trekking")

    def test_mixed_valid_invalid(self):
        observations = [
            self._make_obs(label="cooking", confidence=0.8),
            self._make_obs(label="", confidence=0.8),
            self._make_obs(label="yoga", confidence=0.05),
            self._make_obs(label="trekking", confidence=0.6),
        ]
        result = validate_observations(observations)
        self.assertEqual(len(result), 2)
        labels = {o.label for o in result}
        self.assertIn("cooking", labels)
        self.assertIn("trekking", labels)


if __name__ == "__main__":
    unittest.main(verbosity=2)
