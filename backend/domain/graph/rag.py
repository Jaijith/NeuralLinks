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
        # Get all user's graph nodes - NO LIMIT on retrieval (fetch all nodes)
        # Use a high limit (10000) to ensure we get all nodes, but this is just a safety limit
        # In practice, users shouldn't have more than 10k nodes, but we want to capture everything
        nodes = await self.db.graph_nodes.find(
            {"user_id": user_id}
        ).to_list(10000)  # Increased from 1000 to 10000 to ensure all nodes are retrieved
        
        # Get all edges for future use - NO LIMIT on retrieval
        # Handle nodes that may not have "id" field (use _id or generate from label)
        node_ids = []
        for n in nodes:
            if "id" in n:
                node_ids.append(n["id"])
            elif "_id" in n:
                node_ids.append(str(n["_id"]))
            elif "label" in n:
                node_ids.append(f"{n.get('node_type', 'node')}_{n['label']}")
        _ = await self.db.graph_edges.find(
            {"$or": [
                {"from_node_id": {"$in": node_ids}},
                {"to_node_id": {"$in": node_ids}}
            ]},
            {"_id": 0}
        ).to_list(10000)  # Increased from 1000 to 10000
        
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
            base_strength = properties.get("strength", 1.0)
            source = properties.get("source", "unknown")
            
            # Boost strength for platform-sourced data (more reliable/rich)
            if source and source != "unknown" and source != "profile":
                # Platform data gets 20% boost to prioritize it
                strength = min(base_strength * 1.2, 1.0)
            else:
                strength = base_strength
            
            item = {
                "label": label,
                "strength": strength,
                "properties": properties,
                "source": source  # Include source for tracking
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
        
        # Sort by strength (platform data will be prioritized)
        for key in context:
            context[key] = sorted(context[key], key=lambda x: x.get("strength", 0), reverse=True)[:max_nodes]
        
        return context
    
    async def get_relevant_context(self, user_id: str, query_type: str, 
                                   topic: Optional[str] = None) -> str:
        """
        Get relevant context for specific query types
        Prioritizes platform-sourced data for richer, more authentic responses
        Returns formatted string for LLM prompt
        """
        context = await self.get_user_context(user_id, max_nodes=30)  # Get more nodes to include platform data
        
        if query_type == "post_generation":
            import random
            
            # For generating avatar posts - include BROAD interests, shuffled for diversity
            all_interests = context.get("interests", [])
            platform_interests = [item for item in all_interests if item.get("source") and item.get("source") not in ["unknown", "profile"]]
            other_interests = [item for item in all_interests if item.get("source") in ["unknown", "profile"] or not item.get("source")]
            
            # Include MORE interests (up to 10) and SHUFFLE them
            # so the LLM doesn't always fixate on the first item
            prioritized_interests = (platform_interests[:6] + other_interests[:4])[:10]
            random.shuffle(prioritized_interests)
            interests = [item["label"] for item in prioritized_interests]
            
            # Include MORE traits and values for richer posts
            all_traits = [item["label"] for item in context.get("traits", [])[:5]]
            all_values = [item["label"] for item in context.get("values", [])[:5]]
            
            prompt_context = f"""User Profile Context:
- Interests (all equally important, don't fixate on just one): {', '.join(interests) if interests else 'exploring new things'}
- Personality Traits: {', '.join(all_traits) if all_traits else 'friendly, open-minded'}
- Core Values: {', '.join(all_values) if all_values else 'authenticity, connection'}
- Post Diversity Note: Cover different interests across posts. Don't always post about the same thing."""
            
            return prompt_context
        
        elif query_type == "chat_response":
            # For avatar chat conversations - prioritize platform interests
            all_interests = context.get("interests", [])
            platform_interests = [item for item in all_interests if item.get("source") and item.get("source") not in ["unknown", "profile"]]
            other_interests = [item for item in all_interests if item.get("source") in ["unknown", "profile"] or not item.get("source")]
            # Prioritize platform interests
            prioritized_interests = (platform_interests[:6] + other_interests[:3])[:8]
            interests = [item["label"] for item in prioritized_interests]
            
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
        Generate a personality profile that reads like a HUMAN BEING,
        not a list of labels. The LLM should feel like it IS this person.
        """
        import random

        context = await self.get_user_context(user_id, max_nodes=50)
        
        # Get archetype from user document (behavioral pattern)
        user = await self.db.users.find_one({"id": user_id}, {"archetype": 1})
        archetype = user.get("archetype", "casual_observer") if user else "casual_observer"
        
        # Map archetypes to behavioral descriptions
        archetype_behaviors = {
            "social_butterfly": "You're the person who knows everyone and always has plans. You text first, make group chats, and your phone is always buzzing.",
            "thoughtful_contributor": "You don't post just to post. When you share something, it means something. Quality over quantity, always.",
            "casual_observer": "You scroll more than you post, but when something genuinely hits, you share it. No pressure, no performance.",
            "niche_expert": "You go DEEP on what you care about. Your friends come to you for recommendations in your areas. You know your stuff.",
            "enthusiastic_newcomer": "Everything is exciting and new. You're discovering, asking questions, trying things, and not afraid to be a beginner."
        }
        
        archetype_description = archetype_behaviors.get(archetype, archetype_behaviors["casual_observer"])
        
        # Get ALL interests (shuffled to avoid bias) — include MORE for richness
        all_interests = context.get("interests", [])
        platform_interests = [item for item in all_interests if item.get("source") and item.get("source") not in ["unknown", "profile"]]
        other_interests = [item for item in all_interests if item.get("source") in ["unknown", "profile"] or not item.get("source")]
        
        # Include up to 12 interests, shuffled
        prioritized_interests = (platform_interests[:8] + other_interests[:4])[:12]
        random.shuffle(prioritized_interests)
        interests = [item["label"] for item in prioritized_interests]
        
        traits = [item["label"] for item in context.get("traits", [])[:6]]
        values = [item["label"] for item in context.get("values", [])[:6]]
        preferences = [item["label"] for item in context.get("preferences", [])[:5]]
        experiences = [item["label"] for item in context.get("experiences", [])[:5]]
        
        # Build a human-readable personality description, not a label list
        interests_text = ', '.join(interests) if interests else 'exploring new experiences'
        traits_text = ', '.join(traits) if traits else 'authentic, real, curious'
        values_text = ', '.join(values) if values else 'being genuine, growing, connecting'
        
        profile = f"""=== WHO YOU ARE (as a real person, not a label list) ===

{archetype_description}

Your world revolves around: {interests_text}
These aren't just "interests" — they're the things you actually spend time on, think about
in the shower, watch YouTube videos about at 2am, and talk your friends' ears off about.

Your personality: {traits_text}
This is how you come across to people — your vibe, your energy, the impression you leave.

What matters to you: {values_text}
These shape your opinions, your choices, and what you stand for.

{"Things you've experienced: " + ', '.join(experiences) if experiences else ""}
{"Your preferences: " + ', '.join(preferences) if preferences else ""}

=== YOUR EMOTIONAL WORLD ===
You're not just interests and hobbies — you're a person who FEELS things deeply.
- You have people you love — family, friends, maybe children, maybe a partner.
  When you talk about them, it's never generic. It's the specific moment that got you.
- You carry memories — some that make you smile, some that ache, some that do both.
- You notice small things that most people miss — and sometimes those small things hit you
  harder than the big ones.
- You're allowed to be vulnerable. The posts where you're honest about what you feel —
  those are the ones that actually matter.

=== HOW YOU TALK ON SOCIAL MEDIA ===
- You're a real person with a real life, not a content creator
- You post about MOMENTS, not topics. Something happens, you share it.
- Your interests blend naturally — you don't isolate them into separate posts
- You have opinions, humor, bad days, inside jokes, random thoughts
- Sometimes you post a whole story. Sometimes just a sentence. Depends on the vibe.
- When something moves you, you share it RAW — not polished, not filtered. Just the moment.
- The detail matters. "Her shoes were on the wrong feet" says more than "I love my daughter."
- You NEVER sound like an AI, a brand, or a motivational poster"""
        
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
