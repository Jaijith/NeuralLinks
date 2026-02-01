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
        actual_connections_count = await self.db.graph_nodes.count_documents({"user_id": user_id, "node_type": "connection"})
        
        # Get personality profile
        personality_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        
        # Get user document for avatar info and connections
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
        
        # Get all connections from multiple sources
        connections = await self._get_all_connections(user_id, user_doc)
        
        # Get interests directly from database with proper IDs
        interest_nodes = await self.db.graph_nodes.find({
            "user_id": user_id,
            "node_type": "interest"
        }).sort("strength", -1).limit(50).to_list(50)
        
        top_interests = []
        for node in interest_nodes:
            top_interests.append({
                "id": str(node.get("id") or node.get("_id")),
                "label": _format_interest_label(node.get("display_label") or node.get("label", "")),
                "strength": node.get("strength", 0.5),
                "source": node.get("properties", {}).get("source", "unknown"),
                "mention_count": node.get("mention_count", 0),
                "editable": True
            })
        
        # Get traits directly from database with proper IDs
        trait_nodes = await self.db.graph_nodes.find({
            "user_id": user_id,
            "node_type": "trait"
        }).sort("strength", -1).limit(20).to_list(20)
        
        top_traits = []
        for node in trait_nodes:
            top_traits.append({
                "id": str(node.get("id") or node.get("_id")),
                "label": node.get("display_label") or node.get("label", "").title(),
                "strength": node.get("strength", 0.5),
                "source": node.get("properties", {}).get("source", "unknown"),
                "editable": True
            })
        
        # Get values directly from database
        value_nodes = await self.db.graph_nodes.find({
            "user_id": user_id,
            "node_type": "value"
        }).sort("strength", -1).limit(20).to_list(20)
        
        top_values = []
        for node in value_nodes:
            top_values.append({
                "id": str(node.get("id") or node.get("_id")),
                "label": node.get("display_label") or node.get("label", "").title(),
                "strength": node.get("strength", 0.5),
                "source": node.get("properties", {}).get("source", "unknown")
            })
        
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
                "preferences_count": actual_preferences_count,
                "connections_count": len(connections)
            },
            "top_interests": top_interests,
            "top_connections": connections,
            "top_traits": top_traits,
            "top_values": top_values,
            "personality_profile": personality_profile,
            "sources": source_counts
        }
        
        return visualization_data
    
    async def _get_all_connections(self, user_id: str, user_doc: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all connections from multiple sources"""
        connections = []
        seen_names = set()
        
        # 1. Get connections from users.connections (voice conversations)
        if user_doc:
            for conn in user_doc.get("connections", []):
                name = conn.get("name", "").strip()
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    connections.append({
                        "id": f"conn_{user_id}_{name.lower().replace(' ', '_')}",
                        "name": name,
                        "relationship": conn.get("relationship", "friend"),
                        "source": conn.get("source", "conversation"),
                        "details": conn.get("details", ""),
                        "mentioned_count": conn.get("mentioned_count", 1),
                        "last_mentioned": conn.get("last_mentioned"),
                        "editable": True
                    })
        
        # 2. Get connections from graph_nodes (may include implicit from posts)
        conn_nodes = await self.db.graph_nodes.find({
            "user_id": user_id,
            "node_type": "connection"
        }).to_list(100)
        
        for node in conn_nodes:
            name = node.get("display_label") or node.get("label", "").title()
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                props = node.get("properties", {})
                connections.append({
                    "id": node.get("id", str(node.get("_id"))),
                    "name": name,
                    "relationship": props.get("relationship", "friend"),
                    "source": props.get("source", "implicit"),
                    "details": props.get("details", ""),
                    "mentioned_count": node.get("mention_count", 1),
                    "strength": node.get("strength", 0.5),
                    "editable": True
                })
        
        # 3. Get friends (actual app friends)
        friends_cursor = self.db.friendships.find({
            "$or": [
                {"user_id": user_id, "status": "accepted"},
                {"friend_id": user_id, "status": "accepted"}
            ]
        })
        friends = await friends_cursor.to_list(100)
        
        for friendship in friends:
            friend_user_id = friendship.get("friend_id") if friendship.get("user_id") == user_id else friendship.get("user_id")
            friend_doc = await self.db.users.find_one({"id": friend_user_id}, {"name": 1, "avatar_name": 1, "picture": 1})
            
            if friend_doc:
                friend_name = friend_doc.get("name") or friend_doc.get("avatar_name", "Friend")
                if friend_name and friend_name.lower() not in seen_names:
                    seen_names.add(friend_name.lower())
                    connections.append({
                        "id": f"friend_{friend_user_id}",
                        "name": friend_name,
                        "relationship": "friend",
                        "source": "app_friend",
                        "friend_id": friend_user_id,
                        "picture": friend_doc.get("picture"),
                        "editable": False  # App friends can't be edited here
                    })
        
        # Sort by source priority and mention count
        source_priority = {"conversation": 0, "app_friend": 1, "implicit": 2}
        connections.sort(key=lambda x: (source_priority.get(x.get("source", "implicit"), 3), -x.get("mentioned_count", 0)))
        
        return connections
    
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

