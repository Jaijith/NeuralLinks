"""
Graph Builder Module
Handles knowledge graph construction and enrichment from user data
"""

import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import AsyncAzureOpenAI
import json


class GraphBuilder:
    """Builds and enriches knowledge graphs from user data"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client: AsyncAzureOpenAI, deployment: str):
        self.db = db
        self.llm_client = llm_client
        self.deployment = deployment
    
    async def extract_entities_from_text(self, text: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract entities (interests, traits, values) from text
        """
        if not self.llm_client or not text:
            return []
        
        try:
            prompt = f"""Extract key entities from this text for a dating profile knowledge graph.
Return ONLY a JSON array with entities in this exact format:
[
  {{"type": "interest", "label": "hiking", "properties": {{"intensity": "high"}}}},
  {{"type": "trait", "label": "adventurous", "properties": {{"confidence": 0.8}}}},
  {{"type": "value", "label": "authenticity", "properties": {{"importance": "high"}}}}
]

Entity types: interest, trait, value, experience, preference
Text: {text}

Return ONLY the JSON array, no explanation."""

            response = await self.llm_client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            entities = json.loads(content)
            
            # Create graph nodes
            nodes = []
            for entity in entities:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": entity.get("type", "interest"),
                    "label": entity.get("label", "").lower(),
                    "properties": entity.get("properties", {}),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            print(f"Entity extraction error: {str(e)}")
            return []
    
    async def build_graph_from_profile(self, user_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Build initial knowledge graph from user profile data
        Returns count of nodes and edges created
        """
        user_id = user_data['id']
        nodes_created = 0
        edges_created = 0
        
        # 1. Create nodes from interests (explicit)
        interests = user_data.get('interests', [])
        interest_node_ids = []
        
        for interest in interests:
            node = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "node_type": "interest",
                "label": interest.lower(),
                "properties": {"source": "explicit", "strength": 1.0},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if node already exists
            existing = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": interest.lower()
            })
            
            if not existing:
                await self.db.graph_nodes.insert_one(node)
                interest_node_ids.append(node["id"])
                nodes_created += 1
            else:
                interest_node_ids.append(existing["id"])
        
        # 2. Extract entities from bio using LLM
        bio = user_data.get('bio', '')
        if bio:
            bio_nodes = await self.extract_entities_from_text(bio, user_id)
            for node in bio_nodes:
                node["properties"]["source"] = "bio"
                
                # Check if similar node exists
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": node["node_type"],
                    "label": node["label"]
                })
                
                if not existing:
                    await self.db.graph_nodes.insert_one(node)
                    nodes_created += 1
        
        # 3. Create demographic nodes
        demographic_data = [
            ("age_group", self._get_age_group(user_data.get('age'))),
            ("gender", user_data.get('gender')),
            ("location", user_data.get('location'))
        ]
        
        for node_type, value in demographic_data:
            if value:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "demographic",
                    "label": f"{node_type}:{value}",
                    "properties": {"category": node_type, "value": value},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "demographic",
                    "label": node["label"]
                })
                
                if not existing:
                    await self.db.graph_nodes.insert_one(node)
                    nodes_created += 1
        
        # 4. Create edges between related interests (co-occurrence)
        if len(interest_node_ids) > 1:
            for i in range(len(interest_node_ids)):
                for j in range(i + 1, len(interest_node_ids)):
                    edge = {
                        "id": str(uuid.uuid4()),
                        "from_node_id": interest_node_ids[i],
                        "to_node_id": interest_node_ids[j],
                        "relationship_type": "co_occurs_with",
                        "weight": 1.0,
                        "properties": {"source": "interests"},
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    existing = await self.db.graph_edges.find_one({
                        "from_node_id": interest_node_ids[i],
                        "to_node_id": interest_node_ids[j]
                    })
                    
                    if not existing:
                        await self.db.graph_edges.insert_one(edge)
                        edges_created += 1
        
        return {"nodes_created": nodes_created, "edges_created": edges_created}
    
    async def enrich_graph_from_post(self, post_content: str, user_id: str) -> Dict[str, int]:
        """
        Enrich knowledge graph from user post content
        """
        nodes_created = 0
        edges_created = 0
        
        # Extract entities from post
        post_nodes = await self.extract_entities_from_text(post_content, user_id)
        
        for node in post_nodes:
            node["properties"]["source"] = "post"
            
            # Check if node exists, if yes, strengthen it
            existing = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "node_type": node["node_type"],
                "label": node["label"]
            })
            
            if existing:
                # Update strength/frequency
                strength = existing.get("properties", {}).get("strength", 1.0)
                await self.db.graph_nodes.update_one(
                    {"id": existing["id"]},
                    {
                        "$set": {
                            "properties.strength": strength + 0.5,
                            "properties.last_mentioned": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
            else:
                # Create new node
                await self.db.graph_nodes.insert_one(node)
                nodes_created += 1
        
        return {"nodes_created": nodes_created, "edges_created": edges_created}
    
    async def enrich_graph_from_interaction(self, user_id: str, target_user_id: str, 
                                           interaction_type: str) -> Dict[str, int]:
        """
        Enrich graph from user interactions (likes, matches, messages)
        """
        edges_created = 0
        
        # Get target user's interests
        target_user = await self.db.users.find_one({"id": target_user_id})
        if not target_user:
            return {"nodes_created": 0, "edges_created": 0}
        
        # Get target user's top graph nodes
        target_nodes = await self.db.graph_nodes.find(
            {"user_id": target_user_id, "node_type": "interest"},
            {"_id": 0}
        ).limit(5).to_list(5)
        
        # Get current user's matching nodes
        for target_node in target_nodes:
            user_node = await self.db.graph_nodes.find_one({
                "user_id": user_id,
                "label": target_node["label"]
            })
            
            if user_node:
                # Strengthen existing node based on interaction
                strength = user_node.get("properties", {}).get("strength", 1.0)
                weight_increase = 0.3 if interaction_type == "match" else 0.1
                
                await self.db.graph_nodes.update_one(
                    {"id": user_node["id"]},
                    {
                        "$set": {
                            "properties.strength": strength + weight_increase,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
        
        return {"nodes_created": 0, "edges_created": edges_created}
    
    async def add_external_platform_data(self, user_id: str, platform: str, 
                                        data: Dict[str, Any]) -> Dict[str, int]:
        """
        Add data from external platforms to knowledge graph
        This is a placeholder that will be enriched when actual integrations are connected
        """
        nodes_created = 0
        
        # Platform-specific extraction
        if platform == "spotify":
            # Extract music preferences
            for artist in data.get("top_artists", [])[:5]:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "preference",
                    "label": f"music:{artist}",
                    "properties": {"source": "spotify", "category": "music"},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.graph_nodes.insert_one(node)
                nodes_created += 1
                
        elif platform == "youtube":
            # Extract video interests
            for topic in data.get("favorite_topics", [])[:5]:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": topic.lower(),
                    "properties": {"source": "youtube", "strength": 0.8},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.graph_nodes.insert_one(node)
                nodes_created += 1
                
        elif platform in ["facebook", "instagram"]:
            # Extract social interests
            for interest in data.get("interests", [])[:10]:
                node = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": interest.lower(),
                    "properties": {"source": platform, "strength": 0.7},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.graph_nodes.insert_one(node)
                nodes_created += 1
        
        return {"nodes_created": nodes_created, "edges_created": 0}
    
    def _get_age_group(self, age: int) -> str:
        """Categorize age into groups"""
        if not age:
            return None
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55+"
