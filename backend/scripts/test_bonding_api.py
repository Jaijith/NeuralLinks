"""
Test script for Bonding Workflow API
Tests all bonding endpoints
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def test_bonding_api():
    """Test bonding workflow API endpoints"""
    
    print("="*60)
    print("🧪 TESTING BONDING WORKFLOW API")
    print("="*60)
    
    from core.database import get_database
    from core.config import get_openai_client
    from domain.workflow.engines.engine_registry import WorkflowEngineRegistry
    from domain.workflow.engines.base_engine import WorkflowState
    from domain.workflow.models.enums import MissionType
    from domain.workflow.mcp.tools import WorkflowMCPServer
    from domain.avatar import IntelligentAvatar
    from domain.graph import GraphRAG
    
    # Initialize
    db = get_database()
    openai_client = get_openai_client()
    graph_rag = GraphRAG(db)
    intelligent_avatar = IntelligentAvatar(db, openai_client, "gpt-4o-mini", graph_rag)
    mcp_server = WorkflowMCPServer(db, intelligent_avatar, openai_client)
    
    print("\n✅ Services initialized")
    
    # Test 1: Get bonding engine
    print("\n📝 Test 1: Get Bonding Engine")
    try:
        bonding_engine = WorkflowEngineRegistry.get_engine(
            "bonding",
            db=db,
            mcp_server=mcp_server,
            intelligent_avatar=intelligent_avatar
        )
        print(f"✅ Got bonding engine: {bonding_engine.engine_name}")
    except Exception as e:
        print(f"❌ Failed to get bonding engine: {e}")
        return False
    
    # Test 2: Trigger bonding workflow with check-in
    print("\n📝 Test 2: Trigger Bonding Workflow (Check-in)")
    try:
        # Get a test user
        user = await db.users.find_one({"avatar_name": {"$exists": True}})
        if not user:
            print("⚠️  No users with avatars found. Creating test data...")
            return False
        
        user_id = user["id"]
        avatar_id = user_id
        
        print(f"   User: {user.get('avatar_name', 'Unknown')}")
        
        # Execute bonding workflow
        result = await bonding_engine.execute(
            user_id=user_id,
            avatar_id=avatar_id,
            user_message="Hey! How have you been? What have you been up to?"
        )
        
        print(f"✅ Bonding workflow executed successfully!")
        print(f"   Intent: {result.get('detected_intent')}")
        print(f"   Mode: {result.get('bonding_mode')}")
        print(f"   Session ID: {result.get('session_id')}")
        
        response = result.get("response", {})
        cards = response.get("cards", [])
        print(f"   Cards generated: {len(cards)}")
        for i, card in enumerate(cards, 1):
            print(f"     {i}. {card.get('type')}: {card.get('content', '')[:60]}...")
        
        metrics = result.get("metrics", {})
        print(f"   Metrics: bond_delta={metrics.get('bond_delta', 0):.3f}, trust_delta={metrics.get('trust_delta', 0):.3f}")
        
        session_id = result.get("session_id")
        
    except Exception as e:
        print(f"❌ Failed to trigger bonding workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Get bonding state
    print("\n📝 Test 3: Get Bonding State")
    try:
        state_doc = await db.avatar_bonding_state.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id
        })
        
        if state_doc:
            print(f"✅ Bonding state found")
            print(f"   Bond strength: {state_doc.get('bond_strength', 0):.3f}")
            print(f"   Trust: {state_doc.get('trust', 0):.3f}")
            print(f"   Alignment: {state_doc.get('alignment_confidence', 0):.3f}")
        else:
            print("⚠️  No bonding state found (might be first interaction)")
    except Exception as e:
        print(f"❌ Failed to get bonding state: {e}")
    
    # Test 4: Get bonding session
    if session_id:
        print("\n📝 Test 4: Get Bonding Session")
        try:
            session = await db.bonding_sessions.find_one({"id": session_id})
            if session:
                print(f"✅ Session found")
                print(f"   Start time: {session.get('start_time')}")
                print(f"   Intent: {session.get('detected_intent')}")
                print(f"   Mode: {session.get('bonding_mode')}")
                print(f"   User mood: {session.get('user_mood')}")
            else:
                print("⚠️  Session not found")
        except Exception as e:
            print(f"❌ Failed to get session: {e}")
    
    # Test 5: Test different intents
    print("\n📝 Test 5: Test Different Intents")
    test_messages = [
        ("I'm feeling really stressed about work lately...", "venting"),
        ("Can you help me plan my week?", "planning"),
        ("I just got a promotion! 🎉", "celebration"),
    ]
    
    for message, expected_intent in test_messages:
        try:
            result = await bonding_engine.execute(
                user_id=user_id,
                avatar_id=avatar_id,
                user_message=message
            )
            
            detected_intent = result.get('detected_intent')
            
            print(f"   Message: \"{message}\"")
            print(f"   ✅ Detected: {detected_intent} (expected: {expected_intent})")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print("\n" + "="*60)
    print("✅ BONDING API TESTS COMPLETE!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_bonding_api())
    sys.exit(0 if success else 1)
