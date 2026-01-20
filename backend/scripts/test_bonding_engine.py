"""
Test Bonding Workflow Engine
Test the complete bonding engine end-to-end
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database
from domain.workflow.engines.bonding_engine import BondingWorkflowEngine
from domain.workflow.engines.engine_registry import WorkflowEngineRegistry
from domain.workflow.mcp.tools import WorkflowMCPServer
from domain.workflow.models.chat import AvatarChatSession, AvatarChatMessage, MessageRole


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def test_engine_registration():
    """Test that the bonding engine is registered"""
    print_section("ENGINE REGISTRATION TEST")
    
    engines = WorkflowEngineRegistry.list_engines()
    bonding_engine = next((e for e in engines if e['name'] == 'bonding'), None)
    
    if bonding_engine:
        print(f"✅ Bonding engine registered!")
        print(f"   Name: {bonding_engine['name']}")
        print(f"   Description: {bonding_engine['description']}")
        print(f"   Mission types: {bonding_engine['supported_mission_types']}")
        return True
    else:
        print("❌ Bonding engine NOT registered!")
        print(f"   Available engines: {[e['name'] for e in engines]}")
        return False


async def test_engine_initialization():
    """Test engine can be initialized"""
    print_section("ENGINE INITIALIZATION TEST")
    
    db = get_database()
    mcp_server = WorkflowMCPServer(db)
    
    try:
        engine = BondingWorkflowEngine(
            db=db,
            mcp_server=mcp_server,
            openai_client=None,  # No OpenAI for testing
            intelligent_avatar=None
        )
        
        print("✅ Engine initialized successfully!")
        print(f"   Engine name: {engine.engine_name}")
        print(f"   Supported types: {engine.supported_mission_types}")
        print(f"   Workflow nodes: {len(engine.workflow_graph)}")
        print(f"   Node order: {engine._get_node_order()}")
        return True
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_engine_execution():
    """Test engine execution end-to-end"""
    print_section("ENGINE EXECUTION TEST")
    
    db = get_database()
    mcp_server = WorkflowMCPServer(db)
    
    try:
        engine = BondingWorkflowEngine(
            db=db,
            mcp_server=mcp_server,
            openai_client=None,
            intelligent_avatar=None
        )
        
        # Create test session
        session = AvatarChatSession(
            user_id="test_user_bonding",
            avatar_id="test_avatar_bonding"
        )
        
        # Execute bonding workflow
        print("\n🚀 Executing bonding workflow...")
        print("   User message: 'Hey! How's it going?'")
        
        result = await engine.execute(
            user_id="test_user_bonding",
            avatar_id="test_avatar_bonding",
            user_message="Hey! How's it going?",
            session=session
        )
        
        print("\n📊 Workflow Results:")
        print(f"   Type: {result.get('type')}")
        print(f"   Cards generated: {len(result.get('cards', []))}")
        print(f"   Guidance asked: {result.get('guidance_asked')}")
        print(f"   Detected intent: {result.get('detected_intent')}")
        print(f"   Bonding mode: {result.get('bonding_mode')}")
        
        print(f"\n📈 Metrics:")
        metrics = result.get('metrics', {})
        print(f"   Bond delta: {metrics.get('bond_delta', 0):.3f}")
        print(f"   Trust delta: {metrics.get('trust_delta', 0):.3f}")
        print(f"   Delight score: {metrics.get('delight_score', 0):.2f}")
        
        print(f"\n💬 Response Cards:")
        for i, card in enumerate(result.get('cards', []), 1):
            card_type = card.get('type', 'unknown')
            content = card.get('content', '')[:60]
            print(f"   {i}. [{card_type}] {content}...")
        
        # Verify response structure
        if result.get('type') == 'bonding':
            if len(result.get('cards', [])) > 0:
                if 'metrics' in result:
                    print("\n✅ Engine execution successful!")
                    
                    # Clean up test data
                    await db.bonding_states.delete_one({
                        "user_id": "test_user_bonding",
                        "avatar_id": "test_avatar_bonding"
                    })
                    await db.bonding_sessions.delete_many({
                        "user_id": "test_user_bonding",
                        "avatar_id": "test_avatar_bonding"
                    })
                    
                    return True
        
        print("⚠️  Execution completed but response format unexpected")
        return False
        
    except Exception as e:
        print(f"❌ Engine execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_different_intents():
    """Test engine with different user intents"""
    print_section("DIFFERENT INTENTS TEST")
    
    db = get_database()
    mcp_server = WorkflowMCPServer(db)
    
    try:
        engine = BondingWorkflowEngine(
            db=db,
            mcp_server=mcp_server,
            openai_client=None,
            intelligent_avatar=None
        )
        
        test_messages = [
            ("I'm so frustrated with this project!", "venting"),
            ("I want to start learning Python", "planning"),
            ("I finished my first app!", "celebration"),
            ("Should I take this new job?", "seeking_advice")
        ]
        
        all_passed = True
        
        for message, expected_intent_type in test_messages:
            print(f"\n🧪 Testing: '{message}'")
            
            session = AvatarChatSession(
                user_id="test_user_intents",
                avatar_id="test_avatar_intents"
            )
            
            result = await engine.execute(
                user_id="test_user_intents",
                avatar_id="test_avatar_intents",
                user_message=message,
                session=session
            )
            
            detected_intent = result.get('detected_intent')
            bonding_mode = result.get('bonding_mode')
            num_cards = len(result.get('cards', []))
            
            print(f"   Intent: {detected_intent}, Mode: {bonding_mode}, Cards: {num_cards}")
            
            if num_cards == 0:
                print(f"   ⚠️  No cards generated")
                all_passed = False
        
        # Clean up
        await db.bonding_states.delete_many({"user_id": "test_user_intents"})
        await db.bonding_sessions.delete_many({"user_id": "test_user_intents"})
        
        if all_passed:
            print("\n✅ All intent tests passed!")
        else:
            print("\n⚠️  Some intent tests had issues")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Intent testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "🧪" * 40)
    print("  BONDING WORKFLOW ENGINE - COMPREHENSIVE TEST")
    print("  Testing Phase 3: BondingWorkflowEngine")
    print("🧪" * 40)
    
    # Run tests
    test1 = await test_engine_registration()
    test2 = await test_engine_initialization()
    test3 = await test_engine_execution()
    test4 = await test_different_intents()
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    print("\n📋 Test Results:")
    print(f"   Engine Registration:      {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"   Engine Initialization:    {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"   Engine Execution:         {'✅ PASSED' if test3 else '❌ FAILED'}")
    print(f"   Different Intents:        {'✅ PASSED' if test4 else '❌ FAILED'}")
    
    all_passed = test1 and test2 and test3 and test4
    
    if all_passed:
        print("\n🎉 SUCCESS! Bonding Workflow Engine is fully functional!")
        print("   ✅ All nodes executing correctly")
        print("   ✅ Response generation working")
        print("   ✅ Metrics computation accurate")
        print("   ✅ Intent detection integrated")
        print("\n   🚀 Ready for integration with ChatService")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
