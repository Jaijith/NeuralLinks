"""
Siddhi Bazaar - Agent-to-Agent (A2A) Service
Implements internal A2A protocol for communication between user's personal avatar
and specialized AI Agent Assistants.

Follows Google's Agent2Agent protocol pattern:
- Agent Cards: describe agent capabilities
- Tasks: unit of work with lifecycle (submitted → working → completed/failed)
- Messages: structured communication within tasks
- Artifacts: task outputs

The user's avatar (client agent) sends tasks to specialized agents (remote agents)
who process them using their domain expertise + LLM.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.marketplace.models import (
    make_a2a_task_doc, A2ATaskStatus, now_iso,
)
from core.config import get_openai_client, call_openai_with_system, OPENAI_MODEL

logger = logging.getLogger(__name__)


class A2AService:
    """
    Internal Agent-to-Agent communication service.
    Enables the user's personal avatar to consult specialized AI Agent Assistants.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def discover_agents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Discover available AI agents for a user (subscribed + active).
        Returns Agent Cards for each available agent.
        """
        subscriptions = await self.db.agent_subscriptions.find({
            "user_id": user_id,
            "active": True,
        }).to_list(None)

        agents = []
        for sub in subscriptions:
            agent_user = await self.db.users.find_one({"id": sub["agent_user_id"]})
            if not agent_user:
                continue

            agent_card = agent_user.get("agent_card")
            if agent_card:
                agent_card["agent_user_id"] = sub["agent_user_id"]
                agent_card["domain"] = sub.get("agent_domain", agent_user.get("agent_domain"))
                agent_card["is_active"] = True
                agents.append(agent_card)

        return agents

    async def create_task(
        self,
        client_agent_id: str,
        remote_agent_id: str,
        query: str,
        source: str = "chat",
        skill_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new A2A task — the client agent (user's avatar) requests
        consultation from a remote agent (specialized AI assistant).
        """
        # Validate remote agent exists and is subscribed
        subscription = await self.db.agent_subscriptions.find_one({
            "user_id": client_agent_id,
            "agent_user_id": remote_agent_id,
            "active": True,
        })

        if not subscription:
            return {
                "success": False,
                "error": "Agent not subscribed or not active for this user",
            }

        remote_agent = await self.db.users.find_one({"id": remote_agent_id})
        if not remote_agent:
            return {"success": False, "error": "Remote agent user not found"}

        remote_agent_slug = remote_agent.get("avatar_name", "unknown").lower().replace(" ", "_")

        task_doc = make_a2a_task_doc(
            client_agent_id=client_agent_id,
            remote_agent_id=remote_agent_id,
            remote_agent_slug=remote_agent_slug,
            query=query,
            source=source,
            skill_id=skill_id,
        )

        await self.db.a2a_tasks.insert_one(task_doc)

        logger.info(
            f"🤝 A2A task created: {task_doc['id'][:8]}... "
            f"({client_agent_id[:8]}... → {remote_agent_slug})"
        )

        return {
            "success": True,
            "task_id": task_doc["id"],
            "status": A2ATaskStatus.SUBMITTED.value,
        }

    async def process_task(self, task_id: str) -> Dict[str, Any]:
        """
        Process an A2A task: the remote agent generates a response
        using its domain expertise + LLM.
        """
        task = await self.db.a2a_tasks.find_one({"id": task_id})
        if not task:
            return {"success": False, "error": "Task not found"}

        if task["status"] not in [A2ATaskStatus.SUBMITTED.value, A2ATaskStatus.WORKING.value]:
            return {
                "success": False,
                "error": f"Task is in '{task['status']}' state, cannot process",
            }

        # Mark as working
        await self.db.a2a_tasks.update_one(
            {"id": task_id},
            {"$set": {"status": A2ATaskStatus.WORKING.value, "updated_at": now_iso()}}
        )

        start_time = time.time()

        try:
            remote_agent = await self.db.users.find_one({"id": task["remote_agent_id"]})
            if not remote_agent:
                raise ValueError("Remote agent not found")

            # Build the consultation system prompt from the agent's specialization
            consultation_prompt = remote_agent.get(
                "agent_consultation_prompt",
                f"You are {remote_agent.get('avatar_name', 'an AI assistant')}. "
                f"You specialize in {remote_agent.get('agent_domain', 'general knowledge')}."
            )

            expertise = remote_agent.get("agent_expertise", [])
            domain = remote_agent.get("agent_domain", "general")
            domain_label = remote_agent.get("agent_domain_label", domain.title())

            system_prompt = (
                f"{consultation_prompt}\n\n"
                f"Your domain: {domain_label}\n"
                f"Your expertise areas: {', '.join(expertise)}\n\n"
                "GUIDELINES:\n"
                "- Provide expert, authoritative answers within your domain.\n"
                "- If the question is outside your domain, acknowledge it and provide what you can.\n"
                "- Be concise, actionable, and insightful.\n"
                "- Use your specialized knowledge to add unique value.\n"
                "- Cite sources or reasoning when appropriate.\n"
                "- Format your response clearly."
            )

            # Get the user's query from the last message
            user_query = ""
            for msg in task.get("messages", []):
                if msg.get("role") == "user":
                    for part in msg.get("parts", []):
                        if part.get("type") == "text":
                            user_query = part["text"]

            if not user_query:
                raise ValueError("No user query found in task messages")

            # Call LLM with agent's system prompt
            response_text = await call_openai_with_system(
                system_prompt=system_prompt,
                user_message=user_query,
                model=OPENAI_MODEL,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Create response message
            response_message = {
                "role": "agent",
                "parts": [{"type": "text", "text": response_text}],
                "timestamp": now_iso(),
                "agent_id": task["remote_agent_id"],
                "agent_name": remote_agent.get("avatar_name", "Agent"),
            }

            # Create artifact
            artifact = {
                "type": "text_response",
                "data": response_text,
                "domain": domain,
                "agent_name": remote_agent.get("avatar_name"),
                "created_at": now_iso(),
            }

            # Mark task as completed
            await self.db.a2a_tasks.update_one(
                {"id": task_id},
                {"$set": {
                    "status": A2ATaskStatus.COMPLETED.value,
                    "updated_at": now_iso(),
                    "metadata.latency_ms": elapsed_ms,
                },
                "$push": {
                    "messages": response_message,
                    "artifacts": artifact,
                }}
            )

            logger.info(
                f"🤝 A2A task completed: {task_id[:8]}... "
                f"by {remote_agent.get('avatar_name')} ({elapsed_ms:.0f}ms)"
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": A2ATaskStatus.COMPLETED.value,
                "response": response_text,
                "agent_name": remote_agent.get("avatar_name"),
                "domain": domain,
                "latency_ms": round(elapsed_ms, 1),
            }

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"A2A task failed: {task_id[:8]}... - {e}")

            await self.db.a2a_tasks.update_one(
                {"id": task_id},
                {"$set": {
                    "status": A2ATaskStatus.FAILED.value,
                    "updated_at": now_iso(),
                    "metadata.error": str(e),
                    "metadata.latency_ms": elapsed_ms,
                }}
            )

            return {
                "success": False,
                "task_id": task_id,
                "status": A2ATaskStatus.FAILED.value,
                "error": str(e),
            }

    async def consult(
        self,
        client_agent_id: str,
        remote_agent_id: str,
        query: str,
        source: str = "chat",
    ) -> Dict[str, Any]:
        """
        Full consultation flow: create task + process it in one call.
        This is the primary interface for synchronous agent consultation.
        """
        # Create task
        create_result = await self.create_task(
            client_agent_id=client_agent_id,
            remote_agent_id=remote_agent_id,
            query=query,
            source=source,
        )

        if not create_result.get("success"):
            return create_result

        # Process immediately
        return await self.process_task(create_result["task_id"])

    async def consult_best_agent(
        self,
        client_agent_id: str,
        query: str,
        source: str = "chat",
    ) -> Dict[str, Any]:
        """
        Auto-select the best agent for a query based on domain matching,
        then consult that agent.
        """
        agents = await self.discover_agents(client_agent_id)
        if not agents:
            return {
                "success": False,
                "error": "No agents available. Subscribe to AI Agents in the Siddhi Bazaar.",
            }

        # Score agents by keyword matching
        query_lower = query.lower()
        scored_agents = []
        for agent in agents:
            score = 0
            domain = (agent.get("domain") or "").lower()
            if domain in query_lower:
                score += 10

            for skill in agent.get("skills", []):
                skill_name = skill.get("name", "").lower()
                for tag in skill.get("tags", []):
                    if tag.lower() in query_lower:
                        score += 3
                if any(word in query_lower for word in skill_name.split()):
                    score += 2

            agent_desc = agent.get("description", "").lower()
            for word in agent_desc.split():
                if len(word) > 3 and word in query_lower:
                    score += 1

            scored_agents.append((score, agent))

        scored_agents.sort(key=lambda x: x[0], reverse=True)
        best_agent = scored_agents[0][1]

        return await self.consult(
            client_agent_id=client_agent_id,
            remote_agent_id=best_agent["agent_user_id"],
            query=query,
            source=source,
        )

    async def consult_multiple(
        self,
        client_agent_id: str,
        query: str,
        agent_ids: Optional[List[str]] = None,
        source: str = "chat",
    ) -> List[Dict[str, Any]]:
        """
        Consult multiple agents in parallel for a richer response.
        If agent_ids not specified, consults all subscribed agents.
        """
        if agent_ids:
            target_ids = agent_ids
        else:
            agents = await self.discover_agents(client_agent_id)
            target_ids = [a["agent_user_id"] for a in agents]

        if not target_ids:
            return []

        import asyncio
        tasks = [
            self.consult(
                client_agent_id=client_agent_id,
                remote_agent_id=agent_id,
                query=query,
                source=source,
            )
            for agent_id in target_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append({"success": False, "error": str(r)})
            else:
                processed.append(r)

        return processed

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        task = await self.db.a2a_tasks.find_one({"id": task_id})
        if task:
            task.pop("_id", None)
        return task

    async def get_user_tasks(
        self,
        user_id: str,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent A2A tasks for a user."""
        filters: Dict[str, Any] = {"client_agent_id": user_id}
        if status:
            filters["status"] = status

        tasks = await self.db.a2a_tasks.find(filters).sort(
            "created_at", -1
        ).limit(limit).to_list(limit)

        for t in tasks:
            t.pop("_id", None)
        return tasks
