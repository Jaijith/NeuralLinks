"""
Behavior Tree Nodes
Core node types for behavior tree implementation
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class NodeStatus(str, Enum):
    """Status returned by behavior tree nodes"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BehaviorTreeNode(ABC):
    """
    Base class for all behavior tree nodes
    
    All nodes must implement the `tick` method which is called
    during behavior tree execution.
    """
    
    def __init__(self, name: str = ""):
        self.name = name
        self.status: Optional[NodeStatus] = None
    
    @abstractmethod
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """
        Execute the node
        
        Args:
            context: Behavior tree context containing state, perception, etc.
        
        Returns:
            NodeStatus indicating success, failure, or running
        """
        pass
    
    def reset(self):
        """Reset node state"""
        self.status = None


class CompositeNode(BehaviorTreeNode):
    """
    Base class for composite nodes that have children
    """
    
    def __init__(self, name: str = "", children: Optional[List[BehaviorTreeNode]] = None):
        super().__init__(name)
        self.children: List[BehaviorTreeNode] = children or []
    
    def add_child(self, child: BehaviorTreeNode):
        """Add a child node"""
        self.children.append(child)
    
    def reset(self):
        """Reset node and all children"""
        super().reset()
        for child in self.children:
            child.reset()


class Sequence(CompositeNode):
    """
    Sequence node: Executes children in order until one fails
    
    Returns SUCCESS if all children succeed
    Returns FAILURE if any child fails
    Returns RUNNING if a child is running
    """
    
    def __init__(self, name: str = "Sequence", children: Optional[List[BehaviorTreeNode]] = None):
        super().__init__(name, children)
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Execute children in sequence"""
        for child in self.children:
            status = await child.tick(context)
            
            if status == NodeStatus.FAILURE:
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            elif status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        
        # All children succeeded
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class Selector(CompositeNode):
    """
    Selector node: Executes children in order until one succeeds
    
    Returns SUCCESS if any child succeeds
    Returns FAILURE if all children fail
    Returns RUNNING if a child is running
    """
    
    def __init__(self, name: str = "Selector", children: Optional[List[BehaviorTreeNode]] = None):
        super().__init__(name, children)
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Execute children until one succeeds"""
        for child in self.children:
            status = await child.tick(context)
            
            if status == NodeStatus.SUCCESS:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            elif status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        
        # All children failed
        self.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE


class Parallel(CompositeNode):
    """
    Parallel node: Executes all children concurrently
    
    Returns SUCCESS if all children succeed
    Returns FAILURE if any child fails
    Returns RUNNING if any child is running
    """
    
    def __init__(self, name: str = "Parallel", children: Optional[List[BehaviorTreeNode]] = None):
        super().__init__(name, children)
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Execute all children in parallel"""
        import asyncio
        
        if not self.children:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        
        # Execute all children concurrently
        results = await asyncio.gather(*[child.tick(context) for child in self.children])
        
        # Check results
        if NodeStatus.FAILURE in results:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        elif NodeStatus.RUNNING in results:
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        else:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS


class Condition(BehaviorTreeNode):
    """
    Condition node: Checks a condition
    
    Returns SUCCESS if condition is true
    Returns FAILURE if condition is false
    """
    
    def __init__(
        self,
        name: str,
        condition_func: Callable[[Dict[str, Any]], bool]
    ):
        super().__init__(name)
        self.condition_func = condition_func
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Check condition"""
        try:
            result = self.condition_func(context)
            self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
            return self.status
        except Exception as e:
            # If condition check fails, return failure
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class ActionNode(BehaviorTreeNode):
    """
    Action node: Executes an action
    
    Returns SUCCESS if action succeeds
    Returns FAILURE if action fails
    Returns RUNNING if action is in progress
    """
    
    def __init__(
        self,
        name: str,
        action_func: Callable[[Dict[str, Any]], Any]
    ):
        super().__init__(name)
        self.action_func = action_func
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Execute action"""
        try:
            result = await self.action_func(context) if hasattr(self.action_func, '__call__') else self.action_func(context)
            
            # If result is a NodeStatus, return it
            if isinstance(result, NodeStatus):
                self.status = result
                return result
            
            # If result is a boolean, convert to status
            if isinstance(result, bool):
                self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
                return self.status
            
            # If result is truthy, assume success
            self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
            return self.status
            
        except Exception as e:
            # If action fails, return failure
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class DecoratorNode(BehaviorTreeNode):
    """
    Base class for decorator nodes that modify child behavior
    """
    
    def __init__(self, name: str = "", child: Optional[BehaviorTreeNode] = None):
        super().__init__(name)
        self.child = child
    
    def set_child(self, child: BehaviorTreeNode):
        """Set the child node"""
        self.child = child
    
    def reset(self):
        """Reset node and child"""
        super().reset()
        if self.child:
            self.child.reset()


class Inverter(DecoratorNode):
    """
    Inverter: Inverts the result of its child
    
    SUCCESS becomes FAILURE
    FAILURE becomes SUCCESS
    RUNNING stays RUNNING
    """
    
    def __init__(self, name: str = "Inverter", child: Optional[BehaviorTreeNode] = None):
        super().__init__(name, child)
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Execute child and invert result"""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        child_status = await self.child.tick(context)
        
        if child_status == NodeStatus.SUCCESS:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        elif child_status == NodeStatus.FAILURE:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING


class Repeater(DecoratorNode):
    """
    Repeater: Repeats child execution until it fails
    
    Continues executing child until it returns FAILURE
    """
    
    def __init__(
        self,
        name: str = "Repeater",
        child: Optional[BehaviorTreeNode] = None,
        max_repeats: int = -1  # -1 means infinite
    ):
        super().__init__(name, child)
        self.max_repeats = max_repeats
        self.repeat_count = 0
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Repeat child execution"""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        while True:
            if self.max_repeats > 0 and self.repeat_count >= self.max_repeats:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            
            child_status = await self.child.tick(context)
            
            if child_status == NodeStatus.FAILURE:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            elif child_status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            
            self.repeat_count += 1
    
    def reset(self):
        """Reset repeater"""
        super().reset()
        self.repeat_count = 0


class UntilSuccess(DecoratorNode):
    """
    UntilSuccess: Repeats child until it succeeds
    
    Continues executing child until it returns SUCCESS
    """
    
    def __init__(self, name: str = "UntilSuccess", child: Optional[BehaviorTreeNode] = None):
        super().__init__(name, child)
    
    async def tick(self, context: Dict[str, Any]) -> NodeStatus:
        """Repeat child until success"""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        while True:
            child_status = await self.child.tick(context)
            
            if child_status == NodeStatus.SUCCESS:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            elif child_status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING

