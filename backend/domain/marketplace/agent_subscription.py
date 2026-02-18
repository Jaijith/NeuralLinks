"""
Siddhi Bazaar - Agent Subscription Service
Handles subscribing/unsubscribing to AI Agent Assistants.
Auto-creates friendships on subscribe, removes on unsubscribe.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from domain.marketplace.models import make_installation_doc, now_iso, new_id, SkillType

logger = logging.getLogger(__name__)


class AgentSubscriptionService:
    """
    Manages AI Agent subscriptions:
    1. Creates/removes siddhi_installations for the agent skill
    2. Auto-creates/removes friendships with the agent's bot user
    3. Tracks subscriptions in agent_subscriptions collection
    4. Updates gateway cache
    """

    def __init__(self, db, gateway=None):
        self.db = db
        self.gateway = gateway

    async def subscribe(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """
        Subscribe a user to an AI Agent Assistant.
        1. Validate skill is an ai_agent type
        2. Create siddhi_installation record
        3. Auto-create friendship (accepted)
        4. Create subscription tracking record
        """
        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if not skill:
            return {"success": False, "error": "Agent skill not found"}

        if skill.get("type") != SkillType.AI_AGENT.value:
            return {"success": False, "error": "This skill is not an AI Agent"}

        agent_user_id = skill.get("binding", {}).get("agent_user_id")
        if not agent_user_id:
            return {"success": False, "error": "Agent user ID not configured"}

        agent_user = await self.db.users.find_one({"id": agent_user_id})
        if not agent_user:
            return {"success": False, "error": "Agent bot user not found"}

        # Check if already subscribed
        existing_install = await self.db.siddhi_installations.find_one({
            "user_id": user_id,
            "skill_slug": skill["slug"],
        })
        if existing_install:
            return {
                "success": True,
                "already_subscribed": True,
                "installation_id": existing_install["id"],
                "message": "Already subscribed to this agent",
            }

        # 1. Create installation record
        doc = make_installation_doc(user_id, skill)
        try:
            await self.db.siddhi_installations.insert_one(doc)
        except Exception as e:
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                existing = await self.db.siddhi_installations.find_one({
                    "user_id": user_id, "skill_slug": skill["slug"]
                })
                return {
                    "success": True,
                    "already_subscribed": True,
                    "installation_id": existing["id"] if existing else None,
                    "message": "Already subscribed",
                }
            raise

        # 2. Auto-create friendship (skip if already friends)
        friendship_created = await self._ensure_friendship(user_id, agent_user_id)

        # 3. Create subscription tracking record
        subscription = {
            "id": new_id(),
            "user_id": user_id,
            "agent_user_id": agent_user_id,
            "skill_id": skill_id,
            "skill_slug": skill["slug"],
            "agent_domain": skill.get("binding", {}).get("agent_domain"),
            "active": True,
            "subscribed_at": now_iso(),
            "updated_at": now_iso(),
        }
        try:
            await self.db.agent_subscriptions.insert_one(subscription)
        except Exception as e:
            if "duplicate key" not in str(e).lower() and "E11000" not in str(e):
                logger.warning(f"Failed to create subscription record: {e}")

        # 4. Update skill stats
        await self.db.siddhi_skills.update_one(
            {"id": skill_id},
            {"$inc": {"stats.total_installs": 1, "stats.active_users": 1}}
        )

        # 5. Invalidate gateway cache
        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        agent_name = agent_user.get("avatar_name", agent_user.get("name", "Unknown"))
        logger.info(
            f"🤖 User {user_id[:8]}... subscribed to agent {agent_name} "
            f"(friendship_created={friendship_created})"
        )

        return {
            "success": True,
            "installation_id": doc["id"],
            "friendship_created": friendship_created,
            "agent_name": agent_name,
            "agent_domain": skill.get("binding", {}).get("agent_domain"),
            "message": f"Subscribed to {agent_name}",
        }

    async def unsubscribe(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """
        Unsubscribe a user from an AI Agent Assistant.
        1. Remove installation
        2. Remove friendship
        3. Deactivate subscription record
        """
        skill = await self.db.siddhi_skills.find_one({"id": skill_id})
        if not skill:
            return {"success": False, "error": "Agent skill not found"}

        agent_user_id = skill.get("binding", {}).get("agent_user_id")

        # Remove installation
        result = await self.db.siddhi_installations.delete_one({
            "user_id": user_id,
            "skill_id": skill_id,
        })

        if result.deleted_count == 0:
            return {"success": False, "error": "Not subscribed to this agent"}

        # Remove friendship
        if agent_user_id:
            await self.db.friendships.delete_one({
                "$or": [
                    {"user_id": user_id, "friend_id": agent_user_id},
                    {"user_id": agent_user_id, "friend_id": user_id},
                ]
            })

        # Deactivate subscription
        await self.db.agent_subscriptions.update_one(
            {"user_id": user_id, "skill_id": skill_id},
            {"$set": {"active": False, "unsubscribed_at": now_iso(), "updated_at": now_iso()}}
        )

        # Update skill stats
        await self.db.siddhi_skills.update_one(
            {"id": skill_id},
            {"$inc": {"stats.total_installs": -1, "stats.active_users": -1}}
        )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        logger.info(f"🤖 User {user_id[:8]}... unsubscribed from agent skill {skill['name']}")

        return {
            "success": True,
            "message": f"Unsubscribed from {skill['name']}",
        }

    async def toggle_agent(self, user_id: str, skill_id: str, enabled: bool) -> Dict[str, Any]:
        """Toggle an agent subscription on/off without removing friendship."""
        installation = await self.db.siddhi_installations.find_one({
            "user_id": user_id,
            "skill_id": skill_id,
        })
        if not installation:
            return {"success": False, "error": "Not subscribed to this agent"}

        await self.db.siddhi_installations.update_one(
            {"id": installation["id"]},
            {"$set": {"enabled": enabled, "updated_at": now_iso()}}
        )

        await self.db.agent_subscriptions.update_one(
            {"user_id": user_id, "skill_id": skill_id},
            {"$set": {"active": enabled, "updated_at": now_iso()}}
        )

        if self.gateway:
            self.gateway.invalidate_cache(user_id)

        return {"success": True, "enabled": enabled}

    async def get_subscribed_agents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active agent subscriptions for a user with agent details.
        Lazily syncs existing friendships with AI agent bots on first access."""

        # Lazy sync: if user has friendships with AI agent bots but no subscriptions, create them
        await self._sync_from_friendships(user_id)

        subscriptions = await self.db.agent_subscriptions.find({
            "user_id": user_id,
            "active": True,
        }).to_list(None)

        result = []
        for sub in subscriptions:
            sub.pop("_id", None)
            agent_user = await self.db.users.find_one({"id": sub["agent_user_id"]})
            skill = await self.db.siddhi_skills.find_one({"id": sub["skill_id"]})
            if agent_user and skill:
                skill.pop("_id", None)
                result.append({
                    "subscription": sub,
                    "agent": {
                        "id": agent_user["id"],
                        "name": agent_user.get("avatar_name", agent_user.get("name")),
                        "picture": agent_user.get("avatar_picture", agent_user.get("picture")),
                        "domain": sub.get("agent_domain"),
                        "domain_label": agent_user.get("agent_domain_label", ""),
                        "bio": agent_user.get("avatar_bio", ""),
                        "expertise": agent_user.get("agent_expertise", []),
                        "is_ai_agent": True,
                    },
                    "skill": skill,
                })

        return result

    async def _sync_from_friendships(self, user_id: str) -> int:
        """Sync existing friendships with AI agent bots into subscriptions.
        Creates agent_subscription + siddhi_installation for any AI agent friend
        that isn't already subscribed. Also tags the friendship as ai_agent."""
        from domain.marketplace.models import make_installation_doc

        # Get all AI agent bot IDs
        agent_bots = await self.db.users.find(
            {"is_ai_agent": True}, {"id": 1}
        ).to_list(None)
        if not agent_bots:
            return 0
        agent_ids = [b["id"] for b in agent_bots]

        # Find friendships with AI agent bots
        friendships = await self.db.friendships.find({
            "$or": [
                {"user_id": user_id, "friend_id": {"$in": agent_ids}},
                {"friend_id": user_id, "user_id": {"$in": agent_ids}},
            ]
        }).to_list(None)

        if not friendships:
            return 0

        # Build bot_id -> skill lookup
        agent_skills = await self.db.siddhi_skills.find(
            {"type": "ai_agent"}
        ).to_list(None)
        skill_by_bot = {}
        for s in agent_skills:
            bot_id = s.get("binding", {}).get("agent_user_id")
            if bot_id:
                skill_by_bot[bot_id] = s

        created = 0
        seen_bots = set()

        for fr in friendships:
            bot_id = fr["friend_id"] if fr["user_id"] == user_id else fr["user_id"]
            if bot_id in seen_bots:
                # Tag duplicate friendship and skip
                if fr.get("friend_type") != "ai_agent":
                    await self.db.friendships.update_one(
                        {"_id": fr["_id"]},
                        {"$set": {"friend_type": "ai_agent", "status": "accepted"}}
                    )
                continue
            seen_bots.add(bot_id)

            skill = skill_by_bot.get(bot_id)
            if not skill:
                continue

            # Tag friendship
            if fr.get("friend_type") != "ai_agent":
                await self.db.friendships.update_one(
                    {"_id": fr["_id"]},
                    {"$set": {"friend_type": "ai_agent", "status": "accepted"}}
                )

            # Check if subscription already exists
            existing_sub = await self.db.agent_subscriptions.find_one({
                "user_id": user_id, "skill_id": skill["id"]
            })
            if existing_sub:
                continue

            # Create installation
            existing_install = await self.db.siddhi_installations.find_one({
                "user_id": user_id, "skill_slug": skill["slug"]
            })
            if not existing_install:
                try:
                    doc = make_installation_doc(user_id, skill)
                    await self.db.siddhi_installations.insert_one(doc)
                except Exception:
                    pass  # duplicate key is fine

            # Create subscription
            try:
                await self.db.agent_subscriptions.insert_one({
                    "id": new_id(),
                    "user_id": user_id,
                    "agent_user_id": bot_id,
                    "skill_id": skill["id"],
                    "skill_slug": skill["slug"],
                    "agent_domain": skill.get("binding", {}).get("agent_domain"),
                    "active": True,
                    "subscribed_at": now_iso(),
                    "updated_at": now_iso(),
                })
                created += 1
            except Exception:
                pass  # duplicate key is fine

        if created > 0:
            logger.info(f"🔄 Synced {created} agent subscriptions from friendships for {user_id[:8]}...")
        return created

    async def is_subscribed(self, user_id: str, agent_user_id: str) -> bool:
        """Check if a user is subscribed to an agent."""
        sub = await self.db.agent_subscriptions.find_one({
            "user_id": user_id,
            "agent_user_id": agent_user_id,
            "active": True,
        })
        return sub is not None

    async def _ensure_friendship(self, user_id: str, agent_user_id: str) -> bool:
        """Create auto-accepted friendship with AI Agent badge. Returns True if created."""
        existing = await self.db.friendships.find_one({
            "$or": [
                {"user_id": user_id, "friend_id": agent_user_id},
                {"user_id": agent_user_id, "friend_id": user_id},
            ]
        })

        if existing:
            # Ensure it's accepted and tagged
            if existing.get("status") != "accepted" or not existing.get("friend_type"):
                await self.db.friendships.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "status": "accepted",
                        "friend_type": "ai_agent",
                        "accepted_at": now_iso(),
                    }}
                )
            return False

        friendship = {
            "user_id": user_id,
            "friend_id": agent_user_id,
            "status": "accepted",
            "friend_type": "ai_agent",
            "created_at": now_iso(),
            "accepted_at": now_iso(),
        }
        await self.db.friendships.insert_one(friendship)
        return True

    async def ensure_indexes(self):
        """Create necessary MongoDB indexes for agent subscriptions."""
        await self.db.agent_subscriptions.create_index(
            [("user_id", 1), ("skill_id", 1)], unique=True
        )
        await self.db.agent_subscriptions.create_index(
            [("user_id", 1), ("active", 1)]
        )
        await self.db.agent_subscriptions.create_index("agent_user_id")
        await self.db.a2a_tasks.create_index(
            [("client_agent_id", 1), ("status", 1)]
        )
        await self.db.a2a_tasks.create_index("remote_agent_id")
        await self.db.a2a_tasks.create_index("created_at")
