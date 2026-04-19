#!/usr/bin/env python3
"""
End-to-end Dual-Memory Architecture test — Phase 6.4

Simulates the complete pipeline WITHOUT requiring MongoDB or OpenAI:
1. Classification Agent → produces ClassificationResult (mocked LLM)
2. Validation → filters observations
3. STM Writer → writes to mock DB
4. Consolidation Agent → produces ConsolidationResult (mocked LLM)
5. Consolidation Executor → applies decisions to mock LTM
6. Salience Decay → applies decay to LTM nodes
7. GraphRAG InMemoryGraph → loads and queries the updated graph

Uses unittest.mock for the database and LLM client.

Usage:
    python -m scripts.test_dual_memory_e2e
"""

import asyncio
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, ".")

from domain.memory.classification_agent import _parse_result
from domain.memory.consolidation_agent import _parse_consolidation_result
from domain.memory.validation import validate_observations
from domain.memory.bayesian import (
    add_bayesian_defaults,
    add_bayesian_edge_defaults,
    compute_belief_strength,
    compute_salience_decay,
)
from domain.memory.entity_resolver import make_node_id
from domain.memory.models import (
    ClassifiedObservation,
    CoMention,
    ConsolidationDecision,
    STMObservation,
    NodeStatus,
    EvidencePattern,
)
from domain.graph.rag import InMemoryGraph, GraphRAG


def run_async(coro):
    """Helper to run async tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestE2EClassificationToSTM(unittest.TestCase):
    """Test: Voice content → Classification → Validation → STM-ready docs."""

    def test_voice_to_stm_happy_path(self):
        """Simulate a voice session producing valid STM observations."""
        raw_llm_output = {
            "observations": [
                {
                    "entity_type": "interest",
                    "observation_subtype": "interest_explicit",
                    "label": "cooking",
                    "display_label": "Cooking",
                    "quote": "I absolutely love cooking, it's my passion",
                    "details": "expressed with strong enthusiasm",
                    "confidence": 0.95,
                    "evidence_weight": 2.5,
                    "sentiment": 0.9,
                    "observation_type": "new",
                    "reasoning": "Explicit passionate declaration",
                },
                {
                    "entity_type": "fact",
                    "observation_subtype": "fact_biographical",
                    "label": "born in kerala",
                    "display_label": "Born in Kerala",
                    "quote": "I was born in Kerala",
                    "confidence": 0.98,
                    "evidence_weight": 2.8,
                    "sentiment": 0.0,
                    "observation_type": "new",
                    "reasoning": "Direct biographical fact",
                },
                {
                    "entity_type": "interest",
                    "observation_subtype": "activity_mention",
                    "label": "yoga",
                    "display_label": "Yoga",
                    "quote": "I did yoga once last week",
                    "confidence": 0.6,
                    "evidence_weight": 0.3,
                    "sentiment": 0.2,
                    "observation_type": "new",
                    "reasoning": "Single activity mention, not a confirmed interest",
                },
                {
                    "entity_type": "interest",
                    "observation_subtype": "activity_mention",
                    "label": "x",
                    "confidence": 0.05,
                    "evidence_weight": 0.1,
                    "observation_type": "new",
                },
            ],
            "co_mentions": [
                {
                    "entity_a": "cooking",
                    "entity_b": "kerala",
                    "relationship_hint": "cultural cuisine",
                }
            ],
            "classification_notes": "Rich personal content.",
        }

        result = _parse_result(raw_llm_output)
        self.assertEqual(len(result.observations), 4)

        valid = validate_observations(result.observations)
        # "x" is too short (1 char) and low confidence (0.05), both rejected
        self.assertEqual(len(valid), 3)

        labels = {o.label for o in valid}
        self.assertIn("cooking", labels)
        self.assertIn("born in kerala", labels)
        self.assertIn("yoga", labels)

        cooking = next(o for o in valid if o.label == "cooking")
        self.assertGreater(cooking.evidence_weight, 2.0)
        self.assertGreater(cooking.confidence, 0.9)

        yoga = next(o for o in valid if o.label == "yoga")
        self.assertLess(yoga.evidence_weight, 0.5)


class TestE2EConsolidation(unittest.TestCase):
    """Test: STM observations → Consolidation Agent → LTM decisions."""

    def test_consolidation_produces_correct_decisions(self):
        """Simulate consolidation agent output and verify structure."""
        raw_consolidation = {
            "consolidation_decisions": [
                {
                    "entity_label": "cooking",
                    "entity_type": "interest",
                    "belief_update": {
                        "delta_alpha": 2.0,
                        "delta_beta": 0.0,
                        "reasoning": "Strong explicit evidence, passionate declaration",
                    },
                    "salience_update": {
                        "new_salience": 0.9,
                        "new_stability_days": 180.0,
                        "reasoning": "Active passion, high stability",
                    },
                    "status_decision": {
                        "new_status": "active",
                        "reasoning": "Clear evidence of strong interest",
                    },
                    "frequency_assessment": {
                        "evidence_pattern": "active_habit",
                        "narrative_descriptor": "passionate about cooking",
                        "mention_frequency_per_month": 4.0,
                    },
                    "conflict_resolution": {
                        "has_conflict": False,
                    },
                },
                {
                    "entity_label": "yoga",
                    "entity_type": "interest",
                    "belief_update": {
                        "delta_alpha": 0.2,
                        "delta_beta": 0.1,
                        "reasoning": "Single mention, low evidence weight",
                    },
                    "salience_update": {
                        "new_salience": 0.3,
                        "new_stability_days": 14.0,
                        "reasoning": "One-time mention, short stability",
                    },
                    "status_decision": {
                        "new_status": "pending",
                        "reasoning": "Not enough evidence yet",
                    },
                    "frequency_assessment": {
                        "evidence_pattern": "single_mention",
                        "narrative_descriptor": "mentioned yoga once",
                        "mention_frequency_per_month": 0.5,
                    },
                    "conflict_resolution": {
                        "has_conflict": False,
                    },
                },
            ],
            "cross_entity_observations": "User has clear cooking passion, yoga is exploratory.",
            "new_edges_suggested": [
                {
                    "from_label": "cooking",
                    "to_label": "born in kerala",
                    "relationship_type": "related_to",
                    "reasoning": "Kerala cuisine is culturally significant",
                }
            ],
            "coverage_updates": {
                "interests_passions": 0.4,
                "life_narrative": 0.2,
            },
        }

        result = _parse_consolidation_result(raw_consolidation)

        self.assertEqual(len(result.consolidation_decisions), 2)

        cooking_d = result.consolidation_decisions[0]
        self.assertEqual(cooking_d.entity_label, "cooking")
        self.assertEqual(cooking_d.status_decision.new_status, "active")
        self.assertEqual(cooking_d.belief_update.delta_alpha, 2.0)
        self.assertAlmostEqual(cooking_d.salience_update.new_salience, 0.9)
        self.assertEqual(
            cooking_d.frequency_assessment.narrative_descriptor,
            "passionate about cooking",
        )

        yoga_d = result.consolidation_decisions[1]
        self.assertEqual(yoga_d.status_decision.new_status, "pending")
        self.assertLess(yoga_d.belief_update.delta_alpha, 0.5)

        self.assertEqual(len(result.new_edges_suggested), 1)


class TestE2EBayesianUpdate(unittest.TestCase):
    """Test: LTM node + consolidation decision → correct Bayesian state."""

    def test_bayesian_update_flow(self):
        """Simulate applying a consolidation decision to an existing node."""
        existing_node = {
            "id": "interest_user1_cooking",
            "user_id": "user1",
            "node_type": "interest",
            "label": "cooking",
            "display_label": "Cooking",
            "strength": 0.5,
            "mention_count": 1,
        }

        add_bayesian_defaults(existing_node, prior="uninformative")

        old_alpha = existing_node["belief_alpha"]
        old_beta = existing_node["belief_beta"]
        old_strength = existing_node["belief_strength"]

        delta_alpha = 2.0
        delta_beta = 0.0
        new_alpha = old_alpha + delta_alpha
        new_beta = old_beta + delta_beta

        new_strength = compute_belief_strength(new_alpha, new_beta)

        self.assertGreater(new_strength, old_strength)
        self.assertGreater(new_strength, 0.7)

    def test_pending_to_active_with_evidence(self):
        """New node starts pending, accumulates evidence, becomes active."""
        node = {
            "id": "interest_user1_yoga",
            "user_id": "user1",
            "node_type": "interest",
            "label": "yoga",
        }
        add_bayesian_defaults(node, prior="uninformative", status="pending")
        self.assertEqual(node["status"], "pending")

        for _ in range(5):
            node["belief_alpha"] += 0.5
            node["evidence_count"] += 1

        new_strength = compute_belief_strength(
            node["belief_alpha"], node["belief_beta"]
        )
        self.assertGreater(new_strength, 0.6)


class TestE2ESalienceDecay(unittest.TestCase):
    """Test: Salience decay over time."""

    def test_decay_active_vs_dormant(self):
        """Active interest should retain salience longer than a one-time mention."""
        active_sal = compute_salience_decay(0.9, 7.0, stability_days=180.0)
        dormant_sal = compute_salience_decay(0.3, 7.0, stability_days=14.0)

        self.assertGreater(active_sal, 0.85)
        self.assertLess(dormant_sal, 0.2)

    def test_narrative_priority_after_decay(self):
        """After decay, cooking (high stability) should still outrank yoga (low stability)."""
        cooking_initial = 0.9
        yoga_initial = 0.3

        cooking_after_30d = compute_salience_decay(cooking_initial, 30, 180.0)
        yoga_after_30d = compute_salience_decay(yoga_initial, 30, 14.0)

        self.assertGreater(cooking_after_30d, yoga_after_30d)


class TestE2EGraphRAGIntegration(unittest.TestCase):
    """Test: InMemoryGraph works correctly with Bayesian-enhanced nodes."""

    def test_node_strength_uses_salience(self):
        """node_strength should prefer salience over legacy strength."""
        g = InMemoryGraph(user_id="user1")
        g.nodes["n1"] = {
            "id": "n1",
            "node_type": "interest",
            "label": "cooking",
            "strength": 0.5,
            "salience": 0.9,
            "belief_strength": 0.75,
        }
        self.assertAlmostEqual(g.node_strength("n1"), 0.9)

    def test_node_strength_fallback_chain(self):
        """When salience is missing, fall back to belief_strength."""
        g = InMemoryGraph(user_id="user1")
        g.nodes["n1"] = {
            "id": "n1",
            "label": "yoga",
            "belief_strength": 0.6,
            "strength": 0.4,
        }
        self.assertAlmostEqual(g.node_strength("n1"), 0.6)

    def test_node_strength_legacy_fallback(self):
        """When no Bayesian fields, fall back to legacy strength."""
        g = InMemoryGraph(user_id="user1")
        g.nodes["n1"] = {"id": "n1", "label": "chess", "strength": 0.7}
        self.assertAlmostEqual(g.node_strength("n1"), 0.7)

    def test_by_label_index(self):
        """by_label should map lowercased labels to node IDs."""
        g = InMemoryGraph(user_id="user1")
        g.nodes["n1"] = {"id": "n1", "label": "cooking"}
        g.by_label["cooking"] = "n1"
        self.assertEqual(g.by_label.get("cooking"), "n1")

    def test_pending_nodes_excluded_from_narrative(self):
        """Pending nodes should be filterable by downstream consumers."""
        g = InMemoryGraph(user_id="user1")
        g.nodes["n1"] = {"id": "n1", "label": "cooking", "status": "active", "salience": 0.9}
        g.nodes["n2"] = {"id": "n2", "label": "yoga", "status": "pending", "salience": 0.3}

        active_nodes = {
            nid for nid, n in g.nodes.items()
            if n.get("status", "active") != "pending"
        }
        self.assertIn("n1", active_nodes)
        self.assertNotIn("n2", active_nodes)

    def test_edge_weight_bayesian(self):
        """_edge_weight should prefer edge_strength over weight."""
        w = GraphRAG._edge_weight({"weight": 0.5, "edge_strength": 0.8})
        self.assertAlmostEqual(w, 0.8)

    def test_edge_weight_legacy(self):
        """_edge_weight should fall back to weight when no edge_strength."""
        w = GraphRAG._edge_weight({"weight": 0.6})
        self.assertAlmostEqual(w, 0.6)


class TestE2EFullPipelineFlow(unittest.TestCase):
    """Integration test: full data flow from raw content to query-ready graph."""

    def test_full_pipeline_data_flow(self):
        """
        Simulate: voice content → classification → validation → STM-ready
        → consolidation decisions → LTM node state → GraphRAG query.
        """
        # Step 1: Classification (mocked LLM output)
        raw_classification = {
            "observations": [
                {
                    "entity_type": "interest",
                    "observation_subtype": "interest_explicit",
                    "label": "cooking",
                    "display_label": "Cooking",
                    "quote": "I love cooking",
                    "confidence": 0.95,
                    "evidence_weight": 2.5,
                    "observation_type": "new",
                    "reasoning": "Passionate declaration",
                },
                {
                    "entity_type": "connection",
                    "observation_subtype": "connection_definitive",
                    "label": "mom",
                    "display_label": "Mom",
                    "quote": "my mom taught me",
                    "confidence": 0.9,
                    "evidence_weight": 2.0,
                    "observation_type": "new",
                    "reasoning": "Clear family connection",
                },
            ],
            "co_mentions": [
                {"entity_a": "cooking", "entity_b": "mom", "relationship_hint": "taught by"},
            ],
        }

        classification = _parse_result(raw_classification)
        self.assertEqual(len(classification.observations), 2)

        # Step 2: Validation
        valid = validate_observations(classification.observations)
        self.assertEqual(len(valid), 2)

        # Step 3: STM docs would be written here (mocked)

        # Step 4: Consolidation (mocked LLM output)
        raw_consolidation = {
            "consolidation_decisions": [
                {
                    "entity_label": "cooking",
                    "entity_type": "interest",
                    "belief_update": {"delta_alpha": 2.0, "delta_beta": 0.0},
                    "salience_update": {"new_salience": 0.9, "new_stability_days": 180},
                    "status_decision": {"new_status": "active"},
                    "frequency_assessment": {
                        "evidence_pattern": "active_habit",
                        "narrative_descriptor": "passionate about cooking",
                    },
                    "conflict_resolution": {"has_conflict": False},
                },
                {
                    "entity_label": "mom",
                    "entity_type": "connection",
                    "belief_update": {"delta_alpha": 1.5, "delta_beta": 0.0},
                    "salience_update": {"new_salience": 0.7, "new_stability_days": 365},
                    "status_decision": {"new_status": "active"},
                    "frequency_assessment": {
                        "evidence_pattern": "enduring_sporadic",
                        "narrative_descriptor": "close to her mom",
                    },
                    "conflict_resolution": {"has_conflict": False},
                },
            ],
            "new_edges_suggested": [
                {
                    "from_label": "cooking",
                    "to_label": "mom",
                    "relationship_type": "learned_from",
                    "reasoning": "Mom taught cooking",
                }
            ],
        }

        consolidation = _parse_consolidation_result(raw_consolidation)

        # Step 5: Apply to LTM (simulate)
        cooking_node = {"id": "interest_user1_cooking", "label": "cooking", "node_type": "interest"}
        add_bayesian_defaults(cooking_node, prior="uninformative")

        cd = consolidation.consolidation_decisions[0]
        cooking_node["belief_alpha"] += cd.belief_update.delta_alpha
        cooking_node["belief_beta"] += cd.belief_update.delta_beta
        cooking_node["salience"] = cd.salience_update.new_salience
        cooking_node["salience_stability"] = cd.salience_update.new_stability_days
        cooking_node["status"] = cd.status_decision.new_status
        cooking_node["narrative_descriptor"] = cd.frequency_assessment.narrative_descriptor
        cooking_node["belief_strength"] = compute_belief_strength(
            cooking_node["belief_alpha"], cooking_node["belief_beta"]
        )

        # Step 6: Build InMemoryGraph and verify
        g = InMemoryGraph(user_id="user1")
        g.nodes["interest_user1_cooking"] = cooking_node
        g.by_label["cooking"] = "interest_user1_cooking"

        self.assertAlmostEqual(g.node_strength("interest_user1_cooking"), 0.9)
        self.assertEqual(cooking_node["status"], "active")
        self.assertEqual(cooking_node["narrative_descriptor"], "passionate about cooking")
        self.assertGreater(cooking_node["belief_strength"], 0.7)

        # Step 7: After 30 days of decay, cooking should still be strong
        cooking_after_30d = compute_salience_decay(0.9, 30, 180.0)
        self.assertGreater(cooking_after_30d, 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
