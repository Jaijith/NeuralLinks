"""
Base Workflow Engine
Abstract base class for all workflow engines using LangGraph patterns
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class WorkflowPhase(str, Enum):
    """Standard workflow phases"""
    INITIALIZING = "initializing"
    DISCOVERING = "discovering"
    EVALUATING = "evaluating"
    ENGAGING = "engaging"
    ANALYZING = "analyzing"
    COMPLETING = "completing"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """
    Shared state object passed between workflow nodes.
    This follows LangGraph state management patterns.
    """
    mission_id: str
    avatar_id: str
    user_id: str
    mission_type: str
    phase: WorkflowPhase = WorkflowPhase.INITIALIZING
    
    # Configuration
    criteria: Dict[str, Any] = field(default_factory=dict)
    strategy: Dict[str, Any] = field(default_factory=dict)
    
    # Discovery results
    discovered_profiles: List[Dict[str, Any]] = field(default_factory=list)
    qualified_profiles: List[Dict[str, Any]] = field(default_factory=list)
    
    # Engagement state
    conversations: Dict[str, str] = field(default_factory=dict)  # target_id -> conv_id
    conversation_analyses: Dict[str, Dict] = field(default_factory=dict)
    
    # Results
    leads: List[Dict[str, Any]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    
    # Progress tracking
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Custom state for specific engines
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "avatar_id": self.avatar_id,
            "user_id": self.user_id,
            "mission_type": self.mission_type,
            "phase": self.phase.value,
            "criteria": self.criteria,
            "strategy": self.strategy,
            "discovered_profiles": self.discovered_profiles,
            "qualified_profiles": self.qualified_profiles,
            "conversations": self.conversations,
            "conversation_analyses": self.conversation_analyses,
            "leads": self.leads,
            "insights": self.insights,
            "actions_taken": self.actions_taken,
            "errors": self.errors,
            "custom": self.custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        phase_str = data.get("phase", "initializing")
        phase = WorkflowPhase(phase_str) if phase_str else WorkflowPhase.INITIALIZING
        
        return cls(
            mission_id=data.get("mission_id", ""),
            avatar_id=data.get("avatar_id", ""),
            user_id=data.get("user_id", ""),
            mission_type=data.get("mission_type", ""),
            phase=phase,
            criteria=data.get("criteria", {}),
            strategy=data.get("strategy", {}),
            discovered_profiles=data.get("discovered_profiles", []),
            qualified_profiles=data.get("qualified_profiles", []),
            conversations=data.get("conversations", {}),
            conversation_analyses=data.get("conversation_analyses", {}),
            leads=data.get("leads", []),
            insights=data.get("insights", []),
            actions_taken=data.get("actions_taken", []),
            errors=data.get("errors", []),
            custom=data.get("custom", {})
        )


@dataclass
class WorkflowNode:
    """Represents a node in the workflow graph"""
    name: str
    description: str
    tools: List[str] = field(default_factory=list)
    max_iterations: int = 1
    retry_on_failure: bool = True
    timeout_seconds: int = 60


class BaseWorkflowEngine(ABC):
    """
    Abstract base class for workflow engines.
    Implements LangGraph-style state machine patterns for agentic orchestration.
    """
    
    # Engine metadata - override in subclasses
    engine_name: str = "base_engine"
    engine_description: str = "Base workflow engine"
    supported_mission_types: List[str] = []
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        mcp_server: Any,
        openai_client: Any = None,
        intelligent_avatar: Any = None
    ):
        self.db = db
        self.mcp_server = mcp_server
        self.openai_client = openai_client
        self.intelligent_avatar = intelligent_avatar
        
        # Build the workflow graph
        self.workflow_graph = self._build_workflow_graph()
        
        logger.info(f"🔧 Initialized {self.engine_name} workflow engine")
    
    @abstractmethod
    def _build_workflow_graph(self) -> Dict[str, WorkflowNode]:
        """
        Build the workflow graph defining nodes and transitions.
        Returns a dict of node_name -> WorkflowNode
        """
        pass
    
    @abstractmethod
    def _get_node_order(self) -> List[str]:
        """Return the ordered list of node names for execution"""
        pass
    
    @abstractmethod
    async def _execute_node(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Execute a single workflow node"""
        pass
    
    async def execute(
        self,
        mission_id: str,
        avatar_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main entry point - execute the workflow
        """
        logger.info(f"🚀 {self.engine_name} starting mission: {mission_id}")
        
        try:
            # Load mission
            mission_doc = await self.db.missions.find_one({"id": mission_id})
            if not mission_doc:
                return {"success": False, "error": "Mission not found"}
            
            # Initialize state
            state = self._initialize_state(mission_doc, avatar_id)
            
            # Update mission status to running
            await self._update_mission_status(mission_id, "running")
            
            # Execute workflow graph
            state = await self._execute_workflow(state)
            
            # Complete mission
            if state.phase == WorkflowPhase.FAILED:
                await self._update_mission_status(mission_id, "failed")
                return {"success": False, "error": "; ".join(state.errors)}
            else:
                await self._complete_mission(mission_id, state)
                return {
                    "success": True,
                    "mission_id": mission_id,
                    "leads_count": len(state.leads),
                    "insights": state.insights
                }
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            await self._update_mission_status(mission_id, "failed")
            return {"success": False, "error": str(e)}
    
    def _initialize_state(
        self, 
        mission_doc: Dict[str, Any],
        avatar_id: str
    ) -> WorkflowState:
        """Initialize workflow state from mission document"""
        
        return WorkflowState(
            mission_id=mission_doc.get("id"),
            avatar_id=avatar_id,
            user_id=mission_doc.get("user_id"),
            mission_type=mission_doc.get("type"),
            criteria=mission_doc.get("criteria", {}),
            strategy=mission_doc.get("strategy", {}),
            phase=WorkflowPhase.INITIALIZING
        )
    
    async def _execute_workflow(self, state: WorkflowState) -> WorkflowState:
        """Execute the workflow graph sequentially"""
        
        node_order = self._get_node_order()
        
        for node_name in node_order:
            # Check if mission is cancelled
            mission = await self.db.missions.find_one({"id": state.mission_id})
            if mission and mission.get("status") in ["cancelled", "paused"]:
                logger.info(f"Mission {state.mission_id} is {mission.get('status')}, stopping")
                break
            
            node = self.workflow_graph.get(node_name)
            if not node:
                continue
            
            logger.info(f"📍 Executing node: {node_name}")
            
            try:
                # Update phase
                phase_map = {
                    "discover": WorkflowPhase.DISCOVERING,
                    "analyze_history": WorkflowPhase.DISCOVERING,
                    "evaluate": WorkflowPhase.EVALUATING,
                    "rank": WorkflowPhase.EVALUATING,
                    "engage": WorkflowPhase.ENGAGING,
                    "broadcast": WorkflowPhase.ENGAGING,
                    "analyze": WorkflowPhase.ANALYZING,
                    "generate_leads": WorkflowPhase.ANALYZING,
                    "complete": WorkflowPhase.COMPLETING
                }
                state.phase = phase_map.get(node_name, state.phase)
                await self._update_phase(state.mission_id, state.phase.value)
                
                # Execute node with retries
                for attempt in range(3 if node.retry_on_failure else 1):
                    try:
                        state = await asyncio.wait_for(
                            self._execute_node(node, state),
                            timeout=node.timeout_seconds
                        )
                        break
                    except asyncio.TimeoutError:
                        logger.warning(f"Node {node_name} timed out, attempt {attempt + 1}")
                        if attempt == 2:
                            state.errors.append(f"Node {node_name} timed out")
                    except Exception as e:
                        logger.error(f"Node {node_name} failed: {e}")
                        if attempt == 2 or not node.retry_on_failure:
                            state.errors.append(f"Node {node_name} failed: {str(e)}")
                
                # Update progress
                await self._update_progress(state)
                
                # Small delay between nodes
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Node {node_name} error: {e}", exc_info=True)
                state.errors.append(str(e))
                if not node.retry_on_failure:
                    state.phase = WorkflowPhase.FAILED
                    break
        
        return state
    
    async def call_tool(
        self, 
        tool_name: str, 
        avatar_id: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Call an MCP tool"""
        return await self.mcp_server.call_tool(tool_name, avatar_id, **kwargs)
    
    async def _update_mission_status(self, mission_id: str, status: str):
        """Update mission status in database"""
        now = datetime.now(timezone.utc)
        update = {"status": status, "updated_at": now.isoformat()}
        
        if status == "running":
            update["timeline.started_at"] = now.isoformat()
        elif status == "completed":
            update["timeline.completed_at"] = now.isoformat()
        
        await self.db.missions.update_one({"id": mission_id}, {"$set": update})
    
    async def _update_phase(self, mission_id: str, phase: str):
        """Update current mission phase"""
        await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": {
                "phase": phase, 
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    async def _update_progress(self, state: WorkflowState):
        """Update mission progress based on state"""
        
        # Calculate stats
        stats = {
            "profiles_discovered": len(state.discovered_profiles),
            "profiles_evaluated": len(state.qualified_profiles),
            "conversations_started": len(state.conversations),
            "leads_generated": len(state.leads)
        }
        
        # Calculate percentage based on phase
        phase_percentages = {
            WorkflowPhase.INITIALIZING: 5,
            WorkflowPhase.DISCOVERING: 25,
            WorkflowPhase.EVALUATING: 50,
            WorkflowPhase.ENGAGING: 75,
            WorkflowPhase.ANALYZING: 90,
            WorkflowPhase.COMPLETING: 100,
            WorkflowPhase.FAILED: 0
        }
        
        percentage = phase_percentages.get(state.phase, 50)
        
        await self.db.missions.update_one(
            {"id": state.mission_id},
            {"$set": {
                "progress.stats": stats,
                "progress.percentage": percentage,
                "progress.current_action": f"Phase: {state.phase.value}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    async def _complete_mission(self, mission_id: str, state: WorkflowState):
        """Complete mission successfully"""
        
        # Generate summary
        summary = await self._generate_summary(state)
        
        now = datetime.now(timezone.utc)
        await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": {
                "status": "completed",
                "phase": "completed",
                "progress.percentage": 100,
                "progress.current_action": "Mission completed!",
                "results_summary": summary,
                "timeline.completed_at": now.isoformat(),
                "updated_at": now.isoformat()
            }}
        )
        
        logger.info(f"✅ Mission {mission_id} completed successfully")
    
    async def _generate_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate mission summary"""
        
        total_leads = len(state.leads)
        avg_score = (
            sum(l.get("score", 0) for l in state.leads) / total_leads 
            if total_leads > 0 else 0
        )
        
        high_priority = len([l for l in state.leads if l.get("priority") == "high"])
        
        return {
            "total_leads": total_leads,
            "avg_match_score": round(avg_score, 1),
            "high_priority_leads": high_priority,
            "insights": state.insights,
            "profiles_analyzed": len(state.discovered_profiles),
            "profiles_qualified": len(state.qualified_profiles),
            "conversations_had": len(state.conversations)
        }
    
    async def _log_action(
        self, 
        state: WorkflowState,
        action_type: str, 
        details: Dict[str, Any]
    ):
        """Log a workflow action"""
        action = {
            "type": action_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details
        }
        state.actions_taken.append(action)
        
        # Log to mission_activities collection for frontend display
        user = await self.db.users.find_one({"id": state.avatar_id})
        activity = {
            "mission_id": state.mission_id,
            "avatar_id": state.avatar_id,
            "user_id": state.user_id,
            "type": action_type,
            "metadata": details,  # Use metadata field for details
            "started_at": action["timestamp"],
            "completed_at": action["timestamp"],
            "status": "completed"
        }
        await self.db.mission_activities.insert_one(activity)

