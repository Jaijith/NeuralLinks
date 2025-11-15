"""
Simple Agent Manager - Phase 1 MVP
Coordinates all reactive bot agents
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from simple_reactive_agent import SimpleReactiveAgent
from intelligent_avatar import IntelligentAvatar
from graph_rag import GraphRAG


class SimpleAgentManager:
    """
    Manages all bot agents and coordinates their activities
    Phase 1: Simple scheduler, runs all bots in cycles
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client, deployment: str):
        self.db = db
        self.llm_client = llm_client
        self.deployment = deployment
        self.agents: List[SimpleReactiveAgent] = []
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
    
    async def initialize_agents(self):
        """Initialize all autonomous agents (bots + user avatars)"""
        print("\n" + "="*60)
        print("🤖 INITIALIZING AUTONOMOUS AGENTS - Phase 1.5")
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
            agent = SimpleReactiveAgent(
                bot=agent_data,  # Works for both bots and user avatars
                db=self.db,
                intelligent_avatar=self.intelligent_avatar
            )
            self.agents.append(agent)
            
            # Mark if this is a user avatar (for special handling)
            if not agent_data.get('is_bot'):
                agent.is_user_avatar = True
        
        print(f"\n✅ Initialized {len(self.agents)} agents")
        if user_avatars_count > 0:
            print(f"   🎉 Including {user_avatars_count} user avatar(s)!")
        print("="*60 + "\n")
    
    async def run_single_cycle(self):
        """Run one activity cycle for all agents"""
        print("\n" + "🔄 " + "="*58)
        print(f"⏰ ACTIVITY CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Separate user avatars from bots
        import random
        user_avatars = [a for a in self.agents if getattr(a, 'is_user_avatar', False)]
        bots = [a for a in self.agents if not getattr(a, 'is_user_avatar', False)]
        
        # ALWAYS include user avatars (they should post regularly)
        active_agents = user_avatars.copy()
        
        # Add random bots
        random.shuffle(bots)
        bot_count = random.randint(
            max(1, len(bots) // 4),  # At least 25% of bots
            max(2, len(bots) // 2)    # At most 50% of bots
        )
        active_agents.extend(bots[:bot_count])
        
        # Shuffle final list (but user avatars are guaranteed)
        random.shuffle(active_agents)
        
        print(f"🎯 Running {len(active_agents)} / {len(self.agents)} agents this cycle")
        if user_avatars:
            print(f"   ✨ Including {len(user_avatars)} user avatar(s)\n")
        else:
            print()
        
        # Run agents in parallel (but with delays)
        tasks = []
        for agent in active_agents:
            tasks.append(agent.run_cycle())
            await asyncio.sleep(0.5)  # Stagger starts
        
        # Wait for all to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print("\n✅ Cycle complete")
        print("="*60 + "\n")
    
    async def run_forever(self, cycle_interval_minutes: int = 10):
        """Run agent cycles continuously"""
        self.running = True
        cycle_count = 0
        
        print("\n" + "🚀 " + "="*58)
        print("AUTONOMOUS AGENT SYSTEM STARTED")
        print(f"Cycle interval: {cycle_interval_minutes} minutes")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        try:
            while self.running:
                cycle_count += 1
                
                print(f"\n{'='*60}")
                print(f"📍 CYCLE #{cycle_count}")
                print(f"{'='*60}\n")
                
                # Run cycle
                await self.run_single_cycle()
                
                # Reset hourly limits (every hour)
                if cycle_count % 6 == 0:  # If running every 10 min, 6 cycles = 1 hour
                    self._reset_hourly_limits()
                
                # Wait for next cycle
                print(f"\n⏳ Sleeping for {cycle_interval_minutes} minutes...")
                print(f"   Next cycle at: {self._get_next_cycle_time(cycle_interval_minutes)}")
                
                await asyncio.sleep(cycle_interval_minutes * 60)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping autonomous agent system...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Error in agent manager: {e}")
            self.running = False
    
    def _reset_hourly_limits(self):
        """Reset hourly action limits for all agents"""
        print("\n" + "♻️  " + "="*58)
        print("RESETTING HOURLY LIMITS")
        for agent in self.agents:
            agent.reset_hourly_limit()
        print("="*60 + "\n")
    
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

