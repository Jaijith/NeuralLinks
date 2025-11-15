"""
Quick test script for Phase 1 MVP
Runs a single activity cycle
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from simple_agent_manager import SimpleAgentManager

load_dotenv()

async def test_single_cycle():
    """Test a single activity cycle"""
    
    print("\n" + "="*60)
    print("🧪 PHASE 1 MVP - SINGLE CYCLE TEST")
    print("="*60 + "\n")
    
    # Configuration
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = "neurallinks_local"
    
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_SERVICE")
    if AZURE_OPENAI_ENDPOINT and not AZURE_OPENAI_ENDPOINT.startswith('https://'):
        AZURE_OPENAI_ENDPOINT = f"https://{AZURE_OPENAI_ENDPOINT}.openai.azure.com"
    
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    AZURE_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
    
    print("📋 Configuration:")
    print(f"   MongoDB: {MONGO_URL}")
    print(f"   Azure Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"   Deployment: {AZURE_OPENAI_DEPLOYMENT}")
    print()
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected\n")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Initialize Azure OpenAI
    print("🤖 Initializing Azure OpenAI...")
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    print("✅ Azure OpenAI initialized\n")
    
    # Initialize manager
    print("🚀 Initializing agent manager...")
    manager = SimpleAgentManager(
        db=db,
        llm_client=llm_client,
        deployment=AZURE_OPENAI_DEPLOYMENT
    )
    
    # Initialize agents
    await manager.initialize_agents()
    
    if not manager.agents:
        print("❌ No agents found!")
        return
    
    # Show stats before
    print("\n📊 Statistics BEFORE cycle:")
    stats_before = await manager.get_statistics()
    print(f"   Total Posts: {stats_before['total_posts']}")
    print(f"   Total Comments: {stats_before['total_comments']}")
    print(f"   Total Friendships: {stats_before['total_friendships']}")
    print()
    
    # Run single cycle
    print("🔄 Running activity cycle...\n")
    await manager.run_single_cycle()
    
    # Show stats after
    print("\n📊 Statistics AFTER cycle:")
    stats_after = await manager.get_statistics()
    print(f"   Total Posts: {stats_after['total_posts']} (+{stats_after['total_posts'] - stats_before['total_posts']})")
    print(f"   Total Comments: {stats_after['total_comments']} (+{stats_after['total_comments'] - stats_before['total_comments']})")
    print(f"   Total Friendships: {stats_after['total_friendships']} (+{stats_after['total_friendships'] - stats_before['total_friendships']})")
    print()
    
    # Success!
    print("="*60)
    print("✅ PHASE 1 TEST COMPLETE!")
    print("="*60)
    print("\n🎯 Next step: Run full autonomous system:")
    print("   python run_autonomous_agents.py")
    print("\n💡 Or check the new content in your frontend:")
    print("   http://localhost:3000")
    print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_single_cycle())

