"""
Discovery MCP Tools
Tools for finding and filtering profiles
"""

import logging
from typing import Dict, List, Any
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class SearchProfilesTool(WorkflowBaseTool):
    """Search for profiles matching criteria"""
    
    name = "search_profiles"
    description = "Search Maya World for profiles matching given criteria"
    
    schema = {
        "type": "object",
        "properties": {
            "interests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of interests to match"
            },
            "traits": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Personality traits to look for"
            },
            "activity_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Desired activity level"
            },
            "exclude_friends": {
                "type": "boolean",
                "default": True,
                "description": "Exclude existing friends"
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "Maximum profiles to return"
            }
        },
        "required": []
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        interests = kwargs.get("interests", [])
        traits = kwargs.get("traits", [])
        exclude_friends = kwargs.get("exclude_friends", False)  # Changed default to False - include friends!
        limit = kwargs.get("limit", 50)
        
        logger.info(f"🔍 Searching profiles: interests={interests}, traits={traits}, exclude_friends={exclude_friends}, limit={limit}")
        
        # Build query - find ALL users (not just those with avatar_name)
        # This ensures we don't miss profiles like VoidSeeker68
        query = {
            "id": {"$ne": avatar_id}
        }
        
        # Exclude friends if requested
        if exclude_friends:
            friend_ids = await self._get_friend_ids(avatar_id)
            if friend_ids:
                query["id"]["$nin"] = friend_ids
                logger.info(f"🚫 Excluding {len(friend_ids)} friends from search")
        
        # Get candidates (increased multiplier to ensure we get enough)
        candidates = await self.db.users.find(query).limit(limit * 5).to_list(limit * 5)
        logger.info(f"📋 Found {len(candidates)} initial candidates")
        
        # Score and filter by interests
        scored_candidates = []
        for c in candidates:
            user_interests = await self._get_interests(c["id"])
            user_traits = await self._get_traits(c["id"])
            
            # Calculate overlap
            interest_overlap = set(interests) & set(user_interests) if interests and user_interests else set()
            trait_overlap = set(traits) & set(user_traits) if traits and user_traits else set()
            
            # Score based on overlap (give base score of 1 for all users to include them)
            score = len(interest_overlap) * 2 + len(trait_overlap) + 1
            
            # Always include candidates - they can be filtered in evaluation phase
            scored_candidates.append({
                "user_id": c["id"],
                "avatar_name": c.get("avatar_name") or c.get("display_name") or c.get("name", "Unknown"),
                "archetype": c.get("avatar_archetype"),
                "interests": user_interests[:10] if user_interests else [],
                "traits": user_traits[:5] if user_traits else [],
                "interest_overlap": list(interest_overlap),
                "trait_overlap": list(trait_overlap),
                "score": score
            })
        
        # Sort by score and limit
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        results = scored_candidates[:limit]
        
        logger.info(f"✅ Returning {len(results)} profiles (from {len(candidates)} candidates)")
        
        return {
            "success": True,
            "profiles": results,
            "total_found": len(results),
            "total_scanned": len(candidates)
        }


class GetUserInterestsTool(WorkflowBaseTool):
    """Get interests for a specific user from knowledge graph"""
    
    name = "get_user_interests"
    description = "Retrieve all known interests for a user"
    
    schema = {
        "type": "object",
        "properties": {
            "target_user_id": {
                "type": "string",
                "description": "User ID to get interests for"
            }
        },
        "required": ["target_user_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        target_user_id = kwargs.get("target_user_id")
        
        nodes = await self.db.knowledge_graph.find({
            "user_id": target_user_id,
            "type": "interest"
        }).to_list(100)
        
        interests = [
            {
                "label": n.get("label"),
                "strength": n.get("properties", {}).get("strength", 0.5),
                "source": n.get("properties", {}).get("source", "unknown")
            }
            for n in nodes if n.get("label")
        ]
        
        return {
            "success": True,
            "user_id": target_user_id,
            "interests": interests,
            "count": len(interests)
        }


class FilterByCriteriaTool(WorkflowBaseTool):
    """Filter a list of profiles by specific criteria"""
    
    name = "filter_by_criteria"
    description = "Filter profiles based on detailed criteria"
    
    schema = {
        "type": "object",
        "properties": {
            "profile_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of profile IDs to filter"
            },
            "min_interest_overlap": {
                "type": "integer",
                "default": 1,
                "description": "Minimum shared interests required"
            },
            "required_interests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Must have at least one of these interests"
            },
            "excluded_interests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exclude profiles with these interests"
            }
        },
        "required": ["profile_ids"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        profile_ids = kwargs.get("profile_ids", [])
        min_overlap = kwargs.get("min_interest_overlap", 1)
        required = kwargs.get("required_interests", [])
        excluded = kwargs.get("excluded_interests", [])
        
        # Get avatar's interests
        avatar_interests = set(await self._get_interests(avatar_id))
        
        filtered = []
        for pid in profile_ids:
            profile_interests = set(await self._get_interests(pid))
            
            # Check exclusions
            if excluded and (profile_interests & set(excluded)):
                continue
            
            # Check required
            if required and not (profile_interests & set(required)):
                continue
            
            # Check overlap
            overlap = avatar_interests & profile_interests
            if len(overlap) >= min_overlap:
                filtered.append({
                    "user_id": pid,
                    "shared_interests": list(overlap),
                    "overlap_count": len(overlap)
                })
        
        return {
            "success": True,
            "filtered_profiles": filtered,
            "original_count": len(profile_ids),
            "filtered_count": len(filtered)
        }

