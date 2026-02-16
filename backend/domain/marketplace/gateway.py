"""
Siddhi Gateway - Central Control Plane
Every tool call and engine execution flows through this gateway.

Layers:
1. Access Control  → Is this skill installed & enabled?
2. Rate Limiter    → Within quotas?
3. Circuit Breaker → Is the tool healthy?
4. Skill Router    → Forward to correct provider
5. Usage Tracker   → Record result
"""

import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from domain.marketplace.models import GatewayResult
from domain.marketplace.gateway_layers.access_control import AccessControlLayer
from domain.marketplace.gateway_layers.rate_limiter import RateLimiterLayer
from domain.marketplace.gateway_layers.circuit_breaker import CircuitBreakerLayer
from domain.marketplace.gateway_layers.usage_tracker import UsageTracker
from domain.marketplace.gateway_layers.skill_router import SkillRouter

logger = logging.getLogger(__name__)


class SiddhiGateway:
    """
    Central gateway for ALL avatar capability execution.

    Replaces direct calls to:
    - AvatarMCPServer.call_tool()
    - WorkflowEngineRegistry.get_engine().execute()
    """

    def __init__(self, db, mcp_server, engine_registry=None):
        self.db = db
        self.mcp_server = mcp_server
        self.engine_registry = engine_registry

        self.access_control = AccessControlLayer(db)
        self.rate_limiter = RateLimiterLayer(db)
        self.circuit_breaker = CircuitBreakerLayer(db)
        self.usage_tracker = UsageTracker(db)
        self.router = SkillRouter(mcp_server, engine_registry)

        self._install_cache: Dict[str, Tuple[Set[str], float]] = {}
        self._perm_cache: Dict[str, Tuple[Dict[str, bool], float]] = {}
        self._CACHE_TTL = 60

        logger.info("🔮 Siddhi Gateway initialized")

    async def execute_tool(
        self,
        tool_name: str,
        avatar_id: str,
        arguments: Dict[str, Any],
        source: str = "agent",
    ) -> GatewayResult:
        """Execute an MCP tool through all gateway layers"""
        start_time = time.monotonic()

        has_marketplace = await self._has_marketplace_data(avatar_id)
        if not has_marketplace:
            result = await self.router.execute_mcp_tool(tool_name, avatar_id, arguments)
            latency_ms = (time.monotonic() - start_time) * 1000
            return GatewayResult(
                success=result.get("success", False),
                data=result,
                skill_slug=tool_name,
                source=source,
                avatar_id=avatar_id,
                was_permitted=True,
                latency_ms=latency_ms,
            )

        access = await self.access_control.check(avatar_id, tool_name, "mcp_tool")
        if not access.permitted:
            return GatewayResult(
                success=False,
                data={"error": access.reason},
                skill_slug=tool_name,
                source=source,
                avatar_id=avatar_id,
                was_permitted=False,
                denial_reason=access.reason,
            )

        rate_ok = await self.rate_limiter.check(avatar_id, tool_name)
        if not rate_ok.allowed:
            return GatewayResult(
                success=False,
                data={"error": rate_ok.reason},
                skill_slug=tool_name,
                source=source,
                avatar_id=avatar_id,
                was_permitted=True,
                denial_reason=rate_ok.reason,
            )

        circuit = await self.circuit_breaker.check(avatar_id, tool_name)
        if circuit.is_open:
            return GatewayResult(
                success=False,
                data={"error": f"Skill '{tool_name}' is temporarily disabled (circuit open)"},
                skill_slug=tool_name,
                source=source,
                avatar_id=avatar_id,
                was_permitted=True,
                denial_reason="Circuit breaker open",
                tool_health="broken",
                consecutive_failures=circuit.consecutive_failures,
            )

        result = await self.router.execute_mcp_tool(tool_name, avatar_id, arguments)
        latency_ms = (time.monotonic() - start_time) * 1000
        success = result.get("success", False)

        try:
            await self.usage_tracker.record(avatar_id, tool_name, result, latency_ms, source)
            await self.circuit_breaker.record_result(avatar_id, tool_name, success)
        except Exception as e:
            logger.warning(f"Post-execution tracking failed: {e}")

        return GatewayResult(
            success=success,
            data=result,
            skill_slug=tool_name,
            source=source,
            avatar_id=avatar_id,
            was_permitted=True,
            latency_ms=latency_ms,
            tool_health=circuit.status,
            consecutive_failures=circuit.consecutive_failures,
        )

    async def execute_engine(
        self,
        mission_type: str,
        mission_id: str,
        avatar_id: str,
        **kwargs,
    ) -> GatewayResult:
        """Execute a workflow engine through all gateway layers"""
        start_time = time.monotonic()

        engine_slug = f"{mission_type}_engine"
        has_marketplace = await self._has_marketplace_data(avatar_id)

        if has_marketplace:
            access = await self.access_control.check(avatar_id, engine_slug, "workflow_engine")
            if not access.permitted:
                access2 = await self.access_control.check(avatar_id, mission_type, "workflow_engine")
                if not access2.permitted:
                    return GatewayResult(
                        success=False,
                        data={"error": access.reason},
                        skill_slug=engine_slug,
                        source="workflow",
                        avatar_id=avatar_id,
                        was_permitted=False,
                        denial_reason=access.reason,
                    )

        result = await self.router.execute_engine(
            mission_type, mission_id, avatar_id, self.db, **kwargs
        )
        latency_ms = (time.monotonic() - start_time) * 1000

        return GatewayResult(
            success=result.get("success", False),
            data=result,
            skill_slug=engine_slug,
            source="workflow",
            avatar_id=avatar_id,
            was_permitted=True,
            latency_ms=latency_ms,
        )

    async def get_available_tools(self, avatar_id: str) -> List[str]:
        """Get list of tool names this avatar has installed & enabled."""
        now = time.time()
        if avatar_id in self._install_cache:
            tools, cached_at = self._install_cache[avatar_id]
            if now - cached_at < self._CACHE_TTL:
                return list(tools)

        has_marketplace = await self._has_marketplace_data(avatar_id)
        if not has_marketplace:
            if hasattr(self.mcp_server, 'tools'):
                return list(self.mcp_server.tools.keys())
            return []

        installations = await self.db.siddhi_installations.find({
            "user_id": avatar_id,
            "enabled": True,
            "skill_type": {"$in": ["mcp_tool"]},
        }).to_list(None)

        tools = {inst["skill_slug"] for inst in installations}
        self._install_cache[avatar_id] = (tools, now)
        return list(tools)

    async def get_permissions_from_installations(self, avatar_id: str) -> Dict[str, bool]:
        """
        Build a permissions dict matching avatar_actions_enabled format
        from marketplace installations.
        """
        now = time.time()
        if avatar_id in self._perm_cache:
            perms, cached_at = self._perm_cache[avatar_id]
            if now - cached_at < self._CACHE_TTL:
                return perms

        has_marketplace = await self._has_marketplace_data(avatar_id)
        if not has_marketplace:
            user = await self.db.users.find_one({"id": avatar_id})
            return user.get("avatar_actions_enabled", {}) if user else {}

        installations = await self.db.siddhi_installations.find({
            "user_id": avatar_id,
            "enabled": True,
        }).to_list(None)

        installed_slugs = {inst["skill_slug"] for inst in installations}
        permissions = {}

        skills = await self.db.siddhi_skills.find({
            "slug": {"$in": list(installed_slugs)},
        }).to_list(None)

        for skill in skills:
            perm_key = skill.get("binding", {}).get("permission_key")
            if perm_key:
                permissions[perm_key] = True

        self._perm_cache[avatar_id] = (permissions, now)
        return permissions

    def invalidate_cache(self, avatar_id: str):
        """Called after install/uninstall/toggle to bust the cache"""
        self._install_cache.pop(avatar_id, None)
        self._perm_cache.pop(avatar_id, None)

    async def _has_marketplace_data(self, avatar_id: str) -> bool:
        """Check if this avatar has any marketplace installations"""
        count = await self.db.siddhi_installations.count_documents({"user_id": avatar_id}, limit=1)
        return count > 0

    async def call_tool(self, tool_name: str, avatar_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible call_tool interface matching AvatarMCPServer"""
        gw_result = await self.execute_tool(tool_name, avatar_id, arguments, source="agent")
        return gw_result.data
