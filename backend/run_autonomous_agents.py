"""
Run Autonomous Agents - Phase 1 MVP
Standalone script to start the reactive bot system
"""

import asyncio
import os
import sys
from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from simple_agent_manager import SimpleAgentManager

# Load environment variables
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_SERVICE")
if AZURE_OPENAI_ENDPOINT and not AZURE_OPENAI_ENDPOINT.startswith('https://'):
    AZURE_OPENAI_ENDPOINT = f"https://{AZURE_OPENAI_ENDPOINT}.openai.azure.com"

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")

# Cycle interval (in minutes)
CYCLE_INTERVAL = int(os.getenv("AGENT_CYCLE_INTERVAL", "10"))


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
    
    # Check Azure OpenAI configuration
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("❌ ERROR: Azure OpenAI configuration incomplete!")
        print("\nRequired environment variables:")
        print("  - AZURE_OPENAI_SERVICE")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        print("\nPlease check your backend/.env file")
        sys.exit(1)
    
    print("📋 Configuration:")
    print(f"   MongoDB: {MONGO_URL}")
    print(f"   Database: {DB_NAME}")
    print(f"   Azure OpenAI: {AZURE_OPENAI_ENDPOINT}")
    print(f"   Deployment: {AZURE_OPENAI_DEPLOYMENT}")
    print(f"   Cycle Interval: {CYCLE_INTERVAL} minutes")
    print()
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Test connection
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)
    
    # Initialize Azure OpenAI client
    print("\n🤖 Initializing Azure OpenAI...")
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    print("✅ Azure OpenAI initialized")
    
    # Initialize agent manager
    print("\n🚀 Initializing agent manager...")
    manager = SimpleAgentManager(
        db=db,
        llm_client=llm_client,
        deployment=AZURE_OPENAI_DEPLOYMENT
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
    
    # Start autonomous system
    try:
        await manager.run_forever(cycle_interval_minutes=CYCLE_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

