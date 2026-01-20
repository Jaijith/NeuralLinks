"""
Bonding Session Manager
Manages bonding conversation sessions
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.bonding_memory import BondingSession
from ..models.bonding_state import BondingState
from ..models.enums import UserIntent, BondingMode

logger = logging.getLogger(__name__)


class BondingSessionManager:
    """
    Manages bonding conversation sessions.
    
    Features:
    - Create and track bonding sessions
    - Compute session metrics
    - Generate session summaries
    - Track patterns and trends
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, openai_client=None):
        self.db = db
        self.openai_client = openai_client
    
    async def create_session(
        self,
        user_id: str,
        avatar_id: str,
        trigger: str,
        detected_intent: Optional[UserIntent] = None,
        user_message: Optional[str] = None
    ) -> BondingSession:
        """
        Create a new bonding session.
        
        Args:
            user_id: User ID
            avatar_id: Avatar ID
            trigger: What triggered this session
            detected_intent: Detected user intent
            user_message: The user's message
        
        Returns:
            Created BondingSession
        """
        
        session = BondingSession(
            user_id=user_id,
            avatar_id=avatar_id,
            trigger=trigger,
            detected_intent=detected_intent.value if detected_intent else None,
            user_message=user_message
        )
        
        # Save to database
        session_dict = session.dict()
        session_dict["start_time"] = session_dict["start_time"].isoformat()
        
        await self.db.bonding_sessions.insert_one(session_dict)
        
        logger.info(f"Created bonding session {session.id} for user {user_id}")
        return session
    
    async def end_session(
        self,
        session_id: str,
        bonding_state: BondingState,
        cards_generated: List[Dict[str, Any]],
        guidance_asked: bool = False,
        micro_missions_proposed: int = 0,
        summary: Optional[str] = None
    ) -> BondingSession:
        """
        End a bonding session and compute metrics.
        
        Args:
            session_id: Session ID
            bonding_state: Updated bonding state
            cards_generated: Response cards that were generated
            guidance_asked: Did avatar ask for guidance?
            micro_missions_proposed: Number of missions proposed
            summary: Optional session summary
        
        Returns:
            Updated BondingSession
        """
        
        # Load session
        session_doc = await self.db.bonding_sessions.find_one({"id": session_id})
        if not session_doc:
            raise ValueError(f"Session {session_id} not found")
        
        session = BondingSession(**session_doc)
        
        # Compute metrics
        delight_score = bonding_state.last_delight_score
        bond_delta = bonding_state.metrics.bond_delta
        trust_delta = bonding_state.metrics.trust_delta
        alignment_delta = bonding_state.metrics.alignment_delta
        
        # Generate summary if not provided
        if not summary:
            summary = await self._generate_session_summary(
                session,
                bonding_state,
                cards_generated
            )
        
        # Update session
        session.end_session(summary=summary)
        session.cards_generated = cards_generated
        session.guidance_asked = guidance_asked
        session.micro_missions_proposed = micro_missions_proposed
        session.delight_score = delight_score
        session.bond_delta = bond_delta
        session.trust_delta = trust_delta
        session.alignment_delta = alignment_delta
        
        # Save to database
        update_dict = {
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_seconds": session.duration_seconds,
            "summary": session.summary,
            "cards_generated": session.cards_generated,
            "guidance_asked": session.guidance_asked,
            "micro_missions_proposed": session.micro_missions_proposed,
            "delight_score": session.delight_score,
            "bond_delta": session.bond_delta,
            "trust_delta": session.trust_delta,
            "alignment_delta": session.alignment_delta
        }
        
        await self.db.bonding_sessions.update_one(
            {"id": session_id},
            {"$set": update_dict}
        )
        
        # Update bonding state's last session timestamp
        await self._update_bonding_state_session_stats(
            user_id=session.user_id,
            avatar_id=session.avatar_id,
            session=session
        )
        
        logger.info(f"Ended bonding session {session_id} (duration: {session.duration_seconds}s)")
        return session
    
    async def get_last_session_summary(
        self,
        user_id: str,
        avatar_id: str
    ) -> Optional[str]:
        """
        Get the summary of the last bonding session.
        
        Returns:
            Summary string or None if no previous session
        """
        
        last_session = await self.db.bonding_sessions.find_one(
            {"user_id": user_id, "avatar_id": avatar_id},
            sort=[("start_time", -1)]
        )
        
        if not last_session:
            return None
        
        return last_session.get("summary")
    
    async def get_session(self, session_id: str) -> Optional[BondingSession]:
        """Get a session by ID"""
        
        session_doc = await self.db.bonding_sessions.find_one({"id": session_id})
        if not session_doc:
            return None
        
        return BondingSession(**session_doc)
    
    async def get_recent_sessions(
        self,
        user_id: str,
        avatar_id: str,
        limit: int = 10
    ) -> List[BondingSession]:
        """Get recent sessions"""
        
        cursor = self.db.bonding_sessions.find(
            {"user_id": user_id, "avatar_id": avatar_id}
        ).sort("start_time", -1).limit(limit)
        
        sessions = []
        async for doc in cursor:
            sessions.append(BondingSession(**doc))
        
        return sessions
    
    async def compute_session_patterns(
        self,
        user_id: str,
        avatar_id: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Compute patterns from recent sessions.
        
        Returns:
            Dict with pattern insights
        """
        
        # Get sessions from last N days
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        
        cursor = self.db.bonding_sessions.find({
            "user_id": user_id,
            "avatar_id": avatar_id,
            "start_time": {"$gte": since.isoformat()}
        })
        
        sessions = []
        async for doc in cursor:
            sessions.append(doc)
        
        if not sessions:
            return {
                "total_sessions": 0,
                "patterns": {}
            }
        
        # Analyze patterns
        total_sessions = len(sessions)
        avg_delight = sum(s.get("delight_score", 0.5) for s in sessions) / total_sessions
        avg_duration = sum(s.get("duration_seconds", 0) for s in sessions) / total_sessions
        
        # Intent distribution
        intent_counts = {}
        for s in sessions:
            intent = s.get("detected_intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        most_common_intent = max(intent_counts, key=intent_counts.get) if intent_counts else None
        
        # Bonding mode distribution
        mode_counts = {}
        for s in sessions:
            mode = s.get("selected_bonding_mode", "unknown")
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        
        # Trends
        recent_delight = [s.get("delight_score", 0.5) for s in sessions[-5:]]
        delight_trend = "stable"
        if len(recent_delight) >= 3:
            if recent_delight[-1] > recent_delight[0] + 0.1:
                delight_trend = "rising"
            elif recent_delight[-1] < recent_delight[0] - 0.1:
                delight_trend = "falling"
        
        return {
            "total_sessions": total_sessions,
            "avg_delight_score": round(avg_delight, 2),
            "avg_duration_minutes": round(avg_duration / 60, 1),
            "most_common_intent": most_common_intent,
            "intent_distribution": intent_counts,
            "mode_distribution": mode_counts,
            "delight_trend": delight_trend,
            "recent_delight_scores": recent_delight
        }
    
    async def submit_feedback(
        self,
        session_id: str,
        rating: Optional[float] = None,
        helpful: Optional[bool] = None,
        feedback_text: Optional[str] = None
    ) -> bool:
        """
        Submit user feedback for a session.
        
        Args:
            session_id: Session ID
            rating: Star rating (0-5)
            helpful: Thumbs up/down
            feedback_text: Optional text feedback
        
        Returns:
            True if successful
        """
        
        update = {
            "user_rated": True
        }
        
        if rating is not None:
            update["user_rating"] = rating
        
        if helpful is not None:
            update["user_found_helpful"] = helpful
        
        if feedback_text:
            update["user_feedback_text"] = feedback_text
        
        result = await self.db.bonding_sessions.update_one(
            {"id": session_id},
            {"$set": update}
        )
        
        if result.modified_count > 0:
            logger.info(f"Feedback submitted for session {session_id}")
            return True
        
        return False
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    async def _generate_session_summary(
        self,
        session: BondingSession,
        bonding_state: BondingState,
        cards_generated: List[Dict[str, Any]]
    ) -> str:
        """Generate a summary of what happened in this session"""
        
        if not self.openai_client:
            # Fallback to simple summary
            return self._generate_simple_summary(session, cards_generated)
        
        try:
            # Build context
            card_descriptions = [
                f"- {card.get('type')}: {card.get('content', '')[:100]}"
                for card in cards_generated
            ]
            
            prompt = f"""Summarize this bonding conversation session in 1-2 sentences.

User intent: {session.detected_intent}
Bonding mode: {session.selected_bonding_mode}
User message: "{session.user_message}"

Response cards:
{chr(10).join(card_descriptions)}

Metrics:
- Bond delta: {bonding_state.metrics.bond_delta:+.2f}
- Trust delta: {bonding_state.metrics.trust_delta:+.2f}

Create a concise summary of what happened and how the relationship evolved."""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return self._generate_simple_summary(session, cards_generated)
    
    def _generate_simple_summary(
        self,
        session: BondingSession,
        cards_generated: List[Dict[str, Any]]
    ) -> str:
        """Simple fallback summary"""
        
        intent = session.detected_intent or "conversation"
        num_cards = len(cards_generated)
        mode = session.selected_bonding_mode or "chat"
        
        return f"Had a {intent} {mode} session. Generated {num_cards} response cards."
    
    async def _update_bonding_state_session_stats(
        self,
        user_id: str,
        avatar_id: str,
        session: BondingSession
    ):
        """Update bonding state with session stats"""
        
        # Load current state
        state_doc = await self.db.bonding_states.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        
        if not state_doc:
            return
        
        # Compute new average duration
        total_sessions = state_doc.get("total_sessions", 0) + 1
        current_avg_seconds = state_doc.get("average_session_duration", 0)
        if isinstance(current_avg_seconds, dict):  # Handle timedelta dict
            current_avg_seconds = 0
        
        new_avg_seconds = (
            (current_avg_seconds * (total_sessions - 1) + session.duration_seconds)
            / total_sessions
        )
        
        # Update
        await self.db.bonding_states.update_one(
            {"user_id": user_id, "avatar_id": avatar_id},
            {
                "$set": {
                    "last_bonding_session": session.end_time.isoformat() if session.end_time else None,
                    "total_sessions": total_sessions,
                    "average_session_duration": new_avg_seconds
                }
            }
        )
