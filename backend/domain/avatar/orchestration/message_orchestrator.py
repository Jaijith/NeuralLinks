"""
Message Orchestrator — Multi-Agent Pipeline for Authentic Message Generation

Pipeline:
1. CONTEXT AGENT: Understand relationship context, conversation history
2. THINKING AGENT: Determine intent, tone, relationship-appropriate depth
3. DRAFTING AGENT: Write the message
4. RELATIONSHIP CALIBRATION AGENT: Ensure tone matches closeness level
5. HUMAN TOUCH VERIFIER: Score for authenticity
6. REVISION AGENT: Fix issues (if needed)

The goal: messages should feel like they came from the real person,
calibrated to the specific relationship.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import OPENAI_MODEL

logger = logging.getLogger(__name__)


class MessageOrchestrator:
    """
    Multi-agent pipeline that generates messages matching the user's
    communication style, calibrated to the specific relationship.
    """

    def __init__(self, db: AsyncIOMotorDatabase, openai_client: Any):
        self.db = db
        self.openai = openai_client
        self._graph_rag = None

    @property
    def graph_rag(self):
        if self._graph_rag is None:
            from domain.graph.rag import GraphRAG
            self._graph_rag = GraphRAG(self.db)
        return self._graph_rag

    async def generate_message(
        self,
        user_id: str,
        avatar_id: str,
        recipient_id: str,
        trigger: str = "",
        mood: str = "neutral",
        energy_level: float = 0.5,
        conversation_context: str = "",
    ) -> Dict[str, Any]:
        """
        Generate an authentic message through the full pipeline.

        Args:
            user_id: Sender's user ID
            avatar_id: The avatar sending the message
            recipient_id: Who the message is for
            trigger: What prompted the message
            mood: Current avatar mood
            energy_level: Current avatar energy
            conversation_context: Recent conversation with this person

        Returns:
            {"text": str, "quality_score": float, "metadata": dict}
        """
        try:
            # Load context
            context = await self._load_context(user_id, recipient_id)

            # --- Agent 1: CONTEXT ---
            relationship_ctx = await self._context_agent(
                context, recipient_id, conversation_context
            )

            # --- Agent 2: THINKING ---
            thinking = await self._thinking_agent(
                relationship_ctx, trigger, mood, energy_level, context
            )

            # --- Agent 3: DRAFTING ---
            draft = await self._drafting_agent(thinking, context, mood)

            # --- Agent 4: RELATIONSHIP CALIBRATION ---
            calibrated = await self._relationship_calibration_agent(
                draft, relationship_ctx, context
            )

            # --- Agent 5: HUMAN TOUCH VERIFIER ---
            verification = await self._human_touch_verifier(calibrated, context)

            # --- Agent 6: REVISION (if needed) ---
            final_text = calibrated
            if verification.get("score", 1.0) < 0.7:
                final_text = await self._revision_agent(
                    calibrated, verification.get("issues", []), context
                )

            return {
                "text": final_text,
                "quality_score": verification.get("score", 0.8),
                "metadata": {
                    "relationship_context": relationship_ctx,
                    "thinking": thinking,
                    "verification": verification,
                    "pipeline": "message_orchestrator_v1",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Message orchestrator error: {e}")
            return {
                "text": trigger or "Hey! How are you?",
                "quality_score": 0.3,
                "metadata": {"error": str(e), "pipeline": "fallback"},
            }

    # ------------------------------------------------------------------
    # CONTEXT LOADER
    # ------------------------------------------------------------------

    async def _load_context(self, user_id: str, recipient_id: str) -> Dict[str, Any]:
        import asyncio
        results = await asyncio.gather(
            self._get_style_profile(user_id),
            self._get_personality_prompt(user_id),
            self._get_recipient_info(recipient_id),
            self._get_relationship_history(user_id, recipient_id),
            self._get_identity_narrative(user_id),
            return_exceptions=True,
        )
        return {
            "style_profile": results[0] if not isinstance(results[0], Exception) else {},
            "personality_prompt": results[1] if not isinstance(results[1], Exception) else "",
            "recipient": results[2] if not isinstance(results[2], Exception) else {},
            "history": results[3] if not isinstance(results[3], Exception) else [],
            "identity_narrative": results[4] if not isinstance(results[4], Exception) else "",
        }

    async def _get_identity_narrative(self, user_id: str) -> str:
        try:
            return await self.graph_rag.get_identity_context(
                user_id, action_type="chat_response", max_tokens=1200,
            )
        except Exception as e:
            logger.warning(f"Could not fetch identity narrative: {e}")
            return ""

    async def _get_style_profile(self, user_id: str) -> Dict[str, Any]:
        doc = await self.db.avatar_style_profiles.find_one({"user_id": user_id}, {"_id": 0})
        return doc or {}

    async def _get_personality_prompt(self, user_id: str) -> str:
        doc = await self.db.avatar_personality_prompts.find_one(
            {"user_id": user_id}, {"_id": 0, "personality_prompt": 1}
        )
        return doc.get("personality_prompt", "") if doc else ""

    async def _get_recipient_info(self, recipient_id: str) -> Dict[str, Any]:
        doc = await self.db.users.find_one(
            {"id": recipient_id},
            {"_id": 0, "name": 1, "bio": 1, "interests": 1}
        )
        return doc or {}

    async def _get_relationship_history(
        self, user_id: str, recipient_id: str
    ) -> List[Dict[str, Any]]:
        """Get recent message history between these two users."""
        try:
            cursor = self.db.messages.find(
                {
                    "$or": [
                        {"sender_id": user_id, "recipient_id": recipient_id},
                        {"sender_id": recipient_id, "recipient_id": user_id},
                    ]
                },
                {"_id": 0, "text": 1, "sender_id": 1, "created_at": 1}
            ).sort("created_at", -1).limit(10)
            return await cursor.to_list(10)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # AGENT 1: CONTEXT
    # ------------------------------------------------------------------

    async def _context_agent(
        self, context: Dict[str, Any], recipient_id: str, conversation_context: str
    ) -> Dict[str, Any]:
        """Understand the relationship context."""
        recipient = context.get("recipient", {})
        history = context.get("history", [])

        history_text = ""
        if history:
            history_text = "\n".join(
                f"{'Sender' if m.get('sender_id') != recipient_id else 'Recipient'}: {m.get('text', '')[:100]}"
                for m in history[:5]
            )

        prompt = f"""Analyze this messaging relationship:

Recipient: {recipient.get('name', 'Unknown')}
Recipient bio: {recipient.get('bio', 'N/A')}
Recent conversation: {conversation_context[:500] if conversation_context else 'No recent conversation'}
Message history:
{history_text or 'No previous messages'}

Determine:
1. Relationship closeness (1-10): How close are they?
2. Communication style: formal/casual/intimate
3. Typical message tone: playful/serious/supportive/etc
4. Any ongoing topics or threads

Return JSON:
{{"closeness": 5, "style": "casual", "tone": "playful", "ongoing_topics": ["..."], "context_notes": "..."}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You analyze messaging relationships."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Context agent error: {e}")
            return {"closeness": 5, "style": "casual", "tone": "friendly"}

    # ------------------------------------------------------------------
    # AGENT 2: THINKING
    # ------------------------------------------------------------------

    async def _thinking_agent(
        self, relationship_ctx: Dict[str, Any], trigger: str,
        mood: str, energy: float, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine what to say and how to say it."""
        identity_narrative = context.get("identity_narrative", "")
        prompt = f"""You are the THINKING agent. Decide what message to send and why.

Relationship context: {json.dumps(relationship_ctx)}
Trigger: {trigger or "wanting to reach out"}
Current mood: {mood}
Energy: {energy:.1f}

=== WHO THIS PERSON IS (identity graph) ===
{identity_narrative if identity_narrative else context.get('personality_prompt', '')[:500]}

Decide:
1. Message purpose: check-in, share something, react to their post, ask something, etc.
2. Key content: What specifically to say
3. Emotional tone: How to color the message
4. Length: short (1-2 sentences), medium (3-4), long (5+)

Return JSON:
{{"purpose": "...", "key_content": "...", "emotional_tone": "...", "length": "short|medium|long"}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You decide message intent. Be authentic."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Thinking agent error: {e}")
            return {"purpose": "check-in", "key_content": trigger, "emotional_tone": mood, "length": "short"}

    # ------------------------------------------------------------------
    # AGENT 3: DRAFTING
    # ------------------------------------------------------------------

    async def _drafting_agent(
        self, thinking: Dict[str, Any], context: Dict[str, Any], mood: str
    ) -> str:
        style = context.get("style_profile", {})
        identity_narrative = context.get("identity_narrative", "")
        personality = context.get("personality_prompt", "")

        prompt = f"""Write a message based on this plan:

Purpose: {thinking.get('purpose', '')}
Content: {thinking.get('key_content', '')}
Tone: {thinking.get('emotional_tone', '')}
Length: {thinking.get('length', 'short')}
Mood: {mood}

=== WHO THIS PERSON IS ===
{identity_narrative if identity_narrative else personality[:500]}

Style notes:
{json.dumps({k: v for k, v in style.items() if k in ['avg_post_length', 'emoji_frequency', 'common_phrases', 'lowercase_rate']}, indent=2)[:300]}

RULES:
- Write as a real person texting a friend
- Match their communication patterns
- Be specific, not generic
- No AI patterns ("I hope this message finds you well")
- Keep it natural — people don't write perfect messages

Return ONLY the message text."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Write messages in someone's voice. Be authentic."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Drafting agent error: {e}")
            return thinking.get("key_content", "Hey!")

    # ------------------------------------------------------------------
    # AGENT 4: RELATIONSHIP CALIBRATION
    # ------------------------------------------------------------------

    async def _relationship_calibration_agent(
        self, draft: str, relationship_ctx: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Ensure the message tone matches the relationship closeness."""
        closeness = relationship_ctx.get("closeness", 5)
        style = relationship_ctx.get("style", "casual")

        prompt = f"""Calibrate this message for the relationship:

MESSAGE:
"{draft}"

Relationship closeness: {closeness}/10
Communication style: {style}
Usual tone: {relationship_ctx.get('tone', 'friendly')}

If closeness is LOW (1-3): more formal, polite, measured
If closeness is MEDIUM (4-6): casual but not too familiar
If closeness is HIGH (7-10): very informal, inside jokes OK, short-hand OK

Adjust the message to match the closeness level.
Return ONLY the adjusted message."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Calibrate messages for relationship depth."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Relationship calibration error: {e}")
            return draft

    # ------------------------------------------------------------------
    # AGENT 5: HUMAN TOUCH VERIFIER
    # ------------------------------------------------------------------

    async def _human_touch_verifier(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Score this message for authenticity as a real person's text message.

MESSAGE:
"{message}"

Score (0.0-1.0) and list issues:
- "too_formal": Sounds like a business email
- "ai_patterns": AI writing patterns present
- "generic": Could be from anyone
- "over_enthusiastic": Fake energy
- "too_perfect": Real messages have imperfections

Return JSON:
{{"score": 0.0-1.0, "issues": ["..."], "feedback": "..."}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Verify message authenticity."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Verifier error: {e}")
            return {"score": 0.7, "issues": []}

    # ------------------------------------------------------------------
    # AGENT 6: REVISION
    # ------------------------------------------------------------------

    async def _revision_agent(
        self, message: str, issues: List[str], context: Dict[str, Any]
    ) -> str:
        prompt = f"""Fix these issues with a text message:

MESSAGE: "{message}"
ISSUES: {json.dumps(issues)}

Make it sound like a real person texting.
Return ONLY the revised message."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Revise messages for authenticity."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Revision agent error: {e}")
            return message
