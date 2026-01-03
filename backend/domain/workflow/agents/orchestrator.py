"""
Orchestrator Agent
Coordinates multi-agent workflow execution
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .base_agent import BaseAgent
from ..models.mission import Mission
from ..models.enums import MissionPhase, MissionStatus, MissionType

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrates multi-agent workflow execution.
    
    Responsibilities:
    - Plan workflow steps based on mission type
    - Execute phases sequentially
    - Track progress and state
    - Handle errors and retries
    - Make decisions based on results
    """
    
    agent_type = "orchestrator"
    
    async def execute(self, mission_id: str, avatar_id: str, **kwargs) -> Dict[str, Any]:
        """Execute a full mission"""
        
        logger.info(f"🎯 Orchestrator starting mission: {mission_id}")
        
        try:
            # Get mission
            mission_doc = await self.db.missions.find_one({"id": mission_id})
            if not mission_doc:
                return {"success": False, "error": "Mission not found"}
            
            mission = Mission.from_dict(mission_doc)
            
            # Update status to running
            await self._update_mission_status(mission_id, MissionStatus.RUNNING)
            await self._update_phase(mission_id, MissionPhase.INITIALIZING)
            
            # Get execution plan
            plan = await self._create_execution_plan(mission)
            
            # Execute phases
            for phase_config in plan["phases"]:
                # Check if mission is still active
                current_mission = await self.db.missions.find_one({"id": mission_id})
                if current_mission.get("status") in ["cancelled", "paused"]:
                    logger.info(f"Mission {mission_id} is {current_mission.get('status')}, stopping")
                    break
                
                # Update phase
                phase_name = phase_config["name"]
                await self._update_phase(mission_id, phase_name)
                
                # Execute phase
                phase_result = await self._execute_phase(mission, phase_config)
                
                if not phase_result.get("continue", True):
                    logger.info(f"Phase {phase_name} indicated to stop")
                    break
                
                # Store phase results
                await self._save_phase_results(mission_id, phase_name, phase_result)
            
            # Complete mission
            await self._complete_mission(mission_id)
            
            return {"success": True, "mission_id": mission_id}
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            await self._fail_mission(mission_id, str(e))
            return {"success": False, "error": str(e)}
    
    async def _create_execution_plan(self, mission: Mission) -> Dict[str, Any]:
        """Create execution plan based on mission type"""
        
        # Default plans for each mission type
        plans = {
            MissionType.MATCHMAKING: {
                "phases": [
                    {
                        "name": MissionPhase.DISCOVERING,
                        "tools": ["search_profiles"],
                        "max_iterations": 1
                    },
                    {
                        "name": MissionPhase.EVALUATING,
                        "tools": ["score_compatibility", "get_shared_interests"],
                        "max_iterations": 50
                    },
                    {
                        "name": MissionPhase.ENGAGING,
                        "tools": ["start_conversation"],
                        "max_iterations": 10
                    },
                    {
                        "name": MissionPhase.ANALYZING,
                        "tools": ["create_lead", "generate_summary"],
                        "max_iterations": 1
                    }
                ]
            },
            MissionType.NETWORKING: {
                "phases": [
                    {
                        "name": MissionPhase.DISCOVERING,
                        "tools": ["search_profiles"],
                        "max_iterations": 1
                    },
                    {
                        "name": MissionPhase.EVALUATING,
                        "tools": ["score_compatibility", "analyze_profile"],
                        "max_iterations": 30
                    },
                    {
                        "name": MissionPhase.ANALYZING,
                        "tools": ["create_lead", "generate_summary"],
                        "max_iterations": 1
                    }
                ]
            },
            MissionType.SALES_LEADS: {
                "phases": [
                    {
                        "name": MissionPhase.DISCOVERING,
                        "tools": ["search_profiles", "filter_by_criteria"],
                        "max_iterations": 1
                    },
                    {
                        "name": MissionPhase.EVALUATING,
                        "tools": ["analyze_profile", "score_compatibility"],
                        "max_iterations": 100
                    },
                    {
                        "name": MissionPhase.ANALYZING,
                        "tools": ["create_lead", "generate_summary"],
                        "max_iterations": 1
                    }
                ]
            }
        }
        
        # Get plan for mission type, or default to matchmaking
        plan = plans.get(mission.type, plans[MissionType.MATCHMAKING])
        
        # Use LLM to enhance plan if available
        if self.openai_client and mission.strategy.custom_instructions:
            enhanced_plan = await self._enhance_plan_with_llm(mission, plan)
            if enhanced_plan:
                plan = enhanced_plan
        
        return plan
    
    async def _enhance_plan_with_llm(self, mission: Mission, base_plan: Dict) -> Optional[Dict]:
        """Use LLM to enhance execution plan based on custom instructions"""
        try:
            prompt = f"""Given this mission configuration and base plan, suggest any modifications.

Mission:
- Type: {mission.type}
- Name: {mission.name}
- Criteria: {mission.criteria.dict()}
- Strategy: {mission.strategy.dict()}
- Custom Instructions: {mission.strategy.custom_instructions}

Base Plan:
{json.dumps(base_plan, default=str)}

Available tools: search_profiles, filter_by_criteria, score_compatibility, analyze_profile, 
get_shared_interests, start_conversation, send_mission_message, check_response,
analyze_conversation, create_lead, generate_summary

Return the plan as JSON. Only modify if the custom instructions require changes.
If no changes needed, return the base plan as-is."""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"Failed to enhance plan with LLM: {e}")
            return None
    
    async def _execute_phase(self, mission: Mission, phase_config: Dict) -> Dict[str, Any]:
        """Execute a single phase"""
        
        phase_name = phase_config["name"]
        tools = phase_config.get("tools", [])
        max_iterations = phase_config.get("max_iterations", 10)
        
        logger.info(f"📍 Executing phase: {phase_name}")
        
        results = []
        state = await self._get_mission_state(mission.id)
        
        for iteration in range(max_iterations):
            for tool_name in tools:
                # Build parameters based on phase and state
                params = await self._build_tool_params(
                    mission, phase_name, tool_name, state, iteration
                )
                
                if params is None:
                    # Skip this tool for this iteration
                    continue
                
                # Execute tool
                result = await self.call_tool(tool_name, mission.avatar_id, **params)
                
                results.append({
                    "tool": tool_name,
                    "iteration": iteration,
                    "result": result
                })
                
                # Update state based on result
                state = await self._update_state_from_result(
                    mission.id, phase_name, tool_name, result, state
                )
                
                # Update progress
                await self._update_progress(mission.id, phase_name, results)
                
                # Log activity
                await self.log_activity(
                    mission.id, tool_name, result,
                    target_user_id=params.get("target_user_id")
                )
                
                # Small delay between tools
                await asyncio.sleep(0.2)
            
            # Check if phase is complete
            if await self._is_phase_complete(phase_name, state, results):
                break
        
        return {
            "phase": phase_name,
            "results": results,
            "iterations": iteration + 1,
            "continue": True
        }
    
    async def _build_tool_params(
        self,
        mission: Mission,
        phase: str,
        tool: str,
        state: Dict,
        iteration: int
    ) -> Optional[Dict]:
        """Build parameters for a tool call based on current state"""
        
        params = {"mission_id": mission.id}
        
        if phase == MissionPhase.DISCOVERING:
            if tool == "search_profiles":
                params.update({
                    "interests": mission.criteria.interests,
                    "traits": mission.criteria.traits,
                    "exclude_friends": mission.criteria.exclude_existing_friends,
                    "limit": mission.strategy.max_targets
                })
            elif tool == "filter_by_criteria":
                discovered = state.get("discovered_profiles", [])
                if not discovered:
                    return None
                params.update({
                    "profile_ids": [p.get("user_id") for p in discovered],
                    "required_interests": mission.criteria.interests[:3] if mission.criteria.interests else []
                })
        
        elif phase == MissionPhase.EVALUATING:
            qualified = state.get("qualified_profiles", [])
            discovered = state.get("discovered_profiles", [])
            
            # Get next profile to evaluate
            evaluated_ids = {p.get("user_id") for p in qualified}
            to_evaluate = [
                p for p in discovered 
                if p.get("user_id") not in evaluated_ids
            ]
            
            if not to_evaluate:
                return None
            
            target = to_evaluate[0]
            params["target_user_id"] = target.get("user_id")
        
        elif phase == MissionPhase.ENGAGING:
            qualified = state.get("qualified_profiles", [])
            conversations = state.get("conversations_started", [])
            
            # Get next qualified profile to engage
            engaged_ids = set(conversations)
            to_engage = [
                p for p in qualified 
                if p.get("user_id") not in engaged_ids
            ]
            
            if not to_engage or len(conversations) >= mission.strategy.max_conversations:
                return None
            
            target = to_engage[0]
            params.update({
                "target_user_id": target.get("user_id"),
                "mission_type": mission.type,
                "talking_points": mission.strategy.talking_points
            })
        
        elif phase == MissionPhase.ANALYZING:
            if tool == "create_lead":
                qualified = state.get("qualified_profiles", [])
                leads_created = state.get("leads_created", [])
                
                to_lead = [
                    p for p in qualified
                    if p.get("user_id") not in leads_created
                ]
                
                if not to_lead:
                    return None
                
                target = to_lead[0]
                params.update({
                    "target_user_id": target.get("user_id"),
                    "score": target.get("score", 50),
                    "score_breakdown": target.get("breakdown", {}),
                    "conversation_id": state.get("conversations", {}).get(target.get("user_id"))
                })
            elif tool == "generate_summary":
                # Only run once
                if iteration > 0:
                    return None
        
        return params
    
    async def _update_state_from_result(
        self,
        mission_id: str,
        phase: str,
        tool: str,
        result: Dict,
        current_state: Dict
    ) -> Dict:
        """Update mission state based on tool result"""
        
        if not result.get("success"):
            return current_state
        
        if tool == "search_profiles":
            profiles = result.get("profiles", [])
            current_state["discovered_profiles"] = profiles
            
        elif tool == "score_compatibility":
            target_id = result.get("target_user_id")
            score = result.get("total_score", 0)
            
            if score >= 60:  # Minimum qualifying score
                qualified = current_state.get("qualified_profiles", [])
                qualified.append({
                    "user_id": target_id,
                    "score": score,
                    "breakdown": result.get("breakdown", {})
                })
                # Sort by score
                qualified.sort(key=lambda x: x.get("score", 0), reverse=True)
                current_state["qualified_profiles"] = qualified
        
        elif tool == "start_conversation":
            target_id = result.get("target_user_id")
            conv_id = result.get("conversation_id")
            
            conversations = current_state.get("conversations_started", [])
            conversations.append(target_id)
            current_state["conversations_started"] = conversations
            
            convs = current_state.get("conversations", {})
            convs[target_id] = conv_id
            current_state["conversations"] = convs
        
        elif tool == "create_lead":
            lead_id = result.get("lead_id")
            target_id = result.get("lead", {}).get("target_user_id")
            
            leads = current_state.get("leads_created", [])
            leads.append(target_id)
            current_state["leads_created"] = leads
        
        # Save state
        await self.call_tool("save_mission_state", "", mission_id=mission_id, state=current_state)
        
        return current_state
    
    async def _is_phase_complete(self, phase: str, state: Dict, results: List) -> bool:
        """Check if phase is complete"""
        
        if phase == MissionPhase.DISCOVERING:
            discovered = state.get("discovered_profiles", [])
            return len(discovered) > 0
        
        elif phase == MissionPhase.EVALUATING:
            discovered = state.get("discovered_profiles", [])
            qualified = state.get("qualified_profiles", [])
            # Complete when all discovered profiles have been evaluated
            return len(qualified) >= len(discovered) or len(qualified) >= 20
        
        elif phase == MissionPhase.ENGAGING:
            conversations = state.get("conversations_started", [])
            return len(conversations) >= 5  # Cap at 5 for now
        
        elif phase == MissionPhase.ANALYZING:
            # Complete after summary is generated
            for r in results:
                if r.get("tool") == "generate_summary" and r.get("result", {}).get("success"):
                    return True
            return False
        
        return False
    
    async def _get_mission_state(self, mission_id: str) -> Dict:
        """Get current mission state"""
        result = await self.call_tool("get_mission_state", "", mission_id=mission_id)
        return result.get("state", {})
    
    async def _save_phase_results(self, mission_id: str, phase: str, result: Dict):
        """Save phase results to state"""
        state = await self._get_mission_state(mission_id)
        
        phase_results = state.get("phase_results", {})
        phase_results[phase] = {
            "iterations": result.get("iterations"),
            "result_count": len(result.get("results", []))
        }
        state["phase_results"] = phase_results
        
        await self.call_tool("save_mission_state", "", mission_id=mission_id, state=state)
    
    async def _update_mission_status(self, mission_id: str, status: MissionStatus):
        """Update mission status"""
        now = datetime.now(timezone.utc)
        update = {"status": status.value, "updated_at": now.isoformat()}
        
        if status == MissionStatus.RUNNING:
            update["timeline.started_at"] = now.isoformat()
        elif status == MissionStatus.COMPLETED:
            update["timeline.completed_at"] = now.isoformat()
        
        await self.db.missions.update_one({"id": mission_id}, {"$set": update})
    
    async def _update_phase(self, mission_id: str, phase: str):
        """Update current phase"""
        phase_value = phase.value if hasattr(phase, 'value') else phase
        await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": {"phase": phase_value, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    async def _update_progress(self, mission_id: str, phase: str, results: List):
        """Update mission progress"""
        # Calculate stats
        stats = {}
        for r in results:
            tool = r.get("tool")
            result = r.get("result", {})
            
            if tool == "search_profiles" and result.get("success"):
                stats["profiles_discovered"] = result.get("total_found", 0)
            elif tool == "score_compatibility" and result.get("success"):
                stats["profiles_evaluated"] = stats.get("profiles_evaluated", 0) + 1
            elif tool == "start_conversation" and result.get("success"):
                stats["conversations_started"] = stats.get("conversations_started", 0) + 1
            elif tool == "create_lead" and result.get("success"):
                stats["leads_generated"] = stats.get("leads_generated", 0) + 1
        
        # Calculate percentage
        phase_weights = {
            MissionPhase.INITIALIZING: 0.05,
            MissionPhase.DISCOVERING: 0.20,
            MissionPhase.EVALUATING: 0.35,
            MissionPhase.ENGAGING: 0.25,
            MissionPhase.ANALYZING: 0.15
        }
        
        phase_value = phase.value if hasattr(phase, 'value') else phase
        completed_weight = sum(
            w for p, w in phase_weights.items() 
            if p.value < phase_value
        ) if hasattr(phase, 'value') else 0.5
        
        percentage = int(completed_weight * 100 + phase_weights.get(phase, 0.1) * 50)
        
        await self.call_tool(
            "update_mission_progress", "",
            mission_id=mission_id,
            phase=phase_value,
            percentage=min(percentage, 95),  # Cap at 95 until complete
            stats=stats
        )
    
    async def _complete_mission(self, mission_id: str):
        """Complete mission successfully"""
        await self._update_mission_status(mission_id, MissionStatus.COMPLETED)
        await self.call_tool(
            "update_mission_progress", "",
            mission_id=mission_id,
            percentage=100,
            current_action="Mission completed!"
        )
        logger.info(f"✅ Mission {mission_id} completed successfully")
    
    async def _fail_mission(self, mission_id: str, error: str):
        """Mark mission as failed"""
        await self.db.missions.update_one(
            {"id": mission_id},
            {
                "$set": {
                    "status": MissionStatus.FAILED.value,
                    "error": error,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        logger.error(f"❌ Mission {mission_id} failed: {error}")

