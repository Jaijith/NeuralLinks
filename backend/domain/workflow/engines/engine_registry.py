"""
Workflow Engine Registry
Central registry for managing and accessing workflow engines
"""

import logging
from typing import Dict, Type, Optional, List, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base_engine import BaseWorkflowEngine
from .matchfinding_engine import MatchFindingEngine
from .marketing_engine import MarketingCampaignEngine

logger = logging.getLogger(__name__)


class WorkflowEngineRegistry:
    """
    Central registry for workflow engines.
    Manages engine registration and provides factory methods.
    """
    
    # Map of mission types to engine classes
    _engines: Dict[str, Type[BaseWorkflowEngine]] = {}
    
    # Engine instances (cached)
    _instances: Dict[str, BaseWorkflowEngine] = {}
    
    @classmethod
    def register_engine(cls, engine_class: Type[BaseWorkflowEngine]):
        """Register a workflow engine class"""
        
        for mission_type in engine_class.supported_mission_types:
            cls._engines[mission_type] = engine_class
            logger.info(f"📦 Registered engine {engine_class.engine_name} for {mission_type}")
    
    @classmethod
    def get_engine_class(cls, mission_type: str) -> Optional[Type[BaseWorkflowEngine]]:
        """Get the engine class for a mission type"""
        return cls._engines.get(mission_type)
    
    @classmethod
    def get_engine(
        cls,
        mission_type: str,
        db: AsyncIOMotorDatabase,
        mcp_server: Any,
        openai_client: Any = None,
        intelligent_avatar: Any = None
    ) -> Optional[BaseWorkflowEngine]:
        """
        Get or create an engine instance for a mission type.
        Engines are cached for reuse.
        """
        
        engine_class = cls._engines.get(mission_type)
        if not engine_class:
            logger.warning(f"No engine registered for mission type: {mission_type}")
            return None
        
        # Check cache
        cache_key = f"{engine_class.engine_name}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Create new instance
        engine = engine_class(
            db=db,
            mcp_server=mcp_server,
            openai_client=openai_client,
            intelligent_avatar=intelligent_avatar
        )
        
        cls._instances[cache_key] = engine
        return engine
    
    @classmethod
    def list_engines(cls) -> List[Dict[str, Any]]:
        """List all registered engines"""
        
        engines = {}
        for mission_type, engine_class in cls._engines.items():
            if engine_class.engine_name not in engines:
                engines[engine_class.engine_name] = {
                    "name": engine_class.engine_name,
                    "description": engine_class.engine_description,
                    "supported_mission_types": engine_class.supported_mission_types
                }
        
        return list(engines.values())
    
    @classmethod
    def clear_cache(cls):
        """Clear cached engine instances"""
        cls._instances.clear()


# Auto-register built-in engines
WorkflowEngineRegistry.register_engine(MatchFindingEngine)
WorkflowEngineRegistry.register_engine(MarketingCampaignEngine)

