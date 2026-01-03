"""
Lead Service
Handles lead management and user follow-up
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.lead import Lead
from ..models.enums import LeadStatus, LeadPriority

logger = logging.getLogger(__name__)


class LeadService:
    """
    Handles lead operations.
    
    Features:
    - Get leads for missions/users
    - Update lead status
    - User feedback on leads
    - Lead analytics
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
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
    
    async def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get lead by ID"""
        doc = await self.db.mission_leads.find_one({"id": lead_id})
        return self._serialize_document(doc) if doc else None
    
    async def get_leads_for_mission(
        self,
        mission_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get leads for a specific mission"""
        
        query = {"mission_id": mission_id}
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        
        leads = await self.db.mission_leads.find(query) \
            .sort([("priority_order", 1), ("score", -1)]) \
            .skip(skip) \
            .limit(limit) \
            .to_list(limit)
        
        return [self._serialize_document(lead) for lead in leads]
    
    async def get_leads_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all leads for a user across missions"""
        
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        leads = await self.db.mission_leads.find(query) \
            .sort([("created_at", -1)]) \
            .skip(skip) \
            .limit(limit) \
            .to_list(limit)
        
        return [self._serialize_document(lead) for lead in leads]
    
    async def update_lead_status(
        self,
        lead_id: str,
        status: LeadStatus
    ) -> Dict[str, Any]:
        """Update lead status"""
        
        now = datetime.now(timezone.utc)
        result = await self.db.mission_leads.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "status": status.value,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True, "lead_id": lead_id, "new_status": status.value}
    
    async def add_user_notes(
        self,
        lead_id: str,
        notes: str
    ) -> Dict[str, Any]:
        """Add or update user notes on a lead"""
        
        now = datetime.now(timezone.utc)
        result = await self.db.mission_leads.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "user_notes": notes,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True}
    
    async def rate_lead(
        self,
        lead_id: str,
        rating: int
    ) -> Dict[str, Any]:
        """Rate a lead (1-5)"""
        
        if rating < 1 or rating > 5:
            return {"success": False, "error": "Rating must be between 1 and 5"}
        
        now = datetime.now(timezone.utc)
        result = await self.db.mission_leads.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "user_rating": rating,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True}
    
    async def mark_followed_up(
        self,
        lead_id: str
    ) -> Dict[str, Any]:
        """Mark a lead as followed up"""
        
        now = datetime.now(timezone.utc)
        result = await self.db.mission_leads.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "followed_up": True,
                    "followed_up_at": now.isoformat(),
                    "status": LeadStatus.CONVERTED.value,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True}
    
    async def dismiss_lead(
        self,
        lead_id: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Dismiss a lead"""
        
        now = datetime.now(timezone.utc)
        result = await self.db.mission_leads.update_one(
            {"id": lead_id},
            {
                "$set": {
                    "status": LeadStatus.DISMISSED.value,
                    "dismiss_reason": reason,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True}
    
    async def get_lead_stats(self, user_id: str) -> Dict[str, Any]:
        """Get lead statistics for a user"""
        
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "avg_score": {"$avg": "$score"},
                "high_priority": {"$sum": {"$cond": [{"$eq": ["$priority", "high"]}, 1, 0]}},
                "followed_up": {"$sum": {"$cond": ["$followed_up", 1, 0]}},
                "dismissed": {"$sum": {"$cond": [{"$eq": ["$status", "dismissed"]}, 1, 0]}}
            }}
        ]
        
        results = await self.db.mission_leads.aggregate(pipeline).to_list(1)
        
        if not results:
            return {
                "total": 0,
                "avg_score": 0,
                "high_priority": 0,
                "followed_up": 0,
                "dismissed": 0,
                "conversion_rate": 0
            }
        
        stats = results[0]
        del stats["_id"]
        stats["avg_score"] = round(stats.get("avg_score", 0), 1)
        stats["conversion_rate"] = round(
            stats["followed_up"] / stats["total"] * 100 if stats["total"] > 0 else 0, 1
        )
        
        return stats
    
    async def get_top_leads(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top leads by score that haven't been followed up"""
        
        leads = await self.db.mission_leads.find({
            "user_id": user_id,
            "followed_up": {"$ne": True},
            "status": {"$nin": [LeadStatus.DISMISSED.value, LeadStatus.STALE.value]}
        }).sort("score", -1).limit(limit).to_list(limit)
        
        return [self._serialize_document(lead) for lead in leads]

