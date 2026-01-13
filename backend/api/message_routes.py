"""
Message Routes - Direct messaging, chat, and conversations
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone
import logging

from core.auth import require_auth
from core.database import get_database
from api.models import AgentConversation, HumanConversation

db = get_database()
router = APIRouter(prefix="/api", tags=["messages"])
logger = logging.getLogger(__name__)


def get_openai_client():
    """Get OpenAI client"""
    from app.globals import openai_client
    return openai_client

def get_azure_client():
    """Get OpenAI client (alias for backwards compatibility)"""
    return get_openai_client()

def get_openai_model():
    """Get OpenAI model name"""
    from app.globals import OPENAI_MODEL
    return OPENAI_MODEL  # Has default in config.py

def get_azure_deployment():
    """Get OpenAI model name (alias for backwards compatibility)"""
    return get_openai_model()


def is_responses_api_model(model: str) -> bool:
    """Check if model uses the new Responses API (gpt-5 models)"""
    return "gpt-5" in model.lower()


async def call_openai_with_system(client, model: str, system_prompt: str, user_message: str) -> str:
    """
    Call OpenAI with appropriate API based on model type.
    For gpt-5 models, combines system and user into single input.
    """
    if is_responses_api_model(model):
        # For gpt-5 models, combine system and user into single input
        combined_prompt = f"""System Instructions:
{system_prompt}

User Message:
{user_message}"""
        
        response = await client.responses.create(
            model=model,
            input=combined_prompt
        )
        return response.output_text.strip() if response.output_text else ""
    else:
        # Use traditional Chat Completions API
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip() if response.choices[0].message.content else ""


def get_intelligent_avatar():
    """Get IntelligentAvatar instance"""
    from app.globals import intelligent_avatar
    return intelligent_avatar


@router.post("/messages/send")
async def send_direct_message(data: Dict[str, Any], request: Request):
    """Send a direct message to a friend (works in both Sense and Maya worlds)"""
    user = await require_auth(request)
    
    recipient_id = data.get("recipient_id")
    message_text = data.get("message", "").strip()
    world_mode = data.get("world_mode", "real")  # "real" for Sense, "avatar" for Maya
    
    if not recipient_id or not message_text:
        raise HTTPException(status_code=400, detail="recipient_id and message are required")
    
    if user.id == recipient_id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    
    # Verify friendship
    friendship = await db.friendships.find_one({
        "$or": [
            {"user_id": user.id, "friend_id": recipient_id, "status": "accepted"},
            {"user_id": recipient_id, "friend_id": user.id, "status": "accepted"}
        ]
    })
    
    if not friendship:
        raise HTTPException(status_code=403, detail="You can only message your friends")
    
    # Determine conversation ID (same for both users)
    user_ids = sorted([user.id, recipient_id])
    conversation_id = f"{user_ids[0]}_{user_ids[1]}_{world_mode}"
    
    # Create message
    new_message = {
        "sender_id": user.id,
        "recipient_id": recipient_id,
        "content": message_text,
        "world_mode": world_mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if world_mode == "avatar":
        # Maya world: Save to agent_conversations
        conversation = await db.agent_conversations.find_one({
            "agent1_user_id": user_ids[0],
            "agent2_user_id": user_ids[1]
        })
        
        conversation_id = None
        if not conversation:
            # Create new agent conversation
            new_conversation = AgentConversation(
                agent1_user_id=user_ids[0],
                agent2_user_id=user_ids[1]
            )
            conv_dict = new_conversation.model_dump()
            conv_dict['created_at'] = conv_dict['created_at'].isoformat()
            conv_dict['updated_at'] = conv_dict['updated_at'].isoformat()
            await db.agent_conversations.insert_one(conv_dict)
            conversation_id = new_conversation.id
        else:
            conversation_id = conversation["id"]
        
        # Add message
        message_dict = {
            "sender": user.id,
            "message": message_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.agent_conversations.update_one(
            {"id": conversation_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        # Generate AI response if recipient is an avatar/bot
        recipient_user = await db.users.find_one({"id": recipient_id})
        if recipient_user and recipient_user.get("is_bot"):
            try:
                # Generate AI response
                intelligent_avatar = get_intelligent_avatar()
                if intelligent_avatar:
                    # Get updated conversation with new message
                    updated_conv = await db.agent_conversations.find_one({"id": conversation_id})
                    conversation_history = updated_conv.get("messages", [])[-5:] if updated_conv else []
                    history_list = [
                        {"sender_id": msg.get("sender"), "content": msg.get("message", "")}
                        for msg in conversation_history
                    ]
                    
                    ai_response = await intelligent_avatar.generate_chat_response(
                        recipient_id, user.id, history_list, message_text
                    )
                    
                    response_content = ai_response.get("content") or ai_response.get("response")
                    if response_content:
                        ai_message = {
                            "sender": recipient_id,
                            "message": response_content,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "is_ai": True
                        }
                        
                        await db.agent_conversations.update_one(
                            {"id": conversation_id},
                            {
                                "$push": {"messages": ai_message},
                                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                            }
                        )
                        
                        return {
                            "message": new_message,
                            "ai_response": {
                                "sender_id": recipient_id,
                                "content": response_content,
                                "timestamp": ai_message["timestamp"],
                                "is_ai": True
                            }
                        }
            except Exception as e:
                logger.error(f"Error generating AI response: {str(e)}")
                # Continue without AI response
        
        return {"message": new_message}
    
    else:
        # Sense world: Save to direct_messages collection
        # Create or update conversation
        conversation = await db.direct_messages.find_one({"conversation_id": conversation_id})
        
        if not conversation:
            conversation = {
                "conversation_id": conversation_id,
                "user1_id": user_ids[0],
                "user2_id": user_ids[1],
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.direct_messages.insert_one(conversation)
        
        # Add message
        await db.direct_messages.update_one(
            {"conversation_id": conversation_id},
            {
                "$push": {"messages": new_message},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"message": new_message}


@router.get("/messages/conversations")
async def get_conversations(request: Request):
    """Get all conversations for the current user"""
    user = await require_auth(request)
    world_mode = request.query_params.get("world_mode", "real")
    
    conversations = []
    
    if world_mode == "avatar":
        # Maya world: Get agent conversations
        agent_convs = await db.agent_conversations.find({
            "$or": [
                {"agent1_user_id": user.id},
                {"agent2_user_id": user.id}
            ]
        }, {"_id": 0}).sort("updated_at", -1).to_list(50)
        
        for conv in agent_convs:
            other_user_id = conv["agent2_user_id"] if conv["agent1_user_id"] == user.id else conv["agent1_user_id"]
            other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
            
            if other_user:
                last_message = conv.get("messages", [])[-1] if conv.get("messages") else None
                conversations.append({
                    "conversation_id": conv["id"],
                    "other_user": {
                        "id": other_user["id"],
                        "name": other_user.get("name"),
                        "avatar_name": other_user.get("avatar_name"),
                        "picture": other_user.get("picture"),
                        "avatar_picture": other_user.get("avatar_picture"),
                        "is_bot": other_user.get("is_bot", False)
                    },
                    "last_message": last_message.get("message", "") if last_message else "",
                    "last_message_time": last_message.get("timestamp") if last_message else conv.get("updated_at"),
                    "unread_count": 0,  # TODO: Implement unread tracking
                    "world_mode": "avatar"
                })
    
    else:
        # Sense world: Get direct messages
        direct_convs = await db.direct_messages.find({
            "$or": [
                {"user1_id": user.id},
                {"user2_id": user.id}
            ]
        }, {"_id": 0}).sort("updated_at", -1).to_list(50)
        
        for conv in direct_convs:
            other_user_id = conv["user2_id"] if conv["user1_id"] == user.id else conv["user1_id"]
            other_user = await db.users.find_one({"id": other_user_id}, {"_id": 0})
            
            if other_user:
                last_message = conv.get("messages", [])[-1] if conv.get("messages") else None
                conversations.append({
                    "conversation_id": conv["conversation_id"],
                    "other_user": {
                        "id": other_user["id"],
                        "name": other_user.get("name"),
                        "picture": other_user.get("picture")
                    },
                    "last_message": last_message.get("content", "") if last_message else "",
                    "last_message_time": last_message.get("timestamp") if last_message else conv.get("updated_at"),
                    "unread_count": 0,  # TODO: Implement unread tracking
                    "world_mode": "real"
                })
    
    return conversations


@router.get("/messages/{other_user_id}")
async def get_conversation_messages(other_user_id: str, request: Request):
    """Get messages between current user and another user"""
    user = await require_auth(request)
    world_mode = request.query_params.get("world_mode", "real")
    
    if user.id == other_user_id:
        raise HTTPException(status_code=400, detail="Cannot get conversation with yourself")
    
    # Verify friendship
    friendship = await db.friendships.find_one({
        "$or": [
            {"user_id": user.id, "friend_id": other_user_id, "status": "accepted"},
            {"user_id": other_user_id, "friend_id": user.id, "status": "accepted"}
        ]
    })
    
    if not friendship:
        raise HTTPException(status_code=403, detail="You can only view messages with your friends")
    
    if world_mode == "avatar":
        # Maya world: Get agent conversation
        user_ids = sorted([user.id, other_user_id])
        conversation = await db.agent_conversations.find_one({
            "agent1_user_id": user_ids[0],
            "agent2_user_id": user_ids[1]
        }, {"_id": 0})
        
        if not conversation:
            return {"messages": []}
        
        # Convert to unified format
        messages = []
        for msg in conversation.get("messages", []):
            messages.append({
                "sender_id": msg.get("sender"),
                "content": msg.get("content", msg.get("message", "")),
                "timestamp": msg.get("timestamp"),
                "is_ai": msg.get("is_ai", False)
            })
        
        return {"messages": messages, "world_mode": "avatar"}
    
    else:
        # Sense world: Get direct messages
        user_ids = sorted([user.id, other_user_id])
        conversation_id = f"{user_ids[0]}_{user_ids[1]}_real"
        
        conversation = await db.direct_messages.find_one(
            {"conversation_id": conversation_id},
            {"_id": 0}
        )
        
        if not conversation:
            return {"messages": []}
        
        return {"messages": conversation.get("messages", []), "world_mode": "real"}


@router.post("/chat/send")
async def send_message(data: Dict[str, Any], request: Request):
    """Send message in human conversation"""
    user = await require_auth(request)
    
    match_id = data['match_id']
    message_text = data['message']
    
    # Verify match
    match = await db.matches.find_one({"id": match_id, "user_id": user.id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get or create conversation
    conversation = await db.human_conversations.find_one({"match_id": match_id})
    
    if not conversation:
        conversation = HumanConversation(match_id=match_id, messages=[])
        conv_dict = conversation.model_dump()
        conv_dict['created_at'] = conv_dict['created_at'].isoformat()
        await db.human_conversations.insert_one(conv_dict)
    
    # Add message
    new_message = {
        "sender_id": user.id,
        "message": message_text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.human_conversations.update_one(
        {"match_id": match_id},
        {"$push": {"messages": new_message}}
    )
    
    return new_message


@router.get("/chat/{match_id}/messages")
async def get_messages(match_id: str, request: Request):
    """Get messages for a match"""
    _ = await require_auth(request)
    
    conversation = await db.human_conversations.find_one({"match_id": match_id}, {"_id": 0})
    if not conversation:
        return {"messages": []}
    
    return conversation


@router.post("/profile/onboarding-chat")
async def onboarding_chat(message: Dict[str, str], request: Request):
    """Chat with AI agent during onboarding"""
    user = await require_auth(request)
    
    openai_client = get_openai_client()
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI not configured")
    
    openai_model = get_openai_model()
    user_message = message.get("message", "")
    
    # Get user's current profile
    user_doc = await db.users.find_one({"id": user.id})
    
    # Build context from user's profile
    context = f"""
You are helping {user.name} create their dating profile through a friendly conversation.
Current profile status:
- Age: {user_doc.get('age', 'Not set')}
- Gender: {user_doc.get('gender', 'Not set')}
- Location: {user_doc.get('location', 'Not set')}
- Bio: {user_doc.get('bio', 'Not set')}
- Interests: {', '.join(user_doc.get('interests', []))}
- Onboarding stage: {user_doc.get('onboarding_stage', 'start')}

Guide them through completing their profile naturally. Ask about:
1. Basic info (age, gender, location)
2. Personality traits and values
3. Interests and hobbies
4. What they're looking for in a match

Extract information from their responses and provide it in a structured way.
Be warm, engaging, and conversational.
"""
    
    try:
        ai_response = await call_openai_with_system(openai_client, openai_model, context, user_message)
        
        # Store conversation in graph for future learning
        # Extract insights and update graph
        
        return {
            "response": ai_response,
            "profile_completion": 50  # Calculate actual completion
        }
    except Exception as e:
        logger.error(f"Onboarding chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

