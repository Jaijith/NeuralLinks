"""
FastAPI application entry point
Creates and configures the FastAPI app with all routes and services
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from core.config import CORS_ORIGINS, get_openai_client, OPENAI_MODEL
from core.database import get_database, close_database
from domain.graph import GraphBuilder, GraphRAG
from domain.avatar import IntelligentAvatar
from domain.avatar.runner import AutonomousAgentRunner
from services.user_service import UserService
from services.post_service import PostService
from services.friend_service import FriendService
from services.graph_service import GraphService
import logging
import os
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = get_database()

# Initialize OpenAI client
openai_client = get_openai_client()
azure_client = openai_client  # Alias for backwards compatibility

# Initialize Graph RAG modules
graph_rag = GraphRAG(db)
model_name = OPENAI_MODEL  # Has default in config.py
graph_builder = GraphBuilder(db, openai_client, model_name)
intelligent_avatar = IntelligentAvatar(db, openai_client, model_name, graph_rag)

logger.info(f"Initialized with OpenAI model: {model_name}")

# Initialize Services
user_service = UserService(db, graph_builder)
post_service = PostService(db, graph_builder)
friend_service = FriendService(db)
graph_service = GraphService(db, graph_rag, graph_builder)

# Initialize Autonomous Agent Runner (only if OpenAI is configured)
agent_runner = None
if openai_client:
    agent_runner = AutonomousAgentRunner(
        db=db,
        llm_client=openai_client,
        model_name=model_name,
        intelligent_avatar=intelligent_avatar,
        graph_rag=graph_rag
    )
    logger.info("🤖 Autonomous Agent Runner initialized")
else:
    logger.warning("⚠️ OpenAI not configured - Autonomous Agent Runner disabled")

# Initialize global state
from app.globals import initialize_globals
initialize_globals(
    db_instance=db,
    azure_client_instance=openai_client,  # Parameter name kept for backwards compatibility
    deployment_name=model_name,  # Parameter name kept for backwards compatibility
    graph_rag_instance=graph_rag,
    graph_builder_instance=graph_builder,
    intelligent_avatar_instance=intelligent_avatar,
    user_service_instance=user_service,
    post_service_instance=post_service,
    friend_service_instance=friend_service,
    graph_service_instance=graph_service,
    agent_runner_instance=agent_runner
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
from api.signup_routes import router as signup_router
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
from api.voice_routes import router as voice_router
from app.routers.debug import router as debug_router
from api.marketplace_routes import router as marketplace_router
from api.memory_routes import router as memory_router

# NOTE: Workflow router is now in a SEPARATE Lambda function
# Requests to /api/workflow/* are routed to WorkflowFunction by API Gateway

# Initialize Siddhi Bazaar (Marketplace)
from domain.marketplace.service import SiddhiBazaarService
from domain.marketplace.gateway import SiddhiGateway
from domain.marketplace.recommendation import SkillRecommender

# Import MCP server for gateway
from domain.avatar.mcp.server import mcp_server as avatar_mcp_server

siddhi_gateway = SiddhiGateway(db=db, mcp_server=avatar_mcp_server)
marketplace_service = SiddhiBazaarService(db=db, gateway=siddhi_gateway)
skill_recommender = SkillRecommender(db=db)

# Attach to app state so routes can access them
app.state.marketplace_service = marketplace_service
app.state.siddhi_gateway = siddhi_gateway
app.state.skill_recommender = skill_recommender

logger.info("🔮 Siddhi Bazaar marketplace initialized")

# Wire gateway to state-aware agent module
try:
    from domain.avatar.state_aware_agent import set_siddhi_gateway
    set_siddhi_gateway(siddhi_gateway)
    logger.info("🔮 Siddhi Gateway wired to StateAwareAgent")
except Exception as e:
    logger.warning(f"Could not wire Siddhi Gateway to StateAwareAgent: {e}")

app.include_router(auth_router)
app.include_router(signup_router)
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
app.include_router(voice_router)
app.include_router(debug_router)
app.include_router(marketplace_router)
app.include_router(memory_router)
# NOTE: Workflow routes are handled by separate WorkflowFunction Lambda

# Serve static files (uploads)
# Use absolute path to ensure consistency - handle Lambda read-only filesystem
import os
ROOT_DIR = Path(__file__).parent.parent.parent  # Go up to project root

# For Lambda, use /tmp which is writable; otherwise use local uploads folder
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    UPLOAD_DIR = Path('/tmp/uploads')
else:
    UPLOAD_DIR = ROOT_DIR / 'uploads'

# Create directory only if it doesn't exist (handle read-only filesystem)
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
except OSError as e:
    logger.warning(f"Could not create/mount upload directory: {UPLOAD_DIR} - {e}")

# All routes are now in api/ modules - server.py has been removed
# All global instances are available via app.globals


@app.on_event("startup")
async def startup_event():
    """Resume autonomous agents and seed marketplace on startup"""
    # Seed Siddhi Bazaar catalog (idempotent)
    try:
        from domain.marketplace.catalog import seed_catalog
        created = await seed_catalog(db)
        if created > 0:
            logger.info(f"🔮 Siddhi Bazaar: {created} new skills seeded")
        else:
            logger.info("🔮 Siddhi Bazaar catalog up to date")
    except Exception as e:
        logger.warning(f"🔮 Siddhi Bazaar seed failed (non-fatal): {e}")

    if agent_runner:
        # Run in background to not block startup
        asyncio.create_task(agent_runner.resume_all_enabled_agents())
        logger.info("🚀 Autonomous agent resume task scheduled")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    # Stop all autonomous agents
    if agent_runner:
        await agent_runner.stop_all_agents()
        logger.info("⏹️ All autonomous agents stopped")
    
    await close_database()
    logger.info("Application shutdown complete")


# For backward compatibility - allow running as module
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
