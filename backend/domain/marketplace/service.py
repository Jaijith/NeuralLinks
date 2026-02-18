"""
Siddhi Bazaar - Marketplace Service
Core CRUD operations for browsing, searching, and managing skills.
"""

import logging
import math
from typing import Dict, List, Any, Optional
from domain.marketplace.models import SKILL_CATEGORIES, make_review_doc, now_iso, SkillType
from domain.marketplace.installer import SkillInstaller, InstallResult
from domain.marketplace.agent_subscription import AgentSubscriptionService

logger = logging.getLogger(__name__)


class SiddhiBazaarService:
    """Core marketplace service for browsing, installing, and managing skills."""

    def __init__(self, db, gateway=None):
        self.db = db
        self.gateway = gateway
        self.installer = SkillInstaller(db, gateway)
        self.agent_subscription = AgentSubscriptionService(db, gateway)

    async def search_skills(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tier: Optional[str] = None,
        skill_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Search and filter skills"""
        filters: Dict[str, Any] = {}

        if category:
            filters["category"] = category
        if tier:
            filters["tier"] = tier
        if skill_type:
            filters["type"] = skill_type
        if tags:
            filters["tags"] = {"$in": tags}
        if query:
            filters["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"tagline": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$regex": query, "$options": "i"}},
            ]

        total = await self.db.siddhi_skills.count_documents(filters)
        skip = (page - 1) * limit

        skills = await self.db.siddhi_skills.find(filters).sort(
            [("sort_order", 1), ("name", 1)]
        ).skip(skip).limit(limit).to_list(limit)

        for s in skills:
            s.pop("_id", None)

        return {
            "skills": skills,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if limit > 0 else 0,
        }

    async def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID"""
        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if skill:
            skill.pop("_id", None)
        return skill

    async def get_skill_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a skill by slug"""
        skill = await self.db.siddhi_skills.find_one({"slug": slug})
        if skill:
            skill.pop("_id", None)
        return skill

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with skill counts"""
        categories = []
        for cat_id, cat_info in SKILL_CATEGORIES.items():
            count = await self.db.siddhi_skills.count_documents({"category": cat_id})
            categories.append({
                "id": cat_id,
                "name": cat_info["name"],
                "icon": cat_info["icon"],
                "color": cat_info["color"],
                "description": cat_info["description"],
                "skill_count": count,
            })
        return categories

    async def get_featured_skills(self) -> List[Dict[str, Any]]:
        """Get featured skills"""
        skills = await self.db.siddhi_skills.find({"is_featured": True}).sort(
            "sort_order", 1
        ).to_list(20)
        for s in skills:
            s.pop("_id", None)
        return skills

    async def get_popular_skills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most installed skills"""
        skills = await self.db.siddhi_skills.find({}).sort(
            "stats.total_installs", -1
        ).limit(limit).to_list(limit)
        for s in skills:
            s.pop("_id", None)
        return skills

    async def install_skill(self, user_id: str, skill_id: str) -> InstallResult:
        """Install a skill for an avatar"""
        return await self.installer.install(user_id, skill_id)

    async def uninstall_skill(self, user_id: str, skill_id: str) -> bool:
        """Uninstall a skill"""
        return await self.installer.uninstall(user_id, skill_id)

    async def toggle_skill(self, user_id: str, skill_id: str, enabled: bool) -> bool:
        """Toggle a skill on/off"""
        return await self.installer.toggle_skill(user_id, skill_id, enabled)

    async def get_installed_skills(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all installed skills for an avatar with full skill details.
        Lazily migrates existing avatar_actions_enabled for users who have
        never accessed the marketplace before.
        """
        count = await self.db.siddhi_installations.count_documents({"user_id": user_id})
        if count == 0:
            await self.installer.sync_from_legacy(user_id)

        installations = await self.db.siddhi_installations.find({
            "user_id": user_id,
        }).to_list(None)

        result = []
        for inst in installations:
            inst.pop("_id", None)
            skill = await self.db.siddhi_skills.find_one({"id": inst["skill_id"]})
            if skill:
                skill.pop("_id", None)
                result.append({
                    "installation": inst,
                    "skill": skill,
                })

        return result

    async def rate_skill(self, user_id: str, skill_id: str, rating: int, review_text: str = "") -> Dict[str, Any]:
        """Submit a rating/review for a skill"""
        user = await self.db.users.find_one({"id": user_id})
        avatar_name = user.get("avatar_name", user.get("name", "Anonymous")) if user else "Anonymous"

        existing_review = await self.db.siddhi_reviews.find_one({
            "skill_id": skill_id,
            "user_id": user_id,
        })

        if existing_review:
            await self.db.siddhi_reviews.update_one(
                {"id": existing_review["id"]},
                {"$set": {"rating": rating, "review_text": review_text, "updated_at": now_iso()}}
            )
            review = existing_review
            review["rating"] = rating
            review["review_text"] = review_text
        else:
            review = make_review_doc(skill_id, user_id, avatar_name, rating, review_text)
            await self.db.siddhi_reviews.insert_one(review)

        await self.db.siddhi_installations.update_one(
            {"user_id": user_id, "skill_id": skill_id},
            {"$set": {"user_rating": rating}}
        )

        all_reviews = await self.db.siddhi_reviews.find({"skill_id": skill_id}).to_list(None)
        if all_reviews:
            avg_rating = sum(r["rating"] for r in all_reviews) / len(all_reviews)
            await self.db.siddhi_skills.update_one(
                {"id": skill_id},
                {"$set": {
                    "stats.avg_rating": round(avg_rating, 1),
                    "stats.total_ratings": len(all_reviews),
                }}
            )

        review.pop("_id", None)
        return review

    async def get_reviews(self, skill_id: str, page: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
        """Get reviews for a skill"""
        skip = (page - 1) * limit
        reviews = await self.db.siddhi_reviews.find({"skill_id": skill_id}).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(limit)

        for r in reviews:
            r.pop("_id", None)
        return reviews

    async def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get global marketplace statistics"""
        total_skills = await self.db.siddhi_skills.count_documents({})
        total_installations = await self.db.siddhi_installations.count_documents({})
        total_reviews = await self.db.siddhi_reviews.count_documents({})

        return {
            "total_skills": total_skills,
            "total_installations": total_installations,
            "total_reviews": total_reviews,
        }

    async def install_defaults_for_user(self, user_id: str) -> int:
        """Install default skills for a new user"""
        return await self.installer.install_defaults_for_user(user_id)

    # ── AI Agent Subscription ─────────────────────────────

    async def subscribe_agent(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """Subscribe to an AI Agent Assistant"""
        return await self.agent_subscription.subscribe(user_id, skill_id)

    async def unsubscribe_agent(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """Unsubscribe from an AI Agent Assistant"""
        return await self.agent_subscription.unsubscribe(user_id, skill_id)

    async def toggle_agent(self, user_id: str, skill_id: str, enabled: bool) -> Dict[str, Any]:
        """Toggle an agent on/off"""
        return await self.agent_subscription.toggle_agent(user_id, skill_id, enabled)

    async def get_subscribed_agents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all subscribed agents for a user"""
        return await self.agent_subscription.get_subscribed_agents(user_id)

    async def get_ai_agents(self) -> List[Dict[str, Any]]:
        """Get all available AI Agent skills"""
        agents = await self.db.siddhi_skills.find({
            "type": SkillType.AI_AGENT.value
        }).sort("sort_order", 1).to_list(None)

        result = []
        for agent_skill in agents:
            agent_skill.pop("_id", None)
            agent_user_id = agent_skill.get("binding", {}).get("agent_user_id")
            agent_user = None
            if agent_user_id:
                agent_user = await self.db.users.find_one(
                    {"id": agent_user_id},
                    {"_id": 0, "id": 1, "avatar_name": 1, "avatar_picture": 1,
                     "avatar_bio": 1, "agent_domain": 1, "agent_domain_label": 1,
                     "agent_expertise": 1, "is_ai_agent": 1}
                )
            result.append({
                "skill": agent_skill,
                "agent": agent_user,
            })

        return result
