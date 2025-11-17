"""
Agent Routes - AI agent creation and conversations
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
import logging

from core.auth import require_auth
from core.database import get_database
from api.models import AIAgent, AgentConversation

db = get_database()
router = APIRouter(prefix="/api", tags=["agents"])
logger = logging.getLogger(__name__)


def get_azure_client():
    """Get Azure OpenAI client"""
    from app.globals import azure_client
    return azure_client


def get_azure_deployment():
    """Get Azure OpenAI deployment name"""
    from app.globals import AZURE_OPENAI_DEPLOYMENT
    return AZURE_OPENAI_DEPLOYMENT


@router.post("/agent/create")
async def create_agent(request: Request):
    """Create AI agent for user"""
    user = await require_auth(request)
    
    # Check if agent exists
    existing = await db.ai_agents.find_one({"user_id": user.id})
    if existing:
        return AIAgent(**existing)
    
    # Create agent
    agent = AIAgent(
        user_id=user.id,
        personality_summary=f"{user.name}'s AI agent"
    )
    
    agent_dict = agent.model_dump()
    agent_dict['created_at'] = agent_dict['created_at'].isoformat()
    agent_dict['updated_at'] = agent_dict['updated_at'].isoformat()
    await db.ai_agents.insert_one(agent_dict)
    
    return agent


@router.post("/agent/start-conversation/{target_user_id}")
async def start_agent_conversation(target_user_id: str, request: Request):
    """Start AI agent conversation with another user"""
    user = await require_auth(request)
    
    azure_client = get_azure_client()
    AZURE_OPENAI_DEPLOYMENT = get_azure_deployment()
    
    if not azure_client:
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured")
    
    # Get both users' profiles and graphs
    user1_doc = await db.users.find_one({"id": user.id})
    user2_doc = await db.users.find_one({"id": target_user_id})
    
    if not user2_doc:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Get knowledge graphs (reserved for future use in enhanced matching)
    _ = await db.graph_nodes.find({"user_id": user.id}, {"_id": 0}).to_list(100)
    _ = await db.graph_nodes.find({"user_id": target_user_id}, {"_id": 0}).to_list(100)
    
    # Create conversation
    conversation = AgentConversation(
        agent1_user_id=user.id,
        agent2_user_id=target_user_id
    )
    
    # Simulate AI agent conversation (simplified)
    messages = []
    
    # Agent 1 introduces
    agent1_context = f"""You are {user1_doc['name']}'s AI dating agent. Your personality: {', '.join(user1_doc.get('interests', []))}.
Introduce yourself briefly and ask an interesting question."""
    
    response1 = await azure_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "system", "content": agent1_context}],
        temperature=0.8,
        max_tokens=150
    )
    
    agent1_msg = response1.choices[0].message.content
    messages.append({"sender": user.id, "message": agent1_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    # Agent 2 responds
    agent2_context = f"""You are {user2_doc['name']}'s AI dating agent. Your personality: {', '.join(user2_doc.get('interests', []))}.
Respond to the introduction and share something interesting about yourself."""
    
    response2 = await azure_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": agent2_context},
            {"role": "user", "content": agent1_msg}
        ],
        temperature=0.8,
        max_tokens=150
    )
    
    agent2_msg = response2.choices[0].message.content
    messages.append({"sender": target_user_id, "message": agent2_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    conversation.messages = messages
    
    # Calculate basic compatibility score
    shared_interests = list(set(user1_doc.get('interests', [])) & set(user2_doc.get('interests', [])))
    conversation.compatibility_score = min(len(shared_interests) * 15, 100)
    conversation.conversation_summary = f"Agents discussed common interests: {', '.join(shared_interests)}"
    
    conv_dict = conversation.model_dump()
    conv_dict['created_at'] = conv_dict['created_at'].isoformat()
    conv_dict['updated_at'] = conv_dict['updated_at'].isoformat()
    await db.agent_conversations.insert_one(conv_dict)
    
    return conversation

