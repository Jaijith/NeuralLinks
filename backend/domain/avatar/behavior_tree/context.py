"""
Behavior Tree Context
Context object passed to behavior tree nodes
"""
from typing import Dict, Any, Optional
from domain.avatar.perception.engine import PerceptionEngine
from domain.avatar.state import StateManager, InternalState, ExternalState
from domain.avatar.state_machine import AvatarStateMachine
from domain.avatar.mcp.client import AvatarMCPClient


class BehaviorTreeContext:
    """
    Context passed to behavior tree nodes
    
    Contains all necessary references and data for behavior tree execution
    """
    
    def __init__(
        self,
        avatar_id: str,
        perception_engine: Optional[PerceptionEngine] = None,
        state_manager: Optional[StateManager] = None,
        state_machine: Optional[AvatarStateMachine] = None,
        mcp_client: Optional[AvatarMCPClient] = None,
        character_profile: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.avatar_id = avatar_id
        self.perception_engine = perception_engine
        self.state_manager = state_manager
        self.state_machine = state_machine
        self.mcp_client = mcp_client
        self.character_profile = character_profile or {}
        self.additional_data = additional_data or {}
        
        # Cached state references (updated on each tick)
        self._internal_state: Optional[InternalState] = None
        self._external_state: Optional[ExternalState] = None
        self._perception_data: Optional[Dict[str, Any]] = None
    
    async def get_internal_state(self) -> InternalState:
        """Get current internal state (cached)"""
        if self._internal_state is None and self.state_manager:
            self._internal_state, _ = await self.state_manager.get_current_state(self.avatar_id)
        return self._internal_state or InternalState()
    
    async def get_external_state(self) -> ExternalState:
        """Get current external state (cached)"""
        if self._external_state is None and self.state_manager:
            _, self._external_state = await self.state_manager.get_current_state(self.avatar_id)
        return self._external_state or ExternalState()
    
    async def get_perception_data(self) -> Dict[str, Any]:
        """Get current perception data (cached)"""
        if self._perception_data is None and self.perception_engine:
            self._perception_data = await self.perception_engine.perceive_all(self.avatar_id)
        return self._perception_data or {}
    
    async def refresh_states(self):
        """Refresh cached states and perception"""
        if self.state_manager:
            self._internal_state, self._external_state = await self.state_manager.get_current_state(self.avatar_id)
        
        if self.perception_engine:
            self._perception_data = await self.perception_engine.perceive_all(self.avatar_id)
            
            # Update external state from perception
            if self._external_state:
                self._external_state.update_from_perception(self._perception_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization"""
        return {
            "avatar_id": self.avatar_id,
            "character_profile": self.character_profile,
            "additional_data": self.additional_data,
            "has_perception_engine": self.perception_engine is not None,
            "has_state_manager": self.state_manager is not None,
            "has_state_machine": self.state_machine is not None,
            "has_mcp_client": self.mcp_client is not None
        }

