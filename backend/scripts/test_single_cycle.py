"""
Quick Test: Run a Single Agent Cycle
Tests MCP integration with a single agent cycle
"""

import asyncio
import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from domain.avatar.manager import SimpleAgentManager

# Load environment variables
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "neurallinks_local"

# Try both AZURE_OPENAI_SERVICE and AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_SERVICE")
if AZURE_OPENAI_ENDPOINT and not AZURE_OPENAI_ENDPOINT.startswith('https://'):
    AZURE_OPENAI_ENDPOINT = f"https://{AZURE_OPENAI_ENDPOINT}.openai.azure.com"

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")


async def main():
    """Run a single agent cycle to test MCP integration"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🧪 Single Agent Cycle Test - MCP Integration             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
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
    
    # Initialize Azure OpenAI client
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("❌ ERROR: Azure OpenAI configuration incomplete!")
        print("   Required: AZURE_OPENAI_SERVICE, AZURE_OPENAI_API_KEY, AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        return
    
    print("🤖 Initializing Azure OpenAI...")
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    print("✅ Azure OpenAI initialized\n")
    
    # Initialize agent manager
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
    
    print(f"\n✅ Initialized {len(manager.agents)} agents")
    print(f"   Running a single cycle to test MCP integration...\n")
    print("="*60)
    
    # Run a single cycle
    try:
        await manager.run_single_cycle()
        print("\n✅ Cycle completed! Check the output above to see MCP tools in action.")
        print("\nLook for:")
        print("   - '🔧 Available MCP tools: ...' - Shows which tools are enabled")
        print("   - '✅ ... via MCP' - Shows successful MCP tool calls")
        print("   - '⚠️  ... failed' - Shows if any tools failed")
    except Exception as e:
        print(f"\n❌ Cycle failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

