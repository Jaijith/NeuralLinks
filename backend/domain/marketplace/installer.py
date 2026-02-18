"""
Siddhi Bazaar - Skill Installer
Handles install/uninstall and bridges to avatar_actions_enabled + gateway cache.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from domain.marketplace.models import make_installation_doc, now_iso

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    success: bool
    installation_id: Optional[str] = None
    reason: Optional[str] = None


class SkillInstaller:
    """
    Handles install/uninstall and bridges to:
    1. siddhi_installations collection
    2. avatar_actions_enabled field (backward compatibility)
    3. Gateway cache invalidation
    """

    def __init__(self, db, gateway=None):
        self.db = db
        self.gateway = gateway

    async def install(self, user_id: str, skill_id: str) -> InstallResult:
        """Install a skill for an avatar. Delegates to AgentSubscriptionService for AI agents."""
        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if not skill:
            return InstallResult(success=False, reason="Skill not found")

        if skill.get("type") == "ai_agent":
            from domain.marketplace.agent_subscription import AgentSubscriptionService
            agent_svc = AgentSubscriptionService(self.db, self.gateway)
            result = await agent_svc.subscribe(user_id, skill_id)
            return InstallResult(
                success=result.get("success", False),
                installation_id=result.get("installation_id"),
                reason=result.get("message") or result.get("error"),
            )

        return await self._install_skill(user_id, skill)

    async def _install_skill(self, user_id: str, skill: Dict[str, Any]) -> InstallResult:
        """Internal install logic"""
        existing = await self.db.siddhi_installations.find_one({
            "user_id": user_id,
            "skill_slug": skill["slug"],
        })
        if existing:
            return InstallResult(success=True, installation_id=existing["id"], reason="Already installed")

        if skill["type"] == "skill_bundle":
            bundled_ids = skill.get("binding", {}).get("bundled_skill_ids", [])
            for bid in bundled_ids:
                if bid:
                    bundled_skill = await self.db.siddhi_skills.find_one({"id": bid})
                    if bundled_skill:
                        await self._install_skill(user_id, bundled_skill)

        if skill["type"] == "workflow_engine":
            tool_slugs = skill.get("binding", {}).get("workflow_tools_included", [])
            for slug in tool_slugs:
                tool_skill = await self.db.siddhi_skills.find_one({"slug": slug})
                if tool_skill:
                    await self._install_skill(user_id, tool_skill)

        doc = make_installation_doc(user_id, skill)
        try:
            await self.db.siddhi_installations.insert_one(doc)
        except Exception as e:
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                existing = await self.db.siddhi_installations.find_one({
                    "user_id": user_id, "skill_slug": skill["slug"]
                })
                return InstallResult(success=True, installation_id=existing["id"] if existing else None, reason="Already installed")
            raise

        perm_key = skill.get("binding", {}).get("permission_key")
        if perm_key:
            await self.db.users.update_one(
                {"id": user_id},
                {"$set": {f"avatar_actions_enabled.{perm_key}": True}}
            )

        await self.db.siddhi_skills.update_one(
            {"id": skill["id"]},
            {"$inc": {"stats.total_installs": 1, "stats.active_users": 1}}
        )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        logger.info(f"🔮 Installed skill '{skill['name']}' for user {user_id[:8]}...")
        return InstallResult(success=True, installation_id=doc["id"])

    async def uninstall(self, user_id: str, skill_id: str) -> bool:
        """Uninstall a skill"""
        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if not skill:
            return False

        installation = await self.db.siddhi_installations.find_one({
            "user_id": user_id,
            "skill_id": skill_id,
        })
        if not installation:
            return False

        await self.db.siddhi_installations.delete_one({"id": installation["id"]})

        perm_key = skill.get("binding", {}).get("permission_key")
        if perm_key:
            await self.db.users.update_one(
                {"id": user_id},
                {"$set": {f"avatar_actions_enabled.{perm_key}": False}}
            )

        await self.db.siddhi_skills.update_one(
            {"id": skill["id"]},
            {"$inc": {"stats.total_installs": -1, "stats.active_users": -1}}
        )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        logger.info(f"🔮 Uninstalled skill '{skill['name']}' for user {user_id[:8]}...")
        return True

    async def toggle_skill(self, user_id: str, skill_id: str, enabled: bool) -> bool:
        """Toggle a skill on/off — updates both installation and avatar_actions_enabled"""
        installation = await self.db.siddhi_installations.find_one({
            "user_id": user_id,
            "skill_id": skill_id,
        })
        if not installation:
            return False

        await self.db.siddhi_installations.update_one(
            {"id": installation["id"]},
            {"$set": {"enabled": enabled, "updated_at": now_iso()}}
        )

        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if skill:
            perm_key = skill.get("binding", {}).get("permission_key")
            if perm_key:
                await self.db.users.update_one(
                    {"id": user_id},
                    {"$set": {f"avatar_actions_enabled.{perm_key}": enabled}}
                )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        return True

    async def install_defaults_for_user(self, user_id: str) -> int:
        """Install all default skills for a new user"""
        default_skills = await self.db.siddhi_skills.find({"is_default": True}).to_list(None)
        installed = 0

        for skill in default_skills:
            result = await self._install_skill(user_id, skill)
            if result.success:
                installed += 1

        logger.info(f"🔮 Installed {installed} default skills for user {user_id[:8]}...")
        return installed

    async def sync_from_legacy(self, user_id: str) -> int:
        """
        Migrate existing avatar_actions_enabled permissions to siddhi_installations.
        Called lazily on first marketplace access for users who have permissions
        but no installation records. Idempotent — skips already-installed skills.
        """
        existing_count = await self.db.siddhi_installations.count_documents({"user_id": user_id})
        if existing_count > 0:
            return 0

        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return 0

        actions_enabled = user.get("avatar_actions_enabled", {})
        if not actions_enabled:
            return await self.install_defaults_for_user(user_id)

        enabled_keys = {k for k, v in actions_enabled.items() if v}
        if not enabled_keys:
            return await self.install_defaults_for_user(user_id)

        all_skills = await self.db.siddhi_skills.find({}).to_list(None)
        perm_to_skill = {}
        for skill in all_skills:
            perm_key = skill.get("binding", {}).get("permission_key")
            if perm_key:
                perm_to_skill[perm_key] = skill

        installed = 0
        for perm_key, skill in perm_to_skill.items():
            enabled = perm_key in enabled_keys
            doc = make_installation_doc(user_id, skill)
            doc["enabled"] = enabled
            try:
                await self.db.siddhi_installations.insert_one(doc)
                installed += 1
            except Exception as e:
                if "duplicate key" in str(e).lower() or "E11000" in str(e):
                    continue
                raise

        logger.info(
            f"🔮 Legacy sync for user {user_id[:8]}...: "
            f"migrated {installed} skills from avatar_actions_enabled"
        )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        return installed
