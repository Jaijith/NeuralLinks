#!/usr/bin/env python3
"""
Consolidation Pipeline tests — Phase 6.3

Tests:
- _parse_consolidation_result: LLM JSON → ConsolidationResult
- Entity resolver make_node_id
- ConsolidationDecision model integrity
- Edge suggestion parsing
- Coverage update parsing
- Edge cases (empty input, malformed decisions)

Usage:
    python -m scripts.test_consolidation_pipeline
"""

import sys
import unittest

sys.path.insert(0, ".")

from domain.memory.consolidation_agent import _parse_consolidation_result
from domain.memory.entity_resolver import make_node_id, ENTITY_TYPE_TO_NODE_TYPES
from domain.memory.models import (
    ConsolidationResult,
    ConsolidationDecision,
    NodeStatus,
    EvidencePattern,
)


class TestParseConsolidationResult(unittest.TestCase):
    """Test _parse_consolidation_result for various LLM outputs."""

    def _make_raw_decision(self, label="cooking", **overrides):
        d = {
            "entity_label": label,
            "entity_type": "interest",
            "belief_update": {
                "delta_alpha": 1.5,
                "delta_beta": 0.1,
                "reasoning": "strong evidence",
            },
            "salience_update": {
                "new_salience": 0.8,
                "new_stability_days": 90,
                "reasoning": "active interest",
            },
            "status_decision": {
                "new_status": "active",
                "reasoning": "enough evidence",
            },
            "frequency_assessment": {
                "evidence_pattern": "regular_interest",
                "narrative_descriptor": "passionate about cooking",
                "mention_frequency_per_month": 3.0,
            },
            "conflict_resolution": {
                "has_conflict": False,
                "resolution": "",
            },
        }
        d.update(overrides)
        return d

    def test_well_formed_result(self):
        raw = {
            "consolidation_decisions": [
                self._make_raw_decision("cooking"),
                self._make_raw_decision("trekking", **{
                    "belief_update": {"delta_alpha": 0.3, "delta_beta": 0},
                    "salience_update": {"new_salience": 0.4, "new_stability_days": 30},
                    "status_decision": {"new_status": "pending"},
                    "frequency_assessment": {
                        "evidence_pattern": "single_mention",
                        "narrative_descriptor": "mentioned trekking once",
                    },
                }),
            ],
            "cross_entity_observations": "User is active and outdoor-oriented.",
            "new_edges_suggested": [
                {
                    "from_label": "cooking",
                    "to_label": "india",
                    "relationship_type": "co_interest",
                    "reasoning": "cultural connection",
                }
            ],
            "coverage_updates": {
                "interests_passions": 0.3,
                "daily_life": 0.1,
            },
        }

        result = _parse_consolidation_result(raw)
        self.assertIsInstance(result, ConsolidationResult)
        self.assertEqual(len(result.consolidation_decisions), 2)
        self.assertEqual(result.consolidation_decisions[0].entity_label, "cooking")
        self.assertAlmostEqual(
            result.consolidation_decisions[0].belief_update.delta_alpha, 1.5
        )
        self.assertEqual(
            result.consolidation_decisions[0].status_decision.new_status, "active"
        )
        self.assertEqual(len(result.new_edges_suggested), 1)
        self.assertIn("outdoor", result.cross_entity_observations)

    def test_empty_decisions(self):
        result = _parse_consolidation_result({"consolidation_decisions": []})
        self.assertEqual(len(result.consolidation_decisions), 0)

    def test_empty_dict(self):
        result = _parse_consolidation_result({})
        self.assertEqual(len(result.consolidation_decisions), 0)

    def test_missing_label_skipped(self):
        raw = {
            "consolidation_decisions": [
                self._make_raw_decision(""),
                self._make_raw_decision("yoga"),
            ]
        }
        result = _parse_consolidation_result(raw)
        self.assertEqual(len(result.consolidation_decisions), 1)
        self.assertEqual(result.consolidation_decisions[0].entity_label, "yoga")

    def test_delta_alpha_clamping(self):
        raw = {
            "consolidation_decisions": [
                self._make_raw_decision("chess", **{
                    "belief_update": {"delta_alpha": 99.0, "delta_beta": -5.0},
                }),
            ]
        }
        result = _parse_consolidation_result(raw)
        self.assertLessEqual(result.consolidation_decisions[0].belief_update.delta_alpha, 3.0)
        self.assertGreaterEqual(result.consolidation_decisions[0].belief_update.delta_beta, 0.0)

    def test_salience_clamping(self):
        raw = {
            "consolidation_decisions": [
                self._make_raw_decision("reading", **{
                    "salience_update": {"new_salience": 5.0, "new_stability_days": 9999},
                }),
            ]
        }
        result = _parse_consolidation_result(raw)
        self.assertLessEqual(
            result.consolidation_decisions[0].salience_update.new_salience, 1.0
        )
        self.assertLessEqual(
            result.consolidation_decisions[0].salience_update.new_stability_days, 365.0
        )

    def test_self_edge_skipped(self):
        raw = {
            "consolidation_decisions": [],
            "new_edges_suggested": [
                {"from_label": "cooking", "to_label": "cooking", "relationship_type": "self"},
                {"from_label": "cooking", "to_label": "baking", "relationship_type": "related_to"},
            ],
        }
        result = _parse_consolidation_result(raw)
        self.assertEqual(len(result.new_edges_suggested), 1)

    def test_coverage_updates(self):
        raw = {
            "consolidation_decisions": [],
            "coverage_updates": {
                "life_narrative": 0.5,
                "values_beliefs": 0.3,
                "interests_passions": 0.8,
            },
        }
        result = _parse_consolidation_result(raw)
        self.assertAlmostEqual(result.coverage_updates.life_narrative, 0.5)
        self.assertAlmostEqual(result.coverage_updates.interests_passions, 0.8)

    def test_malformed_decision_skipped(self):
        raw = {
            "consolidation_decisions": [
                {"entity_label": "broken", "belief_update": "not_a_dict"},
                self._make_raw_decision("valid_one"),
            ]
        }
        result = _parse_consolidation_result(raw)
        self.assertGreaterEqual(len(result.consolidation_decisions), 1)


class TestEntityResolver(unittest.TestCase):
    """Test entity resolution helpers."""

    def test_make_node_id(self):
        nid = make_node_id("interest", "user123", "cooking")
        self.assertEqual(nid, "interest_user123_cooking")

    def test_make_node_id_spaces(self):
        nid = make_node_id("fact", "user1", "born in india")
        self.assertEqual(nid, "fact_user1_born_in_india")

    def test_make_node_id_case_normalization(self):
        nid = make_node_id("trait", "u1", "  Introverted  ")
        self.assertEqual(nid, "trait_u1_introverted")

    def test_entity_type_mapping(self):
        """All entity types should have node_type mappings."""
        expected_types = {
            "interest", "fact", "connection", "trait",
            "value", "preference", "experience", "demographic",
        }
        for et in expected_types:
            self.assertIn(et, ENTITY_TYPE_TO_NODE_TYPES)
            self.assertIsInstance(ENTITY_TYPE_TO_NODE_TYPES[et], list)
            self.assertGreater(len(ENTITY_TYPE_TO_NODE_TYPES[et]), 0)

    def test_fact_maps_to_preference_fallback(self):
        """Facts should search both 'fact' and 'preference' node types."""
        types = ENTITY_TYPE_TO_NODE_TYPES["fact"]
        self.assertIn("fact", types)
        self.assertIn("preference", types)


class TestConsolidationDecisionModel(unittest.TestCase):
    """Test the ConsolidationDecision Pydantic model."""

    def test_valid_decision(self):
        from domain.memory.models import (
            BeliefUpdate, SalienceUpdate, StatusDecision,
            FrequencyAssessment, ConflictResolution,
        )
        d = ConsolidationDecision(
            entity_label="cooking",
            entity_type="interest",
            belief_update=BeliefUpdate(delta_alpha=1.0, delta_beta=0.1),
            salience_update=SalienceUpdate(new_salience=0.7, new_stability_days=90),
            status_decision=StatusDecision(new_status="active"),
            frequency_assessment=FrequencyAssessment(
                evidence_pattern="regular_interest",
                narrative_descriptor="enjoys cooking",
            ),
            conflict_resolution=ConflictResolution(has_conflict=False),
        )
        self.assertEqual(d.entity_label, "cooking")
        self.assertEqual(d.belief_update.delta_alpha, 1.0)

    def test_status_values(self):
        """Check NodeStatus enum values."""
        self.assertEqual(NodeStatus.ACTIVE.value, "active")
        self.assertEqual(NodeStatus.PENDING.value, "pending")
        self.assertEqual(NodeStatus.FADING.value, "fading")

    def test_evidence_pattern_values(self):
        """Check EvidencePattern enum values."""
        patterns = {e.value for e in EvidencePattern}
        self.assertIn("single_mention", patterns)
        self.assertIn("active_habit", patterns)
        self.assertIn("enduring_sporadic", patterns)
        self.assertIn("fading", patterns)


if __name__ == "__main__":
    unittest.main(verbosity=2)
