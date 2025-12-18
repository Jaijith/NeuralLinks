"""
Character Profile
Encapsulates avatar's personality and preferences derived from knowledge graph
"""
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.rag import GraphRAG
from domain.avatar.config import get_archetype_config
import logging

logger = logging.getLogger(__name__)


class CharacterProfile:
    """
    Avatar's character derived from knowledge graph
    
    Combines:
    - Personality traits from GraphRAG
    - Interests and values from GraphRAG
    - Archetype configuration
    - Behavioral patterns (learned from history)
    - Action preferences
    """
    
    def __init__(
        self,
        avatar_id: str,
        db: AsyncIOMotorDatabase,
        graph_rag: Optional[GraphRAG] = None
    ):
        self.avatar_id = avatar_id
        self.db = db
        self.graph_rag = graph_rag or GraphRAG(db)
        
        # Character data (loaded on demand)
        self._personality_traits: Dict[str, float] = {}
        self._interests: List[str] = []
        self._values: List[str] = []
        self._archetype: str = "general"
        self._archetype_config: Dict[str, Any] = {}
        self._action_preferences: Dict[str, float] = {}
        self._loaded = False
    
    async def load(self):
        """Load character profile from database and GraphRAG"""
        try:
            # Load user document
            user = await self.db.users.find_one({"id": self.avatar_id})
            if not user:
                logger.warning(f"User {self.avatar_id} not found for character profile")
                return
            
            # Get archetype
            self._archetype = user.get("avatar_archetype") or user.get("archetype", "casual_observer")
            self._archetype_config = get_archetype_config(self._archetype)
            
            # Load from GraphRAG
            context = await self.graph_rag.get_user_context(self.avatar_id, max_nodes=50)
            
            # Extract personality traits
            traits = context.get("traits", [])
            self._personality_traits = {
                trait["label"]: trait.get("strength", 1.0)
                for trait in traits
            }
            
            # Extract interests
            interests = context.get("interests", [])
            self._interests = [interest["label"] for interest in interests]
            
            # Extract values
            values = context.get("values", [])
            self._values = [value["label"] for value in values]
            
            # Calculate action preferences based on archetype and personality
            self._calculate_action_preferences()
            
            self._loaded = True
            
            logger.info(f"Character profile loaded for {self.avatar_id}: "
                       f"archetype={self._archetype}, "
                       f"traits={len(self._personality_traits)}, "
                       f"interests={len(self._interests)}")
            
        except Exception as e:
            logger.error(f"Error loading character profile for {self.avatar_id}: {e}")
            # Set defaults
            self._archetype = "casual_observer"
            self._archetype_config = get_archetype_config(self._archetype)
            self._loaded = True
    
    def _calculate_action_preferences(self):
        """Calculate action preferences based on archetype and personality"""
        # Base preferences from archetype
        # INCREASED probabilities for create_post and message_friend across all archetypes
        archetype_prefs = {
            "social_butterfly": {
                "message_friend": 0.95,  # Increased from 0.9
                "like_post": 0.8,
                "comment_on_post": 0.8,
                "send_friend_request": 0.7,
                "create_post": 0.85  # Increased from 0.6
            },
            "thoughtful_contributor": {
                "create_post": 0.95,  # Increased from 0.8
                "comment_on_post": 0.9,
                "message_friend": 0.85,  # Increased from 0.7
                "like_post": 0.6,
                "send_friend_request": 0.5
            },
            "casual_observer": {
                "like_post": 0.7,
                "browse_feed": 0.8,
                "read_messages": 0.7,
                "create_post": 0.75,  # Increased from 0.5
                "message_friend": 0.75  # Increased from 0.5
            },
            "niche_expert": {
                "create_post": 0.95,  # Increased from 0.8
                "comment_on_post": 0.7,
                "like_post": 0.6,
                "message_friend": 0.75  # Increased from 0.5
            },
            "enthusiastic_newcomer": {
                "send_friend_request": 0.8,
                "message_friend": 0.9,  # Increased from 0.8
                "like_post": 0.7,
                "create_post": 0.85,  # Increased from 0.6
                "discover_profiles": 0.9
            }
        }
        
        # Start with archetype preferences
        self._action_preferences = archetype_prefs.get(self._archetype, {}).copy()
        
        # Adjust based on personality traits
        if "outgoing" in self._personality_traits or "extroverted" in self._personality_traits:
            self._action_preferences["message_friend"] = min(1.0, self._action_preferences.get("message_friend", 0.5) + 0.2)
            self._action_preferences["send_friend_request"] = min(1.0, self._action_preferences.get("send_friend_request", 0.5) + 0.2)
        
        if "creative" in self._personality_traits or "artistic" in self._personality_traits:
            self._action_preferences["create_post"] = min(1.0, self._action_preferences.get("create_post", 0.5) + 0.3)
        
        if "thoughtful" in self._personality_traits or "analytical" in self._personality_traits:
            self._action_preferences["comment_on_post"] = min(1.0, self._action_preferences.get("comment_on_post", 0.5) + 0.2)
        
        if "introverted" in self._personality_traits or "shy" in self._personality_traits:
            self._action_preferences["message_friend"] = max(0.0, self._action_preferences.get("message_friend", 0.5) - 0.3)
            self._action_preferences["send_friend_request"] = max(0.0, self._action_preferences.get("send_friend_request", 0.5) - 0.2)
    
    def get_action_modifier(self, action_type: str) -> float:
        """
        Get modifier (0.0 - 2.0) for action based on character
        
        Returns:
            Modifier value (1.0 = neutral, >1.0 = preferred, <1.0 = less preferred)
        """
        if not self._loaded:
            return 1.0
        
        preference = self._action_preferences.get(action_type, 0.5)
        # Convert preference (0-1) to modifier (0.5-2.0)
        # 0.0 preference -> 0.5 modifier (discouraged)
        # 0.5 preference -> 1.0 modifier (neutral)
        # 1.0 preference -> 2.0 modifier (strongly preferred)
        modifier = 0.5 + (preference * 1.5)
        return modifier
    
    def get_personality_traits(self) -> Dict[str, float]:
        """Get personality traits"""
        return self._personality_traits.copy()
    
    def get_interests(self) -> List[str]:
        """Get interests"""
        return self._interests.copy()
    
    def get_values(self) -> List[str]:
        """Get values"""
        return self._values.copy()
    
    def get_archetype(self) -> str:
        """Get archetype"""
        return self._archetype
    
    def get_archetype_config(self) -> Dict[str, Any]:
        """Get archetype configuration"""
        return self._archetype_config.copy()
    
    def get_action_preferences(self) -> Dict[str, float]:
        """Get action preferences"""
        return self._action_preferences.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "avatar_id": self.avatar_id,
            "archetype": self._archetype,
            "personality_traits": self._personality_traits,
            "interests": self._interests,
            "values": self._values,
            "action_preferences": self._action_preferences,
            "archetype_config": self._archetype_config
        }
    
    def is_loaded(self) -> bool:
        """Check if profile is loaded"""
        return self._loaded

