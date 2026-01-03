"""
Mission Service
Handles mission CRUD and execution
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.mission import Mission, MissionCriteria, MissionStrategy
from ..models.enums import MissionType, MissionStatus, MissionPhase
from ..mcp.tools import WorkflowMCPServer
from ..agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)


class MissionService:
    """
    Handles mission operations.
    
    Features:
    - Create missions
    - Start/pause/cancel missions
    - Get mission status and results
    - List user missions
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        mcp_server: WorkflowMCPServer,
        openai_client=None
    ):
        self.db = db
        self.mcp_server = mcp_server
        self.openai_client = openai_client
        self._running_missions: Dict[str, asyncio.Task] = {}
    
    async def create_mission(
        self,
        user_id: str,
        avatar_id: str,
        mission_type: MissionType,
        name: str,
        criteria: Dict[str, Any] = None,
        strategy: Dict[str, Any] = None,
        description: str = "",
        source_chat_id: str = None,
        auto_start: bool = True
    ) -> Mission:
        """Create a new mission"""
        
        # Build criteria and strategy
        mission_criteria = MissionCriteria(**(criteria or {}))
        mission_strategy = MissionStrategy(**(strategy or {}))
        
        # Create mission
        mission = Mission(
            user_id=user_id,
            avatar_id=avatar_id,
            type=mission_type,
            name=name,
            description=description,
            criteria=mission_criteria,
            strategy=mission_strategy,
            source_chat_id=source_chat_id
        )
        
        # Save to database
        await self.db.missions.insert_one(mission.to_dict())
        
        logger.info(f"📋 Created mission: {mission.id} ({mission.type})")
        
        # Auto-start if requested - run synchronously
        if auto_start:
            # Don't await here - let the caller decide
            # The mission will be started via the start endpoint
            logger.info(f"📋 Mission created, auto_start=True but deferring start")
        
        return mission
    
    async def start_mission(self, mission_id: str) -> Dict[str, Any]:
        """Start executing a mission"""
        
        mission_doc = await self.db.missions.find_one({"id": mission_id})
        if not mission_doc:
            return {"success": False, "error": "Mission not found"}
        
        if mission_doc.get("status") == MissionStatus.RUNNING.value:
            return {"success": False, "error": "Mission already running"}
        
        # Update status to running
        now = datetime.now(timezone.utc)
        await self.db.missions.update_one(
            {"id": mission_id},
            {
                "$set": {
                    "status": MissionStatus.RUNNING.value,
                    "timeline.started_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }
            }
        )
        
        # Create orchestrator
        orchestrator = OrchestratorAgent(
            db=self.db,
            mcp_server=self.mcp_server,
            openai_client=self.openai_client
        )
        
        # Execute mission synchronously with timeout
        # Lambda has limited execution time, so we run a limited number of steps
        try:
            result = await asyncio.wait_for(
                orchestrator.execute(mission_id, mission_doc["avatar_id"]),
                timeout=240.0  # 4 minute timeout (Lambda max is 5 min for workflows)
            )
            logger.info(f"✅ Mission completed: {mission_id}")
            return {"success": True, "mission_id": mission_id, "result": result}
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Mission timed out: {mission_id} - will continue on next trigger")
            # Update status to indicate partial progress
            await self.db.missions.update_one(
                {"id": mission_id},
                {
                    "$set": {
                        "progress.current_action": "Paused - will continue on next trigger",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            return {"success": True, "mission_id": mission_id, "status": "timeout", "message": "Mission in progress, will continue"}
        except Exception as e:
            logger.error(f"❌ Mission failed: {mission_id} - {e}")
            await self.db.missions.update_one(
                {"id": mission_id},
                {
                    "$set": {
                        "status": MissionStatus.FAILED.value,
                        "progress.current_action": f"Failed: {str(e)}",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            return {"success": False, "mission_id": mission_id, "error": str(e)}
    
    async def pause_mission(self, mission_id: str) -> Dict[str, Any]:
        """Pause a running mission"""
        
        # Cancel running task if exists
        task = self._running_missions.get(mission_id)
        if task:
            task.cancel()
            del self._running_missions[mission_id]
        
        # Update status
        now = datetime.now(timezone.utc)
        await self.db.missions.update_one(
            {"id": mission_id},
            {
                "$set": {
                    "status": MissionStatus.PAUSED.value,
                    "timeline.paused_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }
            }
        )
        
        logger.info(f"⏸️ Paused mission: {mission_id}")
        return {"success": True}
    
    async def resume_mission(self, mission_id: str) -> Dict[str, Any]:
        """Resume a paused mission"""
        
        mission_doc = await self.db.missions.find_one({"id": mission_id})
        if not mission_doc:
            return {"success": False, "error": "Mission not found"}
        
        if mission_doc.get("status") != MissionStatus.PAUSED.value:
            return {"success": False, "error": "Mission not paused"}
        
        return await self.start_mission(mission_id)
    
    async def cancel_mission(self, mission_id: str) -> Dict[str, Any]:
        """Cancel a mission"""
        
        # Cancel running task if exists
        task = self._running_missions.get(mission_id)
        if task:
            task.cancel()
            del self._running_missions[mission_id]
        
        # Update status
        now = datetime.now(timezone.utc)
        await self.db.missions.update_one(
            {"id": mission_id},
            {
                "$set": {
                    "status": MissionStatus.CANCELLED.value,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        logger.info(f"🚫 Cancelled mission: {mission_id}")
        return {"success": True}
    
    async def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get mission by ID"""
        mission_doc = await self.db.missions.find_one({"id": mission_id})
        return self._serialize_document(mission_doc) if mission_doc else None
    
    async def get_mission_status(self, mission_id: str) -> Dict[str, Any]:
        """Get detailed mission status"""
        
        mission = await self.get_mission(mission_id)
        if not mission:
            return {"success": False, "error": "Mission not found"}
        
        # Get lead count
        lead_count = await self.db.mission_leads.count_documents({"mission_id": mission_id})
        
        # Get activity count
        activity_count = await self.db.mission_activities.count_documents({"mission_id": mission_id})
        
        return {
            "success": True,
            "mission_id": mission_id,
            "status": mission.get("status"),
            "phase": mission.get("phase"),
            "progress": mission.get("progress", {}),
            "results_summary": mission.get("results_summary"),
            "lead_count": lead_count,
            "activity_count": activity_count,
            "timeline": mission.get("timeline", {})
        }
    
    async def list_missions(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """List missions for a user"""
        
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        missions = await self.db.missions.find(query) \
            .sort("created_at", -1) \
            .skip(skip) \
            .limit(limit) \
            .to_list(limit)
        
        # Enrich with lead counts and serialize
        result = []
        for mission in missions:
            mission["lead_count"] = await self.db.mission_leads.count_documents({
                "mission_id": mission["id"]
            })
            # Convert ObjectId and datetime for JSON serialization
            result.append(self._serialize_document(mission))
        
        return result
    
    def _serialize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document to JSON-serializable dict"""
        if doc is None:
            return None
        
        result = {}
        for key, value in doc.items():
            if key == "_id":
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._serialize_document(value)
            elif isinstance(value, list):
                result[key] = [
                    self._serialize_document(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    async def get_mission_activities(
        self,
        mission_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activities for a mission"""
        
        activities = await self.db.mission_activities.find({
            "mission_id": mission_id
        }).sort("started_at", -1).limit(limit).to_list(limit)
        
        return [self._serialize_document(a) for a in activities]
    
    async def update_mission_criteria(
        self,
        mission_id: str,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update mission criteria (only if not running)"""
        
        mission = await self.get_mission(mission_id)
        if not mission:
            return {"success": False, "error": "Mission not found"}
        
        if mission.get("status") == MissionStatus.RUNNING.value:
            return {"success": False, "error": "Cannot update running mission"}
        
        await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": {"criteria": criteria, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True}
    
    async def update_mission_strategy(
        self,
        mission_id: str,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update mission strategy (only if not running)"""
        
        mission = await self.get_mission(mission_id)
        if not mission:
            return {"success": False, "error": "Mission not found"}
        
        if mission.get("status") == MissionStatus.RUNNING.value:
            return {"success": False, "error": "Cannot update running mission"}
        
        await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": {"strategy": strategy, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True}

