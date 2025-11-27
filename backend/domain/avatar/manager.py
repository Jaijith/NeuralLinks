"""
State-Aware Agent Manager - Phase 6
Coordinates all state-aware avatar agents
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.avatar.state_aware_agent import StateAwareAgent
from domain.avatar.intelligent import IntelligentAvatar
from domain.graph.rag import GraphRAG


class SimpleAgentManager:
    """
    Manages all bot agents and coordinates their activities
    Phase 1: Simple scheduler, runs all bots in cycles
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client, deployment: str):
        self.db = db
        self.llm_client = llm_client
        self.deployment = deployment
        self.agents: List[StateAwareAgent] = []
        self.running = False
        
        # Create Graph RAG for intelligent avatar
        self.graph_rag = GraphRAG(db)
        
        # Create intelligent avatar (shared by all agents)
        self.intelligent_avatar = IntelligentAvatar(
            db=db,
            llm_client=llm_client,
            deployment=deployment,
            graph_rag=self.graph_rag
        )
        
        # Initialize MCP server's intelligent_avatar (agents use MCP tools)
        from domain.avatar.mcp.server import intelligent_avatar as mcp_intelligent_avatar
        import domain.avatar.mcp.server as mcp_server_module
        mcp_server_module.intelligent_avatar = self.intelligent_avatar
    
    async def initialize_agents(self):
        """Initialize all autonomous agents (bots + user avatars)"""
        print("\n" + "="*60)
        print("🤖 INITIALIZING STATE-AWARE AGENTS - Phase 6")
        print("="*60)
        
        # Get all users with avatars enabled for autonomy
        # This includes: bots (is_bot=True) AND real users with avatar_autonomous=True
        query = {
            "$or": [
                {"is_bot": True},  # All bots
                {"avatar_autonomous": True}  # Real users with autonomy enabled
            ],
            "avatar_name": {"$exists": True},
            "avatar_picture": {"$exists": True}
        }
        
        agents_data = await self.db.users.find(query, {"_id": 0}).to_list(1000)
        
        # Count bots vs user avatars
        bots_count = sum(1 for u in agents_data if u.get('is_bot'))
        user_avatars_count = len(agents_data) - bots_count
        
        print(f"\n📊 Found {len(agents_data)} autonomous agents:")
        print(f"   🤖 Bots: {bots_count}")
        print(f"   ✨ User Avatars: {user_avatars_count}")
        
        # Create agent for each autonomous entity (bot or user avatar)
        for agent_data in agents_data:
            agent = StateAwareAgent(
                bot=agent_data,  # Works for both bots and user avatars
                db=self.db,
                intelligent_avatar=self.intelligent_avatar
            )
            # Initialize the agent (loads state and character profile)
            await agent.initialize()
            self.agents.append(agent)
        
        print(f"\n✅ Initialized {len(self.agents)} state-aware agents")
        if user_avatars_count > 0:
            print(f"   🎉 Including {user_avatars_count} user avatar(s)!")
        print("="*60 + "\n")
    
    async def run_continuously(self):
        """
        Start all agents in continuous, self-driven loops
        
        Each agent runs independently:
        - Continuously perceives and acts
        - State machine decides when to be passive/resting
        - No external scheduler - agents are self-driven
        """
        self.running = True
        
        print("\n" + "🚀 " + "="*58)
        print("AUTONOMOUS AGENT SYSTEM - CONTINUOUS MODE")
        print("="*60)
        print("🤖 Each agent runs continuously and independently")
        print("🔄 Agents perceive → transition → act → loop")
        print("💤 State machine controls when agents go passive/resting")
        print("⏸️  Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        # Start each agent in its own continuous loop
        agent_tasks = []
        for agent in self.agents:
            task = asyncio.create_task(agent.run_continuously())
            agent_tasks.append(task)
            # Small stagger to prevent all starting at once
            await asyncio.sleep(0.1)
        
        print(f"✅ Started {len(agent_tasks)} agents in continuous mode\n")
        
        # Background task to reset hourly limits
        async def reset_limits_periodically():
            while self.running:
                await asyncio.sleep(3600)  # Every hour
                if self.running:
                    self._reset_hourly_limits()
        
        reset_task = asyncio.create_task(reset_limits_periodically())
        
        try:
            # Wait for all agent tasks (they run forever until cancelled)
            await asyncio.gather(*agent_tasks, return_exceptions=True)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping autonomous agent system...")
            self.running = False
            
            # Cancel all agent tasks
            for task in agent_tasks:
                task.cancel()
            
            # Cancel reset task
            reset_task.cancel()
            
            # Wait for tasks to finish cancelling
            await asyncio.gather(*agent_tasks, reset_task, return_exceptions=True)
            
            print("✅ All agents stopped")
        except Exception as e:
            print(f"\n❌ Error in agent manager: {e}")
            self.running = False
            # Cancel all tasks
            for task in agent_tasks:
                task.cancel()
            reset_task.cancel()
    
    def _reset_hourly_limits(self):
        """Reset hourly action limits for all agents"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("♻️  Resetting hourly limits for all agents")
        for agent in self.agents:
            agent.reset_hourly_limit()
    
    def _get_next_cycle_time(self, minutes: int) -> str:
        """Get next cycle time as string"""
        from datetime import timedelta
        next_time = datetime.now() + timedelta(minutes=minutes)
        return next_time.strftime('%H:%M:%S')
    
    async def get_statistics(self) -> Dict:
        """Get system statistics"""
        # Get activity counts
        total_posts = await self.db.posts.count_documents({"user_id": {"$regex": "^bot-"}})
        total_comments = await self.db.posts.count_documents({"comments": {"$exists": True, "$ne": []}})
        total_friendships = await self.db.friendships.count_documents({})
        
        recent_activities = await self.db.autonomous_activities.count_documents({
            "timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
        })
        
        return {
            "total_agents": len(self.agents),
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_friendships": total_friendships,
            "recent_activities_1h": recent_activities
        }
    
    def stop(self):
        """Stop the agent system"""
        self.running = False

