"""
FastAPI application entry point
Creates and configures the FastAPI app with all routes and services
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from core.config import CORS_ORIGINS, get_azure_client, AZURE_OPENAI_DEPLOYMENT
from core.database import get_database, close_database
from domain.graph import GraphBuilder, GraphRAG
from domain.avatar import IntelligentAvatar
from services.user_service import UserService
from services.post_service import PostService
from services.friend_service import FriendService
from services.graph_service import GraphService
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = get_database()

# Initialize Azure OpenAI client
azure_client = get_azure_client()

# Initialize Graph RAG modules
graph_rag = GraphRAG(db)
graph_builder = GraphBuilder(db, azure_client, AZURE_OPENAI_DEPLOYMENT)
intelligent_avatar = IntelligentAvatar(db, azure_client, AZURE_OPENAI_DEPLOYMENT, graph_rag)

# Initialize Services
user_service = UserService(db, graph_builder)
post_service = PostService(db, graph_builder)
friend_service = FriendService(db)
graph_service = GraphService(db, graph_rag, graph_builder)

# Initialize global state
from app.globals import initialize_globals
initialize_globals(
    db_instance=db,
    azure_client_instance=azure_client,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
    graph_rag_instance=graph_rag,
    graph_builder_instance=graph_builder,
    intelligent_avatar_instance=intelligent_avatar,
    user_service_instance=user_service,
    post_service_instance=post_service,
    friend_service_instance=friend_service,
    graph_service_instance=graph_service
)

# Create FastAPI app
app = FastAPI(
    title="Geneses API",
    description="API for Geneses - The Realm of Maya",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include route routers
from api.auth_routes import router as auth_router
from api.profile_routes import router as profile_router
from api.post_routes import router as post_router
from api.friend_routes import router as friend_router
from api.graph_routes import router as graph_router
from api.message_routes import router as message_router
from api.mcp_routes import router as mcp_router
from api.avatar_routes import router as avatar_router
from api.integration_routes import router as integration_router
from api.search_routes import router as search_router
from api.match_routes import router as match_router
from api.agent_routes import router as agent_router

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(post_router)
app.include_router(friend_router)
app.include_router(graph_router)
app.include_router(message_router)
app.include_router(mcp_router)
app.include_router(avatar_router)
app.include_router(integration_router)
app.include_router(search_router)
app.include_router(match_router)
app.include_router(agent_router)

# Serve static files (uploads)
# Use absolute path to ensure consistency
import os
ROOT_DIR = Path(__file__).parent.parent.parent  # Go up to project root
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# All routes are now in api/ modules - server.py has been removed
# All global instances are available via app.globals


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await close_database()
    logger.info("Application shutdown complete")


# For backward compatibility - allow running as module
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
