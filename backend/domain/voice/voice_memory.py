"""
Voice Memory Service
Handles transcript storage, memory extraction, and retrieval for voice conversations.

Flow:
1. Transcript saved to S3 on call end (fire-and-forget)
2. Background Lambda extracts memories using LLM
3. Memories stored in existing collections (identity_memory, users.connections, episodic_memory)
4. Memories loaded at session start (parallel, with timeout)
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import boto3
from botocore.exceptions import ClientError

from core.config import OPENAI_MODEL

logger = logging.getLogger(__name__)

# S3 Configuration
AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET', '')
AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-west-2')
TRANSCRIPT_PREFIX = 'voice-transcripts'


class VoiceMemoryService:
    """
    Service for managing voice conversation memories.
    
    Responsibilities:
    - Store transcripts to S3
    - Retrieve user's memory (connections, interests, facts)
    - Format memory for voice prompts
    - Check for unprocessed transcripts
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._s3_client = None
    
    @property
    def s3_client(self):
        """Lazy-load S3 client"""
        if self._s3_client is None:
            self._s3_client = boto3.client('s3', region_name=AWS_S3_REGION)
        return self._s3_client
    
    # =========================================================================
    # TRANSCRIPT STORAGE
    # =========================================================================
    
    async def save_transcript(
        self,
        session_id: str,
        user_id: str,
        avatar_id: str,
        messages: List[Dict[str, Any]],
        started_at: str,
        ended_at: str,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Save transcript to S3 (called immediately when call ends).
        
        Returns immediately - this is fire-and-forget.
        """
        try:
            transcript = {
                "session_id": session_id,
                "user_id": user_id,
                "avatar_id": avatar_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": duration_seconds,
                "messages": messages,
                "processed": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # S3 key: voice-transcripts/{user_id}/{session_id}.json
            s3_key = f"{TRANSCRIPT_PREFIX}/{user_id}/{session_id}.json"
            
            # Store in S3
            self.s3_client.put_object(
                Bucket=AWS_S3_BUCKET,
                Key=s3_key,
                Body=json.dumps(transcript),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Transcript saved: s3://{AWS_S3_BUCKET}/{s3_key}")
            
            # Also track in MongoDB for quick lookup
            await self.db.voice_transcripts.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "avatar_id": avatar_id,
                        "s3_key": s3_key,
                        "processed": False,
                        "duration_seconds": duration_seconds,
                        "created_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            return {"success": True, "s3_key": s3_key}
            
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_unprocessed_transcripts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of unprocessed transcripts for a user.
        Called at session start to check if background processing needed.
        """
        try:
            cursor = self.db.voice_transcripts.find({
                "user_id": user_id,
                "processed": False
            }).limit(10)
            
            return await cursor.to_list(length=10)
            
        except Exception as e:
            logger.error(f"Error fetching unprocessed transcripts: {e}")
            return []
    
    async def mark_transcript_processed(self, session_id: str):
        """Mark a transcript as processed after memory extraction"""
        try:
            await self.db.voice_transcripts.update_one(
                {"session_id": session_id},
                {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}}
            )
        except Exception as e:
            logger.error(f"Error marking transcript processed: {e}")
    
    # =========================================================================
    # MEMORY RETRIEVAL (for session start)
    # =========================================================================
    
    async def get_user_memory(self, user_id: str, avatar_id: str) -> Dict[str, Any]:
        """
        Get user's COMPREHENSIVE memory for voice prompt.
        
        Enhanced to load:
        - users.connections → ALL people (not limited to 5)
        - graph_nodes → ALL interests with strength scores
        - identity_memory → Facts and preferences from voice
        - episodic_memory → 10 recent conversation summaries (not 3)
        - posts → 10 most recent real posts for context
        
        Called at session start, must be FAST (<3s timeout).
        """
        try:
            # Fetch ALL sources in parallel
            results = await asyncio.gather(
                self._get_user_connections(user_id),
                self._get_identity_memory(user_id, avatar_id),
                self._get_all_interests_from_graph(user_id),
                self._get_recent_conversation_summaries(user_id, avatar_id, limit=10),
                self._get_user_recent_posts(user_id, limit=10),
                return_exceptions=True
            )
            
            connections = results[0] if not isinstance(results[0], Exception) else []
            identity = results[1] if not isinstance(results[1], Exception) else {}
            graph_interests = results[2] if not isinstance(results[2], Exception) else []
            summaries = results[3] if not isinstance(results[3], Exception) else []
            recent_posts = results[4] if not isinstance(results[4], Exception) else []
            
            # Merge interests: graph_nodes (comprehensive) + identity_memory (voice-extracted)
            voice_interests = identity.get("interests", [])
            merged_interests = self._merge_interests(graph_interests, voice_interests)
            
            return {
                "connections": connections,
                "interests": merged_interests,
                "facts": identity.get("facts", []),
                "preferences": identity.get("preferences", []),
                "recent_conversations": summaries,
                "recent_posts": recent_posts,
            }
            
        except Exception as e:
            logger.error(f"Error fetching user memory: {e}")
            return {}
    
    async def _get_all_interests_from_graph(self, user_id: str) -> List[Dict[str, Any]]:
        """Get ALL interests from graph_nodes, sorted by Bayesian salience/strength."""
        try:
            cursor = self.db.graph_nodes.find(
                {
                    "user_id": user_id,
                    "node_type": "interest",
                    "status": {"$nin": ["archived", "rejected"]},
                },
                {
                    "_id": 0, "label": 1, "strength": 1, "belief_strength": 1,
                    "salience": 1, "properties": 1, "mention_count": 1,
                    "narrative_descriptor": 1, "status": 1,
                },
            ).sort("salience", -1).limit(50)
            results = await cursor.to_list(50)
            results.sort(
                key=lambda n: n.get("salience") or n.get("belief_strength") or n.get("strength") or 0,
                reverse=True,
            )
            return results
        except Exception as e:
            logger.error(f"Error fetching graph interests: {e}")
            return []
    
    async def _get_user_recent_posts(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent real posts for voice context."""
        try:
            cursor = self.db.posts.find(
                {"user_id": user_id, "post_type": {"$in": ["real", None]}},
                {"_id": 0, "text": 1, "created_at": 1, "likes": 1, "comment_count": 1}
            ).sort("created_at", -1).limit(limit)
            return await cursor.to_list(limit)
        except Exception as e:
            logger.error(f"Error fetching recent posts: {e}")
            return []
    
    def _merge_interests(
        self,
        graph_interests: List[Dict[str, Any]],
        voice_interests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge graph-sourced and voice-sourced interests, de-duplicating."""
        seen = {}
        merged = []
        
        # Graph interests take priority (they have strength scores)
        for gi in graph_interests:
            label = (gi.get("label") or "").lower()
            if label and label not in seen:
                seen[label] = True
                merged.append({
                    "label": gi.get("label", ""),
                    "topic": gi.get("label", ""),
                    "strength": gi.get("strength", 0.5),
                    "source": "graph",
                })
        
        # Add voice interests not already in graph
        for vi in voice_interests:
            topic = (vi.get("topic") or "").lower()
            if topic and topic not in seen:
                seen[topic] = True
                merged.append({
                    "label": vi.get("topic", ""),
                    "topic": vi.get("topic", ""),
                    "strength": vi.get("strength", 0.6),
                    "source": "voice",
                })
        
        # Sort by strength descending
        merged.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return merged
    
    async def _get_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's network connections (people they've mentioned)"""
        try:
            user = await self.db.users.find_one(
                {"id": user_id},
                {"connections": 1}
            )
            return user.get("connections", []) if user else []
        except Exception as e:
            logger.error(f"Error fetching user connections: {e}")
            return []
    
    async def _get_identity_memory(self, user_id: str, avatar_id: str) -> Dict[str, Any]:
        """Get identity memory (interests, facts, preferences)"""
        try:
            memory = await self.db.identity_memory.find_one({
                "user_id": user_id,
                "avatar_id": avatar_id
            })
            return memory or {}
        except Exception as e:
            logger.error(f"Error fetching identity memory: {e}")
            return {}
    
    async def _get_recent_conversation_summaries(
        self, 
        user_id: str, 
        avatar_id: str, 
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get recent conversation summaries from episodic memory"""
        try:
            cursor = self.db.episodic_memory.find({
                "user_id": user_id,
                "avatar_id": avatar_id,
                "episode_type": "voice_conversation"
            }).sort("timestamp", -1).limit(limit)
            
            summaries = await cursor.to_list(length=limit)
            return [
                {
                    "date": s.get("timestamp", ""),
                    "summary": s.get("summary", ""),
                    "topics": s.get("topics", []),
                    "emotional_tone": s.get("emotional_tone", "")
                }
                for s in summaries
            ]
        except Exception as e:
            logger.error(f"Error fetching conversation summaries: {e}")
            return []
    
    # =========================================================================
    # FORMAT FOR PROMPT
    # =========================================================================
    
    def format_memory_for_prompt(
        self, 
        memory: Dict[str, Any],
        user_name: str
    ) -> str:
        """
        Format ALL memory as natural language for the voice prompt.
        
        Enhanced: no artificial limits on connections/interests.
        Groups connections by relationship type, interests by strength tier.
        Includes recent posts and expanded conversation history.
        """
        if not memory:
            return ""
        
        sections = []
        
        # ----- Connections (ALL, grouped by relationship) -----
        connections = memory.get("connections", [])
        if connections:
            family_kw = {"wife", "husband", "daughter", "son", "mother", "father",
                         "sister", "brother", "parent", "child", "spouse", "partner",
                         "mom", "dad"}
            friend_kw = {"friend", "best friend", "close friend", "college friend", "buddy"}
            work_kw = {"colleague", "coworker", "boss", "manager", "teammate", "mentor"}
            
            def _classify(c):
                r = (c.get("relationship") or "").lower()
                if any(k in r for k in family_kw):
                    return "family"
                if any(k in r for k in friend_kw):
                    return "friends"
                if any(k in r for k in work_kw):
                    return "work"
                return "other"
            
            groups: Dict[str, list] = {"family": [], "friends": [], "work": [], "other": []}
            for c in connections:
                groups[_classify(c)].append(c)
            
            conn_text = f"**People in {user_name}'s life:**\n"
            for label, members in [("Family", groups["family"]),
                                    ("Friends", groups["friends"]),
                                    ("Work", groups["work"]),
                                    ("Others", groups["other"])]:
                if members:
                    parts = []
                    for m in members:
                        name = m.get("name", "")
                        rel = m.get("relationship", "")
                        det = m.get("details", "")
                        entry = f"{name} ({rel})" if rel else name
                        if det:
                            entry += f" — {det}"
                        parts.append(entry)
                    conn_text += f"  {label}: {', '.join(parts)}\n"
            sections.append(conn_text.rstrip())
        
        # ----- Interests (ALL, tiered by strength) -----
        interests = memory.get("interests", [])
        if interests:
            core = [i for i in interests if i.get("strength", 0) >= 0.8]
            strong = [i for i in interests if 0.5 <= i.get("strength", 0) < 0.8]
            casual = [i for i in interests if i.get("strength", 0) < 0.5]
            
            def _label(i):
                return i.get("label", i.get("topic", ""))
            
            interest_text = f"**{user_name}'s interests:**\n"
            if core:
                interest_text += f"  Core passions: {', '.join(_label(i) for i in core)}\n"
            if strong:
                interest_text += f"  Strong interests: {', '.join(_label(i) for i in strong)}\n"
            if casual:
                interest_text += f"  Also into: {', '.join(_label(i) for i in casual[:15])}\n"
            sections.append(interest_text.rstrip())
        
        # ----- Key facts (expanded) -----
        facts = memory.get("facts", [])
        if facts:
            fact_lines = []
            for f in facts[:15]:
                ft = f.get("fact", "") if isinstance(f, dict) else str(f)
                if ft:
                    fact_lines.append(f"  - {ft}")
            if fact_lines:
                sections.append(f"**Things you know about {user_name}:**\n" + "\n".join(fact_lines))
        
        # ----- Preferences -----
        prefs = memory.get("preferences", [])
        if prefs:
            pref_lines = []
            for p in prefs[:10]:
                pt = p.get("preference", "") if isinstance(p, dict) else str(p)
                if pt:
                    pref_lines.append(f"  - {pt}")
            if pref_lines:
                sections.append(f"**{user_name}'s preferences:**\n" + "\n".join(pref_lines))
        
        # ----- Recent posts (what they've been sharing) -----
        posts = memory.get("recent_posts", [])
        if posts:
            post_snippets = [p.get("text", "")[:150] for p in posts[:5] if p.get("text")]
            if post_snippets:
                post_lines = [f'  - "{s}..."' if len(s) >= 150 else f'  - "{s}"'
                              for s in post_snippets]
                sections.append(
                    f"**What {user_name} has been posting recently:**\n" + "\n".join(post_lines)
                )
        
        # ----- Recent conversations (expanded from 2 to 10) -----
        recent = memory.get("recent_conversations", [])
        if recent:
            conv_lines = []
            for conv in recent[:10]:
                summary = conv.get("summary", "")
                if summary:
                    conv_lines.append(f"  - {summary}")
            if conv_lines:
                sections.append(
                    f"**Your recent conversations with {user_name}:**\n" + "\n".join(conv_lines)
                )
        
        return "\n\n".join(sections) if sections else ""
    
    # =========================================================================
    # MEMORY EXTRACTION (called by background Lambda)
    # =========================================================================
    
    async def extract_and_store_memories(
        self,
        session_id: str,
        openai_client: Any
    ) -> Dict[str, Any]:
        """
        Extract memories from a transcript using LLM and store in appropriate collections.
        
        This is called by the background Lambda after a call ends.
        """
        try:
            # Get transcript metadata from MongoDB
            transcript_meta = await self.db.voice_transcripts.find_one({"session_id": session_id})
            if not transcript_meta:
                return {"success": False, "error": "Transcript not found"}
            
            # Get full transcript from S3
            s3_key = transcript_meta.get("s3_key")
            response = self.s3_client.get_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
            transcript = json.loads(response['Body'].read().decode('utf-8'))
            
            user_id = transcript.get("user_id")
            avatar_id = transcript.get("avatar_id")
            messages = transcript.get("messages", [])
            
            if not messages:
                await self.mark_transcript_processed(session_id)
                return {"success": True, "extracted": False, "reason": "No messages"}
            
            # Format conversation for LLM
            conversation_text = self._format_messages_for_extraction(messages)
            
            # Extract memories using LLM
            extracted = await self._extract_with_llm(conversation_text, openai_client)
            
            if extracted:
                # Use agentic orchestrator for more accurate CRUD operations
                # Enhanced: pass session_id, s3_key, duration for conversation indexing
                try:
                    from domain.voice.memory_orchestrator import MemoryOrchestrator
                    
                    orchestrator = MemoryOrchestrator(self.db, openai_client)
                    result = await orchestrator.process_conversation(
                        user_id=user_id,
                        avatar_id=avatar_id,
                        conversation=conversation_text,
                        session_id=session_id,
                        s3_key=s3_key or "",
                        duration_seconds=transcript.get("duration_seconds", 0),
                    )
                    
                    if result.success:
                        logger.info(f"Orchestrator: {len(result.actions_executed)} actions executed, "
                                   f"{len(result.actions_rejected)} rejected")
                    else:
                        logger.warning(f"Orchestrator failed: {result.errors}")
                        # Fallback to legacy extraction
                        await self._legacy_store(user_id, avatar_id, extracted)
                        
                except Exception as e:
                    logger.warning(f"Orchestrator error, using legacy: {e}")
                    # Fallback to legacy extraction
                    await self._legacy_store(user_id, avatar_id, extracted)
                
                # Always store episodic memory
                await self._store_episodic_memory(user_id, avatar_id, session_id, extracted)
            
            # Mark as processed
            await self.mark_transcript_processed(session_id)
            
            return {"success": True, "extracted": True, "data": extracted}
            
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            return {"success": False, "error": str(e)}
    
    async def _legacy_store(self, user_id: str, avatar_id: str, extracted: Dict[str, Any]):
        """Legacy storage method - fallback if orchestrator fails.

        Converts legacy extracted format into a text summary and runs it
        through the Classification Agent → STM pipeline. Also stores
        connections in users.connections for backwards compatibility.
        """
        await self._store_connections(user_id, extracted.get("connections", []))

        # Build a text summary from legacy format for classification
        parts = []
        for interest in extracted.get("interests", []):
            topic = interest.get("topic", "")
            if topic:
                parts.append(f"User is interested in {topic}.")
        for fact in extracted.get("key_facts", []):
            text = fact.get("fact", "")
            if text:
                parts.append(f"Fact: {text}")
        for topic in extracted.get("topics", []):
            if topic:
                parts.append(f"Discussion topic: {topic}")
        for conn in extracted.get("connections", []):
            name = conn.get("name", "")
            rel = conn.get("relationship", "")
            if name:
                parts.append(f"Mentioned {name} ({rel})." if rel else f"Mentioned {name}.")

        if parts:
            from domain.memory.ingestion import classify_and_ingest
            summary = "\n".join(parts)
            await classify_and_ingest(
                openai_client=self._get_openai_client(),
                db=self.db,
                user_id=user_id,
                avatar_id=avatar_id,
                content=summary,
                source="voice_legacy_fallback",
            )

    def _get_openai_client(self):
        """Get OpenAI client from globals."""
        from app.globals import openai_client
        return openai_client
    
    def _format_messages_for_extraction(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages as conversation text for LLM"""
        lines = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Avatar: {content}")
        return "\n".join(lines)
    
    async def _extract_with_llm(
        self, 
        conversation_text: str,
        openai_client: Any
    ) -> Dict[str, Any]:
        """Use LLM to extract memories from conversation"""
        
        extraction_prompt = """Extract ONLY information EXPLICITLY stated in this conversation. Do NOT make assumptions or inferences.

RULES:
- Extract ONLY what the user EXPLICITLY says
- is_correction=true ONLY when user says phrases like "not X but Y", "actually it's Y", "I meant Y not X"
- remove=true ONLY when user says "I don't have", "not my", "I'm not interested in"
- If user just mentions someone ("my daughter Ananya"), it's a normal mention, NOT a correction

CONNECTIONS - People mentioned:
- Normal mention ("my daughter Ananya"): {{"name": "Ananya", "relationship": "daughter"}}
- Explicit name correction ("not Ananya, it's Aanya"): {{"name": "Aanya", "relationship": "daughter", "is_correction": true, "corrects": "Ananya"}}
- Explicit relationship correction ("Arjun is not my son, he's my nephew"): {{"name": "Arjun", "relationship": "nephew", "is_correction": true, "corrects": "son"}}
- Explicit removal ("X is not my daughter"): {{"name": "X", "remove": true}}

INTERESTS - What the user likes:
- Normal mention ("I love chess"): {{"topic": "chess", "strength": 0.8}}
- Explicit correction ("not cooking, I meant baking"): {{"topic": "baking", "is_correction": true, "corrects": "cooking"}}
- Explicit removal ("I don't like X anymore"): {{"topic": "X", "remove": true}}

KEY_FACTS - Information about the user:
- Normal mention ("I work at Amazon"): {{"fact": "Works at Amazon", "confidence": 0.9}}
- Explicit correction ("I don't work at X, I work at Y"): {{"fact": "Works at Y", "is_correction": true, "corrects": "Works at X"}}

Conversation:
---
{conversation}
---

Return JSON: {{connections, interests, key_facts, summary, topics, emotional_tone}}"""
        
        try:
            response = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You extract structured information from conversations. Return only valid JSON."},
                    {"role": "user", "content": extraction_prompt.format(conversation=conversation_text)}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {}
    
    async def _store_connections(self, user_id: str, connections: List[Dict[str, Any]]):
        """Store or update user connections in users collection
        
        Logic:
        - Users can have MULTIPLE people with same relationship (multiple daughters, friends)
        - CORRECTION with different name: "not Ananya but Aanya" -> update name
        - CORRECTION with same name but different relationship: "Arjun is not my son, he's my nephew" -> update relationship
        - REMOVAL: delete the connection
        - Otherwise, ADD new connections (even if same relationship exists)
        """
        if not connections:
            return
        
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            for conn in connections:
                name = conn.get("name", "").strip()
                if not name:
                    continue
                
                relationship = conn.get("relationship", "").strip()
                is_correction = conn.get("is_correction", False)
                corrects = conn.get("corrects", "").strip()  # What's being corrected (name or relationship)
                remove = conn.get("remove", False)
                
                if remove:
                    # DELETE: Remove this connection
                    result = await self.db.users.update_one(
                        {"id": user_id},
                        {"$pull": {"connections": {"name": {"$regex": f"^{name}$", "$options": "i"}}}}
                    )
                    if result.modified_count > 0:
                        logger.info(f"Removed connection: {name}")
                    continue
                
                if is_correction:
                    # Determine what type of correction this is
                    if corrects:
                        # Check if corrects looks like a relationship (son, daughter, etc.)
                        relationship_words = ["son", "daughter", "wife", "husband", "friend", "mother", "father", "brother", "sister", "nephew", "niece", "cousin", "colleague", "boss"]
                        corrects_lower = corrects.lower()
                        
                        if any(rel in corrects_lower for rel in relationship_words):
                            # Relationship correction: "Arjun is not my son, he's my nephew"
                            # Find by name and update relationship
                            result = await self.db.users.update_one(
                                {"id": user_id, "connections.name": {"$regex": f"^{name}$", "$options": "i"}},
                                {
                                    "$set": {
                                        "connections.$.relationship": relationship,
                                        "connections.$.last_mentioned": now
                                    },
                                    "$inc": {"connections.$.mentioned_count": 1}
                                }
                            )
                            if result.modified_count > 0:
                                logger.info(f"Corrected relationship for {name}: {corrects} -> {relationship}")
                                continue
                        else:
                            # Name correction: "not Ananya but Aanya"
                            result = await self.db.users.update_one(
                                {"id": user_id, "connections.name": {"$regex": f"^{corrects}$", "$options": "i"}},
                                {
                                    "$set": {
                                        "connections.$.name": name,
                                        "connections.$.last_mentioned": now,
                                        "connections.$.relationship": relationship or None
                                    },
                                    "$inc": {"connections.$.mentioned_count": 1}
                                }
                            )
                            if result.modified_count > 0:
                                logger.info(f"Corrected name: {corrects} -> {name}")
                                continue
                    
                    # If correction didn't match anything, fall through to add as new
                    logger.info(f"Correction target not found, adding as new: {name}")
                
                # Check if exact same name already exists
                user = await self.db.users.find_one(
                    {"id": user_id, "connections.name": {"$regex": f"^{name}$", "$options": "i"}},
                    {"connections.$": 1}
                )
                
                if user and user.get("connections"):
                    existing = user["connections"][0]
                    # Name exists - update details and relationship if different
                    update_ops = {
                        "$inc": {"connections.$.mentioned_count": 1},
                        "$set": {"connections.$.last_mentioned": now}
                    }
                    
                    # Update relationship if provided and different
                    if relationship and relationship != existing.get("relationship"):
                        update_ops["$set"]["connections.$.relationship"] = relationship
                    
                    if conn.get("details"):
                        update_ops["$set"]["connections.$.details"] = conn.get("details")
                    
                    if conn.get("context"):
                        update_ops["$addToSet"] = {"connections.$.context": {"$each": conn.get("context", [])}}
                    
                    await self.db.users.update_one(
                        {"id": user_id, "connections.name": {"$regex": f"^{name}$", "$options": "i"}},
                        update_ops
                    )
                    logger.info(f"Updated existing connection: {name}")
                else:
                    # New person - add them
                    await self._add_new_connection(user_id, conn, now)
                
        except Exception as e:
            logger.error(f"Error storing connections: {e}")
    
    async def _add_new_connection(self, user_id: str, conn: Dict[str, Any], now: str):
        """Add a new connection to user's connections array"""
        name = conn.get("name", "").strip()
        await self.db.users.update_one(
            {"id": user_id},
            {
                "$push": {
                    "connections": {
                        "name": name,
                        "relationship": conn.get("relationship", ""),
                        "context": conn.get("context", []),
                        "details": conn.get("details", ""),
                        "mentioned_count": 1,
                        "last_mentioned": now,
                        "source": "conversation"
                    }
                }
            },
            upsert=True
        )
        logger.info(f"Added new connection: {name} ({conn.get('relationship', '')})")
    
    async def _store_identity_memory(
        self, 
        user_id: str, 
        avatar_id: str, 
        extracted: Dict[str, Any]
    ):
        """Store interests and facts in identity_memory AND graph_nodes collections
        
        Smart deduplication:
        - Interests: Update strength if already exists, don't duplicate
        - Facts: Check for similar facts before adding
        
        graph_nodes is used by frontend to display in Settings -> Avatar -> Overview/Interests
        """
        try:
            interests = extracted.get("interests", [])
            facts = extracted.get("key_facts", [])
            
            if not interests and not facts:
                return
            
            now = datetime.now(timezone.utc)
            
            # Get existing identity memory for deduplication
            existing = await self.db.identity_memory.find_one({
                "user_id": user_id, 
                "avatar_id": avatar_id
            })
            existing_interests = {i.get("topic", "").lower() for i in (existing or {}).get("interests", [])}
            existing_facts = {f.get("fact", "").lower()[:50] for f in (existing or {}).get("facts", [])}
            
            # Filter to only new interests
            new_interests = []
            for i in interests:
                topic = i.get("topic", "").lower()
                if topic and topic not in existing_interests:
                    i["source"] = "conversation"
                    i["added_at"] = now.isoformat()
                    new_interests.append(i)
            
            # Filter to only new facts (check first 50 chars for similarity)
            new_facts = []
            for f in facts:
                fact_text = f.get("fact", "").lower()[:50]
                if fact_text and fact_text not in existing_facts:
                    f["source"] = "conversation"
                    f["added_at"] = now.isoformat()
                    new_facts.append(f)
            
            # Store only new items in identity_memory
            if new_interests or new_facts:
                update_ops = {
                    "$setOnInsert": {
                        "user_id": user_id,
                        "avatar_id": avatar_id,
                        "created_at": now
                    },
                    "$set": {
                        "updated_at": now
                    }
                }
                
                if new_interests:
                    update_ops["$push"] = {"interests": {"$each": new_interests}}
                if new_facts:
                    if "$push" not in update_ops:
                        update_ops["$push"] = {}
                    update_ops["$push"]["facts"] = {"$each": new_facts}
                
                await self.db.identity_memory.update_one(
                    {"user_id": user_id, "avatar_id": avatar_id},
                    update_ops,
                    upsert=True
                )
                
                logger.info(f"Stored {len(new_interests)} new interests, {len(new_facts)} new facts")
            
            # NOTE: Direct graph_nodes writes removed (Dual-Memory Architecture).
            # Data now flows through Classification Agent → STM → Consolidation → LTM.
            # identity_memory writes above are preserved for backwards compatibility.
            
        except Exception as e:
            logger.error(f"Error storing identity memory: {e}")
    
    async def _store_to_graph_nodes(
        self,
        user_id: str,
        interests: List[Dict[str, Any]],
        facts: List[Dict[str, Any]]
    ):
        """Store extracted data in graph_nodes collection for frontend display
        
        Frontend reads from graph_nodes via /api/graph/visualization endpoint
        
        Handles:
        - Normal mentions: Add or increase strength
        - Corrections: Update old item to new value
        - Removals: Delete or mark as inactive
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Process interests
            for interest in interests:
                topic = interest.get("topic", "").strip()
                if not topic:
                    continue
                
                is_correction = interest.get("is_correction", False)
                corrects = interest.get("corrects", "").strip()
                remove = interest.get("remove", False)
                new_strength = interest.get("strength", 0.5)
                
                if remove:
                    # User no longer has this interest - remove or mark inactive
                    result = await self.db.graph_nodes.delete_one({
                        "user_id": user_id,
                        "node_type": "interest",
                        "label": topic.lower()
                    })
                    if result.deleted_count > 0:
                        logger.info(f"Removed interest: {topic}")
                    continue
                
                if is_correction and corrects:
                    # User corrected an interest (e.g., "not cooking, I meant baking")
                    # Update the old interest to the new one
                    result = await self.db.graph_nodes.update_one(
                        {
                            "user_id": user_id,
                            "node_type": "interest",
                            "label": corrects.lower()
                        },
                        {
                            "$set": {
                                "label": topic.lower(),
                                "display_label": topic.title(),
                                "updated_at": now
                            },
                            "$inc": {"mention_count": 1}
                        }
                    )
                    if result.modified_count > 0:
                        logger.info(f"Corrected interest: {corrects} -> {topic}")
                        continue
                    # If old interest not found, add as new
                
                # Normal case: add or update interest
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": topic.lower()
                })
                
                if existing:
                    # Increase strength (capped at 1.0)
                    current_strength = existing.get("strength", 0.5)
                    updated_strength = min(1.0, current_strength + 0.05)
                    
                    # Update node - also update source to show it was mentioned in conversation
                    await self.db.graph_nodes.update_one(
                        {"_id": existing["_id"]},
                        {
                            "$set": {
                                "strength": updated_strength, 
                                "updated_at": now,
                                "properties.source": "conversation",  # Update source
                                "properties.service": "voice"
                            },
                            "$inc": {"mention_count": 1}
                        }
                    )
                    logger.info(f"Updated interest: {topic} (strength: {updated_strength:.2f})")
                else:
                    # Generate unique id for the node
                    node_id = f"interest_{user_id}_{topic.lower().replace(' ', '_')}"
                    await self.db.graph_nodes.insert_one({
                        "id": node_id,
                        "user_id": user_id,
                        "node_type": "interest",
                        "label": topic.lower(),
                        "display_label": topic.title(),
                        "strength": new_strength,
                        "mention_count": 1,
                        "properties": {"source": "conversation", "service": "voice"},
                        "created_at": now,
                        "updated_at": now
                    })
            
            # Process facts
            for fact in facts:
                fact_text = fact.get("fact", "").strip()
                if not fact_text or len(fact_text) < 5:
                    continue
                
                is_correction = fact.get("is_correction", False)
                corrects = fact.get("corrects", "").strip()
                remove = fact.get("remove", False)
                confidence = fact.get("confidence", 0.5)
                
                label = " ".join(fact_text.split()[:4]).lower()
                
                if remove:
                    # Remove outdated fact
                    corrects_label = " ".join(corrects.split()[:4]).lower() if corrects else label
                    result = await self.db.graph_nodes.delete_one({
                        "user_id": user_id,
                        "node_type": "preference",
                        "label": {"$regex": corrects_label, "$options": "i"}
                    })
                    if result.deleted_count > 0:
                        logger.info(f"Removed fact: {corrects or fact_text}")
                    continue
                
                if is_correction and corrects:
                    # User corrected a fact (e.g., "I don't work at Google, I work at Meta")
                    corrects_label = " ".join(corrects.split()[:4]).lower()
                    result = await self.db.graph_nodes.update_one(
                        {
                            "user_id": user_id,
                            "node_type": "preference",
                            "label": {"$regex": corrects_label, "$options": "i"}
                        },
                        {
                            "$set": {
                                "label": label,
                                "display_label": fact_text[:50],
                                "full_text": fact_text,
                                "strength": confidence,
                                "updated_at": now
                            }
                        }
                    )
                    if result.modified_count > 0:
                        logger.info(f"Corrected fact: {corrects} -> {fact_text}")
                        continue
                
                # Normal case: add or update fact
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "preference",
                    "label": label
                })
                
                if existing:
                    await self.db.graph_nodes.update_one(
                        {"_id": existing["_id"]},
                        {
                            "$set": {
                                "strength": max(existing.get("strength", 0.5), confidence),
                                "full_text": fact_text,
                                "updated_at": now
                            }
                        }
                    )
                else:
                    # Generate unique id for the node
                    node_id = f"preference_{user_id}_{label.replace(' ', '_')}"
                    await self.db.graph_nodes.insert_one({
                        "id": node_id,
                        "user_id": user_id,
                        "node_type": "preference",
                        "label": label,
                        "display_label": fact_text[:50],
                        "full_text": fact_text,
                        "strength": confidence,
                        "properties": {"source": "conversation", "service": "voice"},
                        "created_at": now,
                        "updated_at": now
                    })
            
            logger.info(f"Processed {len(interests)} interests and {len(facts)} facts to graph_nodes")
            
        except Exception as e:
            logger.error(f"Error storing to graph_nodes: {e}")
    
    async def _store_episodic_memory(
        self,
        user_id: str,
        avatar_id: str,
        session_id: str,
        extracted: Dict[str, Any]
    ):
        """Store conversation summary in episodic_memory collection"""
        try:
            summary = extracted.get("summary", "")
            if not summary:
                return
            
            # Get s3_key from transcript metadata for conversation recall
            transcript_meta = await self.db.voice_transcripts.find_one(
                {"session_id": session_id}, {"s3_key": 1}
            )
            s3_key = transcript_meta.get("s3_key", "") if transcript_meta else ""
            
            await self.db.episodic_memory.insert_one({
                "user_id": user_id,
                "avatar_id": avatar_id,
                "session_id": session_id,
                "episode_id": session_id,
                "episode_type": "voice_conversation",
                "timestamp": datetime.now(timezone.utc),
                "summary": summary,
                "topics": extracted.get("topics", []),
                "emotional_tone": extracted.get("emotional_tone", ""),
                "key_moments": [],
                "s3_key": s3_key,
                "source": "conversation"
            })
            
        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
