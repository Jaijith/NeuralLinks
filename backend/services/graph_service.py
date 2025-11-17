"""
Graph Service
Wrapper around GraphRAG for graph operations
"""

from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.rag import GraphRAG
from domain.graph.builder import GraphBuilder
import logging

logger = logging.getLogger(__name__)


class GraphService:
    """Service for graph operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase, graph_rag: GraphRAG, graph_builder: Optional[GraphBuilder] = None):
        self.db = db
        self.graph_rag = graph_rag
        self.graph_builder = graph_builder
    
    async def get_user_context(self, user_id: str, max_nodes: int = 20) -> Dict[str, Any]:
        """Get user context from knowledge graph"""
        return await self.graph_rag.get_user_context(user_id, max_nodes)
    
    async def get_relevant_context(self, user_id: str, query_type: str, topic: Optional[str] = None) -> str:
        """Get relevant context for specific query"""
        return await self.graph_rag.get_relevant_context(user_id, query_type, topic)
    
    async def get_avatar_personality_profile(self, user_id: str) -> str:
        """Get avatar personality profile"""
        return await self.graph_rag.get_avatar_personality_profile(user_id)
    
    async def calculate_compatibility(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """Calculate compatibility between two users"""
        return await self.graph_rag.calculate_compatibility(user1_id, user2_id)
    
    async def get_visualization_data(self, user_id: str, max_nodes: int = 1000) -> Dict[str, Any]:
        """Get graph visualization data"""
        context = await self.graph_rag.get_user_context(user_id, max_nodes)
        
        # Get actual counts from database
        total_nodes = await self.db.graph_nodes.count_documents({"user_id": user_id})
        actual_interests_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "interest"})
        actual_traits_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "trait"})
        actual_values_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "value"})
        actual_experiences_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "experience"})
        actual_preferences_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "preference"})
        
        # Get personality profile
        personality_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        
        # Get user document for avatar info
        user_doc = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        
        # Format interest labels (helper function)
        def _format_interest_label(label: str) -> str:
            if not label:
                return ""
            # Remove prefixes
            if label.startswith("youtube_category_"):
                label = label.replace("youtube_category_", "", 1)
            elif label.startswith("youtube_tag_"):
                label = label.replace("youtube_tag_", "", 1)
            # Replace underscores with spaces and title case
            label = label.replace("_", " ").replace("-", " ")
            words = label.split()
            label = " ".join(word.capitalize() for word in words)
            return label
        
        # Count by source
        nodes = await self.db.graph_nodes.find({"user_id": user_id}).to_list(10000)
        source_counts = {}
        for node in nodes:
            source = node.get("properties", {}).get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Format for visualization (matching frontend expectations)
        visualization_data = {
            "avatar_info": {
                "name": user_doc.get("avatar_name", "Avatar") if user_doc else "Avatar",
                "picture": user_doc.get("avatar_picture") if user_doc else None,
                "bio": user_doc.get("avatar_bio", "") if user_doc else "",
                "archetype": user_doc.get("archetype", "casual_observer") if user_doc else "casual_observer"
            },
            "graph_stats": {
                "total_nodes": total_nodes,
                "interests_count": actual_interests_count,
                "traits_count": actual_traits_count,
                "values_count": actual_values_count,
                "experiences_count": actual_experiences_count,
                "preferences_count": actual_preferences_count
            },
            "top_interests": [
                {
                    **interest,
                    "label": _format_interest_label(interest.get("label", ""))
                }
                for interest in context.get("interests", [])[:50]
            ],
            "top_traits": context.get("traits", [])[:20],
            "top_values": context.get("values", [])[:20],
            "personality_profile": personality_profile,
            "sources": source_counts
        }
        
        return visualization_data
    
    async def build_graph_from_profile(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Build graph from user profile"""
        if not self.graph_builder:
            return {"success": False, "error": "Graph builder not available"}
        
        try:
            await self.graph_builder.build_graph_from_profile(user_doc)
            return {"success": True, "message": "Graph built from profile"}
        except Exception as e:
            logger.error(f"Graph build error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def enrich_graph_from_post(self, post_text: str, user_id: str) -> Dict[str, Any]:
        """Enrich graph from post content"""
        if not self.graph_builder:
            return {"success": False, "error": "Graph builder not available"}
        
        try:
            await self.graph_builder.enrich_graph_from_post(post_text, user_id)
            return {"success": True, "message": "Graph enriched from post"}
        except Exception as e:
            logger.error(f"Graph enrichment error: {str(e)}")
            return {"success": False, "error": str(e)}

