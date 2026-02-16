"""
Siddhi Bazaar - Skill Recommendations
Recommends skills based on avatar personality archetype and usage patterns.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ARCHETYPE_AFFINITY = {
    "the_creator": {"content_creation": 0.9, "discovery": 0.6, "intelligence": 0.5, "workflow_engines": 0.4},
    "the_sage": {"intelligence": 0.9, "analytics": 0.8, "discovery": 0.7, "workflow_engines": 0.5},
    "the_explorer": {"discovery": 0.9, "intelligence": 0.7, "workflow_engines": 0.6, "content_creation": 0.4},
    "the_rebel": {"content_creation": 0.7, "social_engagement": 0.6, "workflow_engines": 0.5, "discovery": 0.4},
    "the_hero": {"social_networking": 0.8, "mission_ops": 0.7, "workflow_engines": 0.6, "social_engagement": 0.5},
    "the_magician": {"workflow_engines": 0.9, "analytics": 0.8, "intelligence": 0.7, "mission_ops": 0.5},
    "the_companion": {"social_networking": 0.9, "social_engagement": 0.8, "bundles": 0.5, "discovery": 0.4},
    "the_jester": {"social_engagement": 0.9, "content_creation": 0.7, "discovery": 0.5, "social_networking": 0.4},
    "social_butterfly": {"social_engagement": 0.9, "social_networking": 0.8, "content_creation": 0.5},
    "thoughtful_contributor": {"content_creation": 0.9, "intelligence": 0.7, "analytics": 0.6},
    "casual_observer": {"discovery": 0.8, "intelligence": 0.7, "social_engagement": 0.5},
    "niche_expert": {"analytics": 0.9, "intelligence": 0.8, "content_creation": 0.7},
    "enthusiastic_newcomer": {"discovery": 0.8, "social_engagement": 0.7, "social_networking": 0.6, "bundles": 0.5},
}


class SkillRecommender:
    """Recommends skills based on avatar personality and usage patterns"""

    def __init__(self, db):
        self.db = db

    async def get_recommendations(self, user_id: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Get personalized skill recommendations"""
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return await self._get_popular_uninstalled(user_id, limit)

        archetype = user.get("avatar_archetype") or user.get("archetype", "casual_observer")
        affinity = ARCHETYPE_AFFINITY.get(archetype, ARCHETYPE_AFFINITY.get("casual_observer", {}))

        installed_slugs = set()
        installations = await self.db.siddhi_installations.find({"user_id": user_id}).to_list(None)
        for inst in installations:
            installed_slugs.add(inst["skill_slug"])

        all_skills = await self.db.siddhi_skills.find({
            "slug": {"$nin": list(installed_slugs)},
        }).to_list(None)

        scored = []
        for skill in all_skills:
            score = 0.0
            category = skill.get("category", "")
            score += affinity.get(category, 0.0) * 0.4
            installs = skill.get("stats", {}).get("total_installs", 0)
            score += min(installs / 100.0, 0.3) * 0.2
            avg_rating = skill.get("stats", {}).get("avg_rating", 0)
            score += (avg_rating / 5.0) * 0.2
            if skill.get("is_featured"):
                score += 0.1
            if skill.get("tier") in ["core", "standard"]:
                score += 0.1

            skill.pop("_id", None)
            scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        result = []
        for skill, score in scored[:limit]:
            skill["recommendation_score"] = round(score, 3)
            skill["recommendation_reason"] = self._get_reason(skill, archetype, affinity)
            result.append(skill)

        return result

    def _get_reason(self, skill: Dict, archetype: str, affinity: Dict) -> str:
        category = skill.get("category", "")
        cat_score = affinity.get(category, 0)
        display_archetype = archetype.replace("_", " ").title()

        if cat_score >= 0.8:
            return f"Perfect match for your {display_archetype} personality"
        elif cat_score >= 0.5:
            return f"Recommended for {display_archetype} avatars"
        elif skill.get("is_featured"):
            return "Featured skill in Siddhi Bazaar"
        elif skill.get("stats", {}).get("total_installs", 0) > 50:
            return "Popular among Maya World avatars"
        else:
            return "Expand your avatar's capabilities"

    async def _get_popular_uninstalled(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        installed_slugs = set()
        installations = await self.db.siddhi_installations.find({"user_id": user_id}).to_list(None)
        for inst in installations:
            installed_slugs.add(inst["skill_slug"])

        skills = await self.db.siddhi_skills.find({
            "slug": {"$nin": list(installed_slugs)},
        }).sort("stats.total_installs", -1).limit(limit).to_list(limit)

        for s in skills:
            s.pop("_id", None)
            s["recommendation_score"] = 0.5
            s["recommendation_reason"] = "Popular among Maya World avatars"

        return skills
