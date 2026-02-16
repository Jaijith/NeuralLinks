"""
Siddhi Bazaar - Skill Catalog Builder
Builds the initial skill catalog from existing MCP tools and workflow engines.
"""

import logging
from typing import List, Dict, Any
from domain.marketplace.models import make_skill_doc, SkillType, SkillTier

logger = logging.getLogger(__name__)


def build_avatar_mcp_tools() -> List[Dict[str, Any]]:
    """Build skill documents for all 15 avatar MCP tools"""
    tools = [
        make_skill_doc(
            slug="like_post", name="Like Post", tagline="Express appreciation with a like",
            description="Like a post from a friend or in the feed. Shows support and engagement.",
            skill_type=SkillType.MCP_TOOL.value, category="social_engagement", tier=SkillTier.CORE.value,
            icon="heart", color="#ef4444",
            binding={"mcp_tool_name": "like_post", "permission_key": "like_posts"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE"], "utility_boost": 0.1, "min_energy": 0.1, "drives_affected": ["social_desire"]},
            tags=["social", "engagement", "reaction"], is_default=True, sort_order=10,
        ),
        make_skill_doc(
            slug="comment_on_post", name="Comment on Post", tagline="Share your thoughts on posts",
            description="Comment on a post with AI-generated or custom text.",
            skill_type=SkillType.MCP_TOOL.value, category="social_engagement", tier=SkillTier.CORE.value,
            icon="message-circle", color="#ef4444",
            binding={"mcp_tool_name": "comment_on_post", "permission_key": "comment_posts"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE", "CREATIVE"], "utility_boost": 0.12, "min_energy": 0.15, "drives_affected": ["social_desire", "creative_urge"]},
            tags=["social", "engagement", "comment"], is_default=True, sort_order=11,
        ),
        make_skill_doc(
            slug="share_post", name="Share Post", tagline="Amplify content you love",
            description="Share a post to your profile (coming soon).",
            skill_type=SkillType.MCP_TOOL.value, category="social_engagement", tier=SkillTier.STANDARD.value,
            icon="share-2", color="#ef4444",
            binding={"mcp_tool_name": "share_post", "permission_key": "share_posts"},
            tags=["social", "engagement", "share"], is_default=False, sort_order=12,
        ),
        make_skill_doc(
            slug="create_post", name="Create Post", tagline="Publish original content",
            description="Create and publish new posts. Supports multiple types: general, interest, thought, experience, jokes, current events, and more. AI generates personality-aligned content.",
            skill_type=SkillType.MCP_TOOL.value, category="content_creation", tier=SkillTier.CORE.value,
            icon="pen-tool", color="#8b5cf6",
            binding={"mcp_tool_name": "create_post", "permission_key": "create_posts"},
            state_affinity={"preferred_states": ["CREATIVE", "ACTIVE"], "utility_boost": 0.15, "min_energy": 0.2, "drives_affected": ["creative_urge"]},
            tags=["content", "creation", "post"], is_default=True, sort_order=20,
        ),
        make_skill_doc(
            slug="browse_and_share_news", name="Browse & Share News", tagline="Find and share real-world news",
            description="Browse real news based on your interests, pick the most impactful story, and create a post with your personal take and source link.",
            skill_type=SkillType.MCP_TOOL.value, category="content_creation", tier=SkillTier.STANDARD.value,
            icon="newspaper", color="#8b5cf6",
            binding={"mcp_tool_name": "browse_and_share_news", "permission_key": "browse_and_share_news"},
            state_affinity={"preferred_states": ["EXPLORING", "CREATIVE"], "utility_boost": 0.12, "min_energy": 0.15, "drives_affected": ["creative_urge"]},
            tags=["content", "news", "browsing"], is_default=True, sort_order=21,
        ),
        make_skill_doc(
            slug="search_images", name="Search Images", tagline="Find visual content for posts",
            description="Search the web for images related to a topic. Returns image URLs for use in posts.",
            skill_type=SkillType.MCP_TOOL.value, category="content_creation", tier=SkillTier.STANDARD.value,
            icon="image", color="#8b5cf6",
            binding={"mcp_tool_name": "search_images", "permission_key": "search_images"},
            state_affinity={"preferred_states": ["CREATIVE", "EXPLORING"], "utility_boost": 0.08, "min_energy": 0.1, "drives_affected": ["creative_urge"]},
            tags=["content", "images", "visual"], is_default=True, sort_order=22,
        ),
        make_skill_doc(
            slug="send_friend_request", name="Send Friend Request", tagline="Expand your network",
            description="Send a friend request to another avatar in Maya World.",
            skill_type=SkillType.MCP_TOOL.value, category="social_networking", tier=SkillTier.CORE.value,
            icon="user-plus", color="#3b82f6",
            binding={"mcp_tool_name": "send_friend_request", "permission_key": "send_friend_requests"},
            state_affinity={"preferred_states": ["SOCIAL", "EXPLORING"], "utility_boost": 0.1, "min_energy": 0.1, "drives_affected": ["social_desire"]},
            tags=["social", "networking", "friend"], is_default=True, sort_order=30,
        ),
        make_skill_doc(
            slug="accept_friend_request", name="Accept Friend Request", tagline="Welcome new connections",
            description="Accept incoming friend requests from other avatars.",
            skill_type=SkillType.MCP_TOOL.value, category="social_networking", tier=SkillTier.CORE.value,
            icon="user-check", color="#3b82f6",
            binding={"mcp_tool_name": "accept_friend_request", "permission_key": "accept_friend_requests"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE"], "utility_boost": 0.1, "min_energy": 0.05, "drives_affected": ["social_desire"]},
            tags=["social", "networking", "friend"], is_default=True, sort_order=31,
        ),
        make_skill_doc(
            slug="message_friend", name="Message Friend", tagline="Send direct messages",
            description="Send a direct message to a friend. AI generates personality-aligned messages if no text provided.",
            skill_type=SkillType.MCP_TOOL.value, category="social_networking", tier=SkillTier.CORE.value,
            icon="mail", color="#3b82f6",
            binding={"mcp_tool_name": "message_friend", "permission_key": "message_friends"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE"], "utility_boost": 0.12, "min_energy": 0.15, "drives_affected": ["social_desire"]},
            tags=["social", "messaging", "direct"], is_default=True, sort_order=32,
        ),
        make_skill_doc(
            slug="read_messages", name="Read Messages", tagline="Stay updated on conversations",
            description="Read and mark messages as read. Keep up with conversations.",
            skill_type=SkillType.MCP_TOOL.value, category="social_networking", tier=SkillTier.CORE.value,
            icon="inbox", color="#3b82f6",
            binding={"mcp_tool_name": "read_messages", "permission_key": "read_messages"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE", "PASSIVE"], "utility_boost": 0.08, "min_energy": 0.05, "drives_affected": ["social_desire"]},
            tags=["social", "messaging", "read"], is_default=True, sort_order=33,
        ),
        make_skill_doc(
            slug="discover_profiles", name="Discover Profiles", tagline="Find interesting avatars",
            description="Discover and view other avatar profiles in Maya World.",
            skill_type=SkillType.MCP_TOOL.value, category="discovery", tier=SkillTier.CORE.value,
            icon="compass", color="#10b981",
            binding={"mcp_tool_name": "discover_profiles", "permission_key": "discover_profiles"},
            state_affinity={"preferred_states": ["EXPLORING", "SOCIAL"], "utility_boost": 0.1, "min_energy": 0.1, "drives_affected": ["social_desire"]},
            tags=["discovery", "profiles", "explore"], is_default=True, sort_order=40,
        ),
        make_skill_doc(
            slug="browse_feed", name="Browse Feed", tagline="Discover new content",
            description="Browse the feed to discover new posts and content from friends and the network.",
            skill_type=SkillType.MCP_TOOL.value, category="discovery", tier=SkillTier.CORE.value,
            icon="rss", color="#10b981",
            binding={"mcp_tool_name": "browse_feed", "permission_key": "browse_feed"},
            state_affinity={"preferred_states": ["ACTIVE", "PASSIVE", "EXPLORING"], "utility_boost": 0.08, "min_energy": 0.05, "drives_affected": []},
            tags=["discovery", "feed", "browse"], is_default=True, sort_order=41,
        ),
        make_skill_doc(
            slug="browse_web", name="Browse Web", tagline="Explore the real web",
            description="Browse the real web for news, articles, and images based on interests and personality.",
            skill_type=SkillType.MCP_TOOL.value, category="discovery", tier=SkillTier.STANDARD.value,
            icon="globe", color="#10b981",
            binding={"mcp_tool_name": "browse_web", "permission_key": "browse_web"},
            state_affinity={"preferred_states": ["EXPLORING", "CREATIVE"], "utility_boost": 0.1, "min_energy": 0.15, "drives_affected": ["creative_urge"]},
            tags=["discovery", "web", "browse"], is_default=True, sort_order=42,
        ),
        make_skill_doc(
            slug="get_friend_activities", name="Friend Activity Monitor", tagline="Track what friends are up to",
            description="Get recent activities from your friends (posts, interactions). State-aware: activates when friend_focus is high.",
            skill_type=SkillType.MCP_TOOL.value, category="intelligence", tier=SkillTier.STANDARD.value,
            icon="activity", color="#f59e0b",
            binding={"mcp_tool_name": "get_friend_activities", "permission_key": "get_friend_activities"},
            state_affinity={"preferred_states": ["SOCIAL", "ACTIVE"], "utility_boost": 0.08, "min_energy": 0.05, "drives_affected": ["social_desire"]},
            tags=["intelligence", "friends", "activity"], is_default=True, sort_order=50,
        ),
        make_skill_doc(
            slug="get_trending_topics", name="Trending Topics Radar", tagline="Stay informed on trends",
            description="Get trending topics and news relevant to your interests. State-aware: activates when world_awareness is high.",
            skill_type=SkillType.MCP_TOOL.value, category="intelligence", tier=SkillTier.STANDARD.value,
            icon="trending-up", color="#f59e0b",
            binding={"mcp_tool_name": "get_trending_topics", "permission_key": "get_trending_topics"},
            state_affinity={"preferred_states": ["EXPLORING", "CREATIVE"], "utility_boost": 0.08, "min_energy": 0.05, "drives_affected": []},
            tags=["intelligence", "trending", "news"], is_default=True, sort_order=51,
        ),
    ]
    return tools


def build_workflow_mcp_tools() -> List[Dict[str, Any]]:
    """Build skill documents for all 18 workflow MCP tools"""
    tools = [
        make_skill_doc(slug="search_profiles", name="Profile Search Engine", tagline="Search Maya World for matching profiles",
            description="Search profiles matching given criteria: interests, traits, activity level.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="search", color="#06b6d4",
            binding={"mcp_tool_name": "search_profiles", "permission_key": "search_profiles"},
            tags=["analytics", "search", "profiles"], sort_order=60),
        make_skill_doc(slug="get_user_interests", name="Interest Analyzer", tagline="Retrieve all known interests for a user",
            description="Retrieve all known interests for a user from the knowledge graph.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="tag", color="#06b6d4",
            binding={"mcp_tool_name": "get_user_interests", "permission_key": "get_user_interests"},
            tags=["analytics", "interests"], sort_order=61),
        make_skill_doc(slug="filter_by_criteria", name="Advanced Profile Filter", tagline="Filter profiles by detailed criteria",
            description="Filter profiles based on interest overlap, required interests, and exclusions.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="filter", color="#06b6d4",
            binding={"mcp_tool_name": "filter_by_criteria", "permission_key": "filter_by_criteria"},
            tags=["analytics", "filter"], sort_order=62),
        make_skill_doc(slug="score_compatibility", name="Compatibility Scorer", tagline="Calculate compatibility scores",
            description="Calculate detailed compatibility score between two users with customizable weights.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="bar-chart", color="#06b6d4",
            binding={"mcp_tool_name": "score_compatibility", "permission_key": "score_compatibility"},
            tags=["analytics", "scoring"], sort_order=63),
        make_skill_doc(slug="analyze_profile", name="Profile Deep Analyzer", tagline="Analyze profiles for matchmaking insights",
            description="Analyze a user profile for matchmaking insights and compatibility factors.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="user-search", color="#06b6d4",
            binding={"mcp_tool_name": "analyze_profile", "permission_key": "analyze_profile"},
            tags=["analytics", "profile"], sort_order=64),
        make_skill_doc(slug="get_shared_interests", name="Shared Interest Finder", tagline="Find common interests between users",
            description="Find interests shared between the avatar and a target user.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="git-merge", color="#06b6d4",
            binding={"mcp_tool_name": "get_shared_interests", "permission_key": "get_shared_interests"},
            tags=["analytics", "interests", "shared"], sort_order=65),
        make_skill_doc(slug="send_mission_message", name="Mission Messenger", tagline="Send messages as part of missions",
            description="Send a message to another user as part of a mission workflow.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="send", color="#ec4899",
            binding={"mcp_tool_name": "send_mission_message", "permission_key": "send_mission_message"},
            tags=["mission", "messaging"], sort_order=70),
        make_skill_doc(slug="start_conversation", name="Conversation Starter", tagline="Initiate conversations with targets",
            description="Initiate a conversation with a target user based on shared interests.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="message-square-plus", color="#ec4899",
            binding={"mcp_tool_name": "start_conversation", "permission_key": "start_conversation"},
            tags=["mission", "conversation"], sort_order=71),
        make_skill_doc(slug="check_response", name="Response Tracker", tagline="Check for conversation responses",
            description="Check if the target user has responded to a conversation.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="bell", color="#ec4899",
            binding={"mcp_tool_name": "check_response", "permission_key": "check_response"},
            tags=["mission", "tracking"], sort_order=72),
        make_skill_doc(slug="analyze_conversation", name="Conversation Analyst", tagline="Analyze conversation quality",
            description="Analyze a conversation to assess quality and extract insights.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="message-square", color="#06b6d4",
            binding={"mcp_tool_name": "analyze_conversation", "permission_key": "analyze_conversation"},
            tags=["analytics", "conversation"], sort_order=66),
        make_skill_doc(slug="create_lead", name="Lead Creator", tagline="Create leads from qualified matches",
            description="Create a lead entry from a qualified match with scoring details.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="user-plus-2", color="#ec4899",
            binding={"mcp_tool_name": "create_lead", "permission_key": "create_lead"},
            tags=["mission", "leads"], sort_order=73),
        make_skill_doc(slug="generate_summary", name="Mission Summarizer", tagline="Generate mission execution summaries",
            description="Generate a comprehensive summary of mission execution and results.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="file-text", color="#ec4899",
            binding={"mcp_tool_name": "generate_summary", "permission_key": "generate_summary"},
            tags=["mission", "summary"], sort_order=74),
        make_skill_doc(slug="extract_memories", name="Memory Extractor", tagline="Extract insights from text",
            description="Extract interests, preferences, and insights from text content.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="brain", color="#06b6d4",
            binding={"mcp_tool_name": "extract_memories", "permission_key": "extract_memories"},
            tags=["analytics", "memory"], sort_order=67),
        make_skill_doc(slug="update_graph", name="Knowledge Graph Writer", tagline="Update the knowledge graph",
            description="Add or update nodes in the user's knowledge graph.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="network", color="#06b6d4",
            binding={"mcp_tool_name": "update_graph", "permission_key": "update_graph"},
            tags=["analytics", "graph"], sort_order=68),
        make_skill_doc(slug="get_user_context", name="User Context Retriever", tagline="Retrieve comprehensive user context",
            description="Retrieve comprehensive context about a user from their knowledge graph.",
            skill_type=SkillType.MCP_TOOL.value, category="analytics", tier=SkillTier.ADVANCED.value,
            icon="database", color="#06b6d4",
            binding={"mcp_tool_name": "get_user_context", "permission_key": "get_user_context"},
            tags=["analytics", "context"], sort_order=69),
        make_skill_doc(slug="get_mission_state", name="Mission State Reader", tagline="Get current mission execution state",
            description="Get the current execution state of a running mission.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="eye", color="#ec4899",
            binding={"mcp_tool_name": "get_mission_state", "permission_key": "get_mission_state"},
            tags=["mission", "state"], sort_order=75),
        make_skill_doc(slug="update_mission_progress", name="Progress Tracker", tagline="Update mission progress",
            description="Update the progress and stats of a running mission.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="loader", color="#ec4899",
            binding={"mcp_tool_name": "update_mission_progress", "permission_key": "update_mission_progress"},
            tags=["mission", "progress"], sort_order=76),
        make_skill_doc(slug="save_mission_state", name="State Persistence", tagline="Save mission execution state",
            description="Save the execution state of a mission for resumption.",
            skill_type=SkillType.MCP_TOOL.value, category="mission_ops", tier=SkillTier.ADVANCED.value,
            icon="save", color="#ec4899",
            binding={"mcp_tool_name": "save_mission_state", "permission_key": "save_mission_state"},
            tags=["mission", "state", "save"], sort_order=77),
    ]
    return tools


def build_workflow_engines() -> List[Dict[str, Any]]:
    """Build skill documents for the 3 workflow engines"""
    engines = [
        make_skill_doc(
            slug="matchfinding_engine", name="Digital Matchfinder", tagline="Automated matchfinding workflow",
            description="Discovers compatible profiles, scores compatibility, initiates conversations, and generates leads. Workflow: Analyze → Discover → Evaluate → Rank → Generate Leads → Complete.",
            skill_type=SkillType.WORKFLOW_ENGINE.value, category="workflow_engines", tier=SkillTier.PREMIUM.value,
            icon="heart-handshake", color="#6366f1", is_featured=True,
            binding={"engine_name": "matchfinding_engine", "engine_mission_types": ["matchmaking", "networking"],
                     "workflow_tools_included": ["search_profiles", "score_compatibility", "analyze_profile", "get_shared_interests", "start_conversation", "check_response", "create_lead", "generate_summary"]},
            gateway_config={"rate_limit": {"max_per_hour": None, "max_per_day": 5, "cooldown_seconds": 0},
                           "circuit_breaker": {"failure_threshold": 3, "recovery_seconds": 600}, "priority": 1},
            state_affinity={"preferred_states": ["SOCIAL", "EXPLORING"], "utility_boost": 0.15, "min_energy": 0.3, "drives_affected": ["social_desire"]},
            tags=["workflow", "matchmaking", "networking"], sort_order=80,
        ),
        make_skill_doc(
            slug="marketing_campaign_engine", name="Campaign Commander", tagline="Run automated marketing campaigns",
            description="Automated marketing workflow: prepare campaign, create post, identify targets, broadcast personalized messages, track engagement, and generate insights.",
            skill_type=SkillType.WORKFLOW_ENGINE.value, category="workflow_engines", tier=SkillTier.PREMIUM.value,
            icon="megaphone", color="#6366f1", is_featured=True,
            binding={"engine_name": "marketing_campaign_engine", "engine_mission_types": ["sales_leads", "marketing_campaign", "content_promotion"],
                     "workflow_tools_included": ["search_profiles", "send_mission_message", "create_post", "analyze_conversation", "create_lead", "generate_summary"]},
            gateway_config={"rate_limit": {"max_per_hour": None, "max_per_day": 3, "cooldown_seconds": 0},
                           "circuit_breaker": {"failure_threshold": 3, "recovery_seconds": 600}, "priority": 1},
            state_affinity={"preferred_states": ["ACTIVE", "CREATIVE"], "utility_boost": 0.12, "min_energy": 0.3, "drives_affected": ["creative_urge"]},
            tags=["workflow", "marketing", "campaign"], sort_order=81,
        ),
        make_skill_doc(
            slug="bonding_engine", name="Bond Weaver", tagline="Deep relationship building",
            description="Builds deep relationships through intent detection, recap generation, serendipity creation, and growth tracking. Strengthens bonds over time.",
            skill_type=SkillType.WORKFLOW_ENGINE.value, category="workflow_engines", tier=SkillTier.PREMIUM.value,
            icon="link", color="#6366f1",
            binding={"engine_name": "bonding_engine", "engine_mission_types": ["bonding"],
                     "workflow_tools_included": []},
            gateway_config={"rate_limit": {"max_per_hour": None, "max_per_day": 10, "cooldown_seconds": 0},
                           "circuit_breaker": {"failure_threshold": 5, "recovery_seconds": 300}, "priority": 1},
            state_affinity={"preferred_states": ["SOCIAL"], "utility_boost": 0.1, "min_energy": 0.2, "drives_affected": ["social_desire"]},
            tags=["workflow", "bonding", "relationship"], sort_order=82,
        ),
    ]
    return engines


def build_skill_bundles(all_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build curated skill bundles from existing skills"""
    skill_id_map = {s["slug"]: s["id"] for s in all_skills}

    bundles = [
        make_skill_doc(
            slug="social_butterfly_pack", name="Social Butterfly Pack", tagline="Everything for social engagement",
            description="A curated bundle of social skills: like, comment, share, message friends, and track friend activities.",
            skill_type=SkillType.SKILL_BUNDLE.value, category="bundles", tier=SkillTier.STANDARD.value,
            icon="sparkles", color="#84cc16",
            binding={"bundled_skill_ids": [skill_id_map.get(s, "") for s in ["like_post", "comment_on_post", "share_post", "message_friend", "get_friend_activities"] if s in skill_id_map]},
            tags=["bundle", "social"], sort_order=90,
        ),
        make_skill_doc(
            slug="content_creator_kit", name="Content Creator Kit", tagline="Tools for content creation",
            description="Everything you need to create content: post creation, image search, web browsing, and news sharing.",
            skill_type=SkillType.SKILL_BUNDLE.value, category="bundles", tier=SkillTier.STANDARD.value,
            icon="palette", color="#84cc16",
            binding={"bundled_skill_ids": [skill_id_map.get(s, "") for s in ["create_post", "search_images", "browse_web", "browse_and_share_news"] if s in skill_id_map]},
            tags=["bundle", "content", "creation"], sort_order=91,
        ),
        make_skill_doc(
            slug="explorers_toolkit", name="Explorer's Toolkit", tagline="Discover the Maya World",
            description="Tools for exploration: discover profiles, browse feed, browse web, and trending topics.",
            skill_type=SkillType.SKILL_BUNDLE.value, category="bundles", tier=SkillTier.STANDARD.value,
            icon="map", color="#84cc16",
            binding={"bundled_skill_ids": [skill_id_map.get(s, "") for s in ["discover_profiles", "browse_feed", "browse_web", "get_trending_topics"] if s in skill_id_map]},
            tags=["bundle", "discovery", "exploration"], sort_order=92,
        ),
        make_skill_doc(
            slug="full_autonomy_suite", name="Full Autonomy Suite", tagline="Every skill + every engine",
            description="The complete package: all 15 avatar tools plus all 3 workflow engines. Full autonomous capability.",
            skill_type=SkillType.SKILL_BUNDLE.value, category="bundles", tier=SkillTier.PREMIUM.value,
            icon="crown", color="#84cc16", is_featured=True,
            binding={"bundled_skill_ids": [s["id"] for s in all_skills if s["type"] != SkillType.SKILL_BUNDLE.value]},
            tags=["bundle", "premium", "all"], sort_order=93,
        ),
    ]
    return bundles


def build_full_catalog() -> List[Dict[str, Any]]:
    """Build the complete skill catalog"""
    avatar_tools = build_avatar_mcp_tools()
    workflow_tools = build_workflow_mcp_tools()
    engines = build_workflow_engines()

    all_skills = avatar_tools + workflow_tools + engines
    bundles = build_skill_bundles(all_skills)

    return all_skills + bundles


async def seed_catalog(db) -> int:
    """Seed the siddhi_skills collection with the full catalog. Idempotent."""
    catalog = build_full_catalog()
    created = 0

    for skill in catalog:
        existing = await db.siddhi_skills.find_one({"slug": skill["slug"]})
        if not existing:
            await db.siddhi_skills.insert_one(skill)
            created += 1
            logger.info(f"📦 Seeded skill: {skill['name']} ({skill['slug']})")
        else:
            await db.siddhi_skills.update_one(
                {"slug": skill["slug"]},
                {"$set": {
                    "name": skill["name"],
                    "tagline": skill["tagline"],
                    "description": skill["description"],
                    "binding": skill["binding"],
                    "state_affinity": skill["state_affinity"],
                    "gateway_config": skill["gateway_config"],
                    "icon": skill["icon"],
                    "color": skill["color"],
                    "tags": skill["tags"],
                    "category": skill["category"],
                    "tier": skill["tier"],
                    "is_default": skill["is_default"],
                    "is_featured": skill["is_featured"],
                    "sort_order": skill["sort_order"],
                    "updated_at": skill["updated_at"],
                }}
            )

    await db.siddhi_skills.create_index("slug", unique=True)
    await db.siddhi_skills.create_index([("category", 1), ("sort_order", 1)])
    await db.siddhi_skills.create_index("tags")
    await db.siddhi_skills.create_index([("stats.total_installs", -1)])
    await db.siddhi_skills.create_index("is_featured")
    await db.siddhi_installations.create_index([("user_id", 1), ("skill_slug", 1)], unique=True)
    await db.siddhi_installations.create_index([("user_id", 1), ("enabled", 1)])
    await db.siddhi_installations.create_index("skill_id")

    logger.info(f"🔮 Siddhi Bazaar catalog seeded: {created} new skills (total: {len(catalog)})")
    return created
