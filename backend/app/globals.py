"""
Global application state
Centralizes all global instances for easy access across the application
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from domain.graph import GraphBuilder, GraphRAG
    from domain.avatar import IntelligentAvatar
    from domain.avatar.runner import AutonomousAgentRunner
    from services.user_service import UserService
    from services.post_service import PostService
    from services.friend_service import FriendService
    from services.graph_service import GraphService
    from openai import AsyncOpenAI

# Global instances - will be initialized in app/main.py
db: Optional["AsyncIOMotorDatabase"] = None
openai_client: Optional["AsyncOpenAI"] = None
azure_client: Optional["AsyncOpenAI"] = None  # Alias for backwards compatibility
OPENAI_MODEL: Optional[str] = None
AZURE_OPENAI_DEPLOYMENT: Optional[str] = None  # Alias for backwards compatibility
graph_rag: Optional["GraphRAG"] = None
graph_builder: Optional["GraphBuilder"] = None
intelligent_avatar: Optional["IntelligentAvatar"] = None
user_service: Optional["UserService"] = None
post_service: Optional["PostService"] = None
friend_service: Optional["FriendService"] = None
graph_service: Optional["GraphService"] = None
agent_runner: Optional["AutonomousAgentRunner"] = None  # Autonomous agent runner


def initialize_globals(
    db_instance,
    azure_client_instance,  # Now actually OpenAI client
    deployment_name,  # Now actually model name
    graph_rag_instance,
    graph_builder_instance,
    intelligent_avatar_instance,
    user_service_instance,
    post_service_instance,
    friend_service_instance,
    graph_service_instance,
    agent_runner_instance=None  # Optional - for autonomous agents
):
    """Initialize all global instances"""
    global db, openai_client, azure_client, OPENAI_MODEL, AZURE_OPENAI_DEPLOYMENT
    global graph_rag, graph_builder, intelligent_avatar
    global user_service, post_service, friend_service, graph_service
    global agent_runner
    
    db = db_instance
    openai_client = azure_client_instance
    azure_client = azure_client_instance  # Alias for backwards compatibility
    OPENAI_MODEL = deployment_name
    AZURE_OPENAI_DEPLOYMENT = deployment_name  # Alias for backwards compatibility
    graph_rag = graph_rag_instance
    graph_builder = graph_builder_instance
    intelligent_avatar = intelligent_avatar_instance
    user_service = user_service_instance
    post_service = post_service_instance
    friend_service = friend_service_instance
    graph_service = graph_service_instance
    agent_runner = agent_runner_instance


def get_agent_runner() -> Optional["AutonomousAgentRunner"]:
    """Get the global agent runner instance."""
    return agent_runner

