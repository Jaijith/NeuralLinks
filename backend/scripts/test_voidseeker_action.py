"""
Test script to manually trigger an action for VoidSeeker68 and verify completion
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from domain.avatar.state_aware_agent import StateAwareAgent
from domain.avatar.intelligent import IntelligentAvatar
from domain.graph.rag import GraphRAG
from openai import AsyncOpenAI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_voidseeker_action():
    """Manually trigger a single cycle for VoidSeeker68"""
    # Get MongoDB URI
    mongodb_uri = os.environ.get('MONGODB_URI')
    if not mongodb_uri:
        mongodb_uri = "mongodb+srv://2n1user:bSe4As5QIZGGRndR@avatarcluster0.pfih8m3.mongodb.net/?appName=AvatarCluster0"
        logger.warning("Using hardcoded MongoDB URI")
    
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.neurallinks_local
    
    try:
        # Find VoidSeeker68
        user = await db.users.find_one({"avatar_name": "VoidSeeker68"})
        
        if not user:
            logger.error("❌ VoidSeeker68 not found")
            return
        
        user_id = user.get('id')
        logger.info(f"👤 Found VoidSeeker68: {user_id}")
        logger.info(f"📅 Last Activity: {user.get('last_activity', 'Never')}")
        logger.info(f"🤖 Autonomous: {user.get('avatar_autonomous', False)}")
        logger.info(f"📊 Activity Level: {user.get('avatar_activity_level', 'medium')}\n")
        
        # Initialize OpenAI client (optional, for intelligent avatar)
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        openai_client = None
        intelligent_avatar = None
        graph_rag = None
        
        if openai_api_key:
            openai_client = AsyncOpenAI(api_key=openai_api_key)
            graph_rag = GraphRAG(db)
            intelligent_avatar = IntelligentAvatar(db, openai_client, "gpt-4o-mini", graph_rag)
        
        # Create StateAwareAgent
        logger.info("🔄 Initializing StateAwareAgent...")
        agent = StateAwareAgent(
            bot=user,
            db=db,
            intelligent_avatar=intelligent_avatar
        )
        await agent.initialize()
        
        logger.info(f"✅ Agent initialized")
        logger.info(f"   Activity Level: {agent.activity_level}")
        logger.info(f"   Max Actions/Day: {agent.max_actions_per_day}")
        logger.info(f"   Min Interval: {agent.min_action_interval.total_seconds()/60:.1f} minutes")
        logger.info(f"   Last Action Time: {agent.last_action_time}")
        logger.info(f"   Actions Today: {agent.actions_today}\n")
        
        # Check if can take action
        can_act, reason = agent._can_take_action()
        logger.info(f"🔍 Can take action: {can_act} - {reason}\n")
        
        # Run single cycle and see what action is selected
        logger.info("🚀 Running single cycle to see if post action is selected...")
        try:
            await agent._run_single_cycle()
            logger.info("✅ Cycle completed!")
        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}", exc_info=True)
        
        # Check updated state
        updated_user = await db.users.find_one({"id": user_id})
        logger.info(f"\n📊 Updated State:")
        logger.info(f"   Last Activity: {updated_user.get('last_activity', 'Never')}")
        
        # Check recent posts
        from datetime import datetime, timedelta, timezone
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        recent_posts = await db.posts.find(
            {"user_id": user_id, "created_at": {"$gte": one_hour_ago.isoformat()}}
        ).sort("created_at", -1).limit(5).to_list(5)
        
        logger.info(f"   Recent Posts (last hour): {len(recent_posts)}")
        for post in recent_posts:
            created = post.get('created_at', 'Unknown')
            content = post.get('content', '')[:60]
            logger.info(f"      - {created}: {content}...")
        
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_voidseeker_action())

