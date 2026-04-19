#!/usr/bin/env python3
"""
Unit tests for Bayesian math and salience decay — Phase 6.1

Tests:
- Beta distribution belief calculations (strength, variance, confidence)
- Salience decay curves (Ebbinghaus exponential)
- add_bayesian_defaults idempotency
- add_bayesian_edge_defaults idempotency
- Edge cases (zero alpha/beta, extreme values)

Usage:
    python -m scripts.test_bayesian_math
"""

import math
import sys
import unittest
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

from domain.memory.bayesian import (
    add_bayesian_defaults,
    add_bayesian_edge_defaults,
    compute_belief_confidence,
    compute_belief_strength,
    compute_belief_variance,
    compute_salience_decay,
)


class TestBetaDistribution(unittest.TestCase):
    """Test Beta distribution belief calculations."""

    def test_uninformative_prior(self):
        """Beta(1,1) should give strength=0.5, high variance."""
        bs = compute_belief_strength(1.0, 1.0)
        bv = compute_belief_variance(1.0, 1.0)
        self.assertAlmostEqual(bs, 0.5, places=3)
        self.assertGreater(bv, 0.05)

    def test_strong_positive_belief(self):
        """Beta(10,1) should give high strength, low variance."""
        bs = compute_belief_strength(10.0, 1.0)
        bv = compute_belief_variance(10.0, 1.0)
        bc = compute_belief_confidence(10.0, 1.0)
        self.assertGreater(bs, 0.85)
        self.assertLess(bv, 0.02)
        self.assertGreater(bc, 0.8)

    def test_strong_negative_belief(self):
        """Beta(1,10) should give low strength."""
        bs = compute_belief_strength(1.0, 10.0)
        self.assertLess(bs, 0.15)

    def test_high_evidence_reduces_variance(self):
        """More evidence → lower variance for same mean."""
        bv_low = compute_belief_variance(5.0, 5.0)
        bv_high = compute_belief_variance(50.0, 50.0)
        self.assertGreater(bv_low, bv_high)

    def test_confidence_monotonic_with_evidence(self):
        """Confidence should increase with more evidence at same ratio."""
        c1 = compute_belief_confidence(2.0, 1.0)
        c2 = compute_belief_confidence(20.0, 10.0)
        c3 = compute_belief_confidence(200.0, 100.0)
        self.assertLess(c1, c2)
        self.assertLess(c2, c3)

    def test_zero_total_safety(self):
        """Zero or negative totals should not crash."""
        bs = compute_belief_strength(0.0, 0.0)
        bv = compute_belief_variance(0.0, 0.0)
        self.assertEqual(bs, 0.5)
        self.assertEqual(bv, 0.25)

    def test_belief_strength_range(self):
        """Belief strength should always be in [0, 1]."""
        for alpha in [0.1, 1, 5, 50, 500]:
            for beta_val in [0.1, 1, 5, 50, 500]:
                bs = compute_belief_strength(alpha, beta_val)
                self.assertGreaterEqual(bs, 0.0)
                self.assertLessEqual(bs, 1.0)

    def test_confidence_range(self):
        """Confidence should always be in [0, 1]."""
        for alpha in [0.1, 1, 5, 50, 500]:
            for beta_val in [0.1, 1, 5, 50, 500]:
                bc = compute_belief_confidence(alpha, beta_val)
                self.assertGreaterEqual(bc, 0.0)
                self.assertLessEqual(bc, 1.0)


class TestSalienceDecay(unittest.TestCase):
    """Test Ebbinghaus-inspired salience decay curves."""

    def test_no_decay_at_zero_time(self):
        """Zero elapsed time should return same salience."""
        result = compute_salience_decay(0.8, 0.0, 14.0)
        self.assertAlmostEqual(result, 0.8, places=5)

    def test_decay_reduces_salience(self):
        """After some time, salience should decrease."""
        result = compute_salience_decay(0.8, 7.0, 14.0)
        self.assertLess(result, 0.8)
        self.assertGreater(result, 0.0)

    def test_longer_time_more_decay(self):
        """More elapsed time → lower salience."""
        s1 = compute_salience_decay(0.8, 1.0, 14.0)
        s7 = compute_salience_decay(0.8, 7.0, 14.0)
        s30 = compute_salience_decay(0.8, 30.0, 14.0)
        self.assertGreater(s1, s7)
        self.assertGreater(s7, s30)

    def test_higher_stability_slower_decay(self):
        """Higher stability → slower decay."""
        fast = compute_salience_decay(0.8, 7.0, 7.0)
        slow = compute_salience_decay(0.8, 7.0, 30.0)
        self.assertLess(fast, slow)

    def test_half_life_at_stability(self):
        """At t = stability * ln(2), salience should be ~50% of original."""
        stability = 14.0
        half_life = stability * math.log(2)
        result = compute_salience_decay(1.0, half_life, stability)
        self.assertAlmostEqual(result, 0.5, places=2)

    def test_zero_stability_safety(self):
        """Zero stability should not crash (defaults to 1.0)."""
        result = compute_salience_decay(0.5, 1.0, 0.0)
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0.0)

    def test_very_long_time_near_zero(self):
        """After very long time, salience should approach zero."""
        result = compute_salience_decay(1.0, 365.0, 14.0)
        self.assertLess(result, 0.001)


class TestAddBayesianDefaults(unittest.TestCase):
    """Test the add_bayesian_defaults function."""

    def test_basic_defaults(self):
        """Should add all Bayesian fields to a bare node."""
        node = {
            "id": "test_1",
            "user_id": "user1",
            "label": "cooking",
            "node_type": "interest",
            "strength": 0.7,
            "mention_count": 3,
        }
        result = add_bayesian_defaults(node)

        self.assertIn("belief_alpha", result)
        self.assertIn("belief_beta", result)
        self.assertIn("belief_strength", result)
        self.assertIn("belief_variance", result)
        self.assertIn("belief_confidence", result)
        self.assertIn("salience", result)
        self.assertIn("salience_stability", result)
        self.assertIn("status", result)
        self.assertIn("evidence_log", result)
        self.assertEqual(result["status"], "active")

    def test_idempotent(self):
        """Calling twice should not change existing values."""
        node = {
            "id": "test_2",
            "user_id": "user1",
            "label": "trekking",
            "node_type": "interest",
        }
        add_bayesian_defaults(node, prior="uninformative")
        original_alpha = node["belief_alpha"]
        original_salience = node["salience"]

        add_bayesian_defaults(node, prior="strong")
        self.assertEqual(node["belief_alpha"], original_alpha)
        self.assertEqual(node["salience"], original_salience)

    def test_prior_strengths(self):
        """Different priors should give different starting alphas."""
        node_unin = {"id": "a", "user_id": "u", "label": "a"}
        node_ver = {"id": "b", "user_id": "u", "label": "b"}
        node_str = {"id": "c", "user_id": "u", "label": "c"}

        add_bayesian_defaults(node_unin, prior="uninformative")
        add_bayesian_defaults(node_ver, prior="verified")
        add_bayesian_defaults(node_str, prior="strong")

        self.assertLess(node_unin["belief_alpha"], node_ver["belief_alpha"])
        self.assertLess(node_ver["belief_alpha"], node_str["belief_alpha"])


class TestAddBayesianEdgeDefaults(unittest.TestCase):
    """Test the add_bayesian_edge_defaults function."""

    def test_basic_edge_defaults(self):
        """Should add Bayesian fields to a bare edge."""
        edge = {
            "id": "e1",
            "from_node_id": "n1",
            "to_node_id": "n2",
            "weight": 0.6,
        }
        result = add_bayesian_edge_defaults(edge)

        self.assertIn("belief_alpha", result)
        self.assertIn("belief_beta", result)
        self.assertIn("edge_strength", result)
        self.assertIn("evidence_count", result)

    def test_idempotent(self):
        """Should not overwrite existing Bayesian fields."""
        edge = {
            "id": "e2",
            "from_node_id": "n1",
            "to_node_id": "n2",
            "weight": 0.5,
            "belief_alpha": 99.0,
        }
        add_bayesian_edge_defaults(edge)
        self.assertEqual(edge["belief_alpha"], 99.0)

    def test_user_id_propagation(self):
        """Should set user_id if provided and not present."""
        edge = {"id": "e3", "from_node_id": "n1", "to_node_id": "n2", "weight": 0.5}
        add_bayesian_edge_defaults(edge, user_id="user123")
        self.assertEqual(edge["user_id"], "user123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
