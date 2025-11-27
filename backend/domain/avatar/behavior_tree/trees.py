"""
Generic Behavior Trees
Pre-defined behavior trees for common avatar actions
"""
from domain.avatar.behavior_tree.nodes import (
    Sequence, Selector, Condition, ActionNode, NodeStatus
)
from domain.avatar.behavior_tree.context import BehaviorTreeContext
from datetime import timedelta


def create_react_to_post_bt() -> Selector:
    """
    Create behavior tree for reacting to friend posts
    
    Tree structure:
    - Selector (try different reactions)
      - Sequence (like post)
        - Condition: has_unseen_posts
        - Action: like_post
      - Sequence (comment on post)
        - Condition: has_unseen_posts
        - Condition: post_worth_commenting
        - Action: comment_on_post
    """
    
    # Condition: Check if there are unseen posts
    def has_unseen_posts(context: dict) -> bool:
        external_state = context.get("external_state")
        if not external_state:
            return False
        recent_posts = external_state.get_recent_posts(limit=10)
        return len(recent_posts) > 0
    
    # Condition: Check if post is worth commenting on
    def post_worth_commenting(context: dict) -> bool:
        external_state = context.get("external_state")
        if not external_state:
            return False
        recent_posts = external_state.get_recent_posts(limit=5)
        if not recent_posts:
            return False
        
        # Check if any post has engagement (worth commenting)
        for post in recent_posts:
            likes = post.get('likes', 0)
            comments = post.get('comment_count', 0)
            if likes > 0 or comments > 0:
                return True
        return False
    
    # Action: Like a post
    async def like_post(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        external_state = context.get("external_state")
        if not external_state:
            return False
        
        recent_posts = external_state.get_recent_posts(limit=5)
        if not recent_posts:
            return False
        
        # Like the first unseen post
        post = recent_posts[0]
        post_id = post.get('id')
        
        try:
            # Use MCP client to like post
            # This is a placeholder - actual implementation will use MCP tools
            result = await mcp_client.call_tool("like_post", {"post_id": post_id})
            return result.get("success", False)
        except Exception:
            return False
    
    # Action: Comment on a post
    async def comment_on_post(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        external_state = context.get("external_state")
        if not external_state:
            return False
        
        recent_posts = external_state.get_recent_posts(limit=5)
        if not recent_posts:
            return False
        
        # Find a post worth commenting on
        target_post = None
        for post in recent_posts:
            likes = post.get('likes', 0)
            comments = post.get('comment_count', 0)
            if likes > 0 or comments > 0:
                target_post = post
                break
        
        if not target_post:
            return False
        
        post_id = target_post.get('id')
        
        try:
            # Use MCP client to comment
            result = await mcp_client.call_tool("comment_on_post", {"post_id": post_id})
            return result.get("success", False)
        except Exception:
            return False
    
    # Build tree
    like_sequence = Sequence("LikePostSequence", [
        Condition("HasUnseenPosts", has_unseen_posts),
        ActionNode("LikePost", like_post)
    ])
    
    comment_sequence = Sequence("CommentOnPostSequence", [
        Condition("HasUnseenPosts", has_unseen_posts),
        Condition("PostWorthCommenting", post_worth_commenting),
        ActionNode("CommentOnPost", comment_on_post)
    ])
    
    return Selector("ReactToPostBT", [like_sequence, comment_sequence])


def create_initiate_social_interaction_bt() -> Sequence:
    """
    Create behavior tree for initiating social interactions
    
    Tree structure:
    - Sequence
      - Condition: social_desire_high
      - Condition: has_potential_friends
      - Action: discover_profiles
      - Action: send_friend_request
    """
    
    # Condition: Check if social desire is high
    def social_desire_high(context: dict) -> bool:
        internal_state = context.get("internal_state")
        if not internal_state:
            return False
        return internal_state.social_desire > 0.6
    
    # Condition: Check if there are potential friends to discover
    def has_potential_friends(context: dict) -> bool:
        external_state = context.get("external_state")
        if not external_state:
            return False
        
        # Check relationship map for opportunities
        relationship_map = external_state.get_relationship_map()
        if len(relationship_map) < 10:  # If less than 10 friends, can discover more
            return True
        return False
    
    # Action: Discover profiles
    async def discover_profiles(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        try:
            result = await mcp_client.call_tool("discover_profiles", {})
            return result.get("success", False)
        except Exception:
            return False
    
    # Action: Send friend request
    async def send_friend_request(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        # Get a potential friend ID from context or discovery
        friend_id = context.get("additional_data", {}).get("potential_friend_id")
        if not friend_id:
            return False
        
        try:
            result = await mcp_client.call_tool("send_friend_request", {"friend_id": friend_id})
            return result.get("success", False)
        except Exception:
            return False
    
    return Sequence("InitiateSocialInteractionBT", [
        Condition("SocialDesireHigh", social_desire_high),
        Condition("HasPotentialFriends", has_potential_friends),
        ActionNode("DiscoverProfiles", discover_profiles),
        ActionNode("SendFriendRequest", send_friend_request)
    ])


def create_respond_to_messages_bt() -> Sequence:
    """
    Create behavior tree for responding to messages
    
    Tree structure:
    - Sequence
      - Condition: has_unread_messages
      - Action: read_messages
      - Action: respond_to_messages
    """
    
    # Condition: Check if there are unread messages
    def has_unread_messages(context: dict) -> bool:
        external_state = context.get("external_state")
        if not external_state:
            return False
        return external_state.has_unread_interactions()
    
    # Action: Read messages
    async def read_messages(context: dict):
        # This would mark messages as read
        # For now, just return success
        return True
    
    # Action: Respond to messages
    async def respond_to_messages(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        external_state = context.get("external_state")
        if not external_state:
            return False
        
        if external_state.unread_messages == 0:
            return False
        
        try:
            # Get conversation ID from context
            conversation_id = context.get("additional_data", {}).get("conversation_id")
            if conversation_id:
                result = await mcp_client.call_tool("message_friend", {
                    "friend_id": conversation_id,
                    "message": "Hello! How are you?"
                })
                return result.get("success", False)
        except Exception:
            return False
        
        return False
    
    return Sequence("RespondToMessagesBT", [
        Condition("HasUnreadMessages", has_unread_messages),
        ActionNode("ReadMessages", read_messages),
        ActionNode("RespondToMessages", respond_to_messages)
    ])


def create_create_post_bt() -> Sequence:
    """
    Create behavior tree for creating a post
    
    Tree structure:
    - Sequence
      - Condition: creative_urge_high
      - Condition: time_since_last_post_sufficient
      - Action: create_post
    """
    
    # Condition: Check if creative urge is high
    def creative_urge_high(context: dict) -> bool:
        internal_state = context.get("internal_state")
        if not internal_state:
            return False
        return internal_state.creative_urge > 0.6
    
    # Condition: Check if enough time has passed since last post
    def time_since_last_post_sufficient(context: dict) -> bool:
        internal_state = context.get("internal_state")
        if not internal_state:
            return False
        return internal_state.time_since_last_post > timedelta(hours=6)
    
    # Action: Create a post
    async def create_post(context: dict):
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return False
        
        try:
            result = await mcp_client.call_tool("create_post", {})
            return result.get("success", False)
        except Exception:
            return False
    
    return Sequence("CreatePostBT", [
        Condition("CreativeUrgeHigh", creative_urge_high),
        Condition("TimeSinceLastPostSufficient", time_since_last_post_sufficient),
        ActionNode("CreatePost", create_post)
    ])

