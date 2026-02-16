"""
Circuit Breaker Layer
Auto-disable failing tools, auto-recover after cooldown.
States: CLOSED (healthy) → OPEN (broken) → HALF_OPEN (testing)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CircuitState:
    is_open: bool
    status: str = "closed"
    consecutive_failures: int = 0


class CircuitBreakerLayer:
    """Layer 3: Auto-disable failing tools, auto-recover after cooldown"""

    def __init__(self, db):
        self.db = db
        self._threshold_cache: Dict[str, Dict] = {}

    async def _get_config(self, skill_slug: str) -> Dict[str, Any]:
        if skill_slug in self._threshold_cache:
            return self._threshold_cache[skill_slug]

        skill = await self.db.siddhi_skills.find_one({"slug": skill_slug})
        if skill:
            config = skill.get("gateway_config", {}).get("circuit_breaker", {})
            self._threshold_cache[skill_slug] = config
            return config
        return {"failure_threshold": 5, "recovery_seconds": 300}

    async def check(self, avatar_id: str, skill_slug: str) -> CircuitState:
        """Check circuit breaker state"""
        try:
            installation = await self.db.siddhi_installations.find_one({
                "user_id": avatar_id,
                "skill_slug": skill_slug,
            })

            if not installation:
                return CircuitState(is_open=False, status="closed")

            gw_state = installation.get("gateway_state", {})
            status = gw_state.get("circuit_status", "closed")
            failures = gw_state.get("consecutive_failures", 0)

            if status == "open":
                config = await self._get_config(skill_slug)
                recovery_seconds = config.get("recovery_seconds", 300)
                last_failure_str = gw_state.get("last_failure_at")

                if last_failure_str:
                    try:
                        last_failure = datetime.fromisoformat(last_failure_str.replace("Z", "+00:00"))
                        if last_failure.tzinfo is None:
                            last_failure = last_failure.replace(tzinfo=timezone.utc)
                        elapsed = (datetime.now(timezone.utc) - last_failure).total_seconds()

                        if elapsed >= recovery_seconds:
                            await self.db.siddhi_installations.update_one(
                                {"user_id": avatar_id, "skill_slug": skill_slug},
                                {"$set": {"gateway_state.circuit_status": "half_open"}}
                            )
                            return CircuitState(is_open=False, status="half_open", consecutive_failures=failures)
                    except (ValueError, TypeError):
                        pass

                return CircuitState(is_open=True, status="open", consecutive_failures=failures)

            return CircuitState(is_open=False, status=status, consecutive_failures=failures)

        except Exception as e:
            logger.error(f"Circuit breaker check failed: {e}")
            return CircuitState(is_open=False, status="closed")

    async def record_result(self, avatar_id: str, skill_slug: str, success: bool):
        """Record execution result and update circuit state"""
        try:
            if success:
                await self.db.siddhi_installations.update_one(
                    {"user_id": avatar_id, "skill_slug": skill_slug},
                    {"$set": {
                        "gateway_state.consecutive_failures": 0,
                        "gateway_state.circuit_status": "closed",
                        "gateway_state.last_success_at": datetime.now(timezone.utc).isoformat(),
                    }}
                )
            else:
                result = await self.db.siddhi_installations.find_one_and_update(
                    {"user_id": avatar_id, "skill_slug": skill_slug},
                    {
                        "$inc": {"gateway_state.consecutive_failures": 1},
                        "$set": {"gateway_state.last_failure_at": datetime.now(timezone.utc).isoformat()},
                    },
                    return_document=True,
                )

                if result:
                    failures = result.get("gateway_state", {}).get("consecutive_failures", 0)
                    config = await self._get_config(skill_slug)
                    threshold = config.get("failure_threshold", 5)

                    if failures >= threshold:
                        await self.db.siddhi_installations.update_one(
                            {"user_id": avatar_id, "skill_slug": skill_slug},
                            {"$set": {"gateway_state.circuit_status": "open"}}
                        )
                        logger.warning(f"Circuit OPENED for {avatar_id}/{skill_slug} after {failures} failures")

        except Exception as e:
            logger.error(f"Circuit breaker record failed: {e}")
