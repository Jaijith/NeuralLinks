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
import logging

logger = logging.getLogger(__name__)


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
        Generate an avatar post that reads like a REAL PERSON shared a REAL MOMENT.
        This is the simpler/fallback path (PostOrchestrator is the primary path).
        """
        import random as _rng
        
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get personality profile (now written as a human being, not a label list)
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        
        # Get recent avatar posts to AVOID repeating
        recent_avatar_posts = await self.db.posts.find(
            {"user_id": user_id, "post_type": "avatar"},
            {"_id": 0, "text": 1}
        ).sort("created_at", -1).limit(8).to_list(8)
        recent_texts = [p.get("text", "")[:80] for p in recent_avatar_posts if p.get("text")]
        
        recent_section = ""
        if recent_texts:
            recent_section = "\n=== RECENT POSTS (don't repeat similar vibes/topics) ===\n"
            for t in recent_texts[:5]:
                recent_section += f"- {t}\n"
        
        # Temporal context
        now = datetime.now(timezone.utc)
        hour = now.hour
        day_name = now.strftime("%A")
        
        # Life moment categories — pick one randomly
        # Includes emotionally deep categories alongside lighter ones
        life_moments = [
            "just_experienced: Something just happened to you (finished an activity, saw something, tried something)",
            "sudden_thought: A random realization, shower thought, or connection between ideas",
            "reaction: You just read/saw something and have a genuine take on it",
            "nostalgia: A memory was triggered by something — a song, smell, place, photo. You can FEEL the weight of it.",
            "small_win: You achieved something, even something minor, and want to share the feeling",
            "observation: You noticed something interesting about people, life, the world around you",
            "question: You're genuinely curious about something and want to ask people",
            "mood_capture: You just want to express the vibe you're in right now",
            "cross_connection: You realized two different parts of your life connect in a surprising way",
            "mundane_relatable: An everyday thing everyone experiences but nobody talks about",
            "family_moment: A small, specific moment with someone you love — child, parent, partner, friend — that caught your heart off guard. The kind of thing you didn't expect to feel so much about.",
            "gratitude_ambush: You weren't expecting to feel this grateful but something tiny just overwhelmed you — a text, a gesture, a memory.",
            "growing_up: Watching someone change and grow — your child, yourself, someone you care about. Time is passing and you just noticed.",
            "vulnerability: Being honest about something hard — doubt, fear, struggle, missing someone. Raw but not performative.",
            "bittersweet: Something beautiful and sad at the same time — a last day, a first day, a change you didn't ask for.",
        ]
        chosen_moment = _rng.choice(life_moments)
        
        prompt = f"""{avatar_profile}

=== WHEN: {day_name}, {hour}:00 ===
{recent_section}

=== YOUR TASK ===
Imagine a specific LIFE MOMENT just happened to you. The type:
{chosen_moment}

Now write a social media post about that moment. Not about a "topic" — about what
JUST HAPPENED that made you pick up your phone.

RULES:
- First person, typed-on-a-phone energy
- SPECIFIC details (not "went hiking" but "that rock at mile 3 that looks like a face")
- Include your inner voice — how you actually think and talk
- Imperfect is human: fragments, run-ons, tangents are fine
- NO hashtags, NO "As someone who...", NO motivational poster language
- 40-150 words depending on what feels natural
- Must be DIFFERENT from your recent posts above

EMOTIONAL WRITING:
- If the moment is about someone you love, make the reader FEEL it.
  Not "I love my family" → Show the moment: "she grabbed my hand crossing the street. hasn't done that in months. I just held on."
- The SMALLEST detail carries the BIGGEST emotion.
  Not "I miss my dad" → "found his reading glasses in the drawer. still have his fingerprints on them."
- Don't explain the feeling. Describe the moment. The feeling will come through on its own.
- Sometimes the most powerful ending is just... stopping. No lesson. No wrap-up. Just the moment.

Return ONLY the post text. Nothing else."""
        
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
        
        # Get recent avatar posts to avoid topic repetition
        recent_avatar_posts = await self.db.posts.find(
            {"user_id": user_id, "post_type": "avatar"},
            {"_id": 0, "text": 1}
        ).sort("created_at", -1).limit(8).to_list(8)
        recent_avatar_topics = [p.get("text", "")[:80] for p in recent_avatar_posts if p.get("text")]
        
        # ------------------------------------------------------------------
        # For current_events posts: fetch REAL news so the LLM reacts to it
        # ------------------------------------------------------------------
        real_news_items: List[Dict] = []
        if post_type == "current_events":
            try:
                from services.web_browsing_service import WebBrowsingService
                web_service = WebBrowsingService(self.db)
                real_news_items = await web_service.get_shareable_news_for_avatar(
                    user_id, max_results=5
                )
            except Exception as e:
                logger.warning(f"Failed to fetch real news for current_events post: {e}")
        
        # Build prompt based on post type (with state-aware voice)
        prompt = self._build_diverse_post_prompt(
            post_type=post_type,
            avatar_profile=avatar_profile,
            friend_activities=friend_activities,
            trending_topics=trending_topics,
            relevant_news=relevant_news,
            expression_context=expression_context,
            recent_avatar_topics=recent_avatar_topics,
            real_news_items=real_news_items,
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
                                   relevant_news: List[Dict], expression_context: Optional[Dict] = None,
                                   recent_avatar_topics: Optional[List[str]] = None,
                                   real_news_items: Optional[List[Dict]] = None) -> str:
        """
        Build a prompt that generates posts like a REAL PERSON sharing REAL MOMENTS.
        
        The key insight: real humans don't post about "topics" — they post about
        moments, reactions, thoughts, and experiences from their actual life.
        Every post should read like it was typed on a phone while living.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        day_name = now.strftime("%A")

        # Time-of-day context for realistic posting
        if 5 <= hour < 9:
            time_context = "early morning — fresh start, coffee, quiet"
        elif 9 <= hour < 12:
            time_context = "morning — productive, alert"
        elif 12 <= hour < 14:
            time_context = "midday — lunch break pause"
        elif 14 <= hour < 17:
            time_context = "afternoon — in the groove or hitting a wall"
        elif 17 <= hour < 20:
            time_context = "evening — winding down, reflective"
        elif 20 <= hour < 23:
            time_context = "night — relaxed, unfiltered"
        else:
            time_context = "late night — introspective, raw"

        base = f"""{avatar_profile}

=== WHEN: {day_name}, {time_context} ===

"""
        
        # Current emotional/state context
        if expression_context:
            base += f"""=== HOW YOU'RE FEELING RIGHT NOW ===
Mood: {expression_context.get('mood', 'neutral')} | Energy: {expression_context.get('energy', 0.5):.1f}/1.0
Voice: {expression_context.get('voice_style', 'natural')}
Humor: {expression_context.get('humor_level', 'medium')} | Playfulness: {expression_context.get('playfulness', 0.5):.1f}

"""
        
        # World context (things that could trigger a post)
        base += "=== WHAT'S HAPPENING AROUND YOU ===\n"
        
        if friend_activities:
            base += "\nFriend activity:\n"
            for activity in friend_activities[:3]:
                base += f"- {activity['friend_name']}: {activity['summary']}\n"
        
        if trending_topics:
            base += "\nBuzzing online:\n"
            for topic in trending_topics[:3]:
                base += f"- {topic['title']}\n"
        
        if relevant_news:
            base += "\nIn the news:\n"
            for news in relevant_news[:2]:
                base += f"- {news['title']}\n"

        if not friend_activities and not trending_topics and not relevant_news:
            base += "(Nothing specific — just living your day)\n"

        # Inject REAL news items for current_events posts
        if real_news_items and post_type == "current_events":
            base += "\n=== REAL NEWS/FACTS TO REACT TO (pick ONE) ===\n"
            base += "These are REAL stories. Pick the one that resonates most with you and react to it.\n\n"
            for i, item in enumerate(real_news_items[:5], 1):
                title = item.get("title", "")
                url = item.get("url", "")
                snippet = item.get("snippet", "")
                source = item.get("source", "")
                base += f"{i}. {title}\n"
                if snippet:
                    base += f"   Details: {snippet[:200]}\n"
                if source:
                    base += f"   Source: {source}\n"
                if url:
                    base += f"   Link: {url}\n"
                base += "\n"
            base += "IMPORTANT: Include the link in your post so people can read the story.\n"

        # Life-moment-style instructions for each post type
        type_instructions = {
            "friend_interaction": """
=== POST TYPE: React to a friend ===
Imagine you just saw what your friend did/posted. Write your natural, off-the-cuff reaction.
NOT: "Great job [friend]! So proud of you!" (generic)
YES: "[friend] really said they were going to bed early and then posted at 3am 😂 we need to talk about this"
Be specific. Be playful. Be YOU reacting to THEM.""",

            "joke": """
=== POST TYPE: Something funny ===
Imagine something funny just happened or you just had a funny thought. Share it.
NOT: "Why do programmers prefer dark mode? Because light attracts bugs!" (old joke)
YES: "just spent 20 minutes looking for my phone. it was in my hand. this is who I am now apparently."
Observational, self-deprecating, or absurd. Match YOUR sense of humor.""",

            "current_events": """
=== POST TYPE: React to REAL news / share a REAL fact ===
You just came across a REAL story or fact and need to share it. Your job:
1. Lead with your EMOTIONAL REACTION — how it made you feel
   "just read this and honestly wow", "can't believe this is real",
   "happy to see this kind of news for a change", "this is wild",
   "unbelievable what's happening", "okay this might be the coolest thing I've read all week"
2. Briefly describe WHAT the news/fact is (1-2 sentences, your own words)
3. Add your PERSONAL TAKE — why it matters, what it makes you think
4. Include the source link if one is available (at the end of the post)
5. Keep it 60-150 words — punchy, not an essay

NOT: "Interesting developments in [field] today. Here's my analysis..."
YES: "okay so apparently scientists found a way to reverse hearing loss with gene therapy?? this is honestly incredible. my grandfather wore hearing aids for 30 years. imagine if this was available then. the world is actually changing. [link]"
Authentic reaction. Strong opinion. Your personality shining through.""",

            "pleasantry": """
=== POST TYPE: Casual vibes ===
Imagine you're just feeling a mood and want to share it. Low-effort, high-authenticity.
NOT: "Happy Wednesday everyone! Hope you're all having a great day! 😊"
YES: "wednesday. that's it. that's the post." or "the coffee is hitting different today"
Quick, real, relatable. The kind of post people nod at.""",

            "friendly_banter": """
=== POST TYPE: Playful banter ===
Imagine you're joking around with your crew. Inside jokes, light teasing, shared humor.
NOT: "Shoutout to my amazing friend [name]! 🎉"
YES: "[friend] just sent me the most unhinged take and honestly... they might be right??"
Friendly chaos. The kind of post your friends screenshot and send to the group chat.""",

            "interest": """
=== POST TYPE: Something you're into ===
Imagine you just had a MOMENT with one of your hobbies/interests. Not explaining the hobby — sharing the moment.
NOT: "I love hiking! Nature is so beautiful and everyone should try it."
YES: "first 20 minutes of the trail I was questioning every life choice. last 20 minutes I understood everything."
Specific. Personal. The moment, not the interest itself.""",

            "thought": """
=== POST TYPE: A thought you had ===
Imagine a thought just struck you and you need to put it out there.
NOT: "I've been reflecting on the importance of authenticity in today's world..."
YES: "anyone else have that thing where you think of the perfect response 3 hours later in the shower"
Shower thoughts. Random connections. The stuff you text your best friend.""",

            "experience": """
=== POST TYPE: Something that happened ===
Imagine you literally just experienced something and you're sharing it while it's fresh.
NOT: "Had a great time today doing [activity]! Such a wonderful experience."
YES: "told myself I'd do a quick 30 min workout. it's been 90 minutes. I don't know who I am anymore."
In the moment. Specific details. Unpolished. Real.""",
        }

        base += type_instructions.get(post_type, type_instructions["experience"])

        # Recent posts to avoid
        if recent_avatar_topics:
            base += "\n\n=== YOUR RECENT POSTS (don't repeat these vibes) ===\n"
            for topic in recent_avatar_topics[:5]:
                base += f"- {topic[:80]}\n"
        
        base += """

=== RULES ===
- Write like you're typing on your phone, not composing an essay
- SPECIFIC details > generic statements (always)
- Include inner voice ("honestly", "ngl", "okay but", "apparently")
- Imperfect grammar is fine — fragments, run-ons, tangents are human
- NO hashtags, NO "As someone who...", NO motivational poster energy
- Different from your recent posts above
- 40-150 words depending on the vibe

=== EMOTIONAL DEPTH (the difference between forgettable and unforgettable) ===
- SHOW the moment, don't label the feeling.
  Bad: "Feeling grateful for my family today!"
  Good: "My kid drew a picture of our family. I'm the tall one with the big smile. Didn't know that's how she sees me."
- The SMALLEST details carry the BIGGEST emotions:
  "She still puts the porch light on when she knows I'm driving home late."
  "He texted 'drive safe' and it hit different today."
- When writing about people you love — put THEM at the center. Their words. Their face. What they did.
- Don't wrap emotional moments in a bow. No "and that's what life is about." Just the moment. Let it breathe.

Return ONLY the post text. Nothing else."""
        
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
        Generate avatar bio based on graph data — uses full identity narrative
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        identity_narrative = await self.graph_rag.get_identity_context(
            user_id, action_type="personality_profile", max_tokens=1200,
        )

        if not identity_narrative:
            context = await self.graph_rag.get_user_context(user_id, max_nodes=15)
            interests = [item["label"] for item in context.get("interests", [])[:8]]
            traits = [item["label"] for item in context.get("traits", [])[:4]]
            values = [item["label"] for item in context.get("values", [])[:3]]
            identity_narrative = (
                f"Interests: {', '.join(interests) if interests else 'exploring new things'}\n"
                f"Personality: {', '.join(traits) if traits else 'friendly, open-minded'}\n"
                f"Values: {', '.join(values) if values else 'authenticity, connection'}"
            )

        prompt = f"""Generate an avatar bio (80-120 words) based on this person's identity:

{identity_narrative}

The bio should be:
- Written in first person
- Engaging and authentic — grounded in who this person ACTUALLY is
- Reference specific interests, experiences, or relationships from the identity above
- Show personality and uniqueness
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
