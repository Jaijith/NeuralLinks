"""
Memory MCP Tools
Tools for extracting and updating knowledge graph
"""

import logging
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime, timezone
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class ExtractMemoriesTool(WorkflowBaseTool):
    """Extract memories from text for knowledge graph"""
    
    name = "extract_memories"
    description = "Extract interests, preferences, and insights from text"
    
    schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to extract memories from"
            },
            "context": {
                "type": "string",
                "description": "Context for extraction (chat, mission, etc.)"
            }
        },
        "required": ["text"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        text = kwargs.get("text", "")
        context = kwargs.get("context", "general")
        
        if not text.strip():
            return {"success": False, "error": "No text provided"}
        
        # Default extraction result
        extracted = {
            "interests": [],
            "preferences": [],
            "goals": [],
            "facts": []
        }
        
        # Use LLM for extraction
        if self.openai_client:
            prompt = f"""Extract structured information from this text.
Context: {context}

Text: "{text}"

Return JSON with these fields (use empty arrays if nothing found):
- interests: [{{"label": "interest name", "confidence": 0.0-1.0}}]
- preferences: [{{"label": "preference", "sentiment": "positive" or "negative"}}]
- goals: [{{"label": "goal description", "type": "matchmaking"|"networking"|"career"|"personal"}}]
- facts: [{{"label": "factual statement about user", "category": "personal"|"professional"|"preference"}}]

Only extract explicit information, don't infer. Return only valid JSON."""

            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=500
                )
                extracted = json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"Memory extraction failed: {e}")
        
        return {
            "success": True,
            "extracted": extracted,
            "source_text": text[:100] + "..." if len(text) > 100 else text,
            "context": context
        }


class UpdateGraphTool(WorkflowBaseTool):
    """Update knowledge graph with new information"""
    
    name = "update_graph"
    description = "Add or update nodes in the user's knowledge graph"
    
    schema = {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["interest", "preference", "goal", "fact", "trait"]},
                        "label": {"type": "string"},
                        "properties": {"type": "object"}
                    }
                },
                "description": "List of graph updates to make"
            }
        },
        "required": ["updates"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        updates = kwargs.get("updates", [])
        
        if not updates:
            return {"success": True, "updates_made": 0, "results": []}
        
        now = datetime.now(timezone.utc)
        results = []
        
        for update in updates:
            node_type = update.get("type")
            label = update.get("label")
            properties = update.get("properties", {})
            
            if not node_type or not label:
                continue
            
            # Normalize label
            label = label.strip().lower()
            
            # Check if exists
            existing = await self.db.knowledge_graph.find_one({
                "user_id": avatar_id,
                "type": node_type,
                "label": label
            })
            
            if existing:
                # Update existing node
                new_props = {**existing.get("properties", {}), **properties}
                new_props["mention_count"] = existing.get("properties", {}).get("mention_count", 0) + 1
                new_props["updated_at"] = now.isoformat()
                
                await self.db.knowledge_graph.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"properties": new_props}}
                )
                results.append({"label": label, "type": node_type, "action": "updated"})
            else:
                # Create new node
                node_id = str(uuid.uuid4())
                node = {
                    "id": node_id,
                    "user_id": avatar_id,
                    "type": node_type,
                    "label": label,
                    "properties": {
                        **properties,
                        "source": "avatar_chat",
                        "mention_count": 1,
                        "created_at": now.isoformat(),
                        "strength": properties.get("confidence", 0.7)
                    }
                }
                await self.db.knowledge_graph.insert_one(node)
                results.append({"label": label, "type": node_type, "action": "created", "node_id": node_id})
        
        logger.info(f"📊 Updated knowledge graph: {len(results)} changes for avatar {avatar_id[:8]}")
        
        return {
            "success": True,
            "updates_made": len(results),
            "results": results
        }


class GetUserContextTool(WorkflowBaseTool):
    """Get full context about a user from knowledge graph"""
    
    name = "get_user_context"
    description = "Retrieve comprehensive context about a user from their knowledge graph"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User to get context for (defaults to avatar)"
            },
            "include_missions": {
                "type": "boolean",
                "default": True,
                "description": "Include past mission history"
            }
        }
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_id = kwargs.get("target_user_id", avatar_id)
        include_missions = kwargs.get("include_missions", True)
        
        # Get all knowledge graph nodes for user
        nodes = await self.db.knowledge_graph.find({"user_id": target_id}).to_list(200)
        
        context = {
            "interests": [],
            "preferences": [],
            "goals": [],
            "facts": [],
            "traits": []
        }
        
        for node in nodes:
            node_type = node.get("type")
            if node_type in context:
                context[node_type].append({
                    "label": node.get("label"),
                    "strength": node.get("properties", {}).get("strength", 0.5),
                    "sentiment": node.get("properties", {}).get("sentiment"),
                    "mention_count": node.get("properties", {}).get("mention_count", 1)
                })
        
        # Sort by strength/mention count
        for key in context:
            context[key].sort(key=lambda x: (x.get("strength", 0), x.get("mention_count", 0)), reverse=True)
            context[key] = context[key][:20]  # Limit each category
        
        # Get mission history if requested
        if include_missions:
            missions = await self.db.missions.find({
                "user_id": target_id,
                "status": "completed"
            }).sort("timeline.completed_at", -1).limit(5).to_list(5)
            
            context["recent_missions"] = [
                {
                    "type": m.get("type"),
                    "name": m.get("name"),
                    "leads_generated": m.get("results_summary", {}).get("total_leads", 0),
                    "completed_at": m.get("timeline", {}).get("completed_at")
                }
                for m in missions
            ]
        
        # Get user profile info
        user = await self.db.users.find_one({"id": target_id})
        if user:
            context["profile"] = {
                "avatar_name": user.get("avatar_name"),
                "archetype": user.get("avatar_archetype"),
                "bio": user.get("avatar_bio", "")[:200]
            }
        
        return {
            "success": True,
            "user_id": target_id,
            "context": context
        }

