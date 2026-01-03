"""
Workflow FastAPI Application
Separate FastAPI app for the workflow engine
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS, get_openai_client, OPENAI_MODEL
from core.database import get_database
from domain.graph import GraphBuilder, GraphRAG
from domain.avatar import IntelligentAvatar

logger = logging.getLogger(__name__)


def create_workflow_app() -> FastAPI:
    """Create and configure the workflow FastAPI application"""
    
    # Initialize database
    db = get_database()
    
    # Initialize OpenAI client
    openai_client = get_openai_client()
    
    # Initialize Graph RAG modules
    graph_rag = GraphRAG(db)
    model_name = OPENAI_MODEL
    graph_builder = GraphBuilder(db, openai_client, model_name)
    intelligent_avatar = IntelligentAvatar(db, openai_client, model_name, graph_rag)
    
    logger.info(f"Workflow engine initialized with OpenAI model: {model_name}")
    
    # Initialize workflow globals
    from app.globals import initialize_globals
    initialize_globals(
        db_instance=db,
        azure_client_instance=openai_client,
        deployment_name=model_name,
        graph_rag_instance=graph_rag,
        graph_builder_instance=graph_builder,
        intelligent_avatar_instance=intelligent_avatar,
        user_service_instance=None,
        post_service_instance=None,
        friend_service_instance=None,
        graph_service_instance=None,
        agent_runner_instance=None
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="2N1 Workflow Engine API",
        description="Multi-agent workflow orchestration system",
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
    
    # Import and include workflow router
    from domain.workflow.router import router as workflow_router
    app.include_router(workflow_router)
    
    logger.info(f"✅ Workflow router registered with {len(workflow_router.routes)} routes")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "workflow-engine"}
    
    return app

