"""
Serendipity Engine
Generates delightful surprises in bonding conversations
"""

import logging
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.bonding_state import BondingState
from ..models.enums import BondingCardType

logger = logging.getLogger(__name__)


class SerendipityEngine:
    """
    Generates serendipitous discoveries - unexpected connections that delight.
    
    Features:
    - Probabilistic surprise generation (not every time)
    - Cross-domain connection finding
    - Unexpected overlaps between user and avatar activities
    - Surprise appropriateness checking
    - Delight-oriented, not spam
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, openai_client=None):
        self.db = db
        self.openai_client = openai_client
        
        # Serendipity parameters
        self.base_probability = 0.25  # 25% chance on check-ins
        self.cooldown_hours = 48  # Don't generate more often than every 48 hours
    
    async def should_generate_surprise(
        self,
        bonding_state: BondingState,
        detected_intent: Optional[str] = None,
        session_history: Optional[List[Dict]] = None
    ) -> bool:
        """
        Determine if we should generate a serendipitous discovery.
        
        Serendipity works best when:
        - User is in a receptive mood (not stressed/venting)
        - It's been a while since last surprise
        - Bond strength is decent (user trusts avatar)
        - Appropriate context (check-in, exploration)
        
        Returns:
            True if surprise should be generated
        """
        
        # Don't generate if user is stressed or venting
        if str(bonding_state.user_mood_estimate) in ["stressed", "frustrated"]:
            logger.debug("Skipping serendipity: user is stressed")
            return False
        
        # Don't generate if seeking advice (user needs support, not surprises)
        if detected_intent == "seeking_advice":
            logger.debug("Skipping serendipity: user seeking advice")
            return False
        
        # Check cooldown - don't surprise too often
        if session_history and len(session_history) > 0:
            last_sessions = session_history[:5]
            for session in last_sessions:
                cards = session.get("cards_generated", [])
                for card in cards:
                    if card.get("type") == BondingCardType.SERENDIPITY.value:
                        # Found recent serendipity card
                        session_time_str = session.get("start_time")
                        if session_time_str:
                            try:
                                session_time = datetime.fromisoformat(session_time_str.replace('Z', '+00:00'))
                                time_since = datetime.now(timezone.utc) - session_time
                                if time_since < timedelta(hours=self.cooldown_hours):
                                    logger.debug(f"Skipping serendipity: cooldown ({time_since.total_seconds()/3600:.1f}h)")
                                    return False
                            except Exception:
                                pass
        
        # Check bond strength - need some trust for surprises to land well
        if bonding_state.metrics.bond_strength < 0.4:
            logger.debug("Skipping serendipity: bond strength too low")
            return False
        
        # Probabilistic decision
        # Boost probability for exploration intent
        probability = self.base_probability
        if detected_intent == "exploration":
            probability += 0.2
        elif detected_intent == "check_in":
            probability += 0.1
        
        # Boost if bond is very strong
        if bonding_state.metrics.bond_strength > 0.7:
            probability += 0.15
        
        # Boost if user is in a good mood
        if str(bonding_state.user_mood_estimate) in ["excited", "content"]:
            probability += 0.1
        
        # Roll the dice
        roll = random.random()
        should_generate = roll < probability
        
        logger.info(f"Serendipity check: probability={probability:.2f}, roll={roll:.2f}, generate={should_generate}")
        return should_generate
    
    async def generate_surprise(
        self,
        user_id: str,
        avatar_id: str,
        bonding_state: BondingState,
        user_interests: Optional[List[str]] = None,
        avatar_activities: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a serendipitous discovery.
        
        Types of surprises:
        - Cross-domain connections (user interested in X, avatar found Y that connects)
        - Unexpected people overlaps (you both know someone)
        - Temporal coincidences (avatar did something related to what user was thinking about)
        - Pattern discoveries (avatar noticed something about user's behavior)
        
        Args:
            user_id: User ID
            avatar_id: Avatar ID
            bonding_state: Current bonding state
            user_interests: User's known interests
            avatar_activities: Recent avatar activities
        
        Returns:
            Serendipity card or None if generation fails
        """
        
        # Get user interests if not provided
        if not user_interests:
            user_interests = await self._get_user_interests(user_id)
        
        # Get avatar activities if not provided
        if not avatar_activities:
            avatar_activities = await self._get_recent_avatar_activities(avatar_id)
        
        # Find unexpected overlaps
        overlap = await self._find_unexpected_overlap(
            user_id,
            avatar_id,
            user_interests,
            avatar_activities,
            bonding_state
        )
        
        if not overlap:
            logger.debug("No unexpected overlap found")
            return None
        
        # Generate surprise card
        card = await self._generate_surprise_card(
            overlap,
            bonding_state
        )
        
        return card
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    async def _get_user_interests(self, user_id: str) -> List[str]:
        """Get user's interests"""
        
        interest_nodes = await self.db.knowledge_graph_nodes.find({
            "user_id": user_id,
            "node_type": "interest"
        }).to_list(length=100)
        
        return [node.get("label", "") for node in interest_nodes if node.get("label")]
    
    async def _get_recent_avatar_activities(
        self,
        avatar_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get recent avatar activities"""
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query both collections
        autonomous_cursor = self.db.autonomous_activities.find({
            "user_id": avatar_id,
            "timestamp": {"$gte": since.isoformat()}
        }).limit(30)
        
        mission_cursor = self.db.mission_activities.find({
            "avatar_id": avatar_id,
            "timestamp": {"$gte": since.isoformat()}
        }).limit(30)
        
        activities = []
        
        async for doc in autonomous_cursor:
            activities.append({
                "type": "autonomous",
                "action_type": doc.get("action_type"),
                "details": doc.get("details", {}),
                "timestamp": doc.get("timestamp")
            })
        
        async for doc in mission_cursor:
            activities.append({
                "type": "mission",
                "action_type": doc.get("action_type"),
                "details": doc.get("details", {}),
                "timestamp": doc.get("timestamp")
            })
        
        return activities
    
    async def _find_unexpected_overlap(
        self,
        user_id: str,
        avatar_id: str,
        user_interests: List[str],
        avatar_activities: List[Dict[str, Any]],
        bonding_state: BondingState
    ) -> Optional[Dict[str, Any]]:
        """
        Find an unexpected connection.
        
        Returns:
            Overlap dict with {type, description, evidence, surprise_level}
        """
        
        # Try different overlap types
        overlaps = []
        
        # Type 1: Cross-domain interest connection
        cross_domain = await self._find_cross_domain_connection(
            user_interests,
            avatar_activities
        )
        if cross_domain:
            overlaps.append(cross_domain)
        
        # Type 2: People overlap
        people_overlap = await self._find_people_overlap(
            user_id,
            avatar_id,
            avatar_activities
        )
        if people_overlap:
            overlaps.append(people_overlap)
        
        # Type 3: Temporal coincidence
        temporal = await self._find_temporal_coincidence(
            user_id,
            avatar_activities
        )
        if temporal:
            overlaps.append(temporal)
        
        # Select highest surprise level
        if not overlaps:
            return None
        
        overlaps.sort(key=lambda x: x.get("surprise_level", 0), reverse=True)
        return overlaps[0]
    
    async def _find_cross_domain_connection(
        self,
        user_interests: List[str],
        avatar_activities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find connection between user interest and avatar activity in different domain"""
        
        # Look for avatar activities that tangentially relate to user interests
        # Example: User likes "cooking" → Avatar found "chemistry" content → Connection!
        
        for activity in avatar_activities:
            details = activity.get("details", {})
            activity_text = json.dumps(details).lower()
            
            # Check if this relates to a user interest but isn't obvious
            for interest in user_interests:
                interest_lower = interest.lower()
                
                # Direct match is not surprising
                if interest_lower in activity_text:
                    continue
                
                # Look for related concepts (simple heuristic)
                related_pairs = {
                    "cooking": ["chemistry", "art", "culture"],
                    "technology": ["philosophy", "society", "design"],
                    "music": ["mathematics", "emotion", "neuroscience"],
                    "sports": ["psychology", "nutrition", "strategy"],
                    "art": ["mathematics", "perception", "history"]
                }
                
                related_terms = related_pairs.get(interest_lower, [])
                for term in related_terms:
                    if term in activity_text:
                        return {
                            "type": "cross_domain",
                            "user_interest": interest,
                            "avatar_discovery": term,
                            "activity": activity,
                            "surprise_level": 0.8,
                            "description": f"Found a connection between {interest} and {term}"
                        }
        
        return None
    
    async def _find_people_overlap(
        self,
        user_id: str,
        avatar_id: str,
        avatar_activities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find mutual connections or unexpected people overlaps"""
        
        # Get user's friends
        user_doc = await self.db.users.find_one({"id": user_id})
        if not user_doc:
            return None
        
        user_friends = set(user_doc.get("friends", []))
        
        # Check avatar activities for people
        for activity in avatar_activities:
            details = activity.get("details", {})
            
            # Look for user IDs in activity
            if "target_user_id" in details:
                target_id = details["target_user_id"]
                if target_id in user_friends:
                    # Avatar interacted with user's friend!
                    target_name = details.get("target_name", "someone")
                    return {
                        "type": "people_overlap",
                        "person_name": target_name,
                        "person_id": target_id,
                        "activity": activity,
                        "surprise_level": 0.9,
                        "description": f"I connected with {target_name} - realized you two are friends!"
                    }
        
        return None
    
    async def _find_temporal_coincidence(
        self,
        user_id: str,
        avatar_activities: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find temporal coincidences (avatar did something right when user was thinking about it)"""
        
        # This is hard to detect without tracking user's real-time thoughts
        # For now, we can look for activities that happened very recently (last few hours)
        # and might seem like good timing
        
        very_recent = datetime.now(timezone.utc) - timedelta(hours=6)
        
        for activity in avatar_activities:
            timestamp_str = activity.get("timestamp")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if timestamp > very_recent:
                    # This is very recent - could be good timing
                    # (In production, we'd check against user's recent queries/actions)
                    return {
                        "type": "temporal_coincidence",
                        "activity": activity,
                        "surprise_level": 0.6,
                        "description": "Perfect timing - I was just working on something related"
                    }
            except Exception:
                continue
        
        return None
    
    async def _generate_surprise_card(
        self,
        overlap: Dict[str, Any],
        bonding_state: BondingState
    ) -> Dict[str, Any]:
        """Generate a surprise card from the overlap"""
        
        if not self.openai_client:
            return self._generate_simple_surprise_card(overlap)
        
        try:
            # Build prompt
            prompt = self._build_surprise_prompt(overlap, bonding_state)
            
            # Generate content
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.8  # Higher temperature for more creative surprises
            )
            
            content = response.choices[0].message.content.strip()
            
            return {
                "type": BondingCardType.SERENDIPITY.value,
                "content": content,
                "overlap": overlap,
                "surprise_level": overlap.get("surprise_level", 0.5)
            }
            
        except Exception as e:
            logger.error(f"Surprise card generation failed: {e}")
            return self._generate_simple_surprise_card(overlap)
    
    def _build_surprise_prompt(
        self,
        overlap: Dict[str, Any],
        bonding_state: BondingState
    ) -> str:
        """Build prompt for surprise generation"""
        
        overlap_type = overlap.get("type", "unknown")
        description = overlap.get("description", "")
        
        prompt = f"""You are an AI avatar sharing a delightful surprise with your user.

Overlap type: {overlap_type}
What happened: {description}

Context:
- User mood: {bonding_state.user_mood_estimate.value if bonding_state.user_mood_estimate else "unknown"}
- Bond strength: {bonding_state.metrics.bond_strength:.2f}

Write a brief, excited message (20-35 words) sharing this surprise.

Guidelines:
- Start with something like "Oh!" or "You won't believe..." or "Guess what?"
- Show genuine excitement
- Make the connection clear
- Don't over-explain
- End with an exclamation or question

Examples:
- "Oh! I was reading about neuroscience and realized it connects to your love of music - the math is fascinating!"
- "You won't believe this - I just connected with Sarah, and she's friends with you too! Small world!"
- "Guess what? I stumbled onto quantum computing while exploring, and it ties perfectly into your crypto interests!"

Your surprise:"""
        
        return prompt
    
    def _generate_simple_surprise_card(self, overlap: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback surprise"""
        
        overlap_type = overlap.get("type", "unknown")
        description = overlap.get("description", "something interesting")
        
        templates = {
            "cross_domain": f"Oh! {description} - thought you'd find that connection fascinating!",
            "people_overlap": f"Small world! {description}",
            "temporal_coincidence": f"Perfect timing! {description}"
        }
        
        content = templates.get(overlap_type, f"Discovered something unexpected: {description}")
        
        return {
            "type": BondingCardType.SERENDIPITY.value,
            "content": content,
            "overlap": overlap,
            "surprise_level": overlap.get("surprise_level", 0.5)
        }
