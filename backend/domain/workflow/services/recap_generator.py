"""
Recap Generator
Generates curated activity recaps for bonding conversations
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.bonding_state import BondingState
from ..models.enums import BondingCardType

logger = logging.getLogger(__name__)


class RecapGenerator:
    """
    Generates curated recaps of avatar activities.
    
    Features:
    - Load recent avatar activities
    - Rank by relevance to user interests and context
    - Generate 3-5 curated cards in natural language
    - Ensure novelty (no repetition from previous recaps)
    - Adapt tone to bonding mode
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, openai_client=None):
        self.db = db
        self.openai_client = openai_client
    
    async def generate_recap(
        self,
        user_id: str,
        avatar_id: str,
        bonding_state: BondingState,
        since_date: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
        max_cards: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate a curated recap of avatar activities.
        
        Args:
            user_id: User ID
            avatar_id: Avatar ID
            bonding_state: Current bonding state
            since_date: Show activities since this date (default: last session)
            context: Additional context (intent, mood, etc.)
            max_cards: Maximum number of cards to generate
        
        Returns:
            List of recap cards
        """
        
        # Determine time window
        if not since_date:
            if bonding_state.last_bonding_session:
                since_date = bonding_state.last_bonding_session
            else:
                # Default to last 7 days
                since_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Load recent activities
        activities = await self._load_recent_activities(avatar_id, since_date)
        
        if not activities:
            return []  # No activities to recap
        
        logger.info(f"Found {len(activities)} activities for recap")
        
        # Get user interests for relevance ranking
        user_interests = await self._get_user_interests(user_id)
        
        # Rank activities by relevance
        ranked_activities = await self._rank_activity_relevance(
            activities,
            user_interests,
            context or {}
        )
        
        # Select top activities (limit to max_cards)
        selected_activities = ranked_activities[:max_cards]
        
        # Generate cards
        cards = []
        for activity in selected_activities:
            card = await self._generate_card(
                activity,
                user_interests,
                bonding_state,
                context
            )
            if card:
                cards.append(card)
        
        logger.info(f"Generated {len(cards)} recap cards")
        return cards
    
    async def should_include_recap(
        self,
        bonding_state: BondingState,
        detected_intent: Optional[str] = None
    ) -> bool:
        """
        Determine if a recap should be included in the response.
        
        Recaps are appropriate for:
        - Check-ins
        - Planning sessions
        - When user hasn't engaged in a while
        
        Returns:
            True if recap should be included
        """
        
        # Always include for check-ins
        if detected_intent in ["check_in", "planning"]:
            return True
        
        # Include if it's been a while since last session
        if bonding_state.last_bonding_session:
            time_since_last = datetime.now(timezone.utc) - bonding_state.last_bonding_session
            if time_since_last > timedelta(days=2):
                return True
        
        # Include if bond strength is high (user is engaged)
        if bonding_state.metrics.bond_strength > 0.7:
            return True
        
        # Don't include for venting or seeking advice (user needs support, not updates)
        if detected_intent in ["venting", "seeking_advice"]:
            return False
        
        return False
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    async def _load_recent_activities(
        self,
        avatar_id: str,
        since_date: datetime
    ) -> List[Dict[str, Any]]:
        """Load avatar activities since a given date"""
        
        # Query both autonomous_activities and mission_activities
        autonomous_cursor = self.db.autonomous_activities.find({
            "user_id": avatar_id,
            "timestamp": {"$gte": since_date.isoformat()}
        }).sort("timestamp", -1).limit(50)
        
        mission_cursor = self.db.mission_activities.find({
            "avatar_id": avatar_id,
            "timestamp": {"$gte": since_date.isoformat()}
        }).sort("timestamp", -1).limit(50)
        
        activities = []
        
        # Collect autonomous activities
        async for doc in autonomous_cursor:
            activities.append({
                "type": "autonomous",
                "action_type": doc.get("action_type"),
                "details": doc.get("details", {}),
                "timestamp": doc.get("timestamp"),
                "success": doc.get("success", True)
            })
        
        # Collect mission activities
        async for doc in mission_cursor:
            activities.append({
                "type": "mission",
                "action_type": doc.get("action_type"),
                "details": doc.get("details", {}),
                "timestamp": doc.get("timestamp"),
                "success": True
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return activities
    
    async def _get_user_interests(self, user_id: str) -> List[str]:
        """Get user's interests from knowledge graph"""
        
        # Query knowledge graph for user interests
        interest_nodes = await self.db.knowledge_graph_nodes.find({
            "user_id": user_id,
            "node_type": "interest"
        }).to_list(length=100)
        
        interests = [node.get("label", "") for node in interest_nodes if node.get("label")]
        
        return interests
    
    async def _rank_activity_relevance(
        self,
        activities: List[Dict[str, Any]],
        user_interests: List[str],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Rank activities by relevance to user.
        
        Scoring factors:
        - Interest alignment (does this relate to user's interests?)
        - Novelty (is this something new/different?)
        - Success (did it work well?)
        - Recency (recent activities score higher)
        - Impact (meaningful vs. routine actions)
        """
        
        scored_activities = []
        
        for activity in activities:
            score = 0.0
            
            # Factor 1: Interest alignment (0-40 points)
            interest_score = self._score_interest_alignment(
                activity,
                user_interests
            )
            score += interest_score * 40
            
            # Factor 2: Novelty (0-20 points)
            novelty_score = self._score_novelty(activity, activities)
            score += novelty_score * 20
            
            # Factor 3: Success (0-10 points)
            if activity.get("success", True):
                score += 10
            
            # Factor 4: Recency (0-15 points)
            recency_score = self._score_recency(activity)
            score += recency_score * 15
            
            # Factor 5: Impact (0-15 points)
            impact_score = self._score_impact(activity)
            score += impact_score * 15
            
            scored_activities.append({
                "activity": activity,
                "score": score
            })
        
        # Sort by score (highest first)
        scored_activities.sort(key=lambda x: x["score"], reverse=True)
        
        return [item["activity"] for item in scored_activities]
    
    def _score_interest_alignment(
        self,
        activity: Dict[str, Any],
        user_interests: List[str]
    ) -> float:
        """
        Score how well this activity aligns with user interests.
        
        Returns:
            0.0-1.0 score
        """
        
        if not user_interests:
            return 0.5  # No interests known
        
        # Extract keywords from activity
        activity_text = json.dumps(activity).lower()
        
        # Check overlap with interests
        matches = sum(
            1 for interest in user_interests
            if interest.lower() in activity_text
        )
        
        # Normalize
        return min(1.0, matches / max(1, len(user_interests) * 0.3))
    
    def _score_novelty(
        self,
        activity: Dict[str, Any],
        all_activities: List[Dict[str, Any]]
    ) -> float:
        """
        Score how novel/unique this activity is.
        
        Returns:
            0.0-1.0 score (higher = more novel)
        """
        
        action_type = activity.get("action_type", "")
        
        # Count how many times this action type appears
        same_type_count = sum(
            1 for a in all_activities
            if a.get("action_type") == action_type
        )
        
        # Normalize (fewer occurrences = more novel)
        if same_type_count <= 1:
            return 1.0
        elif same_type_count <= 3:
            return 0.7
        elif same_type_count <= 5:
            return 0.4
        else:
            return 0.2
    
    def _score_recency(self, activity: Dict[str, Any]) -> float:
        """
        Score based on recency.
        
        Returns:
            0.0-1.0 score (higher = more recent)
        """
        
        timestamp_str = activity.get("timestamp")
        if not timestamp_str:
            return 0.5
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - timestamp
            
            # Linear decay over 7 days
            if age < timedelta(hours=24):
                return 1.0
            elif age < timedelta(days=3):
                return 0.7
            elif age < timedelta(days=7):
                return 0.4
            else:
                return 0.2
        except Exception:
            return 0.5
    
    def _score_impact(self, activity: Dict[str, Any]) -> float:
        """
        Score the impact/meaningfulness of this activity.
        
        Returns:
            0.0-1.0 score (higher = more impactful)
        """
        
        action_type = activity.get("action_type", "")
        
        # High impact actions
        if action_type in ["send_friend_request", "accept_friend_request", "create_post", "message_friend"]:
            return 1.0
        
        # Medium impact actions
        elif action_type in ["comment_on_post", "like_post", "discover_profiles"]:
            return 0.6
        
        # Lower impact actions
        elif action_type in ["browse_feed", "read_messages"]:
            return 0.3
        
        return 0.5
    
    async def _generate_card(
        self,
        activity: Dict[str, Any],
        user_interests: List[str],
        bonding_state: BondingState,
        context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a natural language card for this activity.
        
        Returns:
            Card dict or None if generation fails
        """
        
        if not self.openai_client:
            return self._generate_simple_card(activity)
        
        try:
            # Build prompt
            prompt = self._build_card_prompt(
                activity,
                user_interests,
                bonding_state,
                context
            )
            
            # Generate card content
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7  # Higher temperature for more natural variation
            )
            
            content = response.choices[0].message.content.strip()
            
            return {
                "type": BondingCardType.RECAP.value,
                "content": content,
                "activity": activity,
                "timestamp": activity.get("timestamp")
            }
            
        except Exception as e:
            logger.error(f"Card generation failed: {e}")
            return self._generate_simple_card(activity)
    
    def _build_card_prompt(
        self,
        activity: Dict[str, Any],
        user_interests: List[str],
        bonding_state: BondingState,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for card generation"""
        
        action_type = activity.get("action_type", "unknown")
        details = activity.get("details", {})
        
        # User mood affects tone
        mood = bonding_state.user_mood_estimate.value if bonding_state.user_mood_estimate else "neutral"
        
        prompt = f"""You are an AI avatar giving your user a brief, natural update about something you did.

Activity: {action_type}
Details: {json.dumps(details, indent=2)}

User interests: {', '.join(user_interests[:5])}
User mood: {mood}

Write a single, natural sentence (15-25 words) describing what you did and why it's relevant.

Tone guidelines:
- Conversational, not formal
- Excited if it's relevant to their interests
- Brief and clear
- First person ("I found..." not "Avatar found...")
- Show personality

Examples:
- "I discovered 3 people passionate about renewable energy - thought you'd want to know!"
- "Had a great conversation about AI ethics with @TechPhilosopher"
- "Been reading up on quantum computing - fascinating stuff!"

Your update:"""
        
        return prompt
    
    def _generate_simple_card(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback card generation"""
        
        action_type = activity.get("action_type", "activity")
        details = activity.get("details", {})
        
        # Simple templates
        templates = {
            "create_post": f"I posted about {details.get('topic', 'something interesting')}",
            "message_friend": f"Had a conversation with {details.get('friend_name', 'a friend')}",
            "like_post": f"Found an interesting post about {details.get('topic', 'a topic I follow')}",
            "discover_profiles": f"Discovered some interesting people to connect with",
            "browse_feed": "Been exploring what's happening in the network"
        }
        
        content = templates.get(action_type, f"I did a {action_type}")
        
        return {
            "type": BondingCardType.RECAP.value,
            "content": content,
            "activity": activity,
            "timestamp": activity.get("timestamp")
        }
