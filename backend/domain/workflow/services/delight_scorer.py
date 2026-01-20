"""
User Delight Scorer
Computes user satisfaction and delight scores
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.bonding_state import BondingState
from ..models.bonding_memory import BondingSession

logger = logging.getLogger(__name__)


class UserDelightScorer:
    """
    Computes user delight scores from various signals.
    
    Delight is measured on a 0-1 scale based on:
    1. Novelty - Is this new/surprising?
    2. Relevance - Does this match user's interests/needs?
    3. Alignment - Does this fit user's values/preferences?
    4. Surprise - Positive unexpected elements
    5. Warmth - Emotional connection felt
    6. Utility - Practical usefulness
    
    Features:
    - Multi-factor scoring
    - Historical trend tracking
    - Prediction based on patterns
    - Feedback integration
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Scoring weights (sum to 1.0)
        self.weights = {
            "novelty": 0.20,
            "relevance": 0.25,
            "alignment": 0.15,
            "surprise": 0.15,
            "warmth": 0.15,
            "utility": 0.10
        }
    
    async def compute_delight(
        self,
        session_data: Dict[str, Any],
        bonding_state: BondingState,
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Compute user delight score for a bonding session.
        
        Args:
            session_data: Session details (cards, intent, etc.)
            bonding_state: Current bonding state
            user_feedback: Optional explicit feedback (rating, helpful, etc.)
        
        Returns:
            Delight score (0.0-1.0)
        """
        
        # Factor 1: Novelty
        novelty_score = self._score_novelty(
            session_data,
            bonding_state
        )
        
        # Factor 2: Relevance
        relevance_score = self._score_relevance(
            session_data,
            bonding_state
        )
        
        # Factor 3: Alignment
        alignment_score = self._score_alignment(
            session_data,
            bonding_state
        )
        
        # Factor 4: Surprise
        surprise_score = self._score_surprise(
            session_data
        )
        
        # Factor 5: Warmth
        warmth_score = self._score_warmth(
            session_data,
            bonding_state
        )
        
        # Factor 6: Utility
        utility_score = self._score_utility(
            session_data
        )
        
        # Weighted sum
        delight = (
            novelty_score * self.weights["novelty"] +
            relevance_score * self.weights["relevance"] +
            alignment_score * self.weights["alignment"] +
            surprise_score * self.weights["surprise"] +
            warmth_score * self.weights["warmth"] +
            utility_score * self.weights["utility"]
        )
        
        # Adjust based on explicit feedback if provided
        if user_feedback:
            delight = self._adjust_for_feedback(delight, user_feedback)
        
        # Clamp to [0, 1]
        delight = max(0.0, min(1.0, delight))
        
        logger.info(f"Computed delight score: {delight:.2f} "
                   f"(novelty={novelty_score:.2f}, relevance={relevance_score:.2f}, "
                   f"alignment={alignment_score:.2f}, surprise={surprise_score:.2f}, "
                   f"warmth={warmth_score:.2f}, utility={utility_score:.2f})")
        
        return delight
    
    async def update_delight_history(
        self,
        user_id: str,
        avatar_id: str,
        delight_score: float
    ):
        """Update bonding state with new delight score"""
        
        state_doc = await self.db.bonding_states.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        
        if not state_doc:
            logger.warning(f"No bonding state found for user {user_id}, avatar {avatar_id}")
            return
        
        # Update delight history
        delight_history = state_doc.get("delight_history", [])
        delight_history.append(delight_score)
        
        # Keep last 10
        if len(delight_history) > 10:
            delight_history = delight_history[-10:]
        
        # Compute trend
        trend = self._compute_trend(delight_history)
        
        # Update database
        await self.db.bonding_states.update_one(
            {"user_id": user_id, "avatar_id": avatar_id},
            {
                "$set": {
                    "delight_history": delight_history,
                    "last_delight_score": delight_score,
                    "delight_trend": trend,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Updated delight history: score={delight_score:.2f}, trend={trend}")
    
    async def predict_satisfaction(
        self,
        user_id: str,
        avatar_id: str,
        bonding_state: BondingState
    ) -> Dict[str, Any]:
        """
        Predict likely user satisfaction for next interaction.
        
        Based on:
        - Historical delight trend
        - Bond strength trajectory
        - Engagement patterns
        
        Returns:
            Prediction dict with score and confidence
        """
        
        # Get recent sessions
        recent_sessions = await self.db.bonding_sessions.find({
            "user_id": user_id,
            "avatar_id": avatar_id
        }).sort("start_time", -1).limit(5).to_list(length=5)
        
        if not recent_sessions:
            return {
                "predicted_satisfaction": 0.5,
                "confidence": 0.3,
                "factors": ["insufficient_data"]
            }
        
        # Compute average recent delight
        recent_delights = [s.get("delight_score", 0.5) for s in recent_sessions]
        avg_delight = sum(recent_delights) / len(recent_delights)
        
        # Factor in bond strength
        bond_factor = bonding_state.metrics.bond_strength
        
        # Factor in engagement rate
        engagement_factor = bonding_state.metrics.engagement_rate
        
        # Weighted prediction
        predicted = (
            avg_delight * 0.5 +
            bond_factor * 0.3 +
            engagement_factor * 0.2
        )
        
        # Confidence based on data quantity and consistency
        confidence = min(0.9, len(recent_sessions) / 10)  # More sessions = higher confidence
        
        # Adjust confidence based on consistency
        if len(recent_delights) >= 3:
            variance = sum((d - avg_delight) ** 2 for d in recent_delights) / len(recent_delights)
            if variance < 0.05:  # Low variance = high confidence
                confidence = min(0.95, confidence + 0.2)
        
        factors = []
        if avg_delight > 0.7:
            factors.append("high_recent_delight")
        if bond_factor > 0.7:
            factors.append("strong_bond")
        if bonding_state.delight_trend == "rising":
            factors.append("rising_trend")
        if bonding_state.delight_trend == "falling":
            factors.append("falling_trend")
        
        return {
            "predicted_satisfaction": round(predicted, 2),
            "confidence": round(confidence, 2),
            "factors": factors,
            "recent_avg_delight": round(avg_delight, 2),
            "bond_strength": round(bond_factor, 2)
        }
    
    # ========================================================================
    # PRIVATE METHODS - Scoring Factors
    # ========================================================================
    
    def _score_novelty(
        self,
        session_data: Dict[str, Any],
        bonding_state: BondingState
    ) -> float:
        """
        Score novelty - is this new/surprising?
        
        Returns:
            0.0-1.0 score
        """
        
        cards = session_data.get("cards_generated", [])
        
        # Check for novelty indicators
        has_serendipity = any(c.get("type") == "serendipity" for c in cards)
        has_growth = any(c.get("type") == "growth" for c in cards)
        
        # More cards = potentially more novelty
        num_cards = len(cards)
        
        score = 0.5  # Base
        
        if has_serendipity:
            score += 0.3
        if has_growth:
            score += 0.2
        if num_cards >= 4:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_relevance(
        self,
        session_data: Dict[str, Any],
        bonding_state: BondingState
    ) -> float:
        """
        Score relevance - does this match user's interests/needs?
        
        Returns:
            0.0-1.0 score
        """
        
        detected_intent = session_data.get("detected_intent", "")
        bonding_mode = session_data.get("selected_bonding_mode", "")
        
        # Check intent-mode alignment
        good_alignments = {
            "venting": "coach",
            "planning": "planning",
            "check_in": "check_in",
            "seeking_advice": "coach",
            "celebration": "celebration",
            "reflection": "deep_talk"
        }
        
        expected_mode = good_alignments.get(detected_intent)
        if expected_mode == bonding_mode:
            score = 0.9  # Excellent alignment
        else:
            score = 0.6  # Decent default
        
        # Boost if recap was included and user likely wanted updates
        cards = session_data.get("cards_generated", [])
        has_recap = any(c.get("type") == "recap" for c in cards)
        
        if has_recap and detected_intent in ["check_in", "planning"]:
            score = min(1.0, score + 0.1)
        
        return score
    
    def _score_alignment(
        self,
        session_data: Dict[str, Any],
        bonding_state: BondingState
    ) -> float:
        """
        Score alignment - does this fit user's values/preferences?
        
        Returns:
            0.0-1.0 score
        """
        
        # Use avatar's confidence in understanding user
        alignment_confidence = bonding_state.metrics.alignment_confidence
        
        # Adjust based on mood match
        user_mood = bonding_state.user_mood_estimate
        
        # If user was stressed but we gave them space, good alignment
        if str(user_mood) in ["stressed", "frustrated"]:
            # Check if we were gentle (no micro-missions, brief)
            micro_missions = session_data.get("micro_missions_proposed", 0)
            if micro_missions == 0:
                return min(1.0, alignment_confidence + 0.1)
        
        # If user was excited and we matched energy, good alignment
        elif str(user_mood) in ["excited", "content"]:
            cards = session_data.get("cards_generated", [])
            if len(cards) >= 3:  # Gave them rich content
                return min(1.0, alignment_confidence + 0.1)
        
        return alignment_confidence
    
    def _score_surprise(self, session_data: Dict[str, Any]) -> float:
        """
        Score surprise - positive unexpected elements
        
        Returns:
            0.0-1.0 score
        """
        
        cards = session_data.get("cards_generated", [])
        
        # Check for surprise cards
        serendipity_cards = [c for c in cards if c.get("type") == "serendipity"]
        
        if not serendipity_cards:
            return 0.5  # No surprise, neutral
        
        # Score based on surprise level
        surprise_levels = [
            c.get("overlap", {}).get("surprise_level", 0.5)
            for c in serendipity_cards
        ]
        
        if surprise_levels:
            return max(surprise_levels)
        
        return 0.7  # Had serendipity but no level specified
    
    def _score_warmth(
        self,
        session_data: Dict[str, Any],
        bonding_state: BondingState
    ) -> float:
        """
        Score warmth - emotional connection felt
        
        Returns:
            0.0-1.0 score
        """
        
        # Warmth correlates with bond strength
        bond_strength = bonding_state.metrics.bond_strength
        trust = bonding_state.metrics.trust
        
        # Check if we had warm presence card
        cards = session_data.get("cards_generated", [])
        has_warm_presence = any(c.get("type") == "warm_presence" for c in cards)
        
        base = (bond_strength + trust) / 2
        
        if has_warm_presence:
            return min(1.0, base + 0.1)
        
        return base
    
    def _score_utility(self, session_data: Dict[str, Any]) -> float:
        """
        Score utility - practical usefulness
        
        Returns:
            0.0-1.0 score
        """
        
        # Utility comes from actionable content
        cards = session_data.get("cards_generated", [])
        micro_missions = session_data.get("micro_missions_proposed", 0)
        guidance_asked = session_data.get("guidance_asked", False)
        
        score = 0.5  # Base
        
        # Micro-missions are useful
        if micro_missions > 0:
            score += 0.3
        
        # Guidance questions can be useful (clarification)
        if guidance_asked:
            score += 0.1
        
        # Recap cards are useful for awareness
        has_recap = any(c.get("type") == "recap" for c in cards)
        if has_recap:
            score += 0.1
        
        return min(1.0, score)
    
    def _adjust_for_feedback(
        self,
        computed_score: float,
        feedback: Dict[str, Any]
    ) -> float:
        """Adjust computed score based on explicit user feedback"""
        
        # If user rated, use that as strong signal
        if "rating" in feedback:
            rating = feedback["rating"]  # Assume 0-5 scale
            normalized_rating = rating / 5.0
            
            # Blend computed with feedback (weight feedback more)
            return computed_score * 0.3 + normalized_rating * 0.7
        
        # If thumbs up/down
        if "helpful" in feedback:
            if feedback["helpful"]:
                return min(1.0, computed_score + 0.2)
            else:
                return max(0.0, computed_score - 0.3)
        
        return computed_score
    
    def _compute_trend(self, delight_history: List[float]) -> str:
        """
        Compute trend from delight history.
        
        Returns:
            "rising", "falling", or "stable"
        """
        
        if len(delight_history) < 3:
            return "stable"
        
        recent = delight_history[-3:]
        older = delight_history[-6:-3] if len(delight_history) >= 6 else recent
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        if recent_avg > older_avg + 0.1:
            return "rising"
        elif recent_avg < older_avg - 0.1:
            return "falling"
        else:
            return "stable"
