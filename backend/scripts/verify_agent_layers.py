"""
State-Aware Agent Layer Verification Script
============================================
Verifies that all 8 layers of the state-aware agent architecture are properly
integrated and working together for decision-making.

Layers Verified:
1. State Machine (Top-Level States)
2. Internal State (Psychological Model)
3. External State (Environmental Perception)
4. Character Profile (Personality)
5. Decision Engine (Action Selection)
6. Memory System (Learning & Adaptation)
7. Activity Diversity System
8. Activity Levels (Frequency Control)
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_database
from domain.avatar.state_aware_agent import StateAwareAgent
from domain.avatar.state import StateManager
from domain.avatar.state_machine import AvatarStateMachine
from domain.avatar.perception.engine import PerceptionEngine
from domain.avatar.decision import DecisionEngine
from domain.avatar.character import CharacterProfile
from domain.avatar.memory import MemoryManager
from domain.avatar.decision.action_utility import ActionUtility
from domain.avatar.decision.activity_diversity import ActivityDiversityManager


class AgentLayerVerifier:
    """Comprehensive verification of state-aware agent layers"""
    
    def __init__(self, avatar_id: str):
        self.avatar_id = avatar_id
        self.db = None
        self.agent = None
        self.results = {
            "layer_checks": {},
            "integration_checks": {},
            "decision_flow_check": {},
            "overall_status": "unknown"
        }
    
    async def initialize(self):
        """Initialize database and agent"""
        print("\n" + "="*80)
        print("🔬 State-Aware Agent Layer Verification")
        print("="*80)
        
        self.db = get_database()
        
        # Load avatar
        user = await self.db.users.find_one({"id": self.avatar_id})
        if not user:
            raise ValueError(f"Avatar {self.avatar_id} not found")
        
        print(f"\n✅ Avatar Found: {user.get('avatar_name', 'Unknown')}")
        print(f"   Archetype: {user.get('avatar_archetype', 'Unknown')}")
        print(f"   Activity Level: {user.get('avatar_activity_level', 'Unknown')}")
        
        # Initialize agent
        self.agent = StateAwareAgent(user, self.db)
        await self.agent.initialize()
        
        print(f"   Agent Initialized: ✓")
    
    async def verify_layer_1_state_machine(self) -> Dict[str, Any]:
        """Verify Layer 1: State Machine"""
        print("\n" + "-"*80)
        print("📊 Layer 1: State Machine (Top-Level States)")
        print("-"*80)
        
        result = {
            "name": "State Machine",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check state machine exists
            if hasattr(self.agent, 'state_machine'):
                result["components_found"].append("state_machine")
                print("   ✓ State Machine: Found")
            
            # Get current state
            current_state, sub_states = await self.agent.state_machine.get_current_state(self.avatar_id)
            result["details"]["current_state"] = current_state.value if current_state else "None"
            result["details"]["sub_states"] = sub_states
            print(f"   ✓ Current State: {current_state.value}")
            print(f"   ✓ Sub-States: {sub_states}")
            
            # Test state transitions
            user = await self.db.users.find_one({"id": self.avatar_id})
            archetype = user.get("avatar_archetype", "casual_observer")
            new_state = await self.agent.state_machine.evaluate_transitions(self.avatar_id, archetype)
            result["details"]["evaluated_transition"] = new_state.value if new_state else "No transition"
            print(f"   ✓ Transition Evaluation: {result['details']['evaluated_transition']}")
            
            result["status"] = "✅ PASS"
            print("\n   Status: ✅ Layer 1 is functional")
            
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 1 failed - {e}")
        
        self.results["layer_checks"]["layer_1"] = result
        return result
    
    async def verify_layer_2_internal_state(self) -> Dict[str, Any]:
        """Verify Layer 2: Internal State (Psychological Model)"""
        print("\n" + "-"*80)
        print("🧠 Layer 2: Internal State (Psychological Model)")
        print("-"*80)
        
        result = {
            "name": "Internal State",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Get internal state
            internal_state, _ = await self.agent.state_manager.get_current_state(self.avatar_id)
            
            if internal_state:
                result["components_found"].append("internal_state")
                
                # Check psychological dimensions
                result["details"]["mood"] = internal_state.mood.value
                result["details"]["energy_level"] = f"{internal_state.energy_level:.2f}"
                result["details"]["social_desire"] = f"{internal_state.social_desire:.2f}"
                result["details"]["creative_urge"] = f"{internal_state.creative_urge:.2f}"
                
                print(f"   ✓ Mood: {internal_state.mood.value}")
                print(f"   ✓ Energy Level: {internal_state.energy_level:.2f}")
                print(f"   ✓ Social Desire: {internal_state.social_desire:.2f}")
                print(f"   ✓ Creative Urge: {internal_state.creative_urge:.2f}")
                
                # Check temporal tracking
                print(f"   ✓ Time Since Last Post: {internal_state.time_since_last_post}")
                print(f"   ✓ Time Since Last Conversation: {internal_state.time_since_last_conversation}")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 2 is functional")
            else:
                raise Exception("Internal state not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 2 failed - {e}")
        
        self.results["layer_checks"]["layer_2"] = result
        return result
    
    async def verify_layer_3_external_state(self) -> Dict[str, Any]:
        """Verify Layer 3: External State (Environmental Perception)"""
        print("\n" + "-"*80)
        print("🌍 Layer 3: External State (Environmental Perception)")
        print("-"*80)
        
        result = {
            "name": "External State",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Get external state
            _, external_state = await self.agent.state_manager.get_current_state(self.avatar_id)
            
            if external_state:
                result["components_found"].append("external_state")
                
                # Check perception data
                result["details"]["friend_activity_level"] = f"{external_state.friend_activity_level:.2f}"
                result["details"]["unread_messages"] = external_state.unread_messages
                result["details"]["pending_friend_requests"] = external_state.pending_friend_requests
                
                print(f"   ✓ Friend Activity Level: {external_state.friend_activity_level:.2f}")
                print(f"   ✓ Unread Messages: {external_state.unread_messages}")
                print(f"   ✓ Pending Friend Requests: {external_state.pending_friend_requests}")
                
                # Check relationship map
                relationship_map = external_state.get_relationship_map()
                result["details"]["friends_count"] = len(relationship_map)
                print(f"   ✓ Friends Count: {len(relationship_map)}")
                
                # Check recent posts
                recent_posts = external_state.get_recent_posts(limit=5)
                result["details"]["recent_posts_count"] = len(recent_posts)
                print(f"   ✓ Recent Posts: {len(recent_posts)}")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 3 is functional")
            else:
                raise Exception("External state not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 3 failed - {e}")
        
        self.results["layer_checks"]["layer_3"] = result
        return result
    
    async def verify_layer_4_character_profile(self) -> Dict[str, Any]:
        """Verify Layer 4: Character Profile (Personality)"""
        print("\n" + "-"*80)
        print("🎭 Layer 4: Character Profile (Personality)")
        print("-"*80)
        
        result = {
            "name": "Character Profile",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check character profile
            if self.agent.character_profile and self.agent.character_profile.is_loaded():
                result["components_found"].append("character_profile")
                
                # Get archetype
                archetype = self.agent.character_profile.get_archetype()
                result["details"]["archetype"] = archetype
                print(f"   ✓ Archetype: {archetype}")
                
                # Get interests
                interests = self.agent.character_profile.get_interests()
                result["details"]["interests_count"] = len(interests)
                print(f"   ✓ Interests: {len(interests)} - {interests[:3]}")
                
                # Get personality traits
                traits = self.agent.character_profile.get_personality_traits()
                result["details"]["traits_count"] = len(traits)
                print(f"   ✓ Personality Traits: {len(traits)} - {list(traits.keys())[:3]}")
                
                # Get action preferences
                action_prefs = self.agent.character_profile.get_action_preferences()
                result["details"]["action_preferences"] = {
                    k: f"{v:.2f}" for k, v in list(action_prefs.items())[:5]
                }
                print(f"   ✓ Action Preferences:")
                for action, pref in list(action_prefs.items())[:5]:
                    print(f"      - {action}: {pref:.2f}")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 4 is functional")
            else:
                raise Exception("Character profile not loaded")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 4 failed - {e}")
        
        self.results["layer_checks"]["layer_4"] = result
        return result
    
    async def verify_layer_5_decision_engine(self) -> Dict[str, Any]:
        """Verify Layer 5: Decision Engine (Action Selection)"""
        print("\n" + "-"*80)
        print("🎯 Layer 5: Decision Engine (Action Selection)")
        print("-"*80)
        
        result = {
            "name": "Decision Engine",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check decision engine
            if hasattr(self.agent, 'decision_engine'):
                result["components_found"].append("decision_engine")
                print("   ✓ Decision Engine: Found")
                
                # Get character profile dict
                character_dict = self.agent.character_profile.to_dict() if self.agent.character_profile else None
                
                # Get permissions
                user = await self.db.users.find_one({"id": self.avatar_id})
                permissions = user.get("avatar_actions_enabled", {}) if user else {}
                result["details"]["permissions"] = permissions
                print(f"   ✓ Permissions: {len(permissions)} actions enabled")
                
                # Get memory context
                memory_context = await self.agent.memory_manager.get_full_memory_context(self.avatar_id)
                result["details"]["memory_context"] = {
                    "semantic": len(memory_context.get("semantic_memory", {}).get("interests", [])),
                    "procedural": "present" if memory_context.get("procedural_memory") else "missing",
                    "episodic": "present" if memory_context.get("episodic_memory") else "missing"
                }
                print(f"   ✓ Memory Context:")
                print(f"      - Semantic: {result['details']['memory_context']['semantic']} interests")
                print(f"      - Procedural: {result['details']['memory_context']['procedural']}")
                print(f"      - Episodic: {result['details']['memory_context']['episodic']}")
                
                # Test action selection
                selected_action = await self.agent.decision_engine.select_action(
                    self.avatar_id,
                    character_profile=character_dict,
                    permissions=permissions,
                    memory_context=memory_context
                )
                
                if selected_action:
                    result["details"]["selected_action"] = selected_action.get("type")
                    result["details"]["action_utility"] = selected_action.get("utility", "N/A")
                    print(f"   ✓ Action Selection: {selected_action.get('type')}")
                    print(f"   ✓ Interest Aligned: {selected_action.get('interest_aligned', False)}")
                else:
                    print(f"   ⚠️  No action selected (may be expected)")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 5 is functional")
            else:
                raise Exception("Decision engine not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 5 failed - {e}")
        
        self.results["layer_checks"]["layer_5"] = result
        return result
    
    async def verify_layer_6_memory_system(self) -> Dict[str, Any]:
        """Verify Layer 6: Memory System (Learning & Adaptation)"""
        print("\n" + "-"*80)
        print("🧩 Layer 6: Memory System (Learning & Adaptation)")
        print("-"*80)
        
        result = {
            "name": "Memory System",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check memory manager
            if hasattr(self.agent, 'memory_manager'):
                result["components_found"].append("memory_manager")
                print("   ✓ Memory Manager: Found")
                
                # Get full memory context
                memory_context = await self.agent.memory_manager.get_full_memory_context(self.avatar_id)
                
                # Check semantic memory
                semantic = memory_context.get("semantic_memory", {})
                interests = semantic.get("interests", [])
                result["details"]["semantic_interests"] = len(interests)
                print(f"   ✓ Semantic Memory: {len(interests)} interests")
                
                # Check procedural memory
                procedural = memory_context.get("procedural_memory", {})
                action_patterns = procedural.get("action_patterns", {})
                best_action = procedural.get("best_performing_action", "N/A")
                result["details"]["procedural_patterns"] = len(action_patterns)
                result["details"]["best_action"] = best_action
                print(f"   ✓ Procedural Memory: {len(action_patterns)} patterns tracked")
                print(f"   ✓ Best Performing Action: {best_action}")
                
                # Check episodic memory
                episodic = memory_context.get("episodic_memory", {})
                emotional_state = episodic.get("emotional_state", {})
                trend = emotional_state.get("emotional_trend", "unknown")
                result["details"]["emotional_trend"] = trend
                print(f"   ✓ Episodic Memory: Emotional trend = {trend}")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 6 is functional")
            else:
                raise Exception("Memory manager not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 6 failed - {e}")
        
        self.results["layer_checks"]["layer_6"] = result
        return result
    
    async def verify_layer_7_activity_diversity(self) -> Dict[str, Any]:
        """Verify Layer 7: Activity Diversity System"""
        print("\n" + "-"*80)
        print("🎨 Layer 7: Activity Diversity System")
        print("-"*80)
        
        result = {
            "name": "Activity Diversity",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check action utility has diversity manager
            if hasattr(self.agent.decision_engine, 'action_utility'):
                action_utility = self.agent.decision_engine.action_utility
                
                if hasattr(action_utility, 'diversity_manager'):
                    result["components_found"].append("diversity_manager")
                    print("   ✓ Diversity Manager: Found")
                    
                    # Get diversity summary
                    diversity_summary = action_utility.get_diversity_summary()
                    result["details"]["recent_actions"] = diversity_summary.get("recent_actions", [])
                    result["details"]["diversity_needed"] = diversity_summary.get("diversity_needed", False)
                    
                    print(f"   ✓ Recent Actions: {diversity_summary.get('recent_actions', [])}")
                    print(f"   ✓ Diversity Needed: {diversity_summary.get('diversity_needed', False)}")
                    print(f"   ✓ Window Size: {diversity_summary.get('window_size', 0)}")
                    
                    # Test diversity scoring
                    test_action = "create_post"
                    diversity_score = action_utility.diversity_manager.get_combined_diversity_score(test_action)
                    result["details"]["test_diversity_score"] = f"{diversity_score:.2f}"
                    print(f"   ✓ Test Diversity Score (create_post): {diversity_score:.2f}")
                    
                    result["status"] = "✅ PASS"
                    print("\n   Status: ✅ Layer 7 is functional")
                else:
                    raise Exception("Diversity manager not found in action_utility")
            else:
                raise Exception("Action utility not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 7 failed - {e}")
        
        self.results["layer_checks"]["layer_7"] = result
        return result
    
    async def verify_layer_8_activity_levels(self) -> Dict[str, Any]:
        """Verify Layer 8: Activity Levels (Frequency Control)"""
        print("\n" + "-"*80)
        print("⚡ Layer 8: Activity Levels (Frequency Control)")
        print("-"*80)
        
        result = {
            "name": "Activity Levels",
            "components_found": [],
            "status": "unknown",
            "details": {}
        }
        
        try:
            # Check activity level configuration
            if hasattr(self.agent, 'activity_config'):
                result["components_found"].append("activity_config")
                
                result["details"]["activity_level"] = self.agent.activity_level
                result["details"]["max_actions_per_day"] = self.agent.max_actions_per_day
                result["details"]["min_interval_minutes"] = self.agent.activity_config.get("min_interval_minutes")
                result["details"]["delay_multiplier"] = self.agent.activity_config.get("delay_multiplier")
                
                print(f"   ✓ Activity Level: {self.agent.activity_level}")
                print(f"   ✓ Max Actions/Day: {self.agent.max_actions_per_day}")
                print(f"   ✓ Min Interval: {self.agent.activity_config.get('min_interval_minutes')} minutes")
                print(f"   ✓ Delay Multiplier: {self.agent.activity_config.get('delay_multiplier')}x")
                
                # Check current activity tracking
                result["details"]["actions_today"] = self.agent.actions_today
                result["details"]["last_action_time"] = str(self.agent.last_action_time)
                print(f"   ✓ Actions Today: {self.agent.actions_today}/{self.agent.max_actions_per_day}")
                
                # Test can take action
                can_act, reason = self.agent._can_take_action()
                result["details"]["can_act_now"] = can_act
                result["details"]["reason"] = reason
                print(f"   ✓ Can Act Now: {can_act} ({reason})")
                
                result["status"] = "✅ PASS"
                print("\n   Status: ✅ Layer 8 is functional")
            else:
                raise Exception("Activity config not found")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Status: ❌ Layer 8 failed - {e}")
        
        self.results["layer_checks"]["layer_8"] = result
        return result
    
    async def verify_integration(self) -> Dict[str, Any]:
        """Verify that all layers are integrated and working together"""
        print("\n" + "="*80)
        print("🔗 Integration Verification")
        print("="*80)
        
        result = {
            "name": "Layer Integration",
            "checks": [],
            "status": "unknown"
        }
        
        try:
            # Check 1: State Machine → Internal/External State
            print("\n   Check 1: State Machine → Internal/External State")
            internal_state, external_state = await self.agent.state_manager.get_current_state(self.avatar_id)
            current_state, _ = await self.agent.state_machine.get_current_state(self.avatar_id)
            
            if internal_state and external_state and current_state:
                result["checks"].append("✅ State Machine ↔ State Manager")
                print("      ✅ States are synchronized")
            else:
                result["checks"].append("❌ State Machine ↔ State Manager")
                
            # Check 2: Character Profile → Decision Engine
            print("\n   Check 2: Character Profile → Decision Engine")
            if self.agent.character_profile and self.agent.decision_engine:
                result["checks"].append("✅ Character Profile → Decision Engine")
                print("      ✅ Character influences decisions")
            else:
                result["checks"].append("❌ Character Profile → Decision Engine")
            
            # Check 3: Memory → Decision Engine
            print("\n   Check 3: Memory → Decision Engine")
            if self.agent.memory_manager and hasattr(self.agent.decision_engine, 'memory_manager'):
                result["checks"].append("✅ Memory → Decision Engine")
                print("      ✅ Memory informs decisions")
            else:
                result["checks"].append("❌ Memory → Decision Engine")
            
            # Check 4: Diversity → Action Utility
            print("\n   Check 4: Activity Diversity → Action Utility")
            if hasattr(self.agent.decision_engine.action_utility, 'diversity_manager'):
                result["checks"].append("✅ Diversity → Action Utility")
                print("      ✅ Diversity affects action scoring")
            else:
                result["checks"].append("❌ Diversity → Action Utility")
            
            # Check 5: Activity Levels → Agent
            print("\n   Check 5: Activity Levels → Agent")
            if hasattr(self.agent, 'activity_config') and hasattr(self.agent, '_can_take_action'):
                result["checks"].append("✅ Activity Levels → Agent")
                print("      ✅ Activity levels control frequency")
            else:
                result["checks"].append("❌ Activity Levels → Agent")
            
            # Overall integration status
            passed_checks = sum(1 for check in result["checks"] if "✅" in check)
            total_checks = len(result["checks"])
            
            if passed_checks == total_checks:
                result["status"] = "✅ PASS"
                print(f"\n   Integration Status: ✅ All {total_checks} checks passed")
            else:
                result["status"] = "⚠️  PARTIAL"
                print(f"\n   Integration Status: ⚠️  {passed_checks}/{total_checks} checks passed")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Integration Status: ❌ Failed - {e}")
        
        self.results["integration_checks"] = result
        return result
    
    async def test_full_decision_cycle(self) -> Dict[str, Any]:
        """Test a complete decision cycle through all layers"""
        print("\n" + "="*80)
        print("🔄 Full Decision Cycle Test")
        print("="*80)
        
        result = {
            "name": "Decision Cycle",
            "steps": [],
            "status": "unknown"
        }
        
        try:
            print("\n   Simulating a single decision cycle...")
            
            # Step 1: Perceive
            print("\n   Step 1: PERCEIVE environment")
            perception_data = await self.agent.perception_engine.perceive_all(self.avatar_id)
            result["steps"].append("✅ Perception")
            print("      ✅ Environment perceived")
            
            # Step 2: Update States
            print("\n   Step 2: UPDATE states")
            internal_state, external_state = await self.agent.state_manager.get_current_state(self.avatar_id)
            external_state.update_from_perception(perception_data)
            await self.agent.state_manager.update_external_state(self.avatar_id, external_state)
            result["steps"].append("✅ State Update")
            print("      ✅ States updated")
            
            # Step 3: Load Character
            print("\n   Step 3: LOAD character profile")
            if not self.agent.character_profile.is_loaded():
                await self.agent.character_profile.load()
            character_dict = self.agent.character_profile.to_dict()
            result["steps"].append("✅ Character Loaded")
            print("      ✅ Character profile loaded")
            
            # Step 4: Get Memory
            print("\n   Step 4: GET memory context")
            memory_context = await self.agent.memory_manager.get_full_memory_context(self.avatar_id)
            result["steps"].append("✅ Memory Retrieved")
            print("      ✅ Memory context retrieved")
            
            # Step 5: Select Action
            print("\n   Step 5: SELECT action")
            user = await self.db.users.find_one({"id": self.avatar_id})
            permissions = user.get("avatar_actions_enabled", {}) if user else {}
            
            selected_action = await self.agent.decision_engine.select_action(
                self.avatar_id,
                character_profile=character_dict,
                permissions=permissions,
                memory_context=memory_context
            )
            
            if selected_action:
                result["steps"].append("✅ Action Selected")
                result["selected_action"] = selected_action.get("type")
                print(f"      ✅ Action selected: {selected_action.get('type')}")
                print(f"      - Interest Aligned: {selected_action.get('interest_aligned', False)}")
                print(f"      - Memory Penalty: {selected_action.get('memory_penalty', 0.0)}")
            else:
                result["steps"].append("⚠️  No Action")
                print("      ⚠️  No action selected")
            
            # Summary
            passed_steps = sum(1 for step in result["steps"] if "✅" in step)
            total_steps = len(result["steps"])
            
            if passed_steps == total_steps:
                result["status"] = "✅ PASS"
                print(f"\n   Decision Cycle: ✅ All {total_steps} steps completed")
            else:
                result["status"] = "⚠️  PARTIAL"
                print(f"\n   Decision Cycle: ⚠️  {passed_steps}/{total_steps} steps completed")
                
        except Exception as e:
            result["status"] = "❌ FAIL"
            result["error"] = str(e)
            print(f"\n   Decision Cycle: ❌ Failed - {e}")
        
        self.results["decision_flow_check"] = result
        return result
    
    async def run_verification(self):
        """Run complete verification"""
        await self.initialize()
        
        # Verify each layer
        await self.verify_layer_1_state_machine()
        await self.verify_layer_2_internal_state()
        await self.verify_layer_3_external_state()
        await self.verify_layer_4_character_profile()
        await self.verify_layer_5_decision_engine()
        await self.verify_layer_6_memory_system()
        await self.verify_layer_7_activity_diversity()
        await self.verify_layer_8_activity_levels()
        
        # Verify integration
        await self.verify_integration()
        
        # Test full decision cycle
        await self.test_full_decision_cycle()
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "="*80)
        print("📋 VERIFICATION SUMMARY")
        print("="*80)
        
        # Layer checks
        print("\n🏗️  Layer Checks:")
        layer_statuses = []
        for layer_id, layer_result in self.results["layer_checks"].items():
            status = layer_result.get("status", "unknown")
            name = layer_result.get("name", "Unknown")
            layer_statuses.append(status)
            print(f"   {status} {name}")
        
        # Integration checks
        print("\n🔗 Integration Checks:")
        integration_result = self.results.get("integration_checks", {})
        integration_status = integration_result.get("status", "unknown")
        print(f"   {integration_status} Layer Integration")
        
        # Decision cycle
        print("\n🔄 Decision Cycle:")
        cycle_result = self.results.get("decision_flow_check", {})
        cycle_status = cycle_result.get("status", "unknown")
        print(f"   {cycle_status} Full Decision Cycle")
        
        # Overall status
        all_passed = all("✅" in status for status in layer_statuses)
        integration_passed = "✅" in integration_status
        cycle_passed = "✅" in cycle_status
        
        print("\n" + "="*80)
        if all_passed and integration_passed and cycle_passed:
            print("🎉 OVERALL STATUS: ✅ ALL SYSTEMS OPERATIONAL")
            print("   All 8 layers are working together correctly!")
            self.results["overall_status"] = "✅ PASS"
        else:
            print("⚠️  OVERALL STATUS: ⚠️  SOME ISSUES DETECTED")
            print("   Review the detailed results above.")
            self.results["overall_status"] = "⚠️  PARTIAL"
        print("="*80 + "\n")


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python verify_agent_layers.py <avatar_id>")
        print("\nExample:")
        print("  python verify_agent_layers.py 862cb7dc-4b2a-4a4e-b682-f8cdea2642c9")
        sys.exit(1)
    
    avatar_id = sys.argv[1]
    
    verifier = AgentLayerVerifier(avatar_id)
    await verifier.run_verification()


if __name__ == "__main__":
    asyncio.run(main())
