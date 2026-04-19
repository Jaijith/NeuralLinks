"""
Post Insight Analyzer
Deep emotional & relational analysis of user posts using LLM.

Extracts:
- Implied connections (people mentioned or hinted at)
- Emotional threads (feelings, longing, pride, nostalgia)
- Life events (milestones, changes, experiences)

Each insight becomes a potential "conversation thread" that the voice avatar
can bring up ONCE, proactively and naturally, during a voice session.

Tracking ensures:
- pending   → eligible for ONE proactive surfacing
- raised    → avatar brought it up; never surface proactively again
- discussed → user engaged; response summary stored
- deflected → user didn't engage; never surface proactively again

Even after raised/discussed/deflected, the avatar retains the KNOWLEDGE
(connections, facts) permanently so it can engage if the user brings it up.
"""

import json
import logging
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import OPENAI_MODEL

logger = logging.getLogger(__name__)

# How old a post can be and still be eligible for proactive surfacing
MAX_POST_AGE_DAYS = 30


class PostInsightAnalyzer:
    """
    Analyzes user posts for deep personal insights using LLM.

    Collection: ``avatar_post_insights``
    """

    def __init__(self, db: AsyncIOMotorDatabase, openai_client=None):
        self.db = db
        self.openai = openai_client

    # ------------------------------------------------------------------
    # PUBLIC — bulk analysis (for init script)
    # ------------------------------------------------------------------

    async def analyze_user_posts(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze ALL posts for a user that haven't been analyzed yet.
        Uses ``last_analyzed_post_date`` as a watermark.

        Returns summary of what was found.
        """
        # Get watermark
        existing = await self.db.avatar_post_insights.find_one(
            {"user_id": user_id},
            {"last_analyzed_post_date": 1}
        )
        watermark = None
        if existing:
            watermark = existing.get("last_analyzed_post_date")

        # Fetch posts newer than watermark
        filt: Dict[str, Any] = {
            "user_id": user_id,
            "post_type": {"$in": ["real", None]},
        }
        if watermark:
            filt["created_at"] = {"$gt": watermark}

        cursor = self.db.posts.find(
            filt,
            {"_id": 0, "id": 1, "text": 1, "content": 1, "created_at": 1}
        ).sort("created_at", 1).limit(100)
        posts = await cursor.to_list(100)

        if not posts:
            return {"analyzed": 0, "insights": 0, "connections": 0}

        # Batch posts into chunks of ~10 for efficient LLM calls
        all_insights: List[Dict[str, Any]] = []
        batch_size = 10
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            insights = await self._analyze_post_batch(user_id, batch)
            all_insights.extend(insights)

        # Store insights
        connections_written = 0
        for insight in all_insights:
            await self._store_insight(user_id, insight)
            # Write discovered connections to graph_nodes + users.connections
            if insight.get("type") == "connection":
                written = await self._write_connection(user_id, insight)
                if written:
                    connections_written += 1

        # Update watermark
        latest_date = posts[-1].get("created_at", datetime.now(timezone.utc).isoformat())
        await self.db.avatar_post_insights.update_one(
            {"user_id": user_id},
            {
                "$set": {"last_analyzed_post_date": latest_date},
                "$setOnInsert": {"user_id": user_id},
            },
            upsert=True,
        )

        return {
            "analyzed": len(posts),
            "insights": len(all_insights),
            "connections": connections_written,
        }

    # ------------------------------------------------------------------
    # PUBLIC — single post (for background trigger on new post)
    # ------------------------------------------------------------------

    async def analyze_single_post(self, user_id: str, post_id: str, post_text: str, post_date: str = ""):
        """
        Analyze a single newly created post (called as background task).
        """
        if not post_text or len(post_text.strip()) < 10:
            return

        try:
            insights = await self._analyze_post_batch(user_id, [{
                "id": post_id,
                "text": post_text,
                "created_at": post_date or datetime.now(timezone.utc).isoformat(),
            }])

            for insight in insights:
                await self._store_insight(user_id, insight)
                if insight.get("type") == "connection":
                    await self._write_connection(user_id, insight)

            # Update watermark
            await self.db.avatar_post_insights.update_one(
                {"user_id": user_id},
                {
                    "$set": {"last_analyzed_post_date": post_date or datetime.now(timezone.utc).isoformat()},
                    "$setOnInsert": {"user_id": user_id},
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Error analyzing single post for {user_id}: {e}")

    # ------------------------------------------------------------------
    # PUBLIC — get threads for voice prompt (only pending, <30 days)
    # ------------------------------------------------------------------

    async def get_conversation_threads(self, user_id: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Return insights eligible for proactive surfacing in voice.

        Only returns:
        - status == "pending"
        - post_date < 30 days old
        - sorted by priority desc
        - max ``limit`` items
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_POST_AGE_DAYS)).isoformat()

        doc = await self.db.avatar_post_insights.find_one(
            {"user_id": user_id},
            {"insights": 1}
        )
        if not doc:
            return []

        insights = doc.get("insights", [])

        eligible = []
        for ins in insights:
            if ins.get("status") != "pending":
                continue
            pd = ins.get("post_date", "")
            if isinstance(pd, str) and pd < cutoff:
                continue  # too old
            eligible.append(ins)

        # Sort by priority descending
        eligible.sort(key=lambda x: x.get("thread", {}).get("priority", 0), reverse=True)
        return eligible[:limit]

    # ------------------------------------------------------------------
    # PUBLIC — mark thread as raised (called after voice prompt is built)
    # ------------------------------------------------------------------

    async def mark_threads_raised(self, user_id: str, insight_ids: List[str], session_id: str):
        """Mark insights as raised (proactively surfaced in a voice session)."""
        now = datetime.now(timezone.utc).isoformat()
        for iid in insight_ids:
            await self.db.avatar_post_insights.update_one(
                {"user_id": user_id, "insights.id": iid},
                {
                    "$set": {
                        "insights.$.status": "raised",
                        "insights.$.raised_at": now,
                        "insights.$.session_id": session_id,
                    }
                }
            )

    # ------------------------------------------------------------------
    # PUBLIC — update thread status after conversation
    # ------------------------------------------------------------------

    async def update_thread_statuses(
        self,
        user_id: str,
        session_id: str,
        conversation_text: str,
        openai_client=None,
    ):
        """
        After a voice conversation, check if any 'raised' threads were
        discussed or deflected. Update status accordingly.
        """
        client = openai_client or self.openai
        doc = await self.db.avatar_post_insights.find_one(
            {"user_id": user_id}, {"insights": 1}
        )
        if not doc:
            return

        raised = [
            ins for ins in doc.get("insights", [])
            if ins.get("status") == "raised" and ins.get("session_id") == session_id
        ]

        if not raised:
            return

        conv_lower = conversation_text.lower()

        for ins in raised:
            topic = ins.get("discovery", {}).get("topic", "")
            post_text = ins.get("post_text", "")

            # Simple keyword matching first
            topic_words = set(re.findall(r'\w+', topic.lower())) - {"the", "a", "an", "is", "was", "and", "or", "of", "to", "in"}
            post_words = set(re.findall(r'\w+', post_text.lower())) - {"the", "a", "an", "is", "was", "and", "or", "of", "to", "in", "i"}

            significant_words = topic_words | post_words
            matches = sum(1 for w in significant_words if len(w) > 3 and w in conv_lower)

            if matches >= 2:
                # Likely discussed — use LLM to confirm & summarize
                if client:
                    summary = await self._get_discussion_summary(client, conversation_text, topic, post_text)
                    if summary:
                        await self._set_thread_status(user_id, ins["id"], "discussed", summary)
                    else:
                        await self._set_thread_status(user_id, ins["id"], "deflected")
                else:
                    await self._set_thread_status(user_id, ins["id"], "discussed", "User engaged with the topic.")
            else:
                # Not discussed — mark as deflected (avatar raised but user didn't engage)
                await self._set_thread_status(user_id, ins["id"], "deflected")

    # ------------------------------------------------------------------
    # PRIVATE — LLM analysis
    # ------------------------------------------------------------------

    async def _analyze_post_batch(
        self, user_id: str, posts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract deep insights from a batch of posts."""
        if not self.openai:
            return []

        post_texts = []
        for p in posts:
            text = p.get("text") or p.get("content") or ""
            if text and len(text.strip()) > 5:
                post_texts.append({
                    "post_id": p.get("id", ""),
                    "text": text[:500],
                    "date": str(p.get("created_at", "")),
                })

        if not post_texts:
            return []

        prompt = """You are an EMOTIONAL INTELLIGENCE agent. Analyze these social media posts from ONE person and extract deep personal insights.

For each post that reveals something meaningful, extract:

1. **Connections**: People mentioned or implied (even without names).
   - "Missing this guy" → likely a child, partner, or close friend they're separated from
   - "Mom's cooking" → has a mother they're nostalgic about
   - "This gang" → has a friend group
   
2. **Emotional threads**: Strong emotions that deserve gentle attention.
   - Sadness, longing, guilt, pride, joy, nostalgia, frustration
   - Only extract emotions that are GENUINE and DEEP, not casual
   
3. **Life events**: Significant happenings in their life.
   - New project, moving, celebration, loss, achievement

For emotional threads, generate a NATURAL, WARM question the avatar could ask.
The question should:
- Feel like it comes from someone who genuinely cares
- Not sound like an interrogation or a survey
- Acknowledge the emotion first, then invite them to share
- Be something a loving partner or best friend would say

POSTS:
{posts}

Return JSON:
{{
  "insights": [
    {{
      "post_id": "...",
      "post_text": "exact post text",
      "type": "connection" | "emotional" | "life_event",
      "discovery": {{
        "topic": "brief description of what was discovered",
        "emotion": "the primary emotion (or null for life_events)",
        "implied_connection": {{
          "name_hint": "name or 'unknown'",
          "relationship": "son/mother/friend/partner/colleague/etc",
          "evidence": "why you think this"
        }} or null,
        "life_event": "description" or null
      }},
      "thread": {{
        "natural_opener": "a warm, natural way the avatar could bring this up",
        "priority": 0.0-1.0,
        "sensitivity": "high" | "medium" | "low",
        "approach": "gentle_empathy" | "celebrate" | "curious" | "playful" | "supportive"
      }}
    }}
  ]
}}

RULES:
- Only extract insights that are MEANINGFUL. Skip generic/shallow posts.
- A post about architecture technique = skip (not personal)
- A post about missing someone = extract (deeply personal)
- A post about mom's food = extract (connection + nostalgia)
- A post celebrating an achievement = extract (life event + pride)
- Priority should reflect emotional depth: missing a child > new project > random thought
- If a post has BOTH a connection AND an emotion, create separate insights for each
- Be conservative — only extract what's clearly there, don't over-interpret"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Extract deep personal insights from posts with emotional intelligence."},
                    {"role": "user", "content": prompt.format(posts=json.dumps(post_texts, indent=2))}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            insights = result.get("insights", [])

            # Enrich each insight with metadata
            for ins in insights:
                ins["id"] = f"insight_{uuid.uuid4().hex[:12]}"
                ins["status"] = "pending"
                ins["raised_at"] = None
                ins["discussed_at"] = None
                ins["session_id"] = None
                ins["user_response_summary"] = None
                # Find the matching post date
                pid = ins.get("post_id", "")
                for p in post_texts:
                    if p["post_id"] == pid:
                        ins["post_date"] = p["date"]
                        break
                else:
                    ins["post_date"] = datetime.now(timezone.utc).isoformat()

            return insights

        except Exception as e:
            logger.error(f"Post insight analysis error: {e}")
            return []

    # ------------------------------------------------------------------
    # PRIVATE — storage
    # ------------------------------------------------------------------

    async def _store_insight(self, user_id: str, insight: Dict[str, Any]):
        """Store a single insight, avoiding duplicates by post_id + type."""
        post_id = insight.get("post_id", "")
        ins_type = insight.get("type", "")

        # Check for existing insight on same post + type
        existing = await self.db.avatar_post_insights.find_one(
            {
                "user_id": user_id,
                "insights": {
                    "$elemMatch": {
                        "post_id": post_id,
                        "type": ins_type,
                    }
                }
            }
        )

        if existing:
            # Already have insight for this post+type, skip
            return

        await self.db.avatar_post_insights.update_one(
            {"user_id": user_id},
            {
                "$push": {"insights": insight},
                "$setOnInsert": {"user_id": user_id},
            },
            upsert=True,
        )

    async def _write_connection(self, user_id: str, insight: Dict[str, Any]) -> bool:
        """
        Write a discovered connection to users.connections and graph_nodes.
        Returns True if a new connection was written.
        """
        discovery = insight.get("discovery", {})
        conn = discovery.get("implied_connection")
        if not conn:
            return False

        relationship = conn.get("relationship", "").strip()
        name_hint = conn.get("name_hint", "unknown").strip()
        evidence = conn.get("evidence", "")

        if not relationship:
            return False

        # Use relationship as label if name is unknown
        display_name = name_hint if name_hint and name_hint.lower() != "unknown" else f"({relationship})"
        label = display_name.lower()

        now = datetime.now(timezone.utc)

        # Check if connection already exists in users.connections
        existing_user = await self.db.users.find_one({
            "id": user_id,
            "connections.relationship": {"$regex": relationship, "$options": "i"}
        })

        if not existing_user:
            # Add to users.connections
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$push": {
                        "connections": {
                            "name": display_name,
                            "relationship": relationship,
                            "details": f"Discovered from post: {evidence}",
                            "source": "post_analysis",
                            "discovered_at": now.isoformat(),
                        }
                    }
                }
            )

        # Check if exists in graph_nodes
        existing_node = await self.db.graph_nodes.find_one({
            "user_id": user_id,
            "node_type": "connection",
            "properties.relationship": {"$regex": relationship, "$options": "i"},
        })

        if not existing_node:
            from domain.memory.bayesian import add_bayesian_defaults
            node_id = f"connection_{user_id}_{relationship.replace(' ', '_')}"
            node = {
                "id": node_id,
                "user_id": user_id,
                "node_type": "connection",
                "label": label,
                "display_label": display_name,
                "strength": 0.8,
                "properties": {
                    "relationship": relationship,
                    "source": "post_analysis",
                    "evidence": evidence,
                    "name_hint": name_hint,
                },
                "mention_count": 1,
                "created_at": now,
                "updated_at": now,
            }
            add_bayesian_defaults(node, prior="uninformative", source="post_analysis")
            await self.db.graph_nodes.insert_one(node)
            return True

        return False

    async def _set_thread_status(
        self, user_id: str, insight_id: str, status: str, summary: str = None
    ):
        """Update thread status."""
        update: Dict[str, Any] = {
            "insights.$.status": status,
        }
        if status == "discussed":
            update["insights.$.discussed_at"] = datetime.now(timezone.utc).isoformat()
            if summary:
                update["insights.$.user_response_summary"] = summary
        elif status == "deflected":
            update["insights.$.discussed_at"] = datetime.now(timezone.utc).isoformat()

        await self.db.avatar_post_insights.update_one(
            {"user_id": user_id, "insights.id": insight_id},
            {"$set": update}
        )

    async def _get_discussion_summary(
        self, openai_client, conversation: str, topic: str, post_text: str
    ) -> Optional[str]:
        """Use LLM to check if a topic was discussed and summarize the response."""
        try:
            prompt = f"""Did the user discuss this topic during the conversation? 
Topic: {topic}
Related post: "{post_text}"

Conversation excerpt (last 3000 chars):
{conversation[-3000:]}

If the user engaged with this topic (talked about it, answered questions about it, shared more details), return a brief summary of what they said.
If the user avoided the topic, changed subject, or it wasn't brought up, return null.

Return JSON: {{"discussed": true/false, "summary": "brief summary of what user shared" or null}}"""

            response = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Detect if a topic was discussed in conversation."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            result = json.loads(response.choices[0].message.content)
            if result.get("discussed"):
                return result.get("summary", "User engaged with the topic.")
            return None
        except Exception as e:
            logger.error(f"Discussion summary error: {e}")
            return None
