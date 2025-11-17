"""
Test MCP Agent Integration
Tests that agents use MCP tools correctly and respect permissions
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
from domain.avatar.agent import SimpleReactiveAgent
from domain.avatar.manager import SimpleAgentManager
from domain.avatar.mcp.server import mcp_server

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


async def test_mcp_tools_availability():
    """Test that MCP tools are available and can be queried"""
    print("\n" + "="*60)
    print("TEST 1: MCP Tools Availability")
    print("="*60)
    
    # Get all tools
    all_tools = mcp_server.get_tools_list()
    print(f"\n✅ Found {len(all_tools)} MCP tools:")
    for tool in all_tools:
        print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
    
    return len(all_tools) > 0


async def test_agent_tool_permissions(db, avatar_id: str):
    """Test that agent can get available tools based on permissions"""
    print("\n" + "="*60)
    print("TEST 2: Agent Tool Permissions")
    print("="*60)
    
    # Get available tools for this avatar
    available_tools = await mcp_server.get_available_tools_for_avatar(avatar_id)
    
    print(f"\n✅ Available tools for avatar {avatar_id[:20]}...:")
    if available_tools:
        for tool in available_tools:
            print(f"   - {tool['name']}")
    else:
        print("   ⚠️  No tools available (all actions may be disabled)")
    
    # Get user to check their settings
    user = await db.users.find_one({"id": avatar_id})
    if user:
        actions_enabled = user.get('avatar_actions_enabled', {})
        print(f"\n📋 Avatar action settings:")
        for action, enabled in actions_enabled.items():
            status = "✅" if enabled else "❌"
            print(f"   {status} {action}: {enabled}")
    
    return len(available_tools) > 0


async def test_single_agent_cycle(db, llm_client, deployment: str, avatar_id: str = None):
    """Test running a single agent cycle"""
    print("\n" + "="*60)
    print("TEST 3: Single Agent Cycle")
    print("="*60)
    
    # Get an avatar to test with
    if not avatar_id:
        # Find a bot or user avatar
        avatar = await db.users.find_one({
            "$or": [
                {"is_bot": True},
                {"avatar_autonomous": True}
            ],
            "avatar_name": {"$exists": True}
        })
        
        if not avatar:
            print("❌ No avatars found for testing")
            return False
        
        avatar_id = avatar['id']
        print(f"\n✅ Testing with avatar: {avatar.get('avatar_name', avatar.get('name'))} ({avatar_id[:20]}...)")
    else:
        avatar = await db.users.find_one({"id": avatar_id})
        if not avatar:
            print(f"❌ Avatar {avatar_id} not found")
            return False
        print(f"\n✅ Testing with avatar: {avatar.get('avatar_name', avatar.get('name'))}")
    
    # Create intelligent avatar
    from domain.avatar.intelligent import IntelligentAvatar
    from domain.graph.rag import GraphRAG
    
    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(
        db=db,
        llm_client=llm_client,
        deployment=deployment,
        graph_rag=graph_rag
    )
    
    # Create agent
    agent = SimpleReactiveAgent(
        bot=avatar,
        db=db,
        intelligent_avatar=intelligent_avatar
    )
    
    print(f"\n🔄 Running agent cycle...")
    print("-" * 60)
    
    # Run a single cycle
    try:
        await agent.run_cycle()
        print("-" * 60)
        print("✅ Agent cycle completed successfully")
        return True
    except Exception as e:
        print(f"❌ Agent cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_tool_call(db, avatar_id: str, tool_name: str, arguments: dict):
    """Test calling a specific MCP tool"""
    print("\n" + "="*60)
    print(f"TEST 4: MCP Tool Call - {tool_name}")
    print("="*60)
    
    # Check if tool exists
    all_tools = mcp_server.get_tools_list()
    tool_exists = any(t['name'] == tool_name for t in all_tools)
    
    if not tool_exists:
        print(f"❌ Tool '{tool_name}' not found")
        return False
    
    # Check permission
    available_tools = await mcp_server.get_available_tools_for_avatar(avatar_id)
    tool_available = any(t['name'] == tool_name for t in available_tools)
    
    if not tool_available:
        print(f"❌ Tool '{tool_name}' not available for this avatar (permission denied)")
        return False
    
    print(f"\n🔧 Calling MCP tool: {tool_name}")
    print(f"   Arguments: {arguments}")
    
    try:
        result = await mcp_server.call_tool(tool_name, avatar_id, arguments)
        
        if result.get('success'):
            print(f"✅ Tool call successful")
            print(f"   Result: {result.get('message', 'No message')}")
            return True
        else:
            print(f"⚠️  Tool call returned error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Tool call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🧪 MCP Agent Integration Test Suite                     ║
║                                                              ║
║     Tests MCP tools, permissions, and agent cycles          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check Azure OpenAI configuration
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("⚠️  WARNING: Azure OpenAI configuration incomplete!")
        print("   Some tests may fail without LLM capabilities")
        print()
    
    # Connect to MongoDB
    print("🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Initialize Azure OpenAI client
    llm_client = None
    if all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("\n🤖 Initializing Azure OpenAI...")
        llm_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_API_VERSION
        )
        print("✅ Azure OpenAI initialized")
    
    # Initialize MCP server intelligent avatar
    from domain.avatar.mcp.server import initialize_intelligent_avatar
    if llm_client:
        await initialize_intelligent_avatar()
    
    # Run tests
    results = []
    
    # Test 1: MCP Tools Availability
    results.append(await test_mcp_tools_availability())
    
    # Test 2: Get an avatar for testing
    avatar = await db.users.find_one({
        "$or": [
            {"is_bot": True},
            {"avatar_autonomous": True}
        ],
        "avatar_name": {"$exists": True}
    })
    
    if avatar:
        avatar_id = avatar['id']
        
        # Test 2: Agent Tool Permissions
        results.append(await test_agent_tool_permissions(db, avatar_id))
        
        # Test 3: Single Agent Cycle (only if LLM is available)
        if llm_client:
            results.append(await test_single_agent_cycle(db, llm_client, AZURE_OPENAI_DEPLOYMENT, avatar_id))
        else:
            print("\n⚠️  Skipping agent cycle test (LLM not available)")
        
        # Test 4: Test a specific tool call (discover_profiles is safe)
        if llm_client:
            results.append(await test_mcp_tool_call(
                db, 
                avatar_id, 
                "discover_profiles", 
                {"limit": 3}
            ))
    else:
        print("\n⚠️  No avatars found for testing")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")
    
    # Cleanup
    client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

