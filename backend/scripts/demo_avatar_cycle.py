"""
Demo: Show how a single avatar cycle works
Demonstrates the complete state-aware decision-making process
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

load_dotenv()

from core.database import get_database
from domain.avatar.state_aware_agent import StateAwareAgent

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "neurallinks_local")


async def demo_avatar_cycle(avatar_id: str = None):
    """Demonstrate a single avatar cycle"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║     🎭 Avatar State-Aware System - Single Cycle Demo                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Connect to database
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected\n")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Get avatar
    if not avatar_id:
        users = await db.users.find({
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        }).limit(1).to_list(1)
        
        if not users:
            print("❌ No avatars found")
            sys.exit(1)
        
        avatar_id = users[0]['id']
        avatar_name = users[0].get('avatar_name', 'Unknown')
    else:
        user = await db.users.find_one({"id": avatar_id})
        if not user:
            print(f"❌ Avatar {avatar_id} not found")
            sys.exit(1)
        avatar_name = user.get('avatar_name', 'Unknown')
    
    print(f"🎭 Using avatar: {avatar_name} ({avatar_id})\n")
    
    # Create agent
    user = await db.users.find_one({"id": avatar_id})
    agent = StateAwareAgent(user, db)
    
    print("="*70)
    print("STEP 1: Initializing Agent")
    print("="*70)
    await agent.initialize()
    print("✅ Agent initialized")
    print(f"   - Character profile loaded: {agent.character_profile.is_loaded()}")
    print(f"   - Archetype: {agent.character_profile.get_archetype() if agent.character_profile else 'N/A'}")
    
    # Get initial state
    summary = await agent.get_state_summary()
    if summary:
        current_state = summary.get('current_state', {})
        print(f"   - Initial state: {current_state.get('top_level')}")
        print(f"   - Mood: {summary.get('internal_state', {}).get('mood')}")
    
    print("\n" + "="*70)
    print("STEP 2: Running Activity Cycle")
    print("="*70)
    print("\nThis will demonstrate:")
    print("  1. Perception (what the avatar sees)")
    print("  2. State updates (how the avatar feels)")
    print("  3. State machine evaluation (state transitions)")
    print("  4. Decision making (what action to take)")
    print("  5. Action execution (doing the action)")
    print("\nRunning cycle...\n")
    
    # Run cycle
    await agent.run_cycle()
    
    # Get final state
    print("\n" + "="*70)
    print("STEP 3: Final State")
    print("="*70)
    summary = await agent.get_state_summary()
    if summary:
        current_state = summary.get('current_state', {})
        internal = summary.get('internal_state', {})
        external = summary.get('external_state', {})
        
        print(f"   - Current state: {current_state.get('top_level')}")
        print(f"   - Mood: {internal.get('mood')}")
        print(f"   - Energy: {internal.get('energy_level')}")
        print(f"   - Social desire: {internal.get('social_desire')}")
        print(f"   - Friend activity: {external.get('friend_activity_level')}")
        print(f"   - Unread messages: {external.get('unread_messages')}")
    
    print("\n" + "="*70)
    print("✅ Demo Complete!")
    print("="*70)
    print("\nTo see continuous activity, run:")
    print("  python scripts/run_autonomous_agents.py")
    print("\nThis will run cycles every 30 minutes for all avatars.")
    
    client.close()


if __name__ == "__main__":
    import sys
    
    avatar_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(demo_avatar_cycle(avatar_id))
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted")

