"""
Chat Service
Handles user-avatar chat interactions and memory updates
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.chat import AvatarChatSession, AvatarChatMessage, ExtractedMemory
from ..models.enums import MessageRole, MissionType
from ..mcp.tools import WorkflowMCPServer

logger = logging.getLogger(__name__)


class ChatService:
    """
    Handles chat between users and their avatars.
    
    Features:
    - Send/receive messages
    - Detect intents (start mission, ask question, etc.)
    - Extract memories from conversations
    - Update knowledge graph with new information
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        mcp_server: WorkflowMCPServer,
        openai_client=None,
        intelligent_avatar=None
    ):
        self.db = db
        self.mcp_server = mcp_server
        self.openai_client = openai_client
        self.intelligent_avatar = intelligent_avatar
    
    async def get_or_create_session(self, user_id: str, avatar_id: str) -> AvatarChatSession:
        """Get active session or create new one"""
        
        # Look for active session
        session_doc = await self.db.avatar_chat.find_one({
            "user_id": user_id,
            "avatar_id": avatar_id,
            "is_active": True
        })
        
        if session_doc:
            return AvatarChatSession.from_dict(session_doc)
        
        # Create new session
        session = AvatarChatSession(user_id=user_id, avatar_id=avatar_id)
        await self.db.avatar_chat.insert_one(session.to_dict())
        
        logger.info(f"📝 Created new chat session: {session.id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[AvatarChatSession]:
        """Get session by ID"""
        session_doc = await self.db.avatar_chat.find_one({"id": session_id})
        return AvatarChatSession.from_dict(session_doc) if session_doc else None
    
    async def send_message(
        self,
        session_id: str,
        content: str,
        role: MessageRole = MessageRole.USER
    ) -> Dict[str, Any]:
        """
        Send a message in a chat session.
        
        If from user:
        - Detect intent
        - Extract memories
        - Generate avatar response
        - Potentially create mission
        """
        
        session = await self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Create user message
        user_message = AvatarChatMessage(
            role=role,
            content=content
        )
        
        # Detect intent
        intent, intent_confidence = await self._detect_intent(content, session)
        user_message.detected_intent = intent
        user_message.intent_confidence = intent_confidence
        
        # Extract memories from user message
        if role == MessageRole.USER:
            memories = await self._extract_memories(content, session.user_id)
            user_message.extracted_memories = memories
            
            # Update knowledge graph
            await self._update_knowledge_graph(session.user_id, memories)
        
        # Add message to session
        session.messages.append(user_message)
        
        # Generate avatar response
        avatar_response = None
        mission_created = None
        
        if role == MessageRole.USER:
            # Handle based on intent
            if intent == "start_mission" and intent_confidence > 0.7:
                mission_created = await self._create_mission_from_chat(
                    session, content
                )
                if mission_created:
                    user_message.triggered_mission_id = mission_created["mission_id"]
                    avatar_response = await self._generate_mission_confirmation(
                        session, mission_created
                    )
            else:
                avatar_response = await self._generate_avatar_response(session, content)
            
            if avatar_response:
                response_message = AvatarChatMessage(
                    role=MessageRole.AVATAR,
                    content=avatar_response
                )
                session.messages.append(response_message)
        
        # Save session
        session.updated_at = datetime.now(timezone.utc)
        await self.db.avatar_chat.update_one(
            {"id": session_id},
            {"$set": session.to_dict()}
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "user_message": user_message.dict(),
            "avatar_response": avatar_response,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "mission_created": mission_created,
            "memories_extracted": len(user_message.extracted_memories)
        }
    
    async def _detect_intent(
        self,
        message: str,
        session: AvatarChatSession
    ) -> tuple[str, float]:
        """Detect user intent from message"""
        
        if not self.openai_client:
            # Simple keyword matching fallback
            lower = message.lower()
            if any(kw in lower for kw in ["find me", "search for", "look for", "match", "help me find"]):
                return "start_mission", 0.8
            if any(kw in lower for kw in ["how many", "status", "progress", "update"]):
                return "check_status", 0.7
            if any(kw in lower for kw in ["stop", "cancel", "pause"]):
                return "control_mission", 0.7
            return "general_chat", 0.5
        
        # Use LLM for intent detection
        prompt = f"""Classify the user's intent from this message.

Message: "{message}"

Recent context:
{self._format_recent_messages(session.messages[-5:])}

Possible intents:
- start_mission: User wants to start a workflow (find matches, search leads, etc.)
- check_status: User asking about mission progress or status
- control_mission: User wants to pause, cancel, or modify a mission
- ask_question: User asking a question about something
- give_feedback: User providing feedback on results
- general_chat: General conversation

Return JSON: {{"intent": "intent_name", "confidence": 0.0-1.0}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=100
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("intent", "general_chat"), result.get("confidence", 0.5)
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return "general_chat", 0.5
    
    async def _extract_memories(
        self,
        message: str,
        user_id: str
    ) -> List[ExtractedMemory]:
        """Extract memories from message"""
        
        result = await self.mcp_server.call_tool(
            "extract_memories",
            user_id,
            text=message,
            context="avatar_chat"
        )
        
        if not result.get("success"):
            return []
        
        extracted = result.get("extracted", {})
        memories = []
        
        for interest in extracted.get("interests", []):
            memories.append(ExtractedMemory(
                type="interest",
                label=interest.get("label"),
                confidence=interest.get("confidence", 0.7)
            ))
        
        for pref in extracted.get("preferences", []):
            memories.append(ExtractedMemory(
                type="preference",
                label=pref.get("label"),
                confidence=0.7,
                sentiment=pref.get("sentiment")
            ))
        
        for goal in extracted.get("goals", []):
            memories.append(ExtractedMemory(
                type="goal",
                label=goal.get("label"),
                confidence=0.8
            ))
        
        for fact in extracted.get("facts", []):
            memories.append(ExtractedMemory(
                type="fact",
                label=fact.get("label"),
                confidence=0.6
            ))
        
        return memories
    
    async def _update_knowledge_graph(
        self,
        user_id: str,
        memories: List[ExtractedMemory]
    ):
        """Update knowledge graph with extracted memories"""
        
        if not memories:
            return
        
        updates = [
            {
                "type": m.type,
                "label": m.label,
                "properties": {
                    "confidence": m.confidence,
                    "sentiment": m.sentiment,
                    "source": "avatar_chat"
                }
            }
            for m in memories
        ]
        
        result = await self.mcp_server.call_tool(
            "update_graph",
            user_id,
            updates=updates
        )
        
        if result.get("success"):
            logger.info(f"📊 Updated knowledge graph with {result.get('updates_made')} memories")
    
    async def _create_mission_from_chat(
        self,
        session: AvatarChatSession,
        message: str
    ) -> Optional[Dict[str, Any]]:
        """Create a mission from chat message"""
        
        # Parse mission parameters from message
        params = await self._parse_mission_params(message, session)
        
        if not params:
            return None
        
        # Create mission
        from .mission_service import MissionService
        mission_service = MissionService(self.db, self.mcp_server, self.openai_client)
        
        mission = await mission_service.create_mission(
            user_id=session.user_id,
            avatar_id=session.avatar_id,
            mission_type=params.get("type", MissionType.MATCHMAKING),
            name=params.get("name", "Finding matches"),
            criteria=params.get("criteria", {}),
            strategy=params.get("strategy", {}),
            source_chat_id=session.id
        )
        
        # Add mission to session
        session.mission_ids.append(mission.id)
        
        return {
            "mission_id": mission.id,
            "mission_type": mission.type,
            "mission_name": mission.name
        }
    
    async def _parse_mission_params(
        self,
        message: str,
        session: AvatarChatSession
    ) -> Optional[Dict[str, Any]]:
        """Parse mission parameters from natural language"""
        
        if not self.openai_client:
            # Simple fallback
            return {
                "type": MissionType.MATCHMAKING,
                "name": "Finding matches",
                "criteria": {"interests": []},
                "strategy": {}
            }
        
        # Get user context for better parsing
        context_result = await self.mcp_server.call_tool(
            "get_user_context",
            session.user_id
        )
        user_context = context_result.get("context", {}) if context_result.get("success") else {}
        
        prompt = f"""Parse this mission request into structured parameters.

User request: "{message}"

User's known interests: {user_context.get("interests", [])}
User's goals: {user_context.get("goals", [])}

Return JSON:
{{
    "type": "matchmaking" | "networking" | "sales_leads" | "job_finder",
    "name": "short mission name",
    "criteria": {{
        "interests": ["list", "of", "interests"],
        "traits": ["optional", "traits"],
        "keywords": ["optional", "keywords"],
        "min_compatibility_score": 60
    }},
    "strategy": {{
        "approach": "casual" | "professional" | "curious" | "enthusiastic",
        "max_targets": 50,
        "max_conversations": 10,
        "talking_points": ["suggested", "topics"],
        "custom_instructions": "any specific instructions from user"
    }}
}}

Infer values from the request. Use user's interests if relevant."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            params = json.loads(response.choices[0].message.content)
            
            # Convert type string to enum
            type_map = {
                "matchmaking": MissionType.MATCHMAKING,
                "networking": MissionType.NETWORKING,
                "sales_leads": MissionType.SALES_LEADS,
                "job_finder": MissionType.JOB_FINDER
            }
            params["type"] = type_map.get(params.get("type"), MissionType.MATCHMAKING)
            
            return params
        except Exception as e:
            logger.error(f"Failed to parse mission params: {e}")
            return None
    
    async def _generate_avatar_response(
        self,
        session: AvatarChatSession,
        user_message: str
    ) -> str:
        """Generate avatar response to user message"""
        
        if self.intelligent_avatar:
            try:
                result = await self.intelligent_avatar.generate_chat_response(
                    user_id=session.avatar_id,
                    other_user_id=session.user_id,
                    conversation_history=session.get_conversation_history(),
                    last_message=user_message
                )
                
                if "error" not in result:
                    return result.get("content", "I understand. How can I help you?")
            except Exception as e:
                logger.error(f"Avatar response generation failed: {e}")
        
        # Fallback response
        return "I'm here to help! Would you like me to search for matches or help with something else?"
    
    async def _generate_mission_confirmation(
        self,
        session: AvatarChatSession,
        mission_info: Dict[str, Any]
    ) -> str:
        """Generate confirmation message for new mission"""
        
        mission_type = mission_info.get("mission_type", "mission")
        mission_name = mission_info.get("mission_name", "your request")
        
        if self.openai_client:
            try:
                prompt = f"""Generate a brief, friendly confirmation that the user's avatar is starting a mission.

Mission type: {mission_type}
Mission name: {mission_name}

Keep it under 2 sentences. Be enthusiastic but professional. Mention that they can check progress anytime."""

                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Confirmation generation failed: {e}")
        
        return f"I'm on it! Starting to {mission_name}. I'll keep you updated on my progress."
    
    def _format_recent_messages(self, messages: List[AvatarChatMessage]) -> str:
        """Format recent messages for context"""
        return "\n".join([
            f"{m.role}: {m.content[:100]}"
            for m in messages
        ])
    
    async def get_chat_history(
        self,
        user_id: str,
        avatar_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get chat history for user-avatar pair"""
        
        sessions = await self.db.avatar_chat.find({
            "user_id": user_id,
            "avatar_id": avatar_id
        }).sort("updated_at", -1).limit(5).to_list(5)
        
        all_messages = []
        for session in sessions:
            for msg in session.get("messages", [])[-limit:]:
                all_messages.append({
                    "session_id": session.get("id"),
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp"),
                    "intent": msg.get("detected_intent"),
                    "mission_id": msg.get("triggered_mission_id")
                })
        
        # Sort by timestamp and limit
        all_messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_messages[:limit]

