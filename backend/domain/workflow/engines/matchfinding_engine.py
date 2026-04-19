"""
MatchFinding Workflow Engine
Specialized engine for finding compatible matches based on conversations, 
posts, profiles, and shared interests.
"""

import logging
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime, timezone

from core.config import OPENAI_MODEL
from .base_engine import (
    BaseWorkflowEngine, WorkflowState, WorkflowNode, WorkflowPhase
)

logger = logging.getLogger(__name__)


class MatchFindingEngine(BaseWorkflowEngine):
    """
    MatchFinding Workflow Engine
    
    This engine analyzes:
    1. Past conversations the avatar has had
    2. Posts and interactions
    3. User profiles in the network
    4. Shared interests and compatibility factors
    
    To generate ranked matches with detailed reasons.
    """
    
    engine_name = "matchfinding"
    engine_description = "Find compatible matches based on conversations, posts, and shared interests"
    supported_mission_types = ["matchmaking", "networking"]
    
    def _build_workflow_graph(self) -> Dict[str, WorkflowNode]:
        """Build the matchfinding workflow graph"""
        
        return {
            "analyze_history": WorkflowNode(
                name="analyze_history",
                description="Analyze past conversations and interactions",
                tools=["get_user_context", "analyze_conversation"],
                max_iterations=1,
                timeout_seconds=90
            ),
            "discover": WorkflowNode(
                name="discover",
                description="Discover potential matches from the network",
                tools=["search_profiles", "get_user_interests"],
                max_iterations=1,
                timeout_seconds=60
            ),
            "evaluate": WorkflowNode(
                name="evaluate",
                description="Evaluate compatibility with each candidate",
                tools=["score_compatibility", "get_shared_interests", "analyze_profile"],
                max_iterations=50,
                timeout_seconds=120
            ),
            "rank": WorkflowNode(
                name="rank",
                description="Rank matches and generate reasons",
                tools=[],  # Uses LLM directly
                max_iterations=1,
                timeout_seconds=60
            ),
            "generate_leads": WorkflowNode(
                name="generate_leads",
                description="Create lead entries for top matches",
                tools=["create_lead"],
                max_iterations=20,
                timeout_seconds=90
            ),
            "complete": WorkflowNode(
                name="complete",
                description="Generate final summary and insights",
                tools=["generate_summary", "update_graph"],
                max_iterations=1,
                timeout_seconds=30
            )
        }
    
    def _get_node_order(self) -> List[str]:
        return [
            "analyze_history",
            "discover", 
            "evaluate",
            "rank",
            "generate_leads",
            "complete"
        ]
    
    async def _execute_node(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Execute a workflow node"""
        
        if node.name == "analyze_history":
            return await self._node_analyze_history(node, state)
        elif node.name == "discover":
            return await self._node_discover(node, state)
        elif node.name == "evaluate":
            return await self._node_evaluate(node, state)
        elif node.name == "rank":
            return await self._node_rank(node, state)
        elif node.name == "generate_leads":
            return await self._node_generate_leads(node, state)
        elif node.name == "complete":
            return await self._node_complete(node, state)
        else:
            logger.warning(f"Unknown node: {node.name}")
            return state
    
    async def _node_analyze_history(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Analyze the avatar's conversation history for patterns and preferences"""
        
        logger.info("📊 Analyzing conversation history...")
        
        # Get avatar's recent conversations
        conversations = await self.db.agent_conversations.find({
            "participants": state.avatar_id
        }).sort("updated_at", -1).limit(20).to_list(20)
        
        # Analyze each conversation
        conversation_insights = []
        positive_interactions = []
        topics_discussed = []
        
        for conv in conversations:
            messages = conv.get("messages", [])
            if len(messages) < 2:
                continue
            
            # Get the other participant
            other_id = [p for p in conv.get("participants", []) if p != state.avatar_id]
            if not other_id:
                continue
            other_id = other_id[0]
            
            # Simple sentiment analysis based on message count/length
            avatar_msgs = [m for m in messages if m.get("sender") == state.avatar_id]
            other_msgs = [m for m in messages if m.get("sender") != state.avatar_id]
            
            engagement_score = min(len(other_msgs) / max(len(avatar_msgs), 1), 2.0)
            
            if engagement_score >= 0.5:
                positive_interactions.append({
                    "user_id": other_id,
                    "engagement_score": engagement_score,
                    "message_count": len(messages)
                })
            
            # Extract topics if we have LLM
            if self.openai_client and len(messages) >= 3:
                try:
                    sample_text = " ".join([m.get("content", "")[:100] for m in messages[-5:]])
                    response = await self.openai_client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[{
                            "role": "user",
                            "content": f"Extract 3-5 main topics from this conversation as a JSON array: {sample_text}"
                        }],
                        response_format={"type": "json_object"},
                        max_tokens=100
                    )
                    topics = json.loads(response.choices[0].message.content)
                    topics_discussed.extend(topics.get("topics", []))
                except Exception as e:
                    logger.warning(f"Topic extraction failed: {e}")
        
        # Store insights in state
        state.custom["conversation_insights"] = {
            "total_conversations": len(conversations),
            "positive_interactions": positive_interactions[:10],
            "common_topics": list(set(topics_discussed))[:15]
        }
        
        # Get avatar's posts for pattern analysis
        posts = await self.db.posts.find({
            "user_id": state.avatar_id
        }).sort("created_at", -1).limit(10).to_list(10)
        
        post_topics = []
        for post in posts:
            content = post.get("content", "")
            if len(content) > 20:
                post_topics.append(content[:100])
        
        state.custom["post_patterns"] = post_topics
        
        state.insights.append(
            f"Analyzed {len(conversations)} conversations, found {len(positive_interactions)} positive interactions"
        )
        
        await self._log_action(state, "analyze_history", {
            "conversations_analyzed": len(conversations),
            "positive_interactions": len(positive_interactions)
        })
        
        return state
    
    async def _node_discover(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Discover potential matches from the network"""
        
        logger.info("🔍 Discovering potential matches...")
        
        # Get criteria from mission
        interests = state.criteria.get("interests", [])
        traits = state.criteria.get("traits", [])
        exclude_friends = state.criteria.get("exclude_existing_friends", False)
        max_targets = state.strategy.get("max_targets", 30)
        
        # Use MCP tool to search profiles
        result = await self.call_tool(
            "search_profiles",
            state.avatar_id,
            interests=interests,
            traits=traits,
            exclude_friends=exclude_friends,
            limit=max_targets
        )
        
        if result.get("success"):
            state.discovered_profiles = result.get("profiles", [])
            state.insights.append(
                f"Discovered {len(state.discovered_profiles)} potential matches"
            )
        else:
            state.errors.append(f"Discovery failed: {result.get('error')}")
        
        await self._log_action(state, "discover_profiles", {
            "profiles_found": len(state.discovered_profiles)
        })
        
        return state
    
    async def _node_evaluate(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Evaluate compatibility with each discovered profile"""
        
        logger.info(f"📋 Evaluating {len(state.discovered_profiles)} profiles...")
        
        evaluated = []
        
        for profile in state.discovered_profiles[:node.max_iterations]:
            target_id = profile.get("user_id")
            
            # NEW: Analyze target user's posts for relevant content
            post_relevance_score = await self._analyze_posts_for_interests(
                target_id, 
                state.criteria.get("interests", [])
            )
            
            # NEW: Analyze past messages/conversations
            conversation_relevance = await self._analyze_conversation_relevance(
                state.avatar_id,
                target_id,
                state.criteria.get("interests", [])
            )
            
            # Score compatibility
            score_result = await self.call_tool(
                "score_compatibility",
                state.avatar_id,
                target_user_id=target_id
            )
            
            if not score_result.get("success"):
                continue
            
            total_score = score_result.get("total_score", 0)
            breakdown = score_result.get("breakdown", {})
            
            # NEW: Boost score based on post relevance
            total_score += post_relevance_score
            breakdown["post_relevance"] = post_relevance_score
            
            # NEW: Boost score based on conversation relevance
            total_score += conversation_relevance
            breakdown["conversation_relevance"] = conversation_relevance
            
            # Get shared interests
            interests_result = await self.call_tool(
                "get_shared_interests",
                state.avatar_id,
                target_user_id=target_id
            )
            
            shared_interests = interests_result.get("shared_interests", []) if interests_result.get("success") else []
            
            # Check if they had positive past interaction
            past_interaction = None
            for pi in state.custom.get("conversation_insights", {}).get("positive_interactions", []):
                if pi.get("user_id") == target_id:
                    past_interaction = pi
                    total_score += 15  # Bonus for positive past interaction
                    break
            
            evaluated.append({
                "user_id": target_id,
                "avatar_name": profile.get("avatar_name"),
                "score": min(total_score, 100),
                "breakdown": breakdown,
                "shared_interests": shared_interests,
                "past_interaction": past_interaction,
                "profile_data": profile
            })
        
        # Sort by score
        evaluated.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Keep top candidates
        state.qualified_profiles = evaluated[:20]
        
        state.insights.append(
            f"Evaluated {len(evaluated)} profiles, qualified {len(state.qualified_profiles)} matches"
        )
        
        await self._log_action(state, "evaluate_profiles", {
            "profiles_evaluated": len(evaluated),
            "profiles_qualified": len(state.qualified_profiles)
        })
        
        return state
    
    async def _node_rank(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Rank matches and generate detailed reasons using LLM"""
        
        logger.info("🏆 Ranking matches and generating reasons...")
        
        if not self.openai_client or not state.qualified_profiles:
            return state
        
        # Prepare ranking context
        avatar_context = await self._get_avatar_context(state.avatar_id)
        
        for profile in state.qualified_profiles:
            try:
                # Generate detailed match reasons
                prompt = f"""Analyze why this person would be a good match.

Your Avatar:
- Interests: {avatar_context.get('interests', [])}
- Traits: {avatar_context.get('traits', [])}
- Recent topics: {state.custom.get('conversation_insights', {}).get('common_topics', [])}

Match Candidate:
- Name: {profile.get('avatar_name')}
- Score: {profile.get('score')}
- Shared interests: {profile.get('shared_interests', [])}
- Past positive interaction: {profile.get('past_interaction') is not None}
- Score breakdown: {profile.get('breakdown', {})}

Provide a JSON response with:
{{
    "match_reasons": ["reason1", "reason2", "reason3"],
    "conversation_starters": ["starter1", "starter2"],
    "compatibility_summary": "brief summary",
    "priority": "high" or "medium" or "low"
}}"""

                response = await self.openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=300
                )
                
                analysis = json.loads(response.choices[0].message.content)
                profile["match_reasons"] = analysis.get("match_reasons", [])
                profile["conversation_starters"] = analysis.get("conversation_starters", [])
                profile["compatibility_summary"] = analysis.get("compatibility_summary", "")
                profile["priority"] = analysis.get("priority", "medium")
                
            except Exception as e:
                logger.warning(f"Failed to generate reasons for {profile.get('avatar_name')}: {e}")
                # Fallback
                profile["match_reasons"] = [
                    f"Shared interests: {', '.join(profile.get('shared_interests', [])[:3]) or 'Exploring similar topics'}"
                ]
                profile["priority"] = "high" if profile.get("score", 0) >= 80 else "medium"
        
        # Re-sort by priority then score
        priority_order = {"high": 0, "medium": 1, "low": 2}
        state.qualified_profiles.sort(
            key=lambda x: (priority_order.get(x.get("priority", "medium"), 1), -x.get("score", 0))
        )
        
        await self._log_action(state, "rank_matches", {
            "profiles_ranked": len(state.qualified_profiles)
        })
        
        return state
    
    async def _node_generate_leads(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Create lead entries for top matches"""
        
        logger.info("📝 Generating leads...")
        
        max_leads = state.strategy.get("max_conversations", 10)
        
        for profile in state.qualified_profiles[:max_leads]:
            result = await self.call_tool(
                "create_lead",
                state.avatar_id,
                mission_id=state.mission_id,
                target_user_id=profile.get("user_id"),
                score=profile.get("score", 50),
                score_breakdown=profile.get("breakdown", {}),
                insights={
                    "compatibility_reasons": profile.get("match_reasons", []),
                    "conversation_starters": profile.get("conversation_starters", []),
                    "compatibility_summary": profile.get("compatibility_summary", "")
                }
            )
            
            if result.get("success"):
                lead = result.get("lead", {})
                lead["match_reasons"] = profile.get("match_reasons", [])
                state.leads.append(lead)
        
        state.insights.append(f"Generated {len(state.leads)} leads for follow-up")
        
        await self._log_action(state, "generate_leads", {
            "leads_created": len(state.leads)
        })
        
        return state
    
    async def _node_complete(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Complete the workflow with summary"""
        
        logger.info("✅ Completing matchfinding workflow...")
        
        # Generate final summary using MCP tool
        await self.call_tool(
            "generate_summary",
            state.avatar_id,
            mission_id=state.mission_id
        )
        
        # Update knowledge graph with insights
        if state.leads:
            await self.call_tool(
                "update_graph",
                state.avatar_id,
                user_id=state.user_id,
                updates=[{
                    "type": "mission_completed",
                    "mission_type": "matchfinding",
                    "leads_count": len(state.leads),
                    "top_match": state.leads[0].get("target_avatar_name") if state.leads else None
                }]
            )
        
        state.phase = WorkflowPhase.COMPLETING
        
        return state
    
    async def _get_avatar_context(self, avatar_id: str) -> Dict[str, Any]:
        """Get avatar's interests and traits for context"""
        
        # Get interests
        interest_nodes = await self.db.knowledge_graph.find({
            "user_id": avatar_id,
            "type": "interest"
        }).to_list(50)
        interests = [n.get("label") for n in interest_nodes if n.get("label")]
        
        # Get traits
        trait_nodes = await self.db.knowledge_graph.find({
            "user_id": avatar_id,
            "type": "trait"
        }).to_list(20)
        traits = [n.get("label") for n in trait_nodes if n.get("label")]
        
        return {
            "interests": interests[:20],
            "traits": traits[:10]
        }
    
    async def _analyze_posts_for_interests(
        self,
        user_id: str,
        target_interests: List[str]
    ) -> int:
        """
        Analyze user's posts to determine relevance to target interests.
        Returns a score 0-20 based on post content relevance.
        """
        if not target_interests:
            return 0
        
        # Get user's recent posts
        posts = await self.db.posts.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(20).to_list(20)
        
        if not posts:
            return 0
        
        # Analyze post content for interest keywords
        relevance_score = 0
        interest_keywords = [i.lower() for i in target_interests]
        
        for post in posts:
            content = (post.get("content") or "").lower()
            
            # Check for keyword matches
            for keyword in interest_keywords:
                if keyword in content:
                    relevance_score += 2  # 2 points per relevant post
                    break  # Count each post max once
        
        # Cap at 20 points
        return min(relevance_score, 20)
    
    async def _analyze_conversation_relevance(
        self,
        avatar_id: str,
        target_id: str,
        target_interests: List[str]
    ) -> int:
        """
        Analyze past conversations between avatar and target for relevance.
        Returns a score 0-15 based on conversation content.
        """
        if not target_interests:
            return 0
        
        # Find conversations between these two users
        conversations = await self.db.agent_conversations.find({
            "participants": {"$all": [avatar_id, target_id]}
        }).to_list(5)
        
        if not conversations:
            return 0
        
        relevance_score = 0
        interest_keywords = [i.lower() for i in target_interests]
        
        for conv in conversations:
            messages = conv.get("messages", [])
            for msg in messages[-10:]:  # Check last 10 messages
                content = (msg.get("content") or "").lower()
                
                for keyword in interest_keywords:
                    if keyword in content:
                        relevance_score += 1.5  # 1.5 points per relevant message
                        break
        
        # Cap at 15 points
        return min(int(relevance_score), 15)

