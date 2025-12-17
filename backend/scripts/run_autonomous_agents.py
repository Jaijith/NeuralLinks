"""
Run Autonomous Agents - Phase 1 MVP
Standalone script to start the reactive bot system
"""

import asyncio
import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from dotenv import load_dotenv
from domain.avatar.manager import SimpleAgentManager

# Load environment variables - explicitly from backend directory
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGODB_URI = os.getenv("MONGODB_URI")  # For production (MongoDB Atlas)
DB_NAME = os.getenv("DB_NAME", "neurallinks_local")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Note: Agents now run continuously (no cycle interval needed)
# Each agent runs its own loop and decides when to be active/passive based on state


async def main():
    """Main entry point"""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🤖 NeuralLinks Autonomous Agent System - Phase 1 MVP    ║
║                                                              ║
║     Simple Reactive Agents - Immediate Bot Activity         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check OpenAI configuration
    if not OPENAI_API_KEY:
        print("❌ ERROR: OpenAI configuration incomplete!")
        print("\nRequired environment variables:")
        print("  - OPENAI_API_KEY")
        print("  - OPENAI_MODEL (optional, defaults to gpt-4o-mini)")
        print("\nPlease check your backend/.env file")
        sys.exit(1)
    
    # Use MongoDB Atlas URI if available, otherwise local
    mongo_connection = MONGODB_URI or MONGO_URL
    
    print("📋 Configuration:")
    print(f"   MongoDB: {'Atlas (production)' if MONGODB_URI else mongo_connection}")
    print(f"   Database: {DB_NAME}")
    print(f"   OpenAI Model: {OPENAI_MODEL}")
    print(f"   Mode: Continuous (self-driven, no scheduler)")
    print()
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(mongo_connection)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Initialize OpenAI client
    print("\n🤖 Initializing OpenAI...")
    llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    print(f"✅ OpenAI initialized (model: {OPENAI_MODEL})")
    
    # Initialize agent manager
    print("\n🚀 Initializing agent manager...")
    manager = SimpleAgentManager(
        db=db,
        llm_client=llm_client,
        deployment=OPENAI_MODEL  # Now model name instead of Azure deployment
    )
    
    # Initialize all bot agents
    await manager.initialize_agents()
    
    if not manager.agents:
        print("❌ No bot agents found! Run generate_dual_world_bots.py first.")
        sys.exit(1)
    
    # Show current statistics
    stats = await manager.get_statistics()
    print("\n📊 Current Statistics:")
    print(f"   Total Agents: {stats['total_agents']}")
    print(f"   Total Posts: {stats['total_posts']}")
    print(f"   Total Comments: {stats['total_comments']}")
    print(f"   Total Friendships: {stats['total_friendships']}")
    print(f"   Activities (last hour): {stats['recent_activities_1h']}")
    print()
    
    # Start autonomous system (continuous mode - no scheduler)
    try:
        await manager.run_continuously()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

