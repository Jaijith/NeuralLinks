"""
Conversation Recall Service
Multi-layer search across past voice conversations and chat messages.

Layers (fastest → most thorough):
1. conversation_index (MongoDB) — lightweight summaries + S3 keys
2. episodic_memory — deeper summaries with emotional data
3. S3 voice transcripts — full transcript retrieval when needed
4. chat_conversations — if it was a text message context

The conversation_index collection stores:
{
    "user_id": str,
    "avatar_id": str,
    "session_id": str,
    "s3_key": str,               # ← for full transcript retrieval
    "summary": str,              # short summary
    "topics": [str],
    "people_mentioned": [str],
    "emotional_tone": str,
    "key_quotes": [str],         # notable phrases from user
    "timestamp": datetime,
    "duration_seconds": int,
}
"""
import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET', '')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-west-2')


class ConversationRecallService:
    """
    Searches past conversations using a multi-layer strategy.
    Used by the voice MCP tool `recall_past_conversations` and
    the `/api/voice/recall` endpoint.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._s3_client = None

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client('s3', region_name=AWS_S3_REGION)
        return self._s3_client

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    async def recall(
        self,
        user_id: str,
        query: str,
        avatar_id: Optional[str] = None,
        limit: int = 5,
        include_full_transcript: bool = False,
    ) -> Dict[str, Any]:
        """
        Search past conversations for a query.
        Returns summaries and optionally full transcript snippets.

        Args:
            user_id: The user to search for
            query: Natural language query (e.g. "when did we talk about Japan trip?")
            avatar_id: Optional filter by avatar
            limit: Maximum results
            include_full_transcript: Whether to fetch S3 transcripts for matching conversations

        Returns:
            {
                "results": [...],
                "total_found": int,
                "sources_searched": [str],
            }
        """
        results: List[Dict[str, Any]] = []
        sources: List[str] = []

        # --- Layer 1: conversation_index (fast, has S3 keys) ---
        index_results = await self._search_conversation_index(user_id, query, avatar_id, limit)
        if index_results:
            results.extend(index_results)
            sources.append("conversation_index")

        # --- Layer 2: episodic_memory (deeper context) ---
        if len(results) < limit:
            ep_results = await self._search_episodic_memory(
                user_id, query, avatar_id, limit - len(results)
            )
            # Deduplicate by session_id
            existing_sessions = {r.get("session_id") for r in results}
            for er in ep_results:
                if er.get("session_id") not in existing_sessions:
                    results.append(er)
            sources.append("episodic_memory")

        # --- Layer 3: Full transcript retrieval (if requested and S3 keys available) ---
        if include_full_transcript:
            for r in results:
                s3_key = r.get("s3_key")
                if s3_key:
                    transcript_text = await self._fetch_transcript_from_s3(s3_key)
                    if transcript_text:
                        relevant = self._extract_relevant_snippets(transcript_text, query)
                        r["relevant_snippets"] = relevant
                        sources.append("s3_transcripts") if "s3_transcripts" not in sources else None

        return {
            "results": results[:limit],
            "total_found": len(results),
            "sources_searched": sources,
        }

    # ------------------------------------------------------------------
    # LAYER 1: Conversation Index
    # ------------------------------------------------------------------

    async def _search_conversation_index(
        self, user_id: str, query: str, avatar_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Search the lightweight conversation_index collection."""
        try:
            query_words = set(query.lower().split())

            # Build filter
            filt: Dict[str, Any] = {"user_id": user_id}
            if avatar_id:
                filt["avatar_id"] = avatar_id

            # Text search across summary, topics, people, key_quotes
            # Use regex for fuzzy matching on meaningful words
            meaningful_words = [w for w in query_words if len(w) > 2]
            if meaningful_words:
                or_conditions = []
                for word in meaningful_words[:5]:  # limit to 5 words for perf
                    pattern = re.escape(word)
                    or_conditions.extend([
                        {"summary": {"$regex": pattern, "$options": "i"}},
                        {"topics": {"$regex": pattern, "$options": "i"}},
                        {"people_mentioned": {"$regex": pattern, "$options": "i"}},
                        {"key_quotes": {"$regex": pattern, "$options": "i"}},
                    ])
                filt["$or"] = or_conditions

            cursor = self.db.conversation_index.find(
                filt,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            results = await cursor.to_list(limit)

            return [
                {
                    "session_id": r.get("session_id"),
                    "summary": r.get("summary", ""),
                    "topics": r.get("topics", []),
                    "people_mentioned": r.get("people_mentioned", []),
                    "emotional_tone": r.get("emotional_tone", ""),
                    "timestamp": r.get("timestamp"),
                    "duration_seconds": r.get("duration_seconds", 0),
                    "s3_key": r.get("s3_key", ""),
                    "key_quotes": r.get("key_quotes", []),
                    "source": "conversation_index",
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error searching conversation_index: {e}")
            return []

    # ------------------------------------------------------------------
    # LAYER 2: Episodic Memory
    # ------------------------------------------------------------------

    async def _search_episodic_memory(
        self, user_id: str, query: str, avatar_id: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Search the richer episodic_memory collection."""
        try:
            filt: Dict[str, Any] = {
                "user_id": user_id,
                "episode_type": "voice_conversation",
            }
            if avatar_id:
                filt["avatar_id"] = avatar_id

            meaningful_words = [w for w in query.lower().split() if len(w) > 2]
            if meaningful_words:
                or_conditions = []
                for word in meaningful_words[:5]:
                    pattern = re.escape(word)
                    or_conditions.extend([
                        {"summary": {"$regex": pattern, "$options": "i"}},
                        {"topics": {"$regex": pattern, "$options": "i"}},
                    ])
                filt["$or"] = or_conditions

            cursor = self.db.episodic_memory.find(
                filt,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            results = await cursor.to_list(limit)

            return [
                {
                    "session_id": r.get("episode_id", ""),
                    "summary": r.get("summary", ""),
                    "topics": r.get("topics", []),
                    "emotional_tone": r.get("emotional_tone", ""),
                    "timestamp": r.get("timestamp"),
                    "significance": r.get("significance", 0.5),
                    "s3_key": r.get("s3_key", ""),
                    "source": "episodic_memory",
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error searching episodic_memory: {e}")
            return []

    # ------------------------------------------------------------------
    # LAYER 3: S3 Full Transcript Retrieval
    # ------------------------------------------------------------------

    async def _fetch_transcript_from_s3(self, s3_key: str) -> Optional[str]:
        """Fetch a full transcript from S3 and return as text."""
        try:
            if not AWS_S3_BUCKET or not s3_key:
                return None
            response = self.s3_client.get_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
            body = response['Body'].read().decode('utf-8')
            data = json.loads(body)
            messages = data.get("messages", [])
            # Format as readable conversation
            lines = []
            for msg in messages:
                role = msg.get("role", "unknown")
                text = msg.get("text", msg.get("content", ""))
                if text:
                    speaker = "User" if role in ("user", "human") else "Avatar"
                    lines.append(f"{speaker}: {text}")
            return "\n".join(lines)
        except ClientError as e:
            logger.error(f"S3 fetch error for {s3_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading transcript from S3: {e}")
            return None

    def _extract_relevant_snippets(self, transcript_text: str, query: str, context_lines: int = 3) -> List[str]:
        """Extract the most relevant snippets from a full transcript."""
        if not transcript_text:
            return []

        lines = transcript_text.split("\n")
        query_words = set(query.lower().split())
        meaningful = {w for w in query_words if len(w) > 2}

        scored_ranges = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            score = sum(1 for w in meaningful if w in line_lower)
            if score > 0:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                scored_ranges.append((score, start, end))

        # Merge overlapping ranges, take top 3
        scored_ranges.sort(key=lambda x: x[0], reverse=True)
        snippets = []
        used_lines: set = set()
        for score, start, end in scored_ranges[:3]:
            snippet_lines = []
            for j in range(start, end):
                if j not in used_lines:
                    snippet_lines.append(lines[j])
                    used_lines.add(j)
            if snippet_lines:
                snippets.append("\n".join(snippet_lines))

        return snippets

    # ------------------------------------------------------------------
    # INDEX POPULATION (called by Memory Orchestrator)
    # ------------------------------------------------------------------

    async def index_conversation(
        self,
        user_id: str,
        avatar_id: str,
        session_id: str,
        s3_key: str,
        summary: str,
        topics: List[str],
        people_mentioned: List[str],
        emotional_tone: str,
        key_quotes: List[str],
        duration_seconds: int,
        timestamp: Optional[datetime] = None,
    ):
        """
        Add or update a conversation in the conversation_index.
        Called by the Memory Orchestrator after processing a transcript.
        """
        doc = {
            "user_id": user_id,
            "avatar_id": avatar_id,
            "session_id": session_id,
            "s3_key": s3_key,
            "summary": summary,
            "topics": topics,
            "people_mentioned": people_mentioned,
            "emotional_tone": emotional_tone,
            "key_quotes": key_quotes,
            "duration_seconds": duration_seconds,
            "timestamp": timestamp or datetime.now(timezone.utc),
        }
        await self.db.conversation_index.update_one(
            {"session_id": session_id},
            {"$set": doc},
            upsert=True,
        )
        logger.info(f"Indexed conversation {session_id} for user {user_id}")
