"""
Test script to manually trigger an action for VoidSeeker68 and verify completion
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Set MongoDB URI BEFORE any imports that might use it
if not os.environ.get('MONGODB_URI'):
    os.environ['MONGODB_URI'] = "mongodb+srv://2n1user:bSe4As5QIZGGRndR@avatarcluster0.pfih8m3.mongodb.net/?appName=AvatarCluster0"

# Try to get OpenAI API key from AWS Secrets Manager if not set
if not os.environ.get('OPENAI_API_KEY'):
    try:
        import boto3
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        secret_name = os.environ.get('OPENAI_SECRET_NAME', '2n1/openai/api-key')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        os.environ['OPENAI_API_KEY'] = response['SecretString']
        print(f"✅ Retrieved OpenAI API key from Secrets Manager: {secret_name}")
    except Exception as e:
        print(f"⚠️ Could not retrieve OpenAI API key from Secrets Manager: {e}")
        print("   Set OPENAI_API_KEY environment variable manually if needed")

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
        # Set environment variable so MCP server uses the same connection
        os.environ['MONGODB_URI'] = mongodb_uri
    
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
        from core.config import get_openai_client, OPENAI_MODEL
        
        openai_client = get_openai_client()
        intelligent_avatar = None
        graph_rag = None
        
        if openai_client:
            graph_rag = GraphRAG(db)
            intelligent_avatar = IntelligentAvatar(db, openai_client, OPENAI_MODEL, graph_rag)
            
            # Also initialize MCP server's intelligent_avatar
            from domain.avatar.mcp.server import initialize_intelligent_avatar, intelligent_avatar as mcp_intelligent_avatar
            await initialize_intelligent_avatar()
            # Check if it was set
            from domain.avatar.mcp import server as mcp_server_module
            logger.info(f"   MCP intelligent_avatar after init: {mcp_server_module.intelligent_avatar is not None}")
            logger.info("   ✅ MCP server intelligent_avatar initialized\n")
        
        # Create StateAwareAgent
        logger.info("🔄 Initializing StateAwareAgent...")
        start_time = time.time()
        agent = StateAwareAgent(
            bot=user,
            db=db,
            intelligent_avatar=intelligent_avatar
        )
        await agent.initialize()
        init_time = time.time() - start_time
        
        logger.info(f"✅ Agent initialized (took {init_time:.2f}s)")
        logger.info(f"   Activity Level: {agent.activity_level}")
        logger.info(f"   Max Actions/Day: {agent.max_actions_per_day}")
        logger.info(f"   Min Interval: {agent.min_action_interval.total_seconds()/60:.1f} minutes")
        logger.info(f"   Last Action Time: {agent.last_action_time}")
        logger.info(f"   Actions Today: {agent.actions_today}\n")
        
        # Enable create_posts permission for testing
        logger.info("🔧 Enabling create_posts permission...")
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": {"avatar_actions_enabled.create_posts": True}}
        )
        logger.info(f"   Update result: matched={result.matched_count}, modified={result.modified_count}")
        
        # Reload user data to get updated permissions
        user = await db.users.find_one({"id": user_id})
        actions = user.get('avatar_actions_enabled', {})
        logger.info(f"   Current permissions: {actions}")
        logger.info(f"   create_posts value: {actions.get('create_posts', 'NOT SET')}\n")
        
        # Check if can take action
        can_act, reason = agent._can_take_action()
        logger.info(f"🔍 Can take action: {can_act} - {reason}\n")
        
        # Force state to CREATIVE (better for posting) and prevent RESTING transitions
        logger.info("🔄 Forcing state to CREATIVE to allow post actions...")
        from domain.avatar.state_machine.avatar_state_machine import TopLevelState
        
        # Force to CREATIVE state
        await agent.state_machine.transition_to(
            user_id,
            TopLevelState.CREATIVE,
            reason="Force creative for testing post creation",
            triggered_by="test_script"
        )
        
        # Also update internal state to prevent RESTING transition
        internal_state, external_state = await agent.state_manager.get_current_state(user_id)
        internal_state.energy_level = 0.8  # High energy
        internal_state.creative_urge = 0.9  # High creative urge
        internal_state.time_since_last_action = timedelta(minutes=5)  # Recent action
        await agent.state_manager.update_internal_state(user_id, internal_state)
        
        logger.info("   ✅ State forced to CREATIVE with high energy/creative urge\n")
        
        # Now run cycle
        logger.info("🚀 Running single cycle to create a post...")
        cycle_start = time.time()
        try:
            await agent._run_single_cycle()
            cycle_time = time.time() - cycle_start
            logger.info(f"✅ Cycle completed! (took {cycle_time:.2f}s)")
        except Exception as e:
            cycle_time = time.time() - cycle_start
            logger.error(f"❌ Cycle failed after {cycle_time:.2f}s: {e}", exc_info=True)
        
        # Check updated state
        updated_user = await db.users.find_one({"id": user_id})
        logger.info(f"\n📊 Updated State:")
        logger.info(f"   Last Activity: {updated_user.get('last_activity', 'Never')}")
        
        # Check recent posts
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

