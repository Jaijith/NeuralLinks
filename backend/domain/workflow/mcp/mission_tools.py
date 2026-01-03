"""
Mission MCP Tools
Tools for managing mission state and progress
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class GetMissionStateTool(WorkflowBaseTool):
    """Get current mission execution state"""
    
    name = "get_mission_state"
    description = "Get the current execution state of a mission"
    
    schema = {
        "type": "object",
        "properties": {
            "mission_id": {
                "type": "string",
                "description": "Mission ID to get state for"
            }
        },
        "required": ["mission_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        mission_id = kwargs.get("mission_id")
        
        # Get mission
        mission = await self.db.missions.find_one({"id": mission_id})
        if not mission:
            return {"success": False, "error": "Mission not found"}
        
        # Get state document
        state_doc = await self.db.mission_state.find_one({"mission_id": mission_id})
        state = state_doc.get("state", {}) if state_doc else {}
        
        return {
            "success": True,
            "mission_id": mission_id,
            "status": mission.get("status"),
            "phase": mission.get("phase"),
            "progress": mission.get("progress", {}),
            "state": state
        }


class UpdateMissionProgressTool(WorkflowBaseTool):
    """Update mission progress"""
    
    name = "update_mission_progress"
    description = "Update the progress and stats of a mission"
    
    schema = {
        "type": "object",
        "properties": {
            "mission_id": {
                "type": "string",
                "description": "Mission ID to update"
            },
            "phase": {
                "type": "string",
                "description": "Current phase"
            },
            "percentage": {
                "type": "integer",
                "description": "Progress percentage 0-100"
            },
            "current_action": {
                "type": "string",
                "description": "Description of current action"
            },
            "stats": {
                "type": "object",
                "description": "Progress stats to merge"
            }
        },
        "required": ["mission_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        mission_id = kwargs.get("mission_id")
        phase = kwargs.get("phase")
        percentage = kwargs.get("percentage")
        current_action = kwargs.get("current_action")
        stats = kwargs.get("stats", {})
        
        now = datetime.now(timezone.utc)
        
        # Build update
        update = {
            "updated_at": now.isoformat(),
            "timeline.last_activity_at": now.isoformat()
        }
        
        if phase:
            update["phase"] = phase
        if percentage is not None:
            update["progress.percentage"] = percentage
        if current_action:
            update["progress.current_action"] = current_action
        
        # Merge stats
        for key, value in stats.items():
            update[f"progress.stats.{key}"] = value
        
        result = await self.db.missions.update_one(
            {"id": mission_id},
            {"$set": update}
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Mission not found or not modified"}
        
        return {
            "success": True,
            "mission_id": mission_id,
            "updated_fields": list(update.keys())
        }


class SaveMissionStateTool(WorkflowBaseTool):
    """Save mission execution state"""
    
    name = "save_mission_state"
    description = "Save the execution state of a mission"
    
    schema = {
        "type": "object",
        "properties": {
            "mission_id": {
                "type": "string",
                "description": "Mission ID"
            },
            "state": {
                "type": "object",
                "description": "State object to save"
            },
            "merge": {
                "type": "boolean",
                "default": True,
                "description": "Merge with existing state or replace"
            }
        },
        "required": ["mission_id", "state"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        mission_id = kwargs.get("mission_id")
        new_state = kwargs.get("state", {})
        merge = kwargs.get("merge", True)
        
        now = datetime.now(timezone.utc)
        
        if merge:
            # Get existing state
            state_doc = await self.db.mission_state.find_one({"mission_id": mission_id})
            existing_state = state_doc.get("state", {}) if state_doc else {}
            
            # Deep merge
            merged_state = {**existing_state, **new_state}
            
            # For arrays, extend rather than replace
            for key in new_state:
                if isinstance(new_state[key], list) and isinstance(existing_state.get(key), list):
                    # Deduplicate if items are dicts with 'user_id'
                    if new_state[key] and isinstance(new_state[key][0], dict):
                        existing_ids = {item.get("user_id") for item in existing_state.get(key, []) if isinstance(item, dict)}
                        merged_state[key] = existing_state.get(key, []) + [
                            item for item in new_state[key] 
                            if isinstance(item, dict) and item.get("user_id") not in existing_ids
                        ]
                    else:
                        merged_state[key] = list(set(existing_state.get(key, []) + new_state[key]))
            
            new_state = merged_state
        
        # Upsert state
        await self.db.mission_state.update_one(
            {"mission_id": mission_id},
            {
                "$set": {
                    "state": new_state,
                    "updated_at": now.isoformat()
                },
                "$setOnInsert": {
                    "mission_id": mission_id,
                    "created_at": now.isoformat()
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "mission_id": mission_id,
            "state_keys": list(new_state.keys())
        }

