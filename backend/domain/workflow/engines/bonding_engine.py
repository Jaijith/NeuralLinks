"""
Bonding Workflow Engine
Orchestrates bonding conversations between users and their avatars
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from .base_engine import BaseWorkflowEngine, WorkflowState, WorkflowNode, WorkflowPhase
from ..models.enums import UserIntent, UserMood, BondingMode, BondingCardType
from ..models.bonding_state import BondingState, BondingMetrics
from ..models.bonding_memory import BondingSession
from ..models.chat import AvatarChatSession

# Lazy imports to avoid circular dependencies
# These are imported in __init__ instead

logger = logging.getLogger(__name__)


class BondingWorkflowEngine(BaseWorkflowEngine):
    """
    Bonding Workflow Engine - Deepens user-avatar relationships.
    
    This engine orchestrates bonding conversations by:
    1. Understanding user intent and emotion
    2. Generating curated recaps of avatar activities
    3. Creating serendipitous discoveries
    4. Asking for guidance when needed
    5. Showing avatar growth
    6. Suggesting micro-missions
    7. Tracking relationship health
    
    Unlike mission-based engines (matchmaking, marketing), this engine
    focuses on relationship building through meaningful conversation.
    """
    
    # Engine metadata
    engine_name = "bonding"
    engine_description = "Deepens user-avatar relationship through bonding conversations"
    supported_mission_types = ["bonding"]
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        mcp_server: Any,
        openai_client: Any = None,
        intelligent_avatar: Any = None
    ):
        # Lazy imports to avoid circular dependencies
        from ..services.intent_detector import IntentDetector
        from ..services.bonding_session import BondingSessionManager
        from ..services.recap_generator import RecapGenerator
        from ..services.serendipity_engine import SerendipityEngine
        from ..services.delight_scorer import UserDelightScorer
        
        # Initialize services
        self.intent_detector = IntentDetector(db, openai_client)
        self.session_manager = BondingSessionManager(db, openai_client)
        self.recap_generator = RecapGenerator(db, openai_client)
        self.serendipity_engine = SerendipityEngine(db, openai_client)
        self.delight_scorer = UserDelightScorer(db)
        
        # Call parent init
        super().__init__(db, mcp_server, openai_client, intelligent_avatar)
    
    def _build_workflow_graph(self) -> Dict[str, WorkflowNode]:
        """Build the bonding workflow graph"""
        return {
            "load_context": WorkflowNode(
                name="load_context",
                description="Load bonding state and context",
                tools=[],
                max_iterations=1,
                timeout_seconds=30
            ),
            "detect_intent_emotion": WorkflowNode(
                name="detect_intent_emotion",
                description="Detect user intent and emotion",
                tools=[],
                max_iterations=1,
                timeout_seconds=30
            ),
            "select_bonding_mode": WorkflowNode(
                name="select_bonding_mode",
                description="Select appropriate bonding mode",
                tools=[],
                max_iterations=1,
                timeout_seconds=10
            ),
            "generate_recap": WorkflowNode(
                name="generate_recap",
                description="Generate curated activity recap",
                tools=[],
                max_iterations=1,
                timeout_seconds=60
            ),
            "create_serendipity": WorkflowNode(
                name="create_serendipity",
                description="Create serendipitous discovery",
                tools=[],
                max_iterations=1,
                timeout_seconds=45
            ),
            "ask_for_guidance": WorkflowNode(
                name="ask_for_guidance",
                description="Ask user for guidance if needed",
                tools=[],
                max_iterations=1,
                timeout_seconds=20
            ),
            "show_growth": WorkflowNode(
                name="show_growth",
                description="Show avatar growth and learning",
                tools=[],
                max_iterations=1,
                timeout_seconds=30
            ),
            "suggest_micro_missions": WorkflowNode(
                name="suggest_micro_missions",
                description="Suggest micro-missions",
                tools=[],
                max_iterations=1,
                timeout_seconds=40
            ),
            "persist_state": WorkflowNode(
                name="persist_state",
                description="Save bonding state and session",
                tools=[],
                max_iterations=1,
                timeout_seconds=30
            )
        }
    
    def _get_node_order(self) -> List[str]:
        """Define the execution order of nodes"""
        return [
            "load_context",
            "detect_intent_emotion",
            "select_bonding_mode",
            "generate_recap",
            "create_serendipity",
            "ask_for_guidance",
            "show_growth",
            "suggest_micro_missions",
            "persist_state"
        ]
    
    async def _execute_node(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Execute a single workflow node"""
        
        node_executors = {
            "load_context": self._node_load_context,
            "detect_intent_emotion": self._node_detect_intent_emotion,
            "select_bonding_mode": self._node_select_bonding_mode,
            "generate_recap": self._node_generate_recap,
            "create_serendipity": self._node_create_serendipity,
            "ask_for_guidance": self._node_ask_for_guidance,
            "show_growth": self._node_show_growth,
            "suggest_micro_missions": self._node_suggest_micro_missions,
            "persist_state": self._node_persist_state
        }
        
        executor = node_executors.get(node.name)
        if not executor:
            logger.error(f"No executor found for node: {node.name}")
            state.errors.append(f"Unknown node: {node.name}")
            return state
        
        try:
            logger.info(f"Executing bonding node: {node.name}")
            state = await executor(node, state)
            logger.info(f"✓ Completed bonding node: {node.name}")
        except Exception as e:
            logger.error(f"Error in node {node.name}: {e}")
            state.errors.append(f"{node.name}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return state
    
    # ========================================================================
    # NODE IMPLEMENTATIONS
    # ========================================================================
    
    async def _node_load_context(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Load bonding state and context"""
        
        logger.info(f"Loading context for user {state.user_id}, avatar {state.avatar_id}")
        
        # Load or create bonding state
        bonding_state_doc = await self.db.bonding_states.find_one({
            "user_id": state.user_id,
            "avatar_id": state.avatar_id
        })
        
        if bonding_state_doc:
            bonding_state = BondingState(**bonding_state_doc)
            logger.info(f"Loaded existing bonding state (bond: {bonding_state.metrics.bond_strength:.2f})")
        else:
            # Create new bonding state
            bonding_state = BondingState(
                user_id=state.user_id,
                avatar_id=state.avatar_id
            )
            await self.db.bonding_states.insert_one(bonding_state.to_dict())
            logger.info("Created new bonding state")
        
        # Load last session summary
        last_summary = await self.session_manager.get_last_session_summary(
            state.user_id,
            state.avatar_id
        )
        
        # Get session history for pattern detection
        recent_sessions = await self.session_manager.get_recent_sessions(
            state.user_id,
            state.avatar_id,
            limit=5
        )
        
        # Store in state
        state.custom["bonding_state"] = bonding_state
        state.custom["last_session_summary"] = last_summary
        state.custom["recent_sessions"] = recent_sessions
        state.custom["cards"] = []  # Will accumulate response cards
        
        logger.info(f"Context loaded: last_session={last_summary is not None}, recent_sessions={len(recent_sessions)}")
        
        return state
    
    async def _node_detect_intent_emotion(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Detect user intent and emotion"""
        
        user_message = state.custom.get("user_message", "")
        if not user_message:
            logger.warning("No user message provided for intent detection")
            state.custom["detected_intent"] = UserIntent.GENERAL_CHAT
            state.custom["intent_confidence"] = 0.5
            state.custom["detected_emotion"] = None
            return state
        
        # Create chat session context
        chat_session = AvatarChatSession(
            user_id=state.user_id,
            avatar_id=state.avatar_id
        )
        
        # Add context from previous messages if available
        previous_messages = state.custom.get("previous_messages", [])
        for msg in previous_messages:
            chat_session.messages.append(msg)
        
        # Detect intent
        intent, intent_confidence = await self.intent_detector.detect_intent(
            user_message,
            chat_session,
            context=state.custom
        )
        
        # Detect emotion
        emotion, emotion_confidence = await self.intent_detector.detect_emotion(
            user_message,
            chat_session,
            context=state.custom
        )
        
        # Estimate mood
        bonding_state = state.custom.get("bonding_state")
        recent_emotions = []
        if bonding_state:
            # Get recent emotions from session history
            recent_sessions = state.custom.get("recent_sessions", [])
            for session in recent_sessions[:3]:
                if hasattr(session, 'detected_emotion') and session.detected_emotion:
                    recent_emotions.append(session.detected_emotion)
        
        mood, mood_confidence = await self.intent_detector.estimate_mood(
            user_message,
            chat_session,
            recent_emotions=recent_emotions
        )
        
        # Check if clarification is needed
        should_clarify, clarifying_question = await self.intent_detector.should_ask_clarifying_question(
            intent,
            intent_confidence,
            emotion,
            emotion_confidence
        )
        
        # Store results
        state.custom["detected_intent"] = intent
        state.custom["intent_confidence"] = intent_confidence
        state.custom["detected_emotion"] = emotion
        state.custom["emotion_confidence"] = emotion_confidence
        state.custom["estimated_mood"] = mood
        state.custom["mood_confidence"] = mood_confidence
        state.custom["needs_clarification"] = should_clarify
        state.custom["clarifying_question"] = clarifying_question
        
        # Update bonding state with mood estimate
        if bonding_state:
            bonding_state.user_mood_estimate = mood
            bonding_state.mood_confidence = mood_confidence
            bonding_state.last_user_emotion = emotion
            bonding_state.emotion_confidence = emotion_confidence
        
        logger.info(f"Intent: {intent.value} ({intent_confidence:.2f}), "
                   f"Emotion: {emotion.value if emotion else 'none'} ({emotion_confidence:.2f}), "
                   f"Mood: {mood.value} ({mood_confidence:.2f})")
        
        return state
    
    async def _node_select_bonding_mode(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Select appropriate bonding mode based on intent and context"""
        
        intent = state.custom.get("detected_intent", UserIntent.GENERAL_CHAT)
        mood = state.custom.get("estimated_mood", UserMood.NEUTRAL)
        bonding_state = state.custom.get("bonding_state")
        
        # Map intent to bonding mode
        intent_to_mode = {
            UserIntent.CHECK_IN: BondingMode.CHECK_IN,
            UserIntent.VENTING: BondingMode.COACH,  # Supportive mode
            UserIntent.PLANNING: BondingMode.PLANNING,
            UserIntent.REFLECTION: BondingMode.DEEP_TALK,
            UserIntent.SEEKING_ADVICE: BondingMode.COACH,
            UserIntent.CELEBRATION: BondingMode.CELEBRATION,
            UserIntent.EXPLORATION: BondingMode.PLAY,
            UserIntent.GENERAL_CHAT: BondingMode.CHECK_IN
        }
        
        bonding_mode = intent_to_mode.get(intent, BondingMode.CHECK_IN)
        
        # Adjust based on mood if needed
        if mood == UserMood.STRESSED and bonding_mode != BondingMode.COACH:
            # User is stressed, switch to coaching mode
            bonding_mode = BondingMode.COACH
            logger.info("Adjusted to COACH mode due to stressed mood")
        
        state.custom["bonding_mode"] = bonding_mode
        logger.info(f"Selected bonding mode: {bonding_mode.value}")
        
        # Add warm presence card (always start with this)
        warm_presence = await self._generate_warm_presence(intent, mood, bonding_state)
        state.custom["cards"].append({
            "type": BondingCardType.WARM_PRESENCE.value,
            "content": warm_presence
        })
        
        return state
    
    async def _node_generate_recap(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Generate curated activity recap if appropriate"""
        
        bonding_state = state.custom.get("bonding_state")
        detected_intent = state.custom.get("detected_intent")
        
        # Check if recap should be included
        should_include = await self.recap_generator.should_include_recap(
            bonding_state,
            detected_intent.value if detected_intent else None
        )
        
        if not should_include:
            logger.info("Skipping recap (not appropriate for this context)")
            return state
        
        # Generate recap
        try:
            recap_cards = await self.recap_generator.generate_recap(
                user_id=state.user_id,
                avatar_id=state.avatar_id,
                bonding_state=bonding_state,
                context=state.custom,
                max_cards=3  # Limit to 3 recap cards
            )
            
            if recap_cards:
                state.custom["cards"].extend(recap_cards)
                logger.info(f"Generated {len(recap_cards)} recap cards")
            else:
                logger.info("No activities to recap")
        except Exception as e:
            logger.error(f"Recap generation failed: {e}")
        
        return state
    
    async def _node_create_serendipity(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Create serendipitous discovery if appropriate"""
        
        bonding_state = state.custom.get("bonding_state")
        detected_intent = state.custom.get("detected_intent")
        recent_sessions = state.custom.get("recent_sessions", [])
        
        # Convert recent_sessions to dicts for serendipity engine
        session_history = []
        for session in recent_sessions:
            if hasattr(session, 'dict'):
                session_history.append(session.dict())
            elif isinstance(session, dict):
                session_history.append(session)
        
        # Check if surprise should be generated
        should_generate = await self.serendipity_engine.should_generate_surprise(
            bonding_state,
            detected_intent.value if detected_intent else None,
            session_history=session_history
        )
        
        if not should_generate:
            logger.info("Skipping serendipity (not appropriate)")
            return state
        
        # Generate surprise
        try:
            surprise_card = await self.serendipity_engine.generate_surprise(
                user_id=state.user_id,
                avatar_id=state.avatar_id,
                bonding_state=bonding_state
            )
            
            if surprise_card:
                state.custom["cards"].append(surprise_card)
                logger.info("Generated serendipity card")
        except Exception as e:
            logger.error(f"Serendipity generation failed: {e}")
        
        return state
    
    async def _node_ask_for_guidance(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Ask user for guidance if needed"""
        
        bonding_state = state.custom.get("bonding_state")
        
        # Check for unresolved threads
        if bonding_state and bonding_state.unresolved_threads:
            # Pick highest importance thread
            threads_sorted = sorted(
                bonding_state.unresolved_threads,
                key=lambda t: t.importance,
                reverse=True
            )
            
            if threads_sorted:
                top_thread = threads_sorted[0]
                
                # Generate guidance question
                question = await self._generate_guidance_question(top_thread, bonding_state)
                
                state.custom["cards"].append({
                    "type": BondingCardType.GUIDANCE.value,
                    "content": question,
                    "thread_id": top_thread.id,
                    "thread_topic": top_thread.topic
                })
                state.custom["guidance_asked"] = True
                logger.info(f"Generated guidance question about: {top_thread.topic}")
                return state
        
        # Check if clarification was needed from intent detection
        if state.custom.get("needs_clarification"):
            question = state.custom.get("clarifying_question")
            if question:
                state.custom["cards"].append({
                    "type": BondingCardType.GUIDANCE.value,
                    "content": question
                })
                state.custom["guidance_asked"] = True
                logger.info("Added clarifying question")
        
        return state
    
    async def _node_show_growth(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Show avatar growth and learning"""
        
        # Check for recent avatar learnings/insights
        # This would query reflection_logs for recent entries
        
        try:
            recent_reflections = await self.db.reflection_logs.find({
                "avatar_id": state.avatar_id,
                "user_id": state.user_id
            }).sort("created_at", -1).limit(3).to_list(length=3)
            
            if recent_reflections:
                # Pick most interesting/confident reflection
                best_reflection = max(
                    recent_reflections,
                    key=lambda r: r.get("confidence", 0) * r.get("usefulness", 0.5)
                )
                
                growth_card = await self._generate_growth_card(best_reflection)
                
                if growth_card:
                    state.custom["cards"].append(growth_card)
                    logger.info("Generated growth card")
        except Exception as e:
            logger.error(f"Growth card generation failed: {e}")
        
        return state
    
    async def _node_suggest_micro_missions(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Suggest micro-missions if appropriate"""
        
        bonding_mode = state.custom.get("bonding_mode")
        bonding_state = state.custom.get("bonding_state")
        
        # Only suggest missions for planning mode or if explicitly appropriate
        if bonding_mode != BondingMode.PLANNING:
            logger.info("Skipping micro-missions (not planning mode)")
            return state
        
        # Check if user wants space (return pressure)
        if bonding_state and bonding_state.compute_return_pressure() > 0.7:
            logger.info("Skipping micro-missions (user needs space)")
            return state
        
        # Generate 1-2 mission proposals
        proposals = await self._generate_micro_mission_proposals(state)
        
        if proposals:
            state.custom["cards"].extend(proposals)
            state.custom["micro_missions_proposed"] = len(proposals)
            logger.info(f"Generated {len(proposals)} micro-mission proposals")
        
        return state
    
    async def _node_persist_state(
        self,
        node: WorkflowNode,
        state: WorkflowState
    ) -> WorkflowState:
        """Save bonding state and session"""
        
        bonding_state = state.custom.get("bonding_state")
        if not bonding_state:
            logger.warning("No bonding state to persist")
            return state
        
        # Compute bond deltas based on interaction quality
        interaction_quality = await self._assess_interaction_quality(state)
        
        # Update metrics
        bond_delta = interaction_quality * 0.02  # Small incremental growth
        trust_delta = interaction_quality * 0.015
        alignment_delta = interaction_quality * 0.01
        
        bonding_state.update_metrics(
            bond_delta=bond_delta,
            trust_delta=trust_delta,
            alignment_delta=alignment_delta
        )
        
        # Compute delight score
        session_data = {
            "detected_intent": state.custom.get("detected_intent", "").value if hasattr(state.custom.get("detected_intent", ""), "value") else "",
            "selected_bonding_mode": state.custom.get("bonding_mode", "").value if hasattr(state.custom.get("bonding_mode", ""), "value") else "",
            "cards_generated": state.custom.get("cards", []),
            "guidance_asked": state.custom.get("guidance_asked", False),
            "micro_missions_proposed": state.custom.get("micro_missions_proposed", 0)
        }
        
        delight = await self.delight_scorer.compute_delight(
            session_data,
            bonding_state
        )
        
        bonding_state.update_delight(delight)
        
        # Save bonding state
        await self.db.bonding_states.update_one(
            {"user_id": state.user_id, "avatar_id": state.avatar_id},
            {"$set": bonding_state.to_dict()},
            upsert=True
        )
        
        # Store metrics in state for response
        state.custom["bond_delta"] = bond_delta
        state.custom["trust_delta"] = trust_delta
        state.custom["delight_score"] = delight
        
        logger.info(f"Persisted bonding state: bond={bonding_state.metrics.bond_strength:.2f} (+{bond_delta:.3f}), "
                   f"trust={bonding_state.metrics.trust:.2f} (+{trust_delta:.3f}), "
                   f"delight={delight:.2f}")
        
        # NEW: Update avatar's internal mood based on bonding conversation outcome
        await self._update_avatar_mood_from_bonding(state, delight, bond_delta)
        
        return state
    
    async def _update_avatar_mood_from_bonding(
        self,
        state: WorkflowState,
        delight_score: float,
        bond_delta: float
    ):
        """
        Update avatar's internal state based on bonding conversation outcome.
        
        This ensures the avatar's mood reflects the quality of conversation:
        - Great conversation → Happy/Excited
        - Deep conversation → Contemplative
        - Helped user → Social
        - Celebration → Excited
        """
        try:
            from domain.avatar.state import StateManager
            from domain.avatar.state.state_models import MoodState
            
            state_manager = StateManager(self.db)
            internal_state, _ = await state_manager.get_current_state(state.avatar_id)
            
            bonding_mode = state.custom.get("bonding_mode")
            detected_intent = state.custom.get("detected_intent")
            estimated_mood = state.custom.get("estimated_mood")
            
            mood_changed = False
            reason = ""
            
            # Beautiful conversation with strong bond growth → Happy
            if delight_score > 0.7 and bond_delta > 0.01:
                internal_state.adjust_mood(MoodState.HAPPY, "Great conversation with user")
                internal_state.boost_energy(0.15)
                mood_changed = True
                reason = "high delight + bond growth"
            
            # Deep meaningful conversation → Contemplative
            elif bonding_mode == BondingMode.DEEP_TALK:
                internal_state.adjust_mood(MoodState.CONTEMPLATIVE, "Deep conversation with user")
                mood_changed = True
                reason = "deep talk mode"
            
            # User was stressed, avatar helped → Social satisfaction
            elif estimated_mood == UserMood.STRESSED and delight_score > 0.5:
                internal_state.adjust_mood(MoodState.SOCIAL, "Helped user through stress")
                internal_state.boost_energy(0.1)
                mood_changed = True
                reason = "helped stressed user"
            
            # User celebrated something → Excited
            elif detected_intent == UserIntent.CELEBRATION:
                internal_state.adjust_mood(MoodState.EXCITED, "Celebrated with user!")
                internal_state.boost_energy(0.2)
                mood_changed = True
                reason = "celebration"
            
            # Good conversation but not exceptional → Mild happiness
            elif delight_score > 0.5 and internal_state.mood in [MoodState.BORED, MoodState.RESTLESS, MoodState.NEUTRAL]:
                internal_state.adjust_mood(MoodState.CALM, "Nice conversation")
                mood_changed = True
                reason = "decent conversation"
            
            # Poor conversation → Slight disappointment
            elif delight_score < 0.3 and bond_delta < 0:
                if internal_state.mood == MoodState.HAPPY:
                    internal_state.adjust_mood(MoodState.NEUTRAL, "Conversation didn't go well")
                    mood_changed = True
                    reason = "low delight"
            
            if mood_changed:
                await state_manager.update_internal_state(state.avatar_id, internal_state)
                logger.info(f"Avatar mood updated to {internal_state.mood.value} after bonding ({reason})")
            
        except Exception as e:
            logger.warning(f"Failed to update avatar mood from bonding: {e}")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    async def _generate_warm_presence(
        self,
        intent: UserIntent,
        mood: UserMood,
        bonding_state: Optional[BondingState]
    ) -> str:
        """Generate warm opening message"""
        
        # Simple templates based on intent
        templates = {
            UserIntent.CHECK_IN: "Hey! Good to hear from you. 😊",
            UserIntent.VENTING: "I'm here for you. What's going on?",
            UserIntent.PLANNING: "Love the energy! What are you thinking?",
            UserIntent.REFLECTION: "I'm listening. What's on your mind?",
            UserIntent.SEEKING_ADVICE: "Let's figure this out together.",
            UserIntent.CELEBRATION: "That's amazing! Tell me more! 🎉",
            UserIntent.EXPLORATION: "Ooh, this sounds interesting!",
            UserIntent.GENERAL_CHAT: "Hey! What's up?"
        }
        
        return templates.get(intent, "Hey there!")
    
    async def _generate_guidance_question(
        self,
        thread: Any,
        bonding_state: BondingState
    ) -> str:
        """Generate a guidance question about an unresolved thread"""
        
        # Simple question generation
        return f"By the way, still thinking about {thread.topic} - any updates on your end?"
    
    async def _generate_growth_card(self, reflection: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a growth card from a reflection"""
        
        title = reflection.get("title", "")
        content = reflection.get("content", "")
        
        if not title:
            return None
        
        return {
            "type": BondingCardType.GROWTH.value,
            "content": f"I've been learning: {title}",
            "details": content
        }
    
    async def _generate_micro_mission_proposals(self, state: WorkflowState) -> List[Dict[str, Any]]:
        """Generate micro-mission proposals"""
        
        # This is a simplified version - in production, this would be more sophisticated
        # For now, return empty list (can be implemented later)
        return []
    
    async def _assess_interaction_quality(self, state: WorkflowState) -> float:
        """
        Assess the quality of the interaction.
        
        Returns:
            Quality score 0.0-1.0
        """
        
        quality = 0.5  # Base
        
        # More cards = more effort = higher quality
        num_cards = len(state.custom.get("cards", []))
        if num_cards >= 3:
            quality += 0.2
        elif num_cards >= 2:
            quality += 0.1
        
        # High intent confidence = better understanding
        intent_confidence = state.custom.get("intent_confidence", 0.5)
        if intent_confidence > 0.8:
            quality += 0.1
        
        # Serendipity adds delight
        has_serendipity = any(
            c.get("type") == BondingCardType.SERENDIPITY.value
            for c in state.custom.get("cards", [])
        )
        if has_serendipity:
            quality += 0.2
        
        return min(1.0, quality)
    
    # ========================================================================
    # PUBLIC INTERFACE
    # ========================================================================
    
    async def execute(
        self,
        user_id: str,
        avatar_id: str,
        user_message: str,
        session: Optional[AvatarChatSession] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the bonding workflow.
        
        Args:
            user_id: User ID
            avatar_id: Avatar ID
            user_message: User's message
            session: Optional chat session for context
            **kwargs: Additional parameters
        
        Returns:
            Bonding response dict
        """
        
        # Create workflow state
        state = WorkflowState(
            mission_id=f"bonding_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            avatar_id=avatar_id,
            user_id=user_id,
            mission_type="bonding"
        )
        
        # Add custom data
        state.custom["user_message"] = user_message
        state.custom["session"] = session
        state.custom["previous_messages"] = session.messages if session else []
        state.custom["guidance_asked"] = False
        state.custom["micro_missions_proposed"] = 0
        
        # Execute workflow
        logger.info(f"Starting bonding workflow for user {user_id}")
        
        node_order = self._get_node_order()
        for node_name in node_order:
            node = self.workflow_graph[node_name]
            state = await self._execute_node(node, state)
            
            # Check for errors
            if state.errors:
                logger.warning(f"Errors in workflow: {state.errors}")
        
        # Format response
        response = self._format_bonding_response(state)
        
        logger.info(f"Bonding workflow complete: {len(response['cards'])} cards, "
                   f"bond_delta={response['metrics']['bond_delta']:.3f}")
        
        return response
    
    def _format_bonding_response(self, state: WorkflowState) -> Dict[str, Any]:
        """Format the workflow state into a bonding response"""
        
        return {
            "type": "bonding",
            "cards": state.custom.get("cards", []),
            "guidance_asked": state.custom.get("guidance_asked", False),
            "micro_missions": state.custom.get("micro_mission_proposals", []),
            "metrics": {
                "bond_delta": state.custom.get("bond_delta", 0.0),
                "trust_delta": state.custom.get("trust_delta", 0.0),
                "delight_score": state.custom.get("delight_score", 0.5)
            },
            "detected_intent": state.custom.get("detected_intent", "").value if hasattr(state.custom.get("detected_intent", ""), "value") else None,
            "bonding_mode": state.custom.get("bonding_mode", "").value if hasattr(state.custom.get("bonding_mode", ""), "value") else None
        }
