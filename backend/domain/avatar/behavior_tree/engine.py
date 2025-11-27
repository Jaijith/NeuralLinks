"""
Behavior Tree Engine
Executes behavior trees
"""
from typing import Dict, Any, Optional, List
from domain.avatar.behavior_tree.nodes import BehaviorTreeNode, NodeStatus
from domain.avatar.behavior_tree.context import BehaviorTreeContext
import logging

logger = logging.getLogger(__name__)


class BehaviorTreeEngine:
    """
    Engine for executing behavior trees
    
    Manages behavior tree execution, state tracking, and result handling
    """
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute_tree(
        self,
        tree_root: BehaviorTreeNode,
        context: BehaviorTreeContext
    ) -> NodeStatus:
        """
        Execute a behavior tree from the root node
        
        Args:
            tree_root: Root node of the behavior tree
            context: Behavior tree context
        
        Returns:
            Final NodeStatus after execution
        """
        try:
            # Refresh context states before execution
            await context.refresh_states()
            
            # Execute tree
            result = await tree_root.tick(context)
            
            # Log execution
            self.execution_history.append({
                "tree_name": tree_root.name,
                "avatar_id": context.avatar_id,
                "result": result.value,
                "timestamp": context.additional_data.get("timestamp")
            })
            
            # Keep only last 100 executions
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing behavior tree for {context.avatar_id}: {e}", exc_info=True)
            return NodeStatus.FAILURE
    
    async def tick(
        self,
        node: BehaviorTreeNode,
        context: BehaviorTreeContext
    ) -> NodeStatus:
        """
        Single execution tick of a node
        
        This is a helper method that can be used for debugging
        or step-by-step execution
        
        Args:
            node: Node to execute
            context: Behavior tree context
        
        Returns:
            NodeStatus after execution
        """
        try:
            return await node.tick(context)
        except Exception as e:
            logger.error(f"Error ticking node {node.name}: {e}")
            return NodeStatus.FAILURE
    
    def get_execution_history(
        self,
        avatar_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get execution history
        
        Args:
            avatar_id: Optional filter by avatar ID
            limit: Maximum number of records to return
        
        Returns:
            List of execution records
        """
        history = self.execution_history
        
        if avatar_id:
            history = [h for h in history if h.get("avatar_id") == avatar_id]
        
        return history[-limit:]
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []

