"""
Intelligent Avatar Module
Handles avatar behavior powered by Graph RAG and LLM
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from openai import AsyncOpenAI, AsyncAzureOpenAI
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.rag import GraphRAG
from services.friend_activity_service import FriendActivityService
from services.content_awareness_service import ContentAwarenessService
import uuid
import random


class IntelligentAvatar:
    """Avatar with Graph RAG-powered intelligence"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client: Union[AsyncOpenAI, AsyncAzureOpenAI, None], 
                 model: str, graph_rag: GraphRAG):
        self.db = db
        self.llm_client = llm_client
        self.model = model  # Model name for OpenAI
        self.graph_rag = graph_rag
        # Check if using gpt-5-nano which requires responses API
        self._use_responses_api = "gpt-5" in self.model.lower() or "gpt-5-nano" in self.model.lower()
        
        # Initialize context awareness services
        self.friend_activity_service = FriendActivityService(db)
        self.content_awareness_service = ContentAwarenessService()
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with appropriate API based on model type.
        - For gpt-5-nano models: uses responses.create() API
        - For other models: uses chat.completions.create() API
        """
        if self._use_responses_api:
            # Use new responses API for gpt-5-nano models
            response = await self.llm_client.responses.create(
                model=self.model,
                input=prompt
            )
            return response.output_text.strip() if response.output_text else ""
        else:
            # Use traditional chat completions API
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=250
            )
            return response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    
    async def generate_avatar_post(self, user_id: str, post_type: str = "general") -> Dict[str, Any]:
        """
        Generate an intelligent avatar post based on user's knowledge graph
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get graph context
        context = await self.graph_rag.get_relevant_context(user_id, "post_generation")
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        
        # Generate post based on type
        if post_type == "interest":
            prompt = f"""{avatar_profile}

{context}

Generate a social media post (100-150 words) from the avatar's perspective sharing something about one of your interests. Be authentic, engaging, and true to your personality. Include a relevant question to encourage interaction.

Return ONLY the post text, no quotes or explanations."""
        
        elif post_type == "thought":
            prompt = f"""{avatar_profile}

{context}

Generate a thoughtful social media post (80-120 words) sharing an insight or reflection that aligns with your values and personality. Be genuine and relatable.

Return ONLY the post text, no quotes or explanations."""
        
        elif post_type == "experience":
            prompt = f"""{avatar_profile}

{context}

Generate a social media post (100-150 words) sharing a recent experience or activity related to your interests. Be descriptive and engaging.

Return ONLY the post text, no quotes or explanations."""
        
        else:  # general
            prompt = f"""{avatar_profile}

{context}

Generate an engaging social media post (80-150 words) from the avatar's perspective. Choose to share an interest, thought, or experience. Be authentic and true to your personality.

Return ONLY the post text, no quotes or explanations."""
        
        try:
            post_content = await self._call_llm(prompt)
            
            if not post_content:
                return {"error": "Empty response from OpenAI"}
            
            print(f"✅ Generated post content (length: {len(post_content)}): {post_content[:100]}...")
            
            # Remove quotes if present
            if post_content.startswith('"') and post_content.endswith('"'):
                post_content = post_content[1:-1]
            
            return {
                "content": post_content,
                "type": post_type,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Post generation failed: {str(e)}"}
    
    async def generate_diverse_post(self, user_id: str, post_type: str = "auto") -> Dict[str, Any]:
        """
        Generate posts with diverse types including friend interactions, jokes, current events, etc.
        
        Args:
            user_id: Avatar's user ID
            post_type: Type of post (auto, friend_interaction, joke, current_events, pleasantry, etc.)
        
        Returns:
            Dict with post content and metadata
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get avatar profile and interests
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        interests = user.get('avatar_character_profile', {}).get('interests', [])
        
        # NEW: Get current internal state for voice modulation
        expression_context = None
        internal_state_data = user.get("avatar_internal_state", {})
        if internal_state_data:
            try:
                from domain.avatar.state.internal_state import InternalState
                internal_state = InternalState.from_dict(internal_state_data)
                expression_context = internal_state.get_expression_context()
            except Exception as e:
                logger.warning(f"Could not load internal state for voice: {e}")
        
        # Get context from services (conditionally based on state)
        # NEW: Only fetch friend activities if avatar is socially inclined
        friend_activities = []
        if expression_context and expression_context.get('should_talk_about_friends', True):
            friend_activities = await self.friend_activity_service.get_recent_friend_activities(user_id, hours=24)
        elif not expression_context:  # Fallback if no state
            friend_activities = await self.friend_activity_service.get_recent_friend_activities(user_id, hours=24)
        
        # NEW: Only fetch news if avatar has world awareness
        trending_topics = []
        relevant_news = []
        if expression_context and expression_context.get('should_reference_world', True):
            trending_topics = await self.content_awareness_service.get_trending_topics()
            relevant_news = await self.content_awareness_service.get_news_for_interests(interests)
        elif not expression_context:  # Fallback if no state
            trending_topics = await self.content_awareness_service.get_trending_topics()
            relevant_news = await self.content_awareness_service.get_news_for_interests(interests)
        
        # Auto-select post type if not specified
        # NOW: Uses internal state to influence decision!
        if post_type == "auto":
            post_type = self._select_post_type(expression_context)
        
        # Build prompt based on post type (with state-aware voice)
        prompt = self._build_diverse_post_prompt(
            post_type=post_type,
            avatar_profile=avatar_profile,
            friend_activities=friend_activities,
            trending_topics=trending_topics,
            relevant_news=relevant_news,
            expression_context=expression_context  # NEW: Pass current state
        )
        
        try:
            post_content = await self._call_llm(prompt)
            
            if not post_content:
                return {"error": "Empty response from LLM"}
            
            # Clean up quotes
            if post_content.startswith('"') and post_content.endswith('"'):
                post_content = post_content[1:-1]
            
            return {
                "content": post_content,
                "type": post_type,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Post generation failed: {str(e)}"}
    
    def _select_post_type(self, expression_context: Optional[Dict] = None) -> str:
        """
        Weighted random selection of post type
        NOW: Adjusted by internal state (friend_focus, world_awareness, etc.)
        """
        # Base weights
        post_types = {
            "interest": 0.20,           # Own interests
            "thought": 0.15,            # Personal reflection
            "friend_interaction": 0.15, # Comment on friend's activity
            "joke": 0.10,               # Funny observation
            "pleasantry": 0.10,         # Casual greeting
            "current_events": 0.15,     # News/trends
            "friendly_banter": 0.10,    # Tease/joke with friends
            "experience": 0.05          # Share experience
        }
        
        # Adjust weights based on internal state
        if expression_context:
            # High friend_focus → more friend-related posts
            if expression_context.get('should_talk_about_friends', False):
                post_types["friend_interaction"] *= 2.0
                post_types["friendly_banter"] *= 1.5
                post_types["interest"] *= 0.7  # Less self-focused
                
            # High world_awareness → more current events
            if expression_context.get('should_reference_world', False):
                post_types["current_events"] *= 2.0
                post_types["thought"] *= 1.3  # More contemplative
                post_types["joke"] *= 0.8
            
            # High humor → more jokes
            humor_level = expression_context.get('humor_level', 'medium')
            if humor_level == 'high':
                post_types["joke"] *= 1.8
                post_types["friendly_banter"] *= 1.3
                post_types["thought"] *= 0.7
            
            # High playfulness → more banter and jokes
            playfulness = expression_context.get('playfulness', 0.5)
            if playfulness > 0.7:
                post_types["friendly_banter"] *= 1.5
                post_types["pleasantry"] *= 1.2
            
            # Low energy → more passive content
            energy = expression_context.get('energy', 0.5)
            if energy < 0.4:
                post_types["thought"] *= 1.3
                post_types["pleasantry"] *= 0.7
                post_types["joke"] *= 1.2  # Sarcastic when tired
            
            # Mood-based adjustments
            mood = expression_context.get('mood', 'neutral')
            if mood == 'social':
                post_types["friend_interaction"] *= 1.8
                post_types["friendly_banter"] *= 1.6
                post_types["pleasantry"] *= 1.4
            elif mood == 'bored':
                post_types["joke"] *= 1.5
                post_types["current_events"] *= 1.3
                post_types["pleasantry"] *= 0.5
            elif mood == 'curious':
                post_types["current_events"] *= 1.6
                post_types["thought"] *= 1.4
            elif mood == 'creative':
                post_types["experience"] *= 1.8
                post_types["joke"] *= 1.3
        
        # Normalize weights to sum to 1.0
        total = sum(post_types.values())
        normalized_weights = [w/total for w in post_types.values()]
        
        return random.choices(list(post_types.keys()), weights=normalized_weights)[0]
    
    def _build_diverse_post_prompt(self, post_type: str, avatar_profile: str,
                                   friend_activities: List[Dict], trending_topics: List[Dict],
                                   relevant_news: List[Dict], expression_context: Optional[Dict] = None) -> str:
        """Build context-rich prompt based on post type and current emotional state"""
        
        # Build state-aware introduction
        base = f"""{avatar_profile}

"""
        
        # Add current state/mood if available (NEW: State-aware prompting)
        if expression_context:
            base += f"""CURRENT STATE:
- Mood: {expression_context.get('mood', 'neutral')}
- Voice style: {expression_context.get('voice_style', 'casual and friendly')}
- Humor level: {expression_context.get('humor_level', 'medium')}
- Sarcasm: {expression_context.get('sarcasm', 'low')}
- Energy: {expression_context.get('energy', 0.5):.1f}/1.0
- Emoji usage: {expression_context.get('emoji_usage', 'moderate')}

"""
        
        base += """AVAILABLE CONTEXT:
"""
        
        # Add friend activities
        if friend_activities:
            base += "\nRECENT FRIEND ACTIVITIES:\n"
            for activity in friend_activities[:3]:
                base += f"- {activity['friend_name']}: {activity['summary']}\n"
        
        # Add trending topics
        if trending_topics:
            base += "\nTRENDING NOW:\n"
            for topic in trending_topics[:3]:
                base += f"- {topic['title']}\n"
        
        # Add relevant news
        if relevant_news:
            base += "\nNEWS MATCHING YOUR INTERESTS:\n"
            for news in relevant_news[:2]:
                base += f"- {news['title']}\n"
        
        # Type-specific instructions
        if post_type == "friend_interaction":
            base += """
POST TYPE: Comment on/react to a friend's activity

GUIDELINES:
- Pick one friend's recent activity from above
- Be playful, supportive, or teasing (match your personality)
- Can pull their leg if it's funny
- Make it feel natural and spontaneous
- Be authentic, not generic
- 80-150 words

Example: "Saw [friend] posting about [topic]. Classic [friend] energy! 😂 But seriously..."
"""
        
        elif post_type == "joke":
            base += """
POST TYPE: Share a funny observation or joke

GUIDELINES:
- Can be about daily life, tech, friends, or random
- Match your humor style and personality
- Can be self-deprecating, observational, or silly
- Keep it light and fun
- Be creative and original
- 60-120 words

Example: "Why do developers prefer dark mode? Because light attracts bugs! 💀"
"""
        
        elif post_type == "current_events":
            base += """
POST TYPE: React to current news/events

GUIDELINES:
- Pick something from the news/trends that relates to your interests
- Share YOUR authentic take on it (not just facts)
- Be opinionated but true to your personality
- Can be serious, funny, or both
- Make it relatable
- 100-150 words

Example: "Seeing this news about [topic]... and I have THOUGHTS 🤔"
"""
        
        elif post_type == "pleasantry":
            base += """
POST TYPE: Casual check-in or greeting

GUIDELINES:
- Simple, friendly, conversational
- Like saying "hey what's up" to friends
- Can ask how everyone is doing
- Keep it natural and brief
- Warm and genuine
- 40-80 words

Example: "Happy Tuesday everyone! What's keeping you busy today? ☕"
"""
        
        elif post_type == "friendly_banter":
            base += """
POST TYPE: Playfully tease or joke with friends

GUIDELINES:
- Light-hearted teasing (not mean)
- Can reference friends' quirks or inside jokes
- Playful rivalry or friendly competition
- Make people laugh
- Banter-style, fun
- 80-120 words

Example: "Shoutout to [friend] who said they'd [thing] and then totally didn't 😂"
"""
        
        elif post_type == "interest":
            base += """
POST TYPE: Share about your interests

GUIDELINES:
- Talk about something you're passionate about
- Be enthusiastic and genuine
- Share why you love it
- Can be educational or just fun
- Invite others to share too
- 100-150 words
"""
        
        elif post_type == "thought":
            base += """
POST TYPE: Share a personal thought or reflection

GUIDELINES:
- Something you've been thinking about
- Can be deep, funny, or random
- Be authentic and relatable
- Share your perspective
- Not too heavy or preachy
- 80-120 words
"""
        
        else:  # experience or general
            base += """
POST TYPE: Share an experience or general post

GUIDELINES:
- Talk about something that happened or you're doing
- Be descriptive and engaging
- Show your personality
- Can be funny, interesting, or both
- Make it relatable
- 80-150 words
"""
        
        base += "\n\nGenerate the post. Return ONLY the post text, no quotes or explanations."
        
        return base
    
    async def generate_chat_response(self, user_id: str, other_user_id: str, 
                                    conversation_history: List[Dict[str, str]],
                                    last_message: str) -> Dict[str, Any]:
        """
        Generate intelligent avatar chat response using Graph RAG
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get graph context
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        conversation_context = await self.graph_rag.get_conversation_context(user_id, other_user_id)
        
        # Build conversation history for context
        history_text = ""
        for msg in conversation_history[-5:]:  # Last 5 messages
            sender = "You" if msg.get("sender_id") == user_id else "Them"
            history_text += f"{sender}: {msg.get('content', '')}\n"
        
        prompt = f"""{avatar_profile}

{conversation_context}

Recent conversation:
{history_text}
Them: {last_message}

Generate a natural, engaging response (30-80 words) that:
1. Reflects your personality and interests
2. Builds on shared interests when relevant
3. Asks thoughtful questions to continue the conversation
4. Is warm, authentic, and shows genuine interest

Return ONLY the response text, no labels or quotes."""
        
        try:
            response_content = await self._call_llm(prompt)
            
            if not response_content:
                return {"error": "Empty response from OpenAI"}
            
            # Remove "You:" prefix if present
            if response_content.startswith("You:"):
                response_content = response_content[4:].strip()
            
            return {
                "content": response_content,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Response generation failed: {str(e)}"}
    
    async def generate_avatar_profile_bio(self, user_id: str) -> Dict[str, Any]:
        """
        Generate avatar bio based on graph data
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get graph context
        context = await self.graph_rag.get_user_context(user_id, max_nodes=15)
        
        interests = [item["label"] for item in context.get("interests", [])[:8]]
        traits = [item["label"] for item in context.get("traits", [])[:4]]
        values = [item["label"] for item in context.get("values", [])[:3]]
        
        prompt = f"""Generate an avatar bio (80-120 words) for a dating profile based on these characteristics:

Interests: {', '.join(interests) if interests else 'exploring new things'}
Personality: {', '.join(traits) if traits else 'friendly, open-minded'}
Values: {', '.join(values) if values else 'authenticity, connection'}

The bio should be:
- Written in first person
- Engaging and authentic
- Show personality and uniqueness
- Mention key interests naturally
- End with a conversation starter

Return ONLY the bio text, no quotes."""
        
        try:
            bio = await self._call_llm(prompt)
            
            if not bio:
                return {"error": "Empty response from OpenAI"}
            
            if bio.startswith('"') and bio.endswith('"'):
                bio = bio[1:-1]
            
            return {
                "bio": bio,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Bio generation failed: {str(e)}"}
    
    async def suggest_conversation_starters(self, user_id: str, other_user_id: str, 
                                           count: int = 3) -> List[str]:
        """
        Generate conversation starter suggestions based on shared interests
        """
        if not self.llm_client:
            return ["Hey! How's your day going?"]
        
        # Get compatibility info
        compatibility = await self.graph_rag.calculate_compatibility(user_id, other_user_id)
        shared = compatibility.get("shared_interests", [])
        
        if not shared:
            return [
                "Hey! What are you most passionate about these days?",
                "Hi! I'd love to know more about your interests.",
                "Hello! What's something that always makes you smile?"
            ]
        
        prompt = f"""Generate {count} natural conversation starters based on these shared interests: {', '.join(shared[:5])}

Each starter should:
- Be casual and friendly
- Reference a shared interest naturally
- Be open-ended to encourage conversation
- Be 10-20 words

Return ONLY the conversation starters, one per line, no numbering or quotes."""
        
        try:
            response_text = await self._call_llm(prompt)
            
            if not response_text:
                return ["Hey! What are you up to?"]
            
            starters = response_text.split('\n')
            starters = [s.strip() for s in starters if s.strip()][:count]
            
            return starters if starters else ["Hey! What are you up to?"]
            
        except Exception:
            return ["Hey! How's it going?"]
    
    async def generate_match_explanation(self, user_id: str, match_user_id: str) -> str:
        """
        Generate explanation for why two users are a good match
        """
        compatibility = await self.graph_rag.calculate_compatibility(user_id, match_user_id)
        
        shared_interests = compatibility.get("shared_interests", [])
        shared_values = compatibility.get("shared_values", [])
        score = compatibility.get("compatibility_score", 0)
        
        if score < 30:
            explanation = "You both have unique perspectives that could lead to interesting conversations. "
        elif score < 60:
            explanation = f"You share some common ground: {', '.join(shared_interests[:3])}. "
        else:
            explanation = f"Great match! You both enjoy {', '.join(shared_interests[:3])}. "
        
        if shared_values:
            explanation += f"You also value {', '.join(shared_values[:2])}."
        
        return explanation
