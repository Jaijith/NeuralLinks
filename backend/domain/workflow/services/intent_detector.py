"""
Intent & Emotion Detector
Enhanced detection for bonding conversations
"""

import logging
import json
from typing import Dict, Tuple, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.enums import UserIntent, UserMood, UserEmotion
from ..models.chat import AvatarChatSession

logger = logging.getLogger(__name__)


class IntentDetector:
    """
    Detects user intent and emotion in bonding conversations.
    
    Features:
    - Bonding-specific intent detection (check-in, venting, planning, etc.)
    - Emotion detection (stressed, excited, bored, etc.)
    - Mood estimation
    - Confidence scoring
    - Clarifying questions for low-confidence detections
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, openai_client=None):
        self.db = db
        self.openai_client = openai_client
    
    async def detect_intent(
        self,
        message: str,
        session: AvatarChatSession,
        context: Optional[Dict] = None
    ) -> Tuple[UserIntent, float]:
        """
        Detect user's intent in a bonding conversation.
        
        Args:
            message: The user's message
            session: The chat session (for context)
            context: Additional context (bonding state, etc.)
        
        Returns:
            (intent, confidence) tuple
        """
        
        if not self.openai_client:
            # Fallback to keyword matching
            return self._detect_intent_fallback(message)
        
        try:
            # Build prompt with context
            prompt = self._build_intent_prompt(message, session, context)
            
            # Call GPT-4 for intent detection
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.3  # Lower temperature for more consistent detection
            )
            
            result = json.loads(response.choices[0].message.content)
            
            intent_str = result.get("intent", "general_chat")
            confidence = result.get("confidence", 0.5)
            
            # Convert string to enum
            try:
                intent = UserIntent(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent '{intent_str}', defaulting to GENERAL_CHAT")
                intent = UserIntent.GENERAL_CHAT
                confidence = 0.3
            
            logger.info(f"Intent detected: {intent.value} (confidence: {confidence:.2f})")
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return self._detect_intent_fallback(message)
    
    async def detect_emotion(
        self,
        message: str,
        session: AvatarChatSession,
        context: Optional[Dict] = None
    ) -> Tuple[UserEmotion, float]:
        """
        Detect user's emotion from their message.
        
        Args:
            message: The user's message
            session: The chat session (for context)
            context: Additional context
        
        Returns:
            (emotion, confidence) tuple
        """
        
        if not self.openai_client:
            # Fallback to basic detection
            return self._detect_emotion_fallback(message)
        
        try:
            # Build prompt
            prompt = self._build_emotion_prompt(message, session, context)
            
            # Call GPT-4 for emotion detection
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            emotion_str = result.get("emotion", "calm")
            confidence = result.get("confidence", 0.5)
            
            # Convert string to enum
            try:
                emotion = UserEmotion(emotion_str)
            except ValueError:
                logger.warning(f"Unknown emotion '{emotion_str}', defaulting to CALM")
                emotion = UserEmotion.CALM
                confidence = 0.3
            
            logger.info(f"Emotion detected: {emotion.value} (confidence: {confidence:.2f})")
            return emotion, confidence
            
        except Exception as e:
            logger.error(f"Emotion detection failed: {e}")
            return self._detect_emotion_fallback(message)
    
    async def estimate_mood(
        self,
        message: str,
        session: AvatarChatSession,
        recent_emotions: Optional[List[UserEmotion]] = None
    ) -> Tuple[UserMood, float]:
        """
        Estimate user's overall mood.
        
        Mood is more stable than emotion - it's the underlying state.
        
        Args:
            message: Current message
            session: Chat session
            recent_emotions: Recent emotional states (for pattern detection)
        
        Returns:
            (mood, confidence) tuple
        """
        
        # Detect current emotion
        emotion, emotion_confidence = await self.detect_emotion(message, session)
        
        # Map emotion → mood (with context from recent emotions)
        mood = self._map_emotion_to_mood(emotion, recent_emotions)
        
        # Confidence is based on emotion confidence and pattern strength
        confidence = emotion_confidence
        if recent_emotions and len(recent_emotions) >= 3:
            # If we have a pattern, increase confidence
            confidence = min(0.9, confidence + 0.2)
        
        logger.info(f"Mood estimated: {mood.value} (confidence: {confidence:.2f})")
        return mood, confidence
    
    async def should_ask_clarifying_question(
        self,
        intent: UserIntent,
        intent_confidence: float,
        emotion: UserEmotion,
        emotion_confidence: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should ask a clarifying question.
        
        Returns:
            (should_ask, question) tuple
        """
        
        # If both intent and emotion are high confidence, no need to clarify
        if intent_confidence > 0.75 and emotion_confidence > 0.75:
            return False, None
        
        # If intent is very unclear
        if intent_confidence < 0.5:
            questions = {
                UserIntent.CHECK_IN: "Just checking in, or is there something specific on your mind?",
                UserIntent.VENTING: "Do you want to just vent, or are you looking for advice?",
                UserIntent.PLANNING: "Are you thinking of starting something new?",
                UserIntent.SEEKING_ADVICE: "What would be most helpful right now?",
            }
            return True, questions.get(intent, "What can I help you with?")
        
        # If emotion is unclear and might affect how we respond
        if emotion_confidence < 0.5:
            return True, "How are you feeling about this?"
        
        return False, None
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    def _build_intent_prompt(
        self,
        message: str,
        session: AvatarChatSession,
        context: Optional[Dict]
    ) -> str:
        """Build prompt for intent detection"""
        
        recent_messages = session.get_conversation_history(limit=5)
        recent_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in recent_messages[-3:]
        ])
        
        prompt = f"""Classify the user's intent in this bonding conversation with their AI avatar.

User's message: "{message}"

Recent conversation:
{recent_context}

Possible intents:
- check_in: Casual "how's it going?" status check
- venting: Emotional release, frustration, stress
- planning: Goal setting, wanting to achieve something
- reflection: Looking back, retrospective thinking
- seeking_advice: Asking for guidance or help
- celebration: Sharing success, excitement
- exploration: Curious, wanting to discover something
- general_chat: Casual conversation

Return JSON: {{"intent": "intent_name", "confidence": 0.0-1.0}}

Consider:
- Emotional tone
- Question vs. statement
- Past context
- Urgency"""
        
        return prompt
    
    def _build_emotion_prompt(
        self,
        message: str,
        session: AvatarChatSession,
        context: Optional[Dict]
    ) -> str:
        """Build prompt for emotion detection"""
        
        prompt = f"""Detect the user's emotional state from this message to their AI avatar.

User's message: "{message}"

Possible emotions:
- happy: Joyful, pleased
- sad: Down, disappointed
- angry: Frustrated, irritated
- anxious: Worried, nervous
- calm: Peaceful, relaxed
- confused: Uncertain, unclear
- confident: Sure, assured
- disappointed: Let down, unsatisfied
- grateful: Thankful, appreciative
- curious: Interested, wondering
- overwhelmed: Too much, stressed
- relieved: Unburdened, at ease

Return JSON: {{"emotion": "emotion_name", "confidence": 0.0-1.0}}

Consider:
- Word choice (strong words = high emotion)
- Punctuation (exclamations, questions)
- Length (venting vs. brief)
- Capitalization"""
        
        return prompt
    
    def _detect_intent_fallback(self, message: str) -> Tuple[UserIntent, float]:
        """Fallback keyword-based intent detection"""
        
        lower = message.lower()
        
        # Check-in patterns
        if any(kw in lower for kw in ["how's it going", "what's up", "checking in", "status", "update"]):
            return UserIntent.CHECK_IN, 0.7
        
        # Venting patterns
        if any(kw in lower for kw in ["frustrated", "annoyed", "stressed", "overwhelmed", "can't believe", "so tired"]):
            return UserIntent.VENTING, 0.7
        
        # Planning patterns
        if any(kw in lower for kw in ["want to", "going to", "planning", "goal", "achieve", "start"]):
            return UserIntent.PLANNING, 0.7
        
        # Seeking advice patterns
        if any(kw in lower for kw in ["should i", "what do you think", "advice", "help me", "not sure"]):
            return UserIntent.SEEKING_ADVICE, 0.7
        
        # Celebration patterns
        if any(kw in lower for kw in ["did it", "accomplished", "finished", "success", "yay", "excited"]):
            return UserIntent.CELEBRATION, 0.7
        
        # Reflection patterns
        if any(kw in lower for kw in ["thinking about", "looking back", "realize", "learned", "noticed"]):
            return UserIntent.REFLECTION, 0.6
        
        # Exploration patterns
        if any(kw in lower for kw in ["curious", "wondering", "explore", "discover", "find out"]):
            return UserIntent.EXPLORATION, 0.6
        
        return UserIntent.GENERAL_CHAT, 0.5
    
    def _detect_emotion_fallback(self, message: str) -> Tuple[UserEmotion, float]:
        """Fallback keyword-based emotion detection"""
        
        lower = message.lower()
        
        # Strong emotion indicators
        if any(kw in lower for kw in ["love", "amazing", "great", "awesome", "fantastic"]):
            return UserEmotion.HAPPY, 0.7
        
        if any(kw in lower for kw in ["sad", "disappointed", "down", "bummed"]):
            return UserEmotion.SAD, 0.7
        
        if any(kw in lower for kw in ["angry", "mad", "furious", "annoyed", "frustrated"]):
            return UserEmotion.ANGRY, 0.7
        
        if any(kw in lower for kw in ["worried", "nervous", "anxious", "scared"]):
            return UserEmotion.ANXIOUS, 0.7
        
        if any(kw in lower for kw in ["overwhelmed", "too much", "can't handle"]):
            return UserEmotion.OVERWHELMED, 0.7
        
        if any(kw in lower for kw in ["confused", "unclear", "don't understand"]):
            return UserEmotion.CONFUSED, 0.6
        
        if any(kw in lower for kw in ["grateful", "thankful", "appreciate"]):
            return UserEmotion.GRATEFUL, 0.7
        
        if any(kw in lower for kw in ["curious", "interested", "wondering"]):
            return UserEmotion.CURIOUS, 0.6
        
        if any(kw in lower for kw in ["relieved", "better", "calmed down"]):
            return UserEmotion.RELIEVED, 0.6
        
        return UserEmotion.CALM, 0.5
    
    def _map_emotion_to_mood(
        self,
        emotion: UserEmotion,
        recent_emotions: Optional[List[UserEmotion]] = None
    ) -> UserMood:
        """Map emotion to underlying mood"""
        
        # Direct mappings
        emotion_to_mood = {
            UserEmotion.HAPPY: UserMood.EXCITED,  # Happy maps to excited mood
            UserEmotion.GRATEFUL: UserMood.CONTENT,
            UserEmotion.CONFIDENT: UserMood.CONTENT,
            UserEmotion.RELIEVED: UserMood.CONTENT,
            
            UserEmotion.SAD: UserMood.REFLECTIVE,
            UserEmotion.DISAPPOINTED: UserMood.FRUSTRATED,
            
            UserEmotion.ANGRY: UserMood.FRUSTRATED,
            
            UserEmotion.ANXIOUS: UserMood.STRESSED,
            UserEmotion.OVERWHELMED: UserMood.STRESSED,
            
            UserEmotion.CONFUSED: UserMood.NEUTRAL,
            UserEmotion.CALM: UserMood.NEUTRAL,
            
            UserEmotion.CURIOUS: UserMood.REFLECTIVE,
        }
        
        base_mood = emotion_to_mood.get(emotion, UserMood.NEUTRAL)
        
        # If we have recent emotions, adjust based on pattern
        if recent_emotions and len(recent_emotions) >= 3:
            # Check for stress pattern
            stress_emotions = [UserEmotion.ANXIOUS, UserEmotion.OVERWHELMED, UserEmotion.ANGRY]
            if sum(1 for e in recent_emotions[-3:] if e in stress_emotions) >= 2:
                return UserMood.STRESSED
            
            # Check for boredom pattern
            if all(e == UserEmotion.CALM for e in recent_emotions[-3:]):
                return UserMood.BORED
            
            # Check for excitement pattern
            exciting_emotions = [UserEmotion.HAPPY, UserEmotion.CURIOUS, UserEmotion.CONFIDENT]
            if sum(1 for e in recent_emotions[-3:] if e in exciting_emotions) >= 2:
                return UserMood.EXCITED
        
        return base_mood
