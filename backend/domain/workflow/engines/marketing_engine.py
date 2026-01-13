"""
Marketing Campaign Workflow Engine
Specialized engine for running marketing campaigns through the avatar's social network.
The avatar posts content, messages contacts, shares with friends, and gathers insights.
"""

import logging
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime, timezone

from .base_engine import (
    BaseWorkflowEngine, WorkflowState, WorkflowNode, WorkflowPhase
)

logger = logging.getLogger(__name__)


class MarketingCampaignEngine(BaseWorkflowEngine):
    """
    Marketing Campaign Workflow Engine
    
    This engine:
    1. Takes a campaign message/ad from the user
    2. Posts it to the avatar's feed
    3. Messages relevant friends/contacts
    4. Shares content strategically
    5. Tracks engagement and generates leads/insights
    """
    
    engine_name = "marketing_campaign"
    engine_description = "Run marketing campaigns through social network"
    supported_mission_types = ["sales_leads", "marketing_campaign", "content_promotion"]
    
    def _build_workflow_graph(self) -> Dict[str, WorkflowNode]:
        """Build the marketing campaign workflow graph"""
        
        return {
            "prepare_campaign": WorkflowNode(
                name="prepare_campaign",
                description="Prepare campaign content and identify target audience",
                tools=["get_user_context", "search_profiles"],
                max_iterations=1,
                timeout_seconds=60
            ),
            "create_post": WorkflowNode(
                name="create_post",
                description="Create the main campaign post",
                tools=[],  # Uses IntelligentAvatar
                max_iterations=1,
                timeout_seconds=45
            ),
            "identify_targets": WorkflowNode(
                name="identify_targets",
                description="Identify best contacts for direct outreach",
                tools=["score_compatibility", "analyze_profile"],
                max_iterations=30,
                timeout_seconds=120
            ),
            "broadcast": WorkflowNode(
                name="broadcast",
                description="Send personalized messages to targets",
                tools=["send_mission_message", "start_conversation"],
                max_iterations=15,
                timeout_seconds=180
            ),
            "track_engagement": WorkflowNode(
                name="track_engagement",
                description="Track engagement and responses",
                tools=["check_response", "analyze_conversation"],
                max_iterations=20,
                timeout_seconds=90
            ),
            "generate_insights": WorkflowNode(
                name="generate_insights",
                description="Generate campaign insights and leads",
                tools=["create_lead", "generate_summary"],
                max_iterations=20,
                timeout_seconds=90
            )
        }
    
    def _get_node_order(self) -> List[str]:
        return [
            "prepare_campaign",
            "create_post",
            "identify_targets",
            "broadcast",
            "track_engagement",
            "generate_insights"
        ]
    
    async def _execute_node(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Execute a workflow node"""
        
        if node.name == "prepare_campaign":
            return await self._node_prepare_campaign(node, state)
        elif node.name == "create_post":
            return await self._node_create_post(node, state)
        elif node.name == "identify_targets":
            return await self._node_identify_targets(node, state)
        elif node.name == "broadcast":
            return await self._node_broadcast(node, state)
        elif node.name == "track_engagement":
            return await self._node_track_engagement(node, state)
        elif node.name == "generate_insights":
            return await self._node_generate_insights(node, state)
        else:
            logger.warning(f"Unknown node: {node.name}")
            return state
    
    async def _node_prepare_campaign(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Prepare the campaign content and strategy"""
        
        logger.info("📢 Preparing marketing campaign...")
        
        # Extract campaign parameters from criteria/strategy
        campaign_message = state.strategy.get("custom_instructions", "")
        campaign_header = state.criteria.get("campaign_header", "")
        target_interests = state.criteria.get("interests", [])
        talking_points = state.strategy.get("talking_points", [])
        
        # Store campaign content
        state.custom["campaign"] = {
            "header": campaign_header,
            "message": campaign_message,
            "target_interests": target_interests,
            "talking_points": talking_points,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Get avatar's social circle stats
        friend_count = await self.db.friendships.count_documents({
            "$or": [
                {"user_id": state.avatar_id, "status": "accepted"},
                {"friend_id": state.avatar_id, "status": "accepted"}
            ]
        })
        
        # Get potential targets based on interests
        result = await self.call_tool(
            "search_profiles",
            state.avatar_id,
            interests=target_interests,
            exclude_friends=False,  # Include friends for marketing
            limit=50
        )
        
        if result.get("success"):
            state.discovered_profiles = result.get("profiles", [])
        
        state.custom["campaign"]["audience_size"] = friend_count
        state.custom["campaign"]["potential_targets"] = len(state.discovered_profiles)
        
        state.insights.append(
            f"Campaign prepared: {friend_count} friends in network, {len(state.discovered_profiles)} potential targets"
        )
        
        await self._log_action(state, "prepare_campaign", {
            "audience_size": friend_count,
            "targets_found": len(state.discovered_profiles)
        })
        
        return state
    
    async def _node_create_post(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Create the main campaign post"""
        
        logger.info("📝 Creating campaign post...")
        
        campaign = state.custom.get("campaign", {})
        header = campaign.get("header", "")
        message = campaign.get("message", "")
        
        # Use LLM to enhance the post if available
        post_content = header if header else message
        
        if self.openai_client and message:
            try:
                # Get avatar persona
                user = await self.db.users.find_one({"id": state.avatar_id})
                avatar_name = user.get("avatar_name", "Unknown") if user else "Unknown"
                archetype = user.get("avatar_archetype", "professional") if user else "professional"
                
                prompt = f"""You are {avatar_name}, a {archetype} avatar. 
Create an engaging social media post based on this campaign brief:

Campaign Header: {header}
Campaign Message: {message}

Guidelines:
- Keep it authentic to the persona
- Make it engaging and shareable
- Include a subtle call to action
- Keep it under 280 characters if possible

Return JSON: {{"post_content": "the post text", "hashtags": ["tag1", "tag2"]}}"""

                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=200
                )
                
                result = json.loads(response.choices[0].message.content)
                post_content = result.get("post_content", post_content)
                hashtags = result.get("hashtags", [])
                
                if hashtags:
                    post_content += "\n\n" + " ".join([f"#{tag}" for tag in hashtags])
                    
            except Exception as e:
                logger.warning(f"Post enhancement failed: {e}")
        
        # Create the post
        now = datetime.now(timezone.utc)
        post_id = str(uuid.uuid4())
        
        user = await self.db.users.find_one({"id": state.avatar_id})
        
        post = {
            "id": post_id,
            "user_id": state.avatar_id,
            "content": post_content,
            "likes": [],
            "comments": [],
            "shares": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "source": "campaign",
            "mission_id": state.mission_id,
            "author": {
                "name": user.get("avatar_name") if user else "Unknown",
                "picture": user.get("avatar_picture") if user else None
            }
        }
        
        await self.db.posts.insert_one(post)
        
        state.custom["campaign"]["post_id"] = post_id
        state.custom["campaign"]["post_content"] = post_content
        
        state.insights.append(f"Campaign post created and published")
        
        await self._log_action(state, "create_campaign_post", {
            "post_id": post_id,
            "content_preview": post_content[:100]
        })
        
        return state
    
    async def _node_identify_targets(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Identify the best targets for direct outreach"""
        
        logger.info("🎯 Identifying outreach targets...")
        
        target_interests = state.custom.get("campaign", {}).get("target_interests", [])
        
        qualified = []
        
        for profile in state.discovered_profiles[:node.max_iterations]:
            target_id = profile.get("user_id")
            
            # Score relevance for campaign
            score_result = await self.call_tool(
                "score_compatibility",
                state.avatar_id,
                target_user_id=target_id
            )
            
            base_score = score_result.get("total_score", 50) if score_result.get("success") else 50
            
            # Boost score for interest alignment
            profile_interests = profile.get("interests", [])
            interest_overlap = len(set(target_interests) & set(profile_interests))
            campaign_score = base_score + (interest_overlap * 10)
            
            # Check if they're a friend (friends are more likely to engage)
            is_friend = await self._is_friend(state.avatar_id, target_id)
            if is_friend:
                campaign_score += 20
            
            qualified.append({
                "user_id": target_id,
                "avatar_name": profile.get("avatar_name"),
                "score": min(campaign_score, 100),
                "is_friend": is_friend,
                "shared_interests": profile.get("interest_overlap", []),
                "profile_data": profile
            })
        
        # Sort by score
        qualified.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Take top targets
        max_messages = state.strategy.get("max_conversations", 10)
        state.qualified_profiles = qualified[:max_messages]
        
        state.insights.append(
            f"Identified {len(state.qualified_profiles)} top targets for outreach"
        )
        
        await self._log_action(state, "identify_targets", {
            "targets_qualified": len(state.qualified_profiles)
        })
        
        return state
    
    async def _node_broadcast(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Send personalized messages to targets"""
        
        logger.info("📨 Broadcasting campaign messages...")
        
        campaign = state.custom.get("campaign", {})
        post_content = campaign.get("post_content", "")
        talking_points = campaign.get("talking_points", [])
        
        messages_sent = 0
        
        for target in state.qualified_profiles[:node.max_iterations]:
            target_id = target.get("user_id")
            target_name = target.get("avatar_name", "friend")
            shared_interests = target.get("shared_interests", [])
            
            # Generate personalized message
            if self.openai_client:
                try:
                    prompt = f"""Generate a brief, personalized message to {target_name} about this campaign:

Campaign Post: {post_content[:200]}
Talking Points: {talking_points}
Shared Interests: {shared_interests}

The message should:
- Be casual and friendly
- Reference shared interests if any
- Include a soft pitch or invitation
- Be under 200 characters

Return JSON: {{"message": "the message text"}}"""

                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=100
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    message_text = result.get("message", "")
                    
                except Exception as e:
                    logger.warning(f"Message generation failed: {e}")
                    message_text = f"Hey {target_name}! I just shared something I think you might be interested in. Check out my latest post! 🚀"
            else:
                # Fallback message
                message_text = f"Hey {target_name}! I just shared something I think you might be interested in. Check out my latest post! 🚀"
            
            # Send the message
            if target.get("is_friend"):
                # Use direct message for friends
                result = await self.call_tool(
                    "send_mission_message",
                    state.avatar_id,
                    recipient_id=target_id,
                    message_text=message_text,
                    context={
                        "mission_type": "marketing",
                        "campaign_id": state.mission_id
                    }
                )
            else:
                # Start new conversation for non-friends
                result = await self.call_tool(
                    "start_conversation",
                    state.avatar_id,
                    target_user_id=target_id,
                    mission_type="marketing",
                    talking_points=talking_points
                )
            
            if result.get("success"):
                conv_id = result.get("conversation_id")
                state.conversations[target_id] = conv_id
                messages_sent += 1
                
                # Log detailed activity for this engagement
                await self._log_action(state, "send_campaign_message", {
                    "target_user_id": target_id,
                    "target_name": target_name,
                    "message_content": message_text,
                    "conversation_id": conv_id,
                    "is_friend": target.get("is_friend", False),
                    "shared_interests": shared_interests[:3] if shared_interests else []
                })
        
        state.custom["campaign"]["messages_sent"] = messages_sent
        state.insights.append(f"Sent campaign messages to {messages_sent} targets")
        
        await self._log_action(state, "broadcast_campaign", {
            "messages_sent": messages_sent
        })
        
        return state
    
    async def _node_track_engagement(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Track engagement with the campaign"""
        
        logger.info("📊 Tracking campaign engagement...")
        
        # Check post engagement
        post_id = state.custom.get("campaign", {}).get("post_id")
        
        engagement = {
            "post_likes": 0,
            "post_comments": 0,
            "post_shares": 0,
            "message_responses": 0,
            "positive_responses": 0
        }
        
        if post_id:
            post = await self.db.posts.find_one({"id": post_id})
            if post:
                engagement["post_likes"] = len(post.get("likes", []))
                engagement["post_comments"] = len(post.get("comments", []))
                engagement["post_shares"] = len(post.get("shares", []))
        
        # Check message responses
        for target_id, conv_id in state.conversations.items():
            result = await self.call_tool(
                "check_response",
                state.avatar_id,
                conversation_id=conv_id
            )
            
            if result.get("success") and result.get("has_response"):
                engagement["message_responses"] += 1
                
                # Analyze sentiment
                analysis = await self.call_tool(
                    "analyze_conversation",
                    state.avatar_id,
                    conversation_id=conv_id
                )
                
                if analysis.get("success"):
                    state.conversation_analyses[target_id] = analysis.get("analysis", {})
                    
                    sentiment = analysis.get("analysis", {}).get("sentiment", "neutral")
                    if sentiment == "positive":
                        engagement["positive_responses"] += 1
        
        state.custom["campaign"]["engagement"] = engagement
        
        total_engagement = (
            engagement["post_likes"] + 
            engagement["post_comments"] + 
            engagement["message_responses"]
        )
        
        state.insights.append(
            f"Campaign engagement: {total_engagement} total interactions, "
            f"{engagement['message_responses']} message responses"
        )
        
        await self._log_action(state, "track_engagement", engagement)
        
        return state
    
    async def _node_generate_insights(
        self, 
        node: WorkflowNode, 
        state: WorkflowState
    ) -> WorkflowState:
        """Generate campaign insights and leads"""
        
        logger.info("💡 Generating campaign insights...")
        
        engagement = state.custom.get("campaign", {}).get("engagement", {})
        
        # Create leads from respondents
        for target_id, conv_id in state.conversations.items():
            analysis = state.conversation_analyses.get(target_id, {})
            
            # Only create leads for engaged users
            if analysis.get("sentiment") in ["positive", "neutral"] or engagement.get("message_responses", 0) > 0:
                # Find target profile
                target_profile = next(
                    (p for p in state.qualified_profiles if p.get("user_id") == target_id),
                    {}
                )
                
                result = await self.call_tool(
                    "create_lead",
                    state.avatar_id,
                    mission_id=state.mission_id,
                    target_user_id=target_id,
                    score=target_profile.get("score", 60),
                    conversation_id=conv_id,
                    insights={
                        "campaign_engagement": "responded",
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "compatibility_reasons": [
                            "Showed interest in campaign",
                            f"Shared interests: {', '.join(target_profile.get('shared_interests', [])[:3])}"
                        ]
                    }
                )
                
                if result.get("success"):
                    state.leads.append(result.get("lead", {}))
        
        # Generate summary using LLM
        if self.openai_client:
            try:
                prompt = f"""Analyze this marketing campaign and provide insights:

Campaign Stats:
- Messages sent: {state.custom.get('campaign', {}).get('messages_sent', 0)}
- Post likes: {engagement.get('post_likes', 0)}
- Post comments: {engagement.get('post_comments', 0)}
- Message responses: {engagement.get('message_responses', 0)}
- Positive responses: {engagement.get('positive_responses', 0)}
- Leads generated: {len(state.leads)}

Return JSON with:
{{
    "campaign_score": 0-100,
    "key_insights": ["insight1", "insight2"],
    "recommendations": ["rec1", "rec2"],
    "best_performing_aspect": "what worked best"
}}"""

                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=250
                )
                
                campaign_analysis = json.loads(response.choices[0].message.content)
                state.custom["campaign"]["analysis"] = campaign_analysis
                state.insights.extend(campaign_analysis.get("key_insights", []))
                
            except Exception as e:
                logger.warning(f"Campaign analysis failed: {e}")
        
        # Generate mission summary
        await self.call_tool(
            "generate_summary",
            state.avatar_id,
            mission_id=state.mission_id
        )
        
        state.insights.append(f"Generated {len(state.leads)} leads from campaign")
        
        await self._log_action(state, "generate_insights", {
            "leads_created": len(state.leads),
            "insights_count": len(state.insights)
        })
        
        state.phase = WorkflowPhase.COMPLETING
        
        return state
    
    async def _is_friend(self, user_id: str, target_id: str) -> bool:
        """Check if two users are friends"""
        friendship = await self.db.friendships.find_one({
            "$or": [
                {"user_id": user_id, "friend_id": target_id, "status": "accepted"},
                {"user_id": target_id, "friend_id": user_id, "status": "accepted"}
            ]
        })
        return friendship is not None
    
    async def _generate_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Override to include campaign-specific summary"""
        
        base_summary = await super()._generate_summary(state)
        
        campaign = state.custom.get("campaign", {})
        engagement = campaign.get("engagement", {})
        
        base_summary.update({
            "campaign_metrics": {
                "post_id": campaign.get("post_id"),
                "messages_sent": campaign.get("messages_sent", 0),
                "post_engagement": {
                    "likes": engagement.get("post_likes", 0),
                    "comments": engagement.get("post_comments", 0),
                    "shares": engagement.get("post_shares", 0)
                },
                "response_rate": (
                    engagement.get("message_responses", 0) / 
                    max(campaign.get("messages_sent", 1), 1) * 100
                )
            },
            "campaign_analysis": campaign.get("analysis", {})
        })
        
        return base_summary

