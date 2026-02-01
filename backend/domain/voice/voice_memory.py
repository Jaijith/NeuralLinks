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
        Get user's memory (connections, interests, facts) for voice prompt.
        
        Fetches from existing collections:
        - users.connections → Network (daughter, wife, friends)
        - identity_memory → Interests and preferences
        - episodic_memory → Recent conversation summaries
        
        Called at session start, must be FAST (<3s timeout).
        """
        try:
            # Fetch all in parallel
            results = await asyncio.gather(
                self._get_user_connections(user_id),
                self._get_identity_memory(user_id, avatar_id),
                self._get_recent_conversation_summaries(user_id, avatar_id, limit=3),
                return_exceptions=True
            )
            
            connections = results[0] if not isinstance(results[0], Exception) else []
            identity = results[1] if not isinstance(results[1], Exception) else {}
            summaries = results[2] if not isinstance(results[2], Exception) else []
            
            return {
                "connections": connections,
                "interests": identity.get("interests", []),
                "facts": identity.get("facts", []),
                "preferences": identity.get("preferences", []),
                "recent_conversations": summaries
            }
            
        except Exception as e:
            logger.error(f"Error fetching user memory: {e}")
            return {}
    
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
        Format memory as natural language for the voice prompt.
        
        Returns something like:
        "**Your Memory of John:**
         - Their daughter Sarah loves soccer and has a birthday coming up
         - They work in marketing and are planning a trip to Japan
         - Last conversation was about vacation plans..."
        """
        if not memory:
            return ""
        
        sections = []
        
        # Format connections (network)
        connections = memory.get("connections", [])
        if connections:
            conn_lines = []
            for conn in connections[:5]:  # Limit to 5 most important
                name = conn.get("name", "")
                rel = conn.get("relationship", "")
                details = conn.get("details", "")
                context = ", ".join(conn.get("context", [])[:3])
                
                if name and rel:
                    line = f"{name} ({rel})"
                    if details:
                        line += f" - {details}"
                    elif context:
                        line += f" - mentioned in context of: {context}"
                    conn_lines.append(f"  - {line}")
            
            if conn_lines:
                sections.append(f"**People in {user_name}'s life:**\n" + "\n".join(conn_lines))
        
        # Format interests
        interests = memory.get("interests", [])
        if interests:
            interest_names = [i.get("topic", "") for i in interests[:5] if i.get("topic")]
            if interest_names:
                sections.append(f"**{user_name}'s interests:** {', '.join(interest_names)}")
        
        # Format key facts
        facts = memory.get("facts", [])
        if facts:
            fact_lines = [f"  - {f.get('fact', '')}" for f in facts[:5] if f.get("fact")]
            if fact_lines:
                sections.append(f"**Things to remember:**\n" + "\n".join(fact_lines))
        
        # Format recent conversations
        recent = memory.get("recent_conversations", [])
        if recent:
            conv_lines = []
            for conv in recent[:2]:  # Last 2 conversations
                summary = conv.get("summary", "")
                if summary:
                    conv_lines.append(f"  - {summary}")
            
            if conv_lines:
                sections.append(f"**Recent conversations:**\n" + "\n".join(conv_lines))
        
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
                try:
                    from domain.voice.memory_orchestrator import MemoryOrchestrator
                    
                    orchestrator = MemoryOrchestrator(self.db, openai_client)
                    result = await orchestrator.process_conversation(
                        user_id=user_id,
                        avatar_id=avatar_id,
                        conversation=conversation_text
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
        """Legacy storage method - fallback if orchestrator fails"""
        # Add topics as interests
        topics = extracted.get("topics", [])
        interests = extracted.get("interests", [])
        existing_topics = {i.get("topic", "").lower() for i in interests}
        for topic in topics:
            if topic.lower() not in existing_topics:
                interests.append({"topic": topic, "strength": 0.7})
        extracted["interests"] = interests
        
        # Store using legacy methods
        await self._store_connections(user_id, extracted.get("connections", []))
        await self._store_identity_memory(user_id, avatar_id, extracted)
    
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
                model="gpt-4o-mini",
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
            
            # Store in graph_nodes for frontend display (uses upsert, handles duplicates)
            await self._store_to_graph_nodes(user_id, interests, facts)
            
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
            
            await self.db.episodic_memory.insert_one({
                "user_id": user_id,
                "avatar_id": avatar_id,
                "session_id": session_id,
                "episode_type": "voice_conversation",
                "timestamp": datetime.now(timezone.utc),
                "summary": summary,
                "topics": extracted.get("topics", []),
                "emotional_tone": extracted.get("emotional_tone", ""),
                "key_moments": [],
                "source": "conversation"
            })
            
        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
