"""
Autonomous Agent Runner - Real-time Avatar Autonomy

Manages individual avatar agents that run when autonomy is enabled.
Each avatar with avatar_autonomous=True gets its own background task
running the full StateAwareAgent (behavior trees, MCP tools, state machine, memory).

This replaces the need for a separate script - agents start/stop automatically
when users toggle autonomy in the UI.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from domain.avatar.state_aware_agent import StateAwareAgent
from domain.avatar.intelligent import IntelligentAvatar
from domain.graph.rag import GraphRAG

logger = logging.getLogger(__name__)


class AutonomousAgentRunner:
    """
    Manages autonomous avatar agents in real-time.
    
    When a user enables autonomy for their avatar:
    1. Creates a StateAwareAgent for that user
    2. Starts the agent's continuous loop as a background task
    3. Tracks the task so it can be stopped when autonomy is disabled
    
    Features:
    - Per-avatar agent management (not all-or-nothing)
    - Automatic cleanup when autonomy is disabled
    - Uses full domain services stack (behavior trees, MCP, state machine, memory)
    - Thread-safe task management
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        llm_client: Any,
        model_name: str,
        intelligent_avatar: Optional[IntelligentAvatar] = None,
        graph_rag: Optional[GraphRAG] = None
    ):
        self.db = db
        self.llm_client = llm_client
        self.model_name = model_name
        
        # Create or use provided Graph RAG
        self.graph_rag = graph_rag or GraphRAG(db)
        
        # Create or use provided intelligent avatar (shared by all agents)
        self.intelligent_avatar = intelligent_avatar or IntelligentAvatar(
            db=db,
            llm_client=llm_client,
            model=model_name,
            graph_rag=self.graph_rag
        )
        
        # Track running agents: user_id -> (task, agent)
        self._running_agents: Dict[str, tuple[asyncio.Task, StateAwareAgent]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("🤖 AutonomousAgentRunner initialized")
    
    async def start_agent(self, user_id: str) -> bool:
        """
        Start autonomous agent for a specific user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if agent started successfully, False otherwise
        """
        async with self._lock:
            # Check if already running
            if user_id in self._running_agents:
                logger.info(f"✨ Agent for {user_id} is already running")
                return True
            
            try:
                # Get user data from database
                user = await self.db.users.find_one({"id": user_id})
                if not user:
                    logger.error(f"❌ User {user_id} not found")
                    return False
                
                # Verify user has avatar configured
                if not user.get('avatar_name') or not user.get('avatar_picture'):
                    logger.warning(f"⚠️ User {user_id} doesn't have avatar configured")
                    return False
                
                # Verify autonomy is enabled
                if not user.get('avatar_autonomous', False):
                    logger.warning(f"⚠️ Autonomy not enabled for user {user_id}")
                    return False
                
                # Create StateAwareAgent for this user
                agent = StateAwareAgent(
                    bot=user,
                    db=self.db,
                    intelligent_avatar=self.intelligent_avatar
                )
                
                # Initialize the agent
                await agent.initialize()
                
                # Initialize MCP server's intelligent_avatar if not already set
                try:
                    import domain.avatar.mcp.server as mcp_server_module
                    if mcp_server_module.intelligent_avatar is None:
                        mcp_server_module.intelligent_avatar = self.intelligent_avatar
                except Exception as e:
                    logger.warning(f"Could not set MCP intelligent_avatar: {e}")
                
                # Start the agent's continuous loop as a background task
                task = asyncio.create_task(
                    self._run_agent_loop(user_id, agent),
                    name=f"agent_{user_id}"
                )
                
                # Track the running agent
                self._running_agents[user_id] = (task, agent)
                
                avatar_name = user.get('avatar_name', 'Unknown')
                activity_level = user.get('avatar_activity_level', 'medium')
                logger.info(
                    f"✅ Started autonomous agent for {avatar_name} (user: {user_id}) "
                    f"| Activity Level: {activity_level} | Max {agent.max_actions_per_day} actions/day"
                )
                
                # Update user's last_activity
                await self.db.users.update_one(
                    {"id": user_id},
                    {"$set": {"agent_started_at": datetime.now(timezone.utc).isoformat()}}
                )
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to start agent for {user_id}: {e}", exc_info=True)
                return False
    
    async def stop_agent(self, user_id: str) -> bool:
        """
        Stop autonomous agent for a specific user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if agent stopped successfully, False if not running
        """
        async with self._lock:
            if user_id not in self._running_agents:
                logger.info(f"ℹ️ No agent running for {user_id}")
                return False
            
            try:
                task, agent = self._running_agents[user_id]
                
                # Cancel the task
                task.cancel()
                
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                
                # Remove from tracking
                del self._running_agents[user_id]
                
                avatar_name = agent.bot.get('avatar_name', 'Unknown')
                logger.info(f"⏹️ Stopped autonomous agent for {avatar_name} (user: {user_id})")
                
                # Update user record
                await self.db.users.update_one(
                    {"id": user_id},
                    {"$set": {"agent_stopped_at": datetime.now(timezone.utc).isoformat()}}
                )
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error stopping agent for {user_id}: {e}", exc_info=True)
                # Try to clean up anyway
                if user_id in self._running_agents:
                    del self._running_agents[user_id]
                return False
    
    async def _run_agent_loop(self, user_id: str, agent: StateAwareAgent):
        """
        Wrapper for agent's continuous loop with error handling.
        """
        avatar_name = agent.bot.get('avatar_name', 'Unknown')
        
        try:
            logger.info(f"🚀 Starting continuous loop for {avatar_name}")
            await agent.run_continuously()
        except asyncio.CancelledError:
            logger.info(f"⏹️ Agent loop cancelled for {avatar_name}")
        except Exception as e:
            logger.error(f"❌ Agent loop error for {avatar_name}: {e}", exc_info=True)
        finally:
            # Clean up if still tracked
            async with self._lock:
                if user_id in self._running_agents:
                    del self._running_agents[user_id]
            logger.info(f"🔚 Agent loop ended for {avatar_name}")
    
    def is_agent_running(self, user_id: str) -> bool:
        """Check if an agent is running for a user."""
        return user_id in self._running_agents
    
    def get_running_agents_count(self) -> int:
        """Get count of currently running agents."""
        return len(self._running_agents)
    
    def get_running_agent_ids(self) -> list:
        """Get list of user IDs with running agents."""
        return list(self._running_agents.keys())
    
    async def resume_all_enabled_agents(self):
        """
        Resume agents for all users who have autonomy enabled.
        Called on application startup to restore running agents.
        """
        logger.info("🔄 Resuming agents for users with autonomy enabled...")
        
        try:
            # Find all users with autonomy enabled and avatar configured
            query = {
                "avatar_autonomous": True,
                "avatar_name": {"$exists": True, "$ne": None},
                "avatar_picture": {"$exists": True, "$ne": None},
                "is_bot": {"$ne": True}  # Only real users, not bots
            }
            
            users = await self.db.users.find(query, {"id": 1, "avatar_name": 1}).to_list(100)
            
            if not users:
                logger.info("ℹ️ No users with autonomy enabled found")
                return
            
            logger.info(f"📊 Found {len(users)} user(s) with autonomy enabled")
            
            # Start agents for each user
            started_count = 0
            for user in users:
                user_id = user.get('id')
                avatar_name = user.get('avatar_name', 'Unknown')
                
                if await self.start_agent(user_id):
                    started_count += 1
                    logger.info(f"   ✅ Resumed {avatar_name}")
                else:
                    logger.warning(f"   ⚠️ Failed to resume {avatar_name}")
                
                # Small delay between starts to prevent overwhelming
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ Resumed {started_count}/{len(users)} autonomous agents")
            
        except Exception as e:
            logger.error(f"❌ Error resuming agents: {e}", exc_info=True)
    
    async def stop_all_agents(self):
        """Stop all running agents. Called on application shutdown."""
        logger.info("⏹️ Stopping all autonomous agents...")
        
        user_ids = list(self._running_agents.keys())
        for user_id in user_ids:
            await self.stop_agent(user_id)
        
        logger.info("✅ All agents stopped")
    
    async def get_agent_status(self, user_id: str) -> Dict[str, Any]:
        """Get status of a specific agent."""
        if user_id not in self._running_agents:
            return {
                "running": False,
                "user_id": user_id
            }
        
        task, agent = self._running_agents[user_id]
        
        return {
            "running": True,
            "user_id": user_id,
            "avatar_name": agent.bot.get('avatar_name'),
            "task_done": task.done(),
            "task_cancelled": task.cancelled(),
            "actions_this_hour": agent.actions_this_hour,
            "max_actions_per_hour": agent.max_actions_per_hour
        }


# Global instance (initialized in globals.py)
_agent_runner: Optional[AutonomousAgentRunner] = None


def get_agent_runner() -> Optional[AutonomousAgentRunner]:
    """Get the global agent runner instance."""
    return _agent_runner


def set_agent_runner(runner: AutonomousAgentRunner):
    """Set the global agent runner instance."""
    global _agent_runner
    _agent_runner = runner

