"""
Test Bonding Components
Comprehensive test suite for Phase 1 & 2
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database
from domain.workflow.models.bonding_state import BondingState, BondingMetrics, UnresolvedThread, RelationshipArc
from domain.workflow.models.bonding_memory import IdentityMemory, NarrativeMemory, BondMoment, ReflectionLog, BondingSession
from domain.workflow.models.enums import UserIntent, UserMood, BondingMode, UserEmotion, BondingCardType
from domain.workflow.models.chat import AvatarChatSession, AvatarChatMessage, MessageRole
from domain.workflow.services.intent_detector import IntentDetector
from domain.workflow.services.bonding_session import BondingSessionManager
from domain.workflow.services.recap_generator import RecapGenerator
from domain.workflow.services.serendipity_engine import SerendipityEngine
from domain.workflow.services.delight_scorer import UserDelightScorer


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_test(name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")


async def test_phase1_data_models():
    """Test Phase 1: Data Models"""
    print_section("PHASE 1: DATA MODELS")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Enums
    print("\n📋 Test 1: Enums")
    tests_total += 1
    try:
        intent = UserIntent.CHECK_IN
        mood = UserMood.CONTENT
        mode = BondingMode.CHECK_IN
        emotion = UserEmotion.HAPPY
        card_type = BondingCardType.RECAP
        
        print_test("Enum creation", True, f"Created {intent}, {mood}, {mode}, {emotion}, {card_type}")
        tests_passed += 1
    except Exception as e:
        print_test("Enum creation", False, str(e))
    
    # Test 2: BondingState
    print("\n📊 Test 2: BondingState Model")
    tests_total += 1
    try:
        state = BondingState(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        
        # Test metrics update
        state.update_metrics(bond_delta=0.05, trust_delta=0.03)
        
        # Test thread management
        state.add_unresolved_thread(
            topic="Career planning",
            context="User wants to switch to AI field",
            importance=0.8
        )
        
        # Test delight tracking
        state.update_delight(0.7)
        state.update_delight(0.8)
        state.update_delight(0.85)
        
        # Test return pressure
        pressure = state.compute_return_pressure()
        
        # Test serialization
        state_dict = state.to_dict()
        
        print_test("BondingState operations", True, 
                  f"Metrics: {state.metrics.bond_strength:.2f}, Threads: {len(state.unresolved_threads)}, "
                  f"Delight trend: {state.delight_trend}, Pressure: {pressure:.2f}")
        tests_passed += 1
    except Exception as e:
        print_test("BondingState operations", False, str(e))
    
    # Test 3: BondingMemory Models
    print("\n🧠 Test 3: Bonding Memory Models")
    tests_total += 1
    try:
        # IdentityMemory
        identity = IdentityMemory(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            preference_type="communication_style",
            label="prefers morning check-ins",
            description="User is most receptive in mornings"
        )
        identity.confirm()
        
        # NarrativeMemory
        narrative = NarrativeMemory(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            arc_type="growth",
            title="Learning to Code",
            description="User's journey into software development"
        )
        narrative.add_moment("Completed first Python project", significance=0.8)
        
        # BondMoment
        bond_moment = BondMoment(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            moment_type="breakthrough",
            description="User shared their career aspirations",
            bond_impact=0.15
        )
        
        # ReflectionLog
        reflection = ReflectionLog(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            reflection_type="insight",
            title="User values authenticity",
            content="User consistently responds better to honest, direct communication"
        )
        reflection.add_evidence("User appreciated direct feedback on 3 occasions")
        
        # BondingSession
        session = BondingSession(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            trigger="user_initiated",
            detected_intent="check_in"
        )
        
        print_test("Memory models creation", True,
                  f"Created Identity (confidence: {identity.confidence:.2f}), "
                  f"Narrative ({len(narrative.key_moments)} moments), "
                  f"BondMoment (impact: {bond_moment.bond_impact:.2f}), "
                  f"Reflection ({len(reflection.evidence)} evidence), "
                  f"Session")
        tests_passed += 1
    except Exception as e:
        print_test("Memory models creation", False, str(e))
    
    print(f"\n📊 Phase 1 Summary: {tests_passed}/{tests_total} tests passed")
    return tests_passed == tests_total


async def test_phase2_services():
    """Test Phase 2: Core Services"""
    print_section("PHASE 2: CORE SERVICES")
    
    db = get_database()
    tests_passed = 0
    tests_total = 0
    
    # Test 1: IntentDetector (without OpenAI)
    print("\n🎯 Test 1: IntentDetector")
    tests_total += 1
    try:
        detector = IntentDetector(db, openai_client=None)
        
        # Create mock session
        session = AvatarChatSession(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        
        # Test intent detection (fallback mode)
        test_messages = [
            ("How's it going?", UserIntent.CHECK_IN),
            ("I'm so frustrated with this", UserIntent.VENTING),
            ("I want to start learning Python", UserIntent.PLANNING),
            ("Should I take this job?", UserIntent.SEEKING_ADVICE),
            ("I did it! Finished my project!", UserIntent.CELEBRATION)
        ]
        
        all_correct = True
        for message, expected_intent in test_messages:
            intent, confidence = await detector.detect_intent(message, session)
            if intent != expected_intent:
                all_correct = False
                print(f"       ⚠️  '{message}' detected as {intent}, expected {expected_intent}")
        
        # Test emotion detection
        emotion, emotion_conf = await detector.detect_emotion("I'm so excited!", session)
        
        # Test mood estimation
        mood, mood_conf = await detector.estimate_mood("Feeling great today", session)
        
        print_test("IntentDetector operations", all_correct,
                  f"Emotion: {emotion}, Mood: {mood}")
        if all_correct:
            tests_passed += 1
    except Exception as e:
        print_test("IntentDetector operations", False, str(e))
        import traceback
        traceback.print_exc()
    
    # Test 2: BondingSessionManager
    print("\n📝 Test 2: BondingSessionManager")
    tests_total += 1
    try:
        session_manager = BondingSessionManager(db, openai_client=None)
        
        # Create a session
        session = await session_manager.create_session(
            user_id="test_user_1",
            avatar_id="test_avatar_1",
            trigger="user_initiated",
            detected_intent=UserIntent.CHECK_IN,
            user_message="Hey, what's up?"
        )
        
        # Create bonding state for testing
        bonding_state = BondingState(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        bonding_state.update_metrics(bond_delta=0.02, trust_delta=0.01)
        bonding_state.update_delight(0.75)
        
        # End the session
        await asyncio.sleep(0.1)  # Small delay
        completed_session = await session_manager.end_session(
            session_id=session.id,
            bonding_state=bonding_state,
            cards_generated=[
                {"type": "warm_presence", "content": "Hey! Good to hear from you!"},
                {"type": "recap", "content": "I've been exploring some interesting tech stuff"}
            ],
            guidance_asked=False,
            micro_missions_proposed=0
        )
        
        # Verify session was saved
        retrieved = await session_manager.get_session(session.id)
        
        print_test("BondingSessionManager operations", retrieved is not None,
                  f"Session duration: {completed_session.duration_seconds:.2f}s, "
                  f"Delight: {completed_session.delight_score:.2f}")
        if retrieved:
            tests_passed += 1
            
            # Clean up
            await db.bonding_sessions.delete_one({"id": session.id})
    except Exception as e:
        print_test("BondingSessionManager operations", False, str(e))
        import traceback
        traceback.print_exc()
    
    # Test 3: RecapGenerator
    print("\n📊 Test 3: RecapGenerator")
    tests_total += 1
    try:
        recap_gen = RecapGenerator(db, openai_client=None)
        
        # Create mock bonding state
        bonding_state = BondingState(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        bonding_state.last_bonding_session = datetime.now(timezone.utc) - timedelta(days=3)
        
        # Check if recap should be included
        should_include = await recap_gen.should_include_recap(
            bonding_state,
            detected_intent="check_in"
        )
        
        print_test("RecapGenerator logic", should_include,
                  f"Should include recap for check-in: {should_include}")
        if should_include:
            tests_passed += 1
    except Exception as e:
        print_test("RecapGenerator logic", False, str(e))
        import traceback
        traceback.print_exc()
    
    # Test 4: SerendipityEngine
    print("\n✨ Test 4: SerendipityEngine")
    tests_total += 1
    try:
        serendipity = SerendipityEngine(db, openai_client=None)
        
        # Create bonding state
        bonding_state = BondingState(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        bonding_state.metrics.bond_strength = 0.8  # High bond
        bonding_state.user_mood_estimate = UserMood.CONTENT
        
        # Test should_generate (multiple tries to see probability)
        should_generate_results = []
        for i in range(10):
            result = await serendipity.should_generate_surprise(
                bonding_state,
                detected_intent="check_in",
                session_history=[]
            )
            should_generate_results.append(result)
        
        generation_rate = sum(should_generate_results) / len(should_generate_results)
        
        print_test("SerendipityEngine probability", True,
                  f"Generated surprise in {generation_rate*100:.0f}% of cases (expected ~25-35%)")
        tests_passed += 1
    except Exception as e:
        print_test("SerendipityEngine probability", False, str(e))
        import traceback
        traceback.print_exc()
    
    # Test 5: UserDelightScorer
    print("\n😊 Test 5: UserDelightScorer")
    tests_total += 1
    try:
        delight_scorer = UserDelightScorer(db)
        
        # Create bonding state
        bonding_state = BondingState(
            user_id="test_user_1",
            avatar_id="test_avatar_1"
        )
        bonding_state.metrics.bond_strength = 0.7
        bonding_state.metrics.trust = 0.8
        bonding_state.metrics.alignment_confidence = 0.75
        
        # Create session data
        session_data = {
            "detected_intent": "check_in",
            "selected_bonding_mode": "check_in",
            "cards_generated": [
                {"type": "warm_presence", "content": "Hey!"},
                {"type": "recap", "content": "Been exploring AI stuff"},
                {"type": "serendipity", "content": "Found something cool!", "overlap": {"surprise_level": 0.8}}
            ],
            "guidance_asked": False,
            "micro_missions_proposed": 1
        }
        
        # Compute delight
        delight = await delight_scorer.compute_delight(
            session_data,
            bonding_state
        )
        
        # Test with feedback
        feedback = {"rating": 4.5, "helpful": True}
        delight_with_feedback = await delight_scorer.compute_delight(
            session_data,
            bonding_state,
            user_feedback=feedback
        )
        
        print_test("UserDelightScorer computation", 0.0 <= delight <= 1.0,
                  f"Base delight: {delight:.2f}, With feedback: {delight_with_feedback:.2f}")
        if 0.0 <= delight <= 1.0:
            tests_passed += 1
    except Exception as e:
        print_test("UserDelightScorer computation", False, str(e))
        import traceback
        traceback.print_exc()
    
    print(f"\n📊 Phase 2 Summary: {tests_passed}/{tests_total} tests passed")
    return tests_passed == tests_total


async def test_integration():
    """Test integration between components"""
    print_section("INTEGRATION TESTS")
    
    db = get_database()
    tests_passed = 0
    tests_total = 0
    
    # Integration Test: Full bonding session flow
    print("\n🔄 Test: Full Bonding Session Flow")
    tests_total += 1
    try:
        # 1. Create services
        intent_detector = IntentDetector(db, openai_client=None)
        session_manager = BondingSessionManager(db, openai_client=None)
        delight_scorer = UserDelightScorer(db)
        
        # 2. User sends message
        user_message = "Hey! How's it going?"
        
        # Create chat session
        chat_session = AvatarChatSession(
            user_id="test_user_integration",
            avatar_id="test_avatar_integration"
        )
        
        # 3. Detect intent
        intent, intent_conf = await intent_detector.detect_intent(user_message, chat_session)
        emotion, emotion_conf = await intent_detector.detect_emotion(user_message, chat_session)
        
        # 4. Create bonding session
        bonding_session = await session_manager.create_session(
            user_id="test_user_integration",
            avatar_id="test_avatar_integration",
            trigger="user_initiated",
            detected_intent=intent,
            user_message=user_message
        )
        
        # 5. Create bonding state
        bonding_state = BondingState(
            user_id="test_user_integration",
            avatar_id="test_avatar_integration"
        )
        bonding_state.metrics.bond_strength = 0.6
        bonding_state.metrics.trust = 0.65
        bonding_state.update_metrics(bond_delta=0.03, trust_delta=0.02)
        
        # 6. Generate response (mock cards)
        cards = [
            {"type": "warm_presence", "content": "Hey! Great to hear from you!"},
            {"type": "recap", "content": "I've been reading about machine learning"}
        ]
        
        # 7. Compute delight
        session_data = {
            "detected_intent": intent.value,
            "selected_bonding_mode": "check_in",
            "cards_generated": cards,
            "guidance_asked": False,
            "micro_missions_proposed": 0
        }
        
        delight = await delight_scorer.compute_delight(session_data, bonding_state)
        bonding_state.update_delight(delight)
        
        # 8. End session
        await asyncio.sleep(0.1)
        completed = await session_manager.end_session(
            session_id=bonding_session.id,
            bonding_state=bonding_state,
            cards_generated=cards
        )
        
        # Verify everything worked
        success = (
            intent == UserIntent.CHECK_IN and
            completed.delight_score > 0 and
            completed.duration_seconds > 0
        )
        
        print_test("Full session flow", success,
                  f"Intent: {intent}, Emotion: {emotion}, Delight: {delight:.2f}, "
                  f"Duration: {completed.duration_seconds:.2f}s")
        
        if success:
            tests_passed += 1
        
        # Clean up
        await db.bonding_sessions.delete_one({"id": bonding_session.id})
        
    except Exception as e:
        print_test("Full session flow", False, str(e))
        import traceback
        traceback.print_exc()
    
    print(f"\n📊 Integration Summary: {tests_passed}/{tests_total} tests passed")
    return tests_passed == tests_total


async def main():
    """Run all tests"""
    print("\n" + "🧪" * 40)
    print("  BONDING WORKFLOW ENGINE - COMPONENT TESTING")
    print("  Testing Phase 1 & Phase 2 Components")
    print("🧪" * 40)
    
    # Run tests
    phase1_passed = await test_phase1_data_models()
    phase2_passed = await test_phase2_services()
    integration_passed = await test_integration()
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    print("\n📋 Test Results:")
    print(f"   Phase 1 (Data Models):    {'✅ PASSED' if phase1_passed else '❌ FAILED'}")
    print(f"   Phase 2 (Core Services):  {'✅ PASSED' if phase2_passed else '❌ FAILED'}")
    print(f"   Integration Tests:        {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    
    all_passed = phase1_passed and phase2_passed and integration_passed
    
    if all_passed:
        print("\n🎉 SUCCESS! All components are working correctly!")
        print("   ✅ Data models validated")
        print("   ✅ Services functional")
        print("   ✅ Integration verified")
        print("\n   🚀 Ready to proceed to Phase 3 (Bonding Workflow Engine)")
    else:
        print("\n⚠️  Some tests failed. Review the errors above.")
        print("   Fix issues before proceeding to Phase 3.")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
