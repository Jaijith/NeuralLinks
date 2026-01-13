"""
Activity Diversity Manager
Prevents repetitive behavior by tracking recent actions and penalizing repeated activities
"""
from typing import Dict, List, Deque
from collections import deque
from datetime import datetime, timezone


class ActivityDiversityManager:
    """
    Manages activity diversity to prevent avatars from doing the same thing repeatedly.
    Tracks the last N actions and applies penalties to recently used actions.
    """
    
    def __init__(self, window_size: int = 5):
        """
        Initialize the diversity manager
        
        Args:
            window_size: Number of recent actions to track (default: 5)
        """
        self.window_size = window_size
        self.recent_actions: Deque[Dict] = deque(maxlen=window_size)
    
    def record_action(self, action_type: str, timestamp: datetime = None):
        """Record an action in the diversity tracker"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.recent_actions.append({
            "type": action_type,
            "timestamp": timestamp
        })
    
    def get_diversity_penalty(self, action_type: str) -> float:
        """
        Calculate diversity penalty for an action type.
        Returns a multiplier between 0.1 and 1.0:
        - 1.0 = no penalty (action not done recently)
        - 0.5 = moderate penalty (action done once in last 5)
        - 0.1 = heavy penalty (action done multiple times recently)
        
        Args:
            action_type: The action type to check
            
        Returns:
            Penalty multiplier (0.1 to 1.0)
        """
        if not self.recent_actions:
            return 1.0  # No history, no penalty
        
        # Count occurrences in recent history
        occurrences = sum(1 for action in self.recent_actions if action["type"] == action_type)
        
        if occurrences == 0:
            return 1.0  # Not done recently, full utility
        elif occurrences == 1:
            return 0.7  # Done once, mild penalty
        elif occurrences == 2:
            return 0.4  # Done twice, moderate penalty
        else:
            return 0.1  # Done 3+ times, heavy penalty
    
    def get_diversity_boost(self, action_type: str) -> float:
        """
        Calculate diversity boost for actions NOT done recently.
        Returns a multiplier between 1.0 and 1.5:
        - 1.5 = action never done in last 5 cycles
        - 1.0 = action done recently
        
        Args:
            action_type: The action type to check
            
        Returns:
            Boost multiplier (1.0 to 1.5)
        """
        if not self.recent_actions:
            return 1.0  # No history, no boost needed
        
        # Check if action was done in recent history
        was_done = any(action["type"] == action_type for action in self.recent_actions)
        
        if not was_done:
            # Action hasn't been done in last N cycles - give it a boost
            return 1.5
        else:
            return 1.0
    
    def get_combined_diversity_score(self, action_type: str) -> float:
        """
        Get combined diversity score that applies both penalty and boost.
        
        Args:
            action_type: The action type to score
            
        Returns:
            Combined multiplier (0.1 to 1.5)
        """
        penalty = self.get_diversity_penalty(action_type)
        
        # If action is heavily penalized (done repeatedly), don't give boost
        if penalty < 0.5:
            return penalty
        
        # Otherwise, apply boost for unused actions
        boost = self.get_diversity_boost(action_type)
        return penalty * boost
    
    def get_recent_action_types(self) -> List[str]:
        """Get list of recent action types in chronological order"""
        return [action["type"] for action in self.recent_actions]
    
    def get_action_frequency(self, action_type: str) -> float:
        """
        Get frequency of an action type in recent history.
        
        Returns:
            Frequency as a percentage (0.0 to 1.0)
        """
        if not self.recent_actions:
            return 0.0
        
        occurrences = sum(1 for action in self.recent_actions if action["type"] == action_type)
        return occurrences / len(self.recent_actions)
    
    def should_encourage_diversity(self) -> bool:
        """
        Check if diversity should be encouraged.
        Returns True if the recent actions show too much repetition.
        """
        if len(self.recent_actions) < self.window_size:
            return False  # Not enough history
        
        # Check if any single action type dominates (>60% of recent actions)
        action_types = self.get_recent_action_types()
        for action_type in set(action_types):
            frequency = self.get_action_frequency(action_type)
            if frequency > 0.6:
                return True
        
        return False
    
    def get_summary(self) -> Dict:
        """Get a summary of recent activity for logging/debugging"""
        if not self.recent_actions:
            return {"recent_actions": [], "diversity_needed": False}
        
        action_types = self.get_recent_action_types()
        action_counts = {}
        for action_type in action_types:
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        return {
            "recent_actions": action_types,
            "action_counts": action_counts,
            "diversity_needed": self.should_encourage_diversity(),
            "window_size": self.window_size,
            "current_size": len(self.recent_actions)
        }
