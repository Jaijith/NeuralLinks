"""
Graph RAG Module
Handles graph querying and retrieval for RAG-powered responses
"""

from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import math


class GraphRAG:
    """Graph-based Retrieval Augmented Generation"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_user_context(self, user_id: str, max_nodes: int = 20) -> Dict[str, Any]:
        """
        Get comprehensive user context from knowledge graph
        Returns structured context for LLM prompts
        """
        # Get all user's graph nodes
        nodes = await self.db.graph_nodes.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Get all edges for future use
        node_ids = [n["id"] for n in nodes]
        _ = await self.db.graph_edges.find(
            {"$or": [
                {"from_node_id": {"$in": node_ids}},
                {"to_node_id": {"$in": node_ids}}
            ]},
            {"_id": 0}
        ).to_list(1000)
        
        # Organize by type
        context = {
            "interests": [],
            "traits": [],
            "values": [],
            "experiences": [],
            "preferences": [],
            "demographics": []
        }
        
        for node in nodes:
            node_type = node.get("node_type", "interest")
            label = node.get("label", "")
            properties = node.get("properties", {})
            strength = properties.get("strength", 1.0)
            
            item = {
                "label": label,
                "strength": strength,
                "properties": properties
            }
            
            # Map singular node types to plural context keys
            type_mapping = {
                "interest": "interests",
                "trait": "traits", 
                "value": "values",
                "experience": "experiences",
                "preference": "preferences",
                "demographic": "demographics"
            }
            
            context_key = type_mapping.get(node_type, "interests")  # Default to interests
            context[context_key].append(item)
        
        # Sort by strength
        for key in context:
            context[key] = sorted(context[key], key=lambda x: x.get("strength", 0), reverse=True)[:max_nodes]
        
        return context
    
    async def get_relevant_context(self, user_id: str, query_type: str, 
                                   topic: Optional[str] = None) -> str:
        """
        Get relevant context for specific query types
        Returns formatted string for LLM prompt
        """
        context = await self.get_user_context(user_id)
        
        if query_type == "post_generation":
            # For generating avatar posts
            interests = [item["label"] for item in context.get("interests", [])[:5]]
            traits = [item["label"] for item in context.get("traits", [])[:3]]
            values = [item["label"] for item in context.get("values", [])[:3]]
            
            prompt_context = f"""User Profile Context:
- Key Interests: {', '.join(interests) if interests else 'exploring new things'}
- Personality Traits: {', '.join(traits) if traits else 'friendly, open-minded'}
- Core Values: {', '.join(values) if values else 'authenticity, connection'}"""
            
            return prompt_context
        
        elif query_type == "chat_response":
            # For avatar chat conversations
            interests = [item["label"] for item in context.get("interests", [])[:8]]
            traits = [item["label"] for item in context.get("traits", [])[:5]]
            
            prompt_context = f"""Avatar Personality:
- Interests & Hobbies: {', '.join(interests) if interests else 'various activities'}
- Personality: {', '.join(traits) if traits else 'friendly and engaging'}"""
            
            return prompt_context
        
        elif query_type == "matching":
            # For finding compatible matches
            interests = [item["label"] for item in context.get("interests", [])]
            values = [item["label"] for item in context.get("values", [])]
            
            return {
                "interests": interests,
                "values": values,
                "traits": [item["label"] for item in context.get("traits", [])]
            }
        
        return ""
    
    async def calculate_compatibility(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """
        Calculate compatibility score between two users based on their graphs
        """
        # Get both users' graphs
        user1_nodes = await self.db.graph_nodes.find({"user_id": user1_id}, {"_id": 0}).to_list(1000)
        user2_nodes = await self.db.graph_nodes.find({"user_id": user2_id}, {"_id": 0}).to_list(1000)
        
        # Extract labels by type
        user1_interests = set(n["label"] for n in user1_nodes if n.get("node_type") == "interest")
        user2_interests = set(n["label"] for n in user2_nodes if n.get("node_type") == "interest")
        
        user1_values = set(n["label"] for n in user1_nodes if n.get("node_type") == "value")
        user2_values = set(n["label"] for n in user2_nodes if n.get("node_type") == "value")
        
        user1_traits = set(n["label"] for n in user1_nodes if n.get("node_type") == "trait")
        user2_traits = set(n["label"] for n in user2_nodes if n.get("node_type") == "trait")
        
        # Calculate overlaps
        shared_interests = user1_interests & user2_interests
        shared_values = user1_values & user2_values
        shared_traits = user1_traits & user2_traits
        
        # Calculate scores
        interest_score = self._jaccard_similarity(user1_interests, user2_interests) * 100
        value_score = self._jaccard_similarity(user1_values, user2_values) * 100
        trait_score = self._jaccard_similarity(user1_traits, user2_traits) * 100
        
        # Weighted compatibility
        compatibility = (interest_score * 0.5) + (value_score * 0.3) + (trait_score * 0.2)
        
        return {
            "compatibility_score": round(compatibility, 2),
            "shared_interests": list(shared_interests),
            "shared_values": list(shared_values),
            "shared_traits": list(shared_traits),
            "breakdown": {
                "interests": round(interest_score, 2),
                "values": round(value_score, 2),
                "traits": round(trait_score, 2)
            }
        }
    
    async def get_avatar_personality_profile(self, user_id: str) -> str:
        """
        Generate a comprehensive personality profile for the avatar based on graph
        """
        context = await self.get_user_context(user_id)
        
        interests = [item["label"] for item in context.get("interests", [])[:8]]
        traits = [item["label"] for item in context.get("traits", [])[:5]]
        values = [item["label"] for item in context.get("values", [])[:5]]
        preferences = [item["label"] for item in context.get("preferences", [])[:5]]
        
        profile = f"""Personality Profile:
You are an avatar representing a user with these characteristics:

Core Interests: {', '.join(interests) if interests else 'exploring new experiences'}
Personality Traits: {', '.join(traits) if traits else 'friendly, open, curious'}
Core Values: {', '.join(values) if values else 'authenticity, growth, connection'}
Preferences: {', '.join(preferences) if preferences else 'meaningful conversations'}

Your communication style should reflect these characteristics naturally. Be authentic, engaging, and true to these interests and values."""
        
        return profile
    
    async def find_similar_users(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find users with similar graph profiles
        """
        # Get current user's nodes
        user_nodes = await self.db.graph_nodes.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(1000)
        
        user_labels = set(n["label"] for n in user_nodes if n.get("node_type") in ["interest", "value"])
        
        # Get all other users
        all_users = await self.db.users.find({"id": {"$ne": user_id}}, {"_id": 0, "id": 1}).to_list(1000)
        
        similarities = []
        
        for other_user in all_users[:50]:  # Limit for performance
            other_user_id = other_user["id"]
            
            # Get other user's nodes
            other_nodes = await self.db.graph_nodes.find(
                {"user_id": other_user_id},
                {"_id": 0}
            ).to_list(1000)
            
            other_labels = set(n["label"] for n in other_nodes if n.get("node_type") in ["interest", "value"])
            
            # Calculate similarity
            similarity = self._jaccard_similarity(user_labels, other_labels)
            
            if similarity > 0:
                similarities.append({
                    "user_id": other_user_id,
                    "similarity": similarity,
                    "shared_items": list(user_labels & other_labels)
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:limit]
    
    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    async def get_conversation_context(self, user_id: str, other_user_id: str) -> str:
        """
        Get conversation context between two users for avatar chat
        """
        # Get both users' contexts
        user_context = await self.get_user_context(user_id, max_nodes=10)
        other_context = await self.get_user_context(other_user_id, max_nodes=10)
        
        # Get compatibility
        compatibility = await self.calculate_compatibility(user_id, other_user_id)
        
        user_interests = [item["label"] for item in user_context.get("interests", [])[:5]]
        other_interests = [item["label"] for item in other_context.get("interests", [])[:5]]
        shared = compatibility.get("shared_interests", [])
        
        context = f"""Conversation Context:
Your interests: {', '.join(user_interests)}
Their interests: {', '.join(other_interests)}
Shared interests: {', '.join(shared) if shared else 'discovering common ground'}
Compatibility: {compatibility.get('compatibility_score', 0):.0f}%

Use this context to have natural, engaging conversations that explore shared interests and build connection."""
        
        return context
