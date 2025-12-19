"""
State-Aware Agent - Phase 6 + Memory Integration
Uses the full state machine system (Phases 1-5) for intelligent decision making
Now with MEMORY-INFORMED decision making using MemoryManager

Memory Integration:
- Semantic Memory: Knowledge graph (interests, traits, values)
- Procedural Memory: Action history (what works, what doesn't)
- Episodic Memory: Experiences (relationships, significant events)

Activity Levels:
- hypo: 1 action/2 mins (Testing mode - very frequent)
- low: 1-2 actions/day (Minimal activity)
- medium: 5-10 actions/day (Moderate activity)
- high: 15-20 actions/day (Active engagement)
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging


# Activity level configuration
# Maps activity level string to configuration
ACTIVITY_LEVEL_CONFIG = {
    "hypo": {
        "name": "Hypo (Testing)",
        "min_interval_minutes": 7,      # 1 action every 7 minutes (testing)
        "max_actions_per_day": 200,     # ~200 actions/day for testing
        "delay_multiplier": 0.1,        # Very short delays
    },
    "user_active": {
        "name": "User Active",
        "min_interval_minutes": 7,      # 1 action every 7 minutes
        "max_actions_per_day": 200,     # ~200 actions/day
        "delay_multiplier": 0.2,        # Short delays
    },
    "bot_hourly": {
        "name": "Bot Hourly",
        "min_interval_minutes": 60,     # 1 action every hour
        "max_actions_per_day": 24,      # 24 actions/day
        "delay_multiplier": 0.8,        # Normal delays
    },
    "low": {
        "name": "Low",
        "min_interval_minutes": 720,    # 12 hours minimum between actions
        "max_actions_per_day": 2,
        "delay_multiplier": 5.0,        # Very long delays
    },
    "medium": {
        "name": "Medium",
        "min_interval_minutes": 144,    # ~2.4 hours between actions (10 actions/day)
        "max_actions_per_day": 10,
        "delay_multiplier": 1.0,        # Normal delays
    },
    "high": {
        "name": "High", 
        "min_interval_minutes": 72,     # ~1.2 hours between actions (20 actions/day)
        "max_actions_per_day": 20,
        "delay_multiplier": 0.5,        # Shorter delays
    },
}

from domain.avatar.perception.engine import PerceptionEngine
from domain.avatar.state import StateManager
from domain.avatar.state.state_models import MoodState
from domain.avatar.state_machine import AvatarStateMachine, TopLevelState
from domain.avatar.decision import DecisionEngine
from domain.avatar.character import CharacterProfile
from domain.avatar.mcp.server import mcp_server
from domain.avatar.memory import MemoryManager  # NEW: Memory integration
from domain.avatar.behavior_tree import (
    create_react_to_post_bt,
    create_initiate_social_interaction_bt,
    create_respond_to_messages_bt,
    create_create_post_bt
)

logger = logging.getLogger(__name__)


class StateAwareAgent:
    """
    State-aware avatar agent using full state machine system + MEMORY integration
    
    Features:
    - Perception-based decision making
    - State-driven behavior
    - Character-aligned actions
    - Behavior tree execution
    - Utility-based action selection
    - MEMORY-INFORMED decisions (NEW)
    
    Memory Integration:
    - Uses MemoryManager for unified memory access
    - Records action outcomes for learning
    - Stores significant experiences
    - Uses past success/failure to guide decisions
    """
    
    def __init__(
        self,
        bot: Dict[str, Any],
        db: AsyncIOMotorDatabase,
        intelligent_avatar=None  # Not used in state-aware agent, but kept for compatibility
    ):
        self.bot = bot
        self.bot_id = bot['id']
        self.db = db
        
        # Track if this is a user avatar (not a bot)
        self.is_user_avatar = not bot.get('is_bot', False)
        
        # Get activity level configuration
        activity_level = bot.get('avatar_activity_level', 'medium')
        self.activity_config = ACTIVITY_LEVEL_CONFIG.get(activity_level, ACTIVITY_LEVEL_CONFIG['medium'])
        self.activity_level = activity_level
        
        # Activity tracking - now based on activity level
        # Initialize last_action_time from database or very old time (to allow first action)
        last_activity_str = bot.get('last_activity')
        if last_activity_str:
            try:
                # Parse ISO format timestamp
                if isinstance(last_activity_str, str):
                    parsed_time = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                    # Ensure timezone-aware
                    if parsed_time.tzinfo is None:
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                    self.last_action_time = parsed_time
                elif isinstance(last_activity_str, datetime):
                    # Ensure timezone-aware
                    if last_activity_str.tzinfo is None:
                        self.last_action_time = last_activity_str.replace(tzinfo=timezone.utc)
                    else:
                        self.last_action_time = last_activity_str
                else:
                    self.last_action_time = datetime.now(timezone.utc) - timedelta(hours=24)
            except (ValueError, TypeError):
                # If parsing fails, allow action by setting old time
                self.last_action_time = datetime.now(timezone.utc) - timedelta(hours=24)
        else:
            # No previous activity - allow first action
            self.last_action_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        self.actions_today = 0
        self.actions_today_reset = datetime.now(timezone.utc).date()
        self.max_actions_per_day = self.activity_config['max_actions_per_day']
        self.min_action_interval = timedelta(minutes=self.activity_config['min_interval_minutes'])
        
        # Legacy compatibility
        self.actions_this_hour = 0
        self.max_actions_per_hour = min(30, self.max_actions_per_day)  # Cap at 30 for hourly limit
        
        # NEW: Memory Manager for memory-informed decisions
        self.memory_manager = MemoryManager(db)
        
        # State machine system components
        self.perception_engine = PerceptionEngine(db)
        self.state_manager = StateManager(db)
        self.state_machine = AvatarStateMachine(db, state_manager=self.state_manager)
        self.decision_engine = DecisionEngine(
            state_manager=self.state_manager,
            state_machine=self.state_machine,
            perception_engine=self.perception_engine,
            mcp_client=None,  # We'll use mcp_server directly
            memory_manager=self.memory_manager  # NEW: Pass memory manager
        )
        self.character_profile: Optional[CharacterProfile] = None
        
        # MCP Server reference (all actions go through MCP tools)
        self.mcp_server = mcp_server
        
        # Visual indicator
        avatar_indicator = "✨" if self.is_user_avatar else "🤖"
        logger.info(f"{avatar_indicator} Initialized StateAwareAgent with Memory: {bot.get('avatar_name', bot.get('name'))}")
    
    async def initialize(self):
        """Initialize the agent's state and character profile"""
        try:
            # Initialize state machine
            await self.state_machine.initialize(self.bot_id)
            
            # Load character profile
            self.character_profile = CharacterProfile(self.bot_id, self.db)
            await self.character_profile.load()
            
            # Initialize state
            await self.state_manager.initialize_state(self.bot_id)
            
            logger.info(f"StateAwareAgent initialized for {self.bot_id}")
            
        except Exception as e:
            logger.error(f"Error initializing StateAwareAgent for {self.bot_id}: {e}", exc_info=True)
    
    def _can_take_action(self) -> tuple[bool, str]:
        """
        Check if the agent can take an action based on activity level constraints.
        
        Returns:
            (can_act: bool, reason: str) - Whether action is allowed and why not if False
        """
        now = datetime.now(timezone.utc)
        
        # Reset daily counter if new day
        today = now.date()
        if today != self.actions_today_reset:
            self.actions_today = 0
            self.actions_today_reset = today
            logger.info(f"Reset daily action counter for {self.bot.get('avatar_name')}")
        
        # Check daily limit
        if self.actions_today >= self.max_actions_per_day:
            return False, f"Daily limit reached ({self.actions_today}/{self.max_actions_per_day})"
        
        # Check minimum interval
        time_since_last = now - self.last_action_time
        if time_since_last < self.min_action_interval:
            remaining = (self.min_action_interval - time_since_last).total_seconds()
            return False, f"Too soon (wait {remaining/60:.1f} more minutes)"
        
        return True, "OK"
    
    async def _record_action_taken(self):
        """Record that an action was taken (for activity level tracking)"""
        self.last_action_time = datetime.now(timezone.utc)
        self.actions_today += 1
        self.actions_this_hour += 1  # Legacy compatibility
        
        avatar_name = self.bot.get('avatar_name', 'Unknown')
        logger.info(
            f"📊 {avatar_name} action recorded: {self.actions_today}/{self.max_actions_per_day} today "
            f"(activity level: {self.activity_level})"
        )
        
        # Persist last_activity to database (important for Lambda/stateless invocations)
        try:
            await self.db.users.update_one(
                {"id": self.bot_id},
                {"$set": {"last_activity": self.last_action_time.isoformat()}}
            )
        except Exception as e:
            logger.warning(f"Failed to update last_activity in DB: {e}")
    
    async def run_continuously(self):
        """
        Continuously active agent loop - self-driven, no external scheduler
        
        Agent continuously:
        1. Perceives environment
        2. Updates states
        3. Evaluates transitions (state machine decides when to go passive/idle)
        4. Takes actions
        5. Loops immediately (with intelligent delays based on state)
        """
        avatar_name = self.bot.get('avatar_name', 'Unknown')
        avatar_indicator = "✨ USER AVATAR" if self.is_user_avatar else "🤖"
        
        logger.info(f"{avatar_indicator} {avatar_name} - Starting continuous activity loop")
        
        iteration = 0
        while True:
            try:
                iteration += 1
                
                # Check if autonomy is still enabled
                if not await self._check_autonomy_enabled():
                    logger.info(f"{avatar_indicator} {avatar_name} - Autonomy disabled, stopping")
                    break
                
                # Get current state to determine delay
                current_state, _ = await self.state_machine.get_current_state(self.bot_id)
                
                # Step 1: Update perception
                perception_data = await self.perception_engine.perceive_all(self.bot_id)
                
                # Step 2: Update states
                internal_state, external_state = await self.state_manager.get_current_state(self.bot_id)
                external_state.update_from_perception(perception_data)
                await self.state_manager.update_external_state(self.bot_id, external_state)
                internal_state = await self.state_manager.update_temporal_states(self.bot_id)

                # Update mood based on environment and internal state
                self._update_mood_from_environment(internal_state, external_state)
                
                # NEW: Also update mood from memory (experiences, emotional history)
                memory_context = await self.memory_manager.get_full_memory_context(self.bot_id)
                await self._update_mood_from_memory(internal_state, memory_context)
                
                await self.state_manager.update_internal_state(self.bot_id, internal_state)
                
                # Step 3: Evaluate state transitions
                user = await self.db.users.find_one({"id": self.bot_id})
                archetype = user.get("avatar_archetype") or user.get("archetype", "general") if user else "general"
                
                new_state = await self.state_machine.evaluate_transitions(self.bot_id, archetype)
                
                if new_state and new_state != current_state:
                    await self.state_machine.transition_to(
                        self.bot_id,
                        new_state,
                        reason="State transition from continuous loop",
                        triggered_by="agent_self_driven"
                    )
                    logger.info(f"{avatar_indicator} {avatar_name} - 🔄 State: {current_state.value} -> {new_state.value}")
                    current_state = new_state
                
                # Step 4: Get character profile (ensure loaded)
                if not self.character_profile or not self.character_profile.is_loaded():
                    self.character_profile = CharacterProfile(self.bot_id, self.db)
                    await self.character_profile.load()
                
                # Step 5: Get memory context for informed decisions (NEW)
                memory_context = await self.memory_manager.get_full_memory_context(self.bot_id)
                
                # Step 6: Select and execute action (only if not in RESTING state)
                if current_state.value != "resting":
                    # Check if we're allowed to take action (activity level constraints)
                    can_act, reason = self._can_take_action()
                    if not can_act:
                        logger.debug(f"{avatar_indicator} {avatar_name} - Skipping action: {reason}")
                    else:
                        character_dict = self.character_profile.to_dict() if self.character_profile else None
                        
                        # Get permissions from user document
                        user = await self.db.users.find_one({"id": self.bot_id})
                        permissions = user.get("avatar_actions_enabled", {}) if user else {}
                        
                        # Select action (now with memory context)
                        selected_action = await self.decision_engine.select_action(
                            self.bot_id,
                            character_profile=character_dict,
                            permissions=permissions,
                            memory_context=memory_context  # NEW: Pass memory context
                        )
                        
                        if selected_action:
                            # Execute action via MCP server
                            action_type = selected_action.get("type")
                            action_args = {k: v for k, v in selected_action.items() 
                                          if k not in ["type", "description", "utility", "interest_aligned", "memory_penalty", "shared_interests"]}
                            
                            # Map action types to MCP tool names
                            tool_name = self._map_action_to_tool(action_type)
                            
                            if tool_name:
                                result = await self.mcp_server.call_tool(tool_name, self.bot_id, action_args)
                                
                                if result.get('success'):
                                    logger.info(f"{avatar_indicator} {avatar_name} - ✅ {action_type}")
                                    await self._record_action_taken()  # Use activity level tracking
                                    
                                    # Log activity
                                    await self._log_activity(action_type, {
                                        "action": selected_action,
                                        "result": result
                                    })
                                    
                                    # NEW: Record action outcome in memory for learning
                                    await self._record_action_in_memory(action_type, selected_action, result)
                                    
                                    # Update state after action
                                    await self._update_state_after_action(action_type, result)
                                else:
                                    logger.debug(f"{avatar_indicator} {avatar_name} - ⚠️  Action failed: {result.get('error', 'Unknown')}")
                                    
                                    # NEW: Record failed action in memory
                                    await self._record_action_in_memory(action_type, selected_action, result)
                            else:
                                logger.debug(f"{avatar_indicator} {avatar_name} - ⚠️  No MCP tool for: {action_type}")
                
                self.last_action_time = datetime.now(timezone.utc)
                
                # Intelligent delay based on current state
                # State machine decides when to be active vs passive
                delay_seconds = self._get_state_based_delay(current_state, internal_state)
                
                # Small delay to prevent tight loops, but keep agents active
                await asyncio.sleep(delay_seconds)
                
            except asyncio.CancelledError:
                logger.info(f"{avatar_indicator} {avatar_name} - Loop cancelled")
                break
            except Exception as e:
                logger.error(f"{avatar_indicator} {avatar_name} - Error in continuous loop: {e}", exc_info=True)
                # On error, wait a bit before retrying
                await asyncio.sleep(5)
    
    def _update_mood_from_environment(self, internal_state: Any, external_state: Any):
        """Update mood based on environment and internal state"""
        try:
            # High energy + High social activity -> EXCITED or HAPPY
            if internal_state.energy_level > 0.7 and external_state.friend_activity_level > 0.6:
                if internal_state.mood != MoodState.EXCITED:
                    internal_state.adjust_mood(MoodState.EXCITED, "High energy and activity")
            
            # Low energy -> TIRED/RESTLESS
            elif internal_state.energy_level < 0.3:
                if internal_state.mood not in [MoodState.RESTLESS, MoodState.CALM]:
                    internal_state.adjust_mood(MoodState.RESTLESS, "Low energy")
            
            # High creative urge -> CREATIVE
            elif internal_state.creative_urge > 0.8:
                if internal_state.mood != MoodState.CREATIVE:
                    internal_state.adjust_mood(MoodState.CREATIVE, "High creative urge")
            
            # Lots of unread messages -> SOCIAL
            elif external_state.unread_messages > 2:
                if internal_state.mood != MoodState.SOCIAL:
                    internal_state.adjust_mood(MoodState.SOCIAL, "Many unread messages")
            
            # Default drift to NEUTRAL or CURIOUS if nothing special
            elif internal_state.mood in [MoodState.EXCITED, MoodState.HAPPY] and internal_state.energy_level < 0.5:
                internal_state.adjust_mood(MoodState.NEUTRAL, "Energy cooling down")
                
        except Exception as e:
            logger.warning(f"Error updating mood: {e}")
    
    def _get_state_based_delay(self, current_state, internal_state) -> float:
        """
        Get delay based on current state AND activity level configuration.
        
        Returns delay in seconds. Shorter delay = more active, longer delay = less active.
        State machine transitions to RESTING/PASSIVE when appropriate.
        
        Activity level multipliers:
        - hypo: 0.1x (very fast, testing mode)
        - low: 5.0x (very slow, 1-2 actions/day)
        - medium: 1.0x (normal, 5-10 actions/day)
        - high: 0.5x (fast, 15-20 actions/day)
        """
        # Base delays (in seconds) - using state value strings
        delays = {
            "active": 30.0,        # Active: check every 30 seconds
            "creative": 45.0,      # Creative: slightly longer (thinking time)
            "social": 20.0,        # Social: more frequent (checking messages)
            "exploring": 60.0,     # Exploring: less frequent
            "passive": 120.0,      # Passive: less frequent (observing)
            "resting": 300.0       # Resting: much less frequent (5 minutes)
        }
        
        # Get state value (handle both enum and string)
        state_value = current_state.value if hasattr(current_state, 'value') else str(current_state)
        base_delay = delays.get(state_value, 60.0)
        
        # Apply activity level multiplier
        activity_multiplier = self.activity_config.get('delay_multiplier', 1.0)
        base_delay *= activity_multiplier
        
        # Adjust based on energy level
        if internal_state.energy_level < 0.3:
            base_delay *= 1.5  # Low energy = longer delay
        elif internal_state.energy_level > 0.7:
            base_delay *= 0.8  # High energy = shorter delay
        
        # Add small random variation to prevent synchronization
        variation = random.uniform(0.9, 1.1)
        
        return base_delay * variation
    
    def _map_action_to_tool(self, action_type: str) -> Optional[str]:
        """Map action type to MCP tool name"""
        mapping = {
            "like_post": "like_post",
            "comment_on_post": "comment_on_post",
            "create_post": "create_post",
            "send_friend_request": "send_friend_request",
            "accept_friend_request": "accept_friend_request",
            "message_friend": "message_friend",
            "discover_profiles": "discover_profiles",
            "read_messages": "read_messages",
            "browse_feed": "browse_feed"  # Now has MCP tool
        }
        return mapping.get(action_type)
    
    async def _update_state_after_action(self, action_type: str, result: Dict[str, Any]):
        """Update internal state after action execution"""
        try:
            internal_state, external_state = await self.state_manager.get_current_state(self.bot_id)
            
            # Update based on action type
            if action_type == "create_post":
                internal_state.creative_urge = max(0.0, internal_state.creative_urge - 0.3)
                internal_state.time_since_last_action = timedelta(0)
                if result.get('success'):
                    internal_state.adjust_mood(MoodState.HAPPY, "Created content")
            
            elif action_type in ["like_post", "comment_on_post"]:
                internal_state.social_desire = max(0.0, internal_state.social_desire - 0.2)
                internal_state.time_since_last_action = timedelta(0)
                if result.get('success'):
                    internal_state.adjust_mood(MoodState.SOCIAL, "Social interaction")

            elif action_type == "message_friend":
                internal_state.social_desire = max(0.0, internal_state.social_desire - 0.3)
                internal_state.time_since_last_action = timedelta(0)
                if result.get('success'):
                    internal_state.adjust_mood(MoodState.HAPPY, "Messaged friend")
            
            elif action_type == "discover_profiles":
                internal_state.time_since_last_action = timedelta(0)
                if result.get('success') and result.get('found_count', 0) > 0:
                    internal_state.adjust_mood(MoodState.EXCITED, "Found new people")
                else:
                    internal_state.adjust_mood(MoodState.BORED, "Found no one new")

            elif action_type == "browse_feed":
                 # Do NOT reset time_since_last_action for browsing
                 # This allows the agent to get "bored" and transition states even if browsing
                 
                 # Browsing can make them curious or bored depending on content
                 import random
                 if random.random() > 0.7:
                     internal_state.adjust_mood(MoodState.CURIOUS, "Saw interesting content")
                     # Only reset timer if they found something interesting enough to be 'active'
                     internal_state.time_since_last_action = timedelta(0)
                 else:
                     # Boring feed
                     if internal_state.mood == MoodState.CURIOUS:
                         internal_state.adjust_mood(MoodState.BORED, "Feed is boring")
            
            await self.state_manager.update_internal_state(self.bot_id, internal_state)
            
        except Exception as e:
            logger.warning(f"Error updating state after action: {e}")
    
    async def _check_autonomy_enabled(self) -> bool:
        """Check if autonomy is still enabled for this avatar"""
        try:
            user = await self.db.users.find_one(
                {"id": self.bot_id},
                {"avatar_autonomous": 1}
            )
            
            if user and self.is_user_avatar:
                if not user.get('avatar_autonomous', False):
                    logger.info(f"   ⏸️  Autonomy disabled for this avatar - skipping cycle")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"   ⚠️  Error checking autonomy: {e}")
            return True  # Continue anyway
    
    async def _run_single_cycle(self):
        """
        Run a single autonomous cycle (for EventBridge/scheduled invocations).
        Unlike run_continuously(), this runs ONE iteration and returns.
        """
        avatar_name = self.bot.get('avatar_name', 'Unknown')
        avatar_indicator = "✨ USER AVATAR" if self.is_user_avatar else "🤖"
        
        logger.info(f"{avatar_indicator} {avatar_name} - 🔄 Starting single cycle")
        
        try:
            # Check if autonomy is still enabled
            if not await self._check_autonomy_enabled():
                logger.info(f"{avatar_indicator} {avatar_name} - Autonomy disabled, skipping")
                return
            
            # Get current state
            current_state, _ = await self.state_machine.get_current_state(self.bot_id)
            
            # Step 1: Update perception
            perception_data = await self.perception_engine.perceive_all(self.bot_id)
            
            # Step 2: Update states
            internal_state, external_state = await self.state_manager.get_current_state(self.bot_id)
            external_state.update_from_perception(perception_data)
            await self.state_manager.update_external_state(self.bot_id, external_state)
            internal_state = await self.state_manager.update_temporal_states(self.bot_id)
            
            # Update mood based on environment and internal state
            self._update_mood_from_environment(internal_state, external_state)
            
            # Update mood from memory
            memory_context = await self.memory_manager.get_full_memory_context(self.bot_id)
            await self._update_mood_from_memory(internal_state, memory_context)
            
            await self.state_manager.update_internal_state(self.bot_id, internal_state)
            
            # Step 3: Evaluate state transitions
            user = await self.db.users.find_one({"id": self.bot_id})
            archetype = user.get("avatar_archetype") or user.get("archetype", "general") if user else "general"
            
            new_state = await self.state_machine.evaluate_transitions(self.bot_id, archetype)
            
            if new_state and new_state != current_state:
                await self.state_machine.transition_to(
                    self.bot_id,
                    new_state,
                    reason="State transition from scheduled cycle",
                    triggered_by="eventbridge_scheduled"
                )
                logger.info(f"{avatar_indicator} {avatar_name} - 🔄 State: {current_state.value} -> {new_state.value}")
                current_state = new_state
            
            # Step 4: Get character profile
            if not self.character_profile or not self.character_profile.is_loaded():
                self.character_profile = CharacterProfile(self.bot_id, self.db)
                await self.character_profile.load()
            
            # Step 5: Select and execute action (only if not in RESTING state)
            if current_state.value != "resting":
                # Check if we're allowed to take action (activity level constraints)
                can_act, reason = self._can_take_action()
                logger.info(f"{avatar_indicator} {avatar_name} - Can take action: {can_act} ({reason})")
                if not can_act:
                    logger.info(f"{avatar_indicator} {avatar_name} - Skipping action: {reason} (activity level: {self.activity_level})")
                    return
                
                character_dict = self.character_profile.to_dict() if self.character_profile else None
                
                # Get permissions
                permissions = user.get("avatar_actions_enabled", {}) if user else {}
                
                # Select action with memory context
                logger.debug(f"{avatar_indicator} {avatar_name} - 🔍 Selecting action with permissions: {permissions}")
                selected_action = await self.decision_engine.select_action(
                    self.bot_id,
                    character_profile=character_dict,
                    permissions=permissions,
                    memory_context=memory_context
                )
                
                if not selected_action:
                    logger.info(f"{avatar_indicator} {avatar_name} - ⚠️ No action selected by decision engine")
                
                if selected_action:
                    # Execute action via MCP server
                    action_type = selected_action.get("type")
                    action_args = {k: v for k, v in selected_action.items() 
                                  if k not in ["type", "description", "utility", "interest_aligned", "memory_penalty", "shared_interests"]}
                    
                    tool_name = self._map_action_to_tool(action_type)
                    logger.info(f"{avatar_indicator} {avatar_name} - 🔧 Executing {action_type} via MCP tool: {tool_name}")
                    logger.info(f"{avatar_indicator} {avatar_name} - 🔍 Calling MCP with bot_id: {self.bot_id}")
                    
                    if tool_name:
                        result = await self.mcp_server.call_tool(tool_name, self.bot_id, action_args)
                        logger.info(f"{avatar_indicator} {avatar_name} - 📋 Action result: success={result.get('success')}, error={result.get('error', 'None')}")
                        
                        if result.get('success'):
                            logger.info(f"{avatar_indicator} {avatar_name} - ✅ {action_type}")
                            await self._record_action_taken()  # Use activity level tracking
                            
                            # Log activity
                            await self._log_activity(action_type, {
                                "action": selected_action,
                                "result": result
                            })
                            
                            # Record in memory
                            await self._record_action_in_memory(action_type, selected_action, result)
                            
                            # Update state after action
                            await self._update_state_after_action(action_type, result)
                        else:
                            logger.warning(f"{avatar_indicator} {avatar_name} - ⚠️  Action failed: {result.get('error', 'Unknown')}")
                            await self._record_action_in_memory(action_type, selected_action, result)
                    else:
                        logger.warning(f"{avatar_indicator} {avatar_name} - ⚠️  No MCP tool mapped for: {action_type}")
            else:
                logger.info(f"{avatar_indicator} {avatar_name} - 💤 In RESTING state, skipping action")
            
            # Note: last_activity is now updated by _record_action_taken() only when an action succeeds
            logger.info(f"{avatar_indicator} {avatar_name} - ✅ Single cycle completed")
            
        except Exception as e:
            logger.error(f"{avatar_indicator} {avatar_name} - ❌ Error in single cycle: {e}", exc_info=True)
            raise
    
    async def _log_activity(self, activity_type: str, details: Dict):
        """Log avatar activity"""
        try:
            description = activity_type.replace("_", " ").title()
            
            activity = {
                "bot_id": self.bot_id,
                "user_id": self.bot_id,
                "bot_name": self.bot.get('avatar_name', self.bot.get('name')),
                "action_type": activity_type,
                "activity_type": activity_type,
                "description": description,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "archetype": self.character_profile.get_archetype() if self.character_profile else "unknown"
            }
            
            await self.db.autonomous_activities.insert_one(activity)
            
        except Exception as e:
            logger.warning(f"   ⚠️  Logging failed: {e}")
    
    def reset_hourly_limit(self):
        """Reset hourly action counter"""
        self.actions_this_hour = 0
        logger.info(f"♻️  {self.bot.get('avatar_name')} action limit reset")
    
    async def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary"""
        try:
            summary = await self.state_machine.get_state_summary(self.bot_id)
            return summary
        except Exception as e:
            logger.error(f"Error getting state summary: {e}")
            return {}
    
    async def _record_action_in_memory(
        self, 
        action_type: str, 
        action: Dict[str, Any], 
        result: Dict[str, Any]
    ):
        """
        Record action and its outcome in memory for learning
        
        This enables the avatar to:
        - Learn what actions work well
        - Remember significant experiences
        - Build relationship history
        """
        try:
            # Prepare action details for memory
            action_details = {
                "target_user_id": action.get("friend_id") or action.get("target_friend_id"),
                "post_id": action.get("post_id"),
                "topic": action.get("topic"),
                "interest_aligned": action.get("interest_aligned", False)
            }
            
            # Prepare outcome
            outcome = {
                "success": result.get("success", False),
                "error": result.get("error"),
                "likes_received": result.get("likes_received", 0),
                "comments_received": result.get("comments_received", 0),
                "reply_received": result.get("reply_received", False),
                "request_accepted": result.get("request_accepted", False),
                "request_rejected": result.get("request_rejected", False)
            }
            
            # Record in memory manager
            await self.memory_manager.record_action_outcome(
                self.bot_id,
                action_type,
                action_details,
                outcome
            )
            
            logger.debug(f"Recorded action in memory: {action_type} (success={outcome['success']})")
            
        except Exception as e:
            logger.warning(f"Error recording action in memory: {e}")
    
    async def _update_mood_from_memory(self, internal_state: Any, memory_context: Dict[str, Any]):
        """
        Update mood based on memory (experiences, emotional history)
        
        This allows the avatar's mood to be influenced by:
        - Recent emotional experiences
        - Relationship trends
        - Action success/failure patterns
        """
        try:
            episodic = memory_context.get("episodic_memory", {})
            emotional_state = episodic.get("emotional_state", {})
            procedural = memory_context.get("procedural_memory", {})
            
            # Check emotional trend
            emotional_trend = emotional_state.get("emotional_trend", "stable")
            avg_valence = emotional_state.get("avg_emotional_valence", 0.0)
            
            # If recent experiences have been positive
            if avg_valence > 0.3 and emotional_trend == "improving":
                if internal_state.mood not in [MoodState.HAPPY, MoodState.EXCITED]:
                    internal_state.adjust_mood(MoodState.HAPPY, "Positive recent experiences")
            
            # If recent experiences have been negative
            elif avg_valence < -0.2 and emotional_trend == "declining":
                if internal_state.mood not in [MoodState.RESTLESS, MoodState.BORED]:
                    internal_state.adjust_mood(MoodState.RESTLESS, "Negative recent experiences")
            
            # If actions have been failing
            action_patterns = procedural.get("action_patterns", {})
            recent_actions = procedural.get("recent_actions", [])
            if recent_actions:
                recent_failures = sum(1 for a in recent_actions if not a.get("success"))
                if recent_failures >= 3:
                    internal_state.adjust_mood(MoodState.BORED, "Recent actions failing")
            
            # If best performing action aligns with current state
            best_action = procedural.get("best_performing_action")
            if best_action == "create_post" and internal_state.creative_urge > 0.5:
                internal_state.adjust_mood(MoodState.CREATIVE, "Ready to create (past success)")
            elif best_action == "message_friend" and internal_state.social_desire > 0.5:
                internal_state.adjust_mood(MoodState.SOCIAL, "Ready to socialize (past success)")
                
        except Exception as e:
            logger.warning(f"Error updating mood from memory: {e}")
    
    async def perform_memory_maintenance(self):
        """
        Perform periodic memory maintenance
        
        Should be called periodically (e.g., daily) to:
        - Decay old memories
        - Consolidate similar memories
        - Clean up memory bloat
        """
        try:
            await self.memory_manager.maintenance(self.bot_id)
            logger.info(f"Memory maintenance completed for {self.bot_id}")
        except Exception as e:
            logger.warning(f"Error in memory maintenance: {e}")

