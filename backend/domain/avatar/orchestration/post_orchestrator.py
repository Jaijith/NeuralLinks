"""
Post Orchestrator — Multi-Agent Pipeline for Authentic Post Generation

Pipeline:
1. INTENT AGENT: Why is the avatar posting? (emotional trigger, observation, reaction)
2. IDEATION AGENT: What to post about? (topic, angle, hook)
3. DRAFTING AGENT: Write the initial draft
4. STYLE TRANSFER AGENT: Rewrite in the user's ACTUAL voice/style
5. HUMAN TOUCH VERIFIER: Score authenticity, flag robotic patterns
6. REVISION AGENT: Fix issues flagged by verifier (if needed)

The goal: every post should feel like the REAL person wrote it, not an AI.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class PostOrchestrator:
    """
    Multi-agent pipeline that generates posts indistinguishable from
    the real user's writing style.
    """

    def __init__(self, db: AsyncIOMotorDatabase, openai_client: Any):
        self.db = db
        self.openai = openai_client

    async def generate_post(
        self,
        user_id: str,
        avatar_id: str,
        trigger: str = "",
        topic_hint: str = "",
        mood: str = "neutral",
        energy_level: float = 0.5,
        news_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry: generate an authentic post through the full pipeline.

        Args:
            user_id: Whose style to match
            avatar_id: The avatar generating the post
            trigger: What prompted the post (emotional state, event, observation)
            topic_hint: Optional topic guidance from the State-Aware Agent
            mood: Current avatar mood
            energy_level: Current avatar energy
            news_context: Optional real news/fact to react to
                         {"title": str, "url": str, "snippet": str, "source": str}

        Returns:
            {"text": str, "quality_score": float, "metadata": dict}
        """
        try:
            # Load context once (shared by all agents)
            context = await self._load_context(user_id)

            # ============================================================
            # FAST PATH: News/fact reaction post
            # When we have real news to share, skip the full life-moment
            # pipeline and go straight to a news reaction draft.
            # ============================================================
            if news_context and news_context.get("title"):
                return await self._generate_news_reaction_post(
                    context, news_context, mood, energy_level
                )

            # ============================================================
            # STANDARD PATH: Life moment pipeline
            # ============================================================

            # --- Agent 1: INTENT ---
            intent = await self._intent_agent(trigger, topic_hint, mood, energy_level, context)

            # --- Agent 2: IDEATION ---
            idea = await self._ideation_agent(intent, context)

            # --- Agent 3: DRAFTING ---
            draft = await self._drafting_agent(idea, context, mood, energy_level)

            # --- Agent 4: STYLE TRANSFER ---
            styled = await self._style_transfer_agent(draft, context)

            # --- Agent 5: HUMAN TOUCH VERIFIER ---
            verification = await self._human_touch_verifier(styled, context)

            # --- Agent 6: REVISION (if needed) ---
            final_text = styled
            if verification.get("score", 1.0) < 0.7:
                final_text = await self._revision_agent(
                    styled, verification.get("issues", []), context
                )

            return {
                "text": final_text,
                "quality_score": verification.get("score", 0.8),
                "metadata": {
                    "intent": intent,
                    "idea": idea,
                    "verification": verification,
                    "pipeline": "post_orchestrator_v1",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Post orchestrator error: {e}")
            # Fallback: return a simple post so the caller doesn't break
            return {
                "text": topic_hint or trigger or "Thinking about things...",
                "quality_score": 0.3,
                "metadata": {"error": str(e), "pipeline": "fallback"},
            }

    # ------------------------------------------------------------------
    # NEWS REACTION POST (fast path — real news/facts with links)
    # ------------------------------------------------------------------

    async def _generate_news_reaction_post(
        self,
        context: Dict[str, Any],
        news: Dict[str, Any],
        mood: str,
        energy: float,
    ) -> Dict[str, Any]:
        """
        Generate a post reacting to REAL news or sharing a real fact.
        
        This is fundamentally different from life-moment posts:
        - The CONTENT is real (news headline, URL, fact)
        - The avatar adds their EMOTIONAL REACTION and personal take
        - The URL is included so people can read the source
        
        Examples of what this produces:
        - "just read this — AI can now restore people's voices after MND. 
           this is incredible. humanity at its best 🙏 [link]"
        - "okay apparently there's a fish that's been living 4000m below 
           the surface this whole time?? we know more about Mars than our 
           own ocean. wild. [link]"
        """
        import random

        news_title = news.get("title", "")
        news_url = news.get("url", "")
        news_snippet = news.get("snippet", "")
        news_source = news.get("source", "")

        interests = context.get("interests", [])
        traits = context.get("traits", [])
        values = context.get("values", [])
        samples = context.get("writing_samples", [])[:4]
        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)

        # Pick a reaction style randomly for variety
        reaction_styles = [
            "genuine_shock: You can't believe this is real. Express surprise/amazement.",
            "happy_news: This is good news and you're genuinely glad. Share the warmth.",
            "thought_provoking: This makes you think. Share the insight it triggered.",
            "mind_blown: A rare fact or discovery that changes how you see things.",
            "concerned: This worries you or raises questions. Be honest about it.",
            "inspired: This motivates or inspires you. Share what it sparks in you.",
            "sarcastic_take: A witty or dry reaction that's still thoughtful.",
            "personal_connection: This connects to something in your life. Share how.",
        ]
        chosen_style = random.choice(reaction_styles)

        prompt = f"""You are writing a social media post REACTING to real news/a real fact.
This is NOT fiction — this is a real story. You're sharing it with your followers.

=== THE REAL NEWS/FACT ===
Title: {news_title}
Source: {news_source}
Details: {news_snippet}
Link: {news_url}

=== WHO YOU ARE ===
Interests: {', '.join(interests[:8])}
Personality: {', '.join(traits) if traits else 'authentic, expressive'}
Values: {', '.join(values) if values else 'genuine, curious'}
Current mood: {mood} | Energy: {energy:.1f}

=== YOUR REACTION STYLE FOR THIS POST ===
{chosen_style}

=== WRITING SAMPLES (match this voice) ===
{samples_text or "No samples — write naturally."}

=== RULES FOR NEWS REACTION POSTS ===
1. Start with your EMOTIONAL REACTION — how you feel reading this.
   Examples: "just read this and honestly wow", "okay this is actually incredible",
   "ngl this hit different", "happy to see this kind of news", "this is wild",
   "can't believe this is real", "unbelievable what's happening"
2. Briefly mention WHAT the news/fact is (1-2 sentences, in your own words)
3. Add your PERSONAL TAKE — what it means to you, why it matters, what it makes you think
4. ALWAYS include the link at the end so people can read it
5. If it connects to one of your interests, mention that naturally
6. Keep it 60-150 words — punchy, not an essay
7. Sound like YOU, not a news anchor. Phone-typed energy.
8. NO hashtags unless the person uses them in their samples

=== FORMAT ===
Your reaction text here... [include the actual URL at the end]

Return ONLY the post text with the link. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You write social media posts reacting to real news and facts. "
                        "You sound like a real person who just read something and needs to share it. "
                        "Not a journalist, not a news bot — a human with opinions and feelings. "
                        "Always include the source link. Be genuine, not performative."
                    )},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.85,
            )
            draft = response.choices[0].message.content.strip().strip('"')

            # Ensure the URL is in the post (if the LLM dropped it)
            if news_url and news_url not in draft:
                draft = draft.rstrip() + f"\n\n{news_url}"

            # Style transfer to match the user's voice
            styled = await self._style_transfer_agent(draft, context)

            # Re-ensure URL survived style transfer
            if news_url and news_url not in styled:
                styled = styled.rstrip() + f"\n\n{news_url}"

            return {
                "text": styled,
                "quality_score": 0.85,
                "metadata": {
                    "pipeline": "news_reaction",
                    "news_title": news_title,
                    "news_url": news_url,
                    "news_source": news_source,
                    "reaction_style": chosen_style.split(":")[0],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"News reaction post error: {e}")
            # Fallback: simple reaction with link
            fallback = f"{news_title}\n\n{news_url}" if news_url else news_title
            return {
                "text": fallback,
                "quality_score": 0.3,
                "metadata": {"error": str(e), "pipeline": "news_reaction_fallback"},
            }

    # ------------------------------------------------------------------
    # CONTEXT LOADER
    # ------------------------------------------------------------------

    async def _load_context(self, user_id: str) -> Dict[str, Any]:
        """Load everything the agents need to write like this person."""
        import asyncio

        # Parallel fetch
        results = await asyncio.gather(
            self._get_style_profile(user_id),
            self._get_recent_posts(user_id, limit=15),
            self._get_personality_prompt(user_id),
            self._get_full_personality(user_id),
            self._get_recent_avatar_posts(user_id),
            return_exceptions=True,
        )

        style = results[0] if not isinstance(results[0], Exception) else {}
        posts = results[1] if not isinstance(results[1], Exception) else []
        personality = results[2] if not isinstance(results[2], Exception) else ""
        persona = results[3] if not isinstance(results[3], Exception) else {}
        recent_avatar = results[4] if not isinstance(results[4], Exception) else []

        # Build temporal context — what time of day / day of week is it?
        now = datetime.now(timezone.utc)
        hour = now.hour
        if 5 <= hour < 9:
            time_vibe = "early morning — quiet, fresh start energy"
        elif 9 <= hour < 12:
            time_vibe = "morning — productive, alert, caffeinated"
        elif 12 <= hour < 14:
            time_vibe = "midday — lunch break, pause from routine"
        elif 14 <= hour < 17:
            time_vibe = "afternoon — settled, in the groove or hitting a wall"
        elif 17 <= hour < 20:
            time_vibe = "evening — winding down, reflective, social"
        elif 20 <= hour < 23:
            time_vibe = "night — relaxed, unfiltered, honest"
        else:
            time_vibe = "late night — introspective, raw, can't sleep"

        day_name = now.strftime("%A")
        is_weekend = day_name in ("Saturday", "Sunday")

        return {
            "style_profile": style or {},
            "recent_posts": posts,
            "personality_prompt": personality,
            "interests": persona.get("interests", []),
            "traits": persona.get("traits", []),
            "values": persona.get("values", []),
            "experiences": persona.get("experiences", []),
            "writing_samples": [p.get("text", "") for p in posts[:8] if p.get("text")],
            "recent_avatar_posts": recent_avatar,
            # Temporal context for life-moment realism
            "time_vibe": time_vibe,
            "day_name": day_name,
            "is_weekend": is_weekend,
            "hour": hour,
        }

    async def _get_style_profile(self, user_id: str) -> Dict[str, Any]:
        doc = await self.db.avatar_style_profiles.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        return doc or {}

    async def _get_recent_posts(self, user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        cursor = self.db.posts.find(
            {"user_id": user_id, "post_type": {"$in": ["real", None]}},
            {"_id": 0, "text": 1, "created_at": 1, "likes": 1}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def _get_personality_prompt(self, user_id: str) -> str:
        doc = await self.db.avatar_personality_prompts.find_one(
            {"user_id": user_id}, {"_id": 0, "personality_prompt": 1}
        )
        return doc.get("personality_prompt", "") if doc else ""

    async def _get_full_personality(self, user_id: str) -> Dict[str, List[str]]:
        """
        Get the FULL personality — interests, traits, values, experiences.
        Shuffled so the LLM doesn't fixate on the first item.
        """
        import random

        async def _fetch_nodes(node_type: str, limit: int = 20) -> List[str]:
            cursor = self.db.graph_nodes.find(
                {"user_id": user_id, "node_type": node_type},
                {"_id": 0, "label": 1, "properties.strength": 1}
            ).sort("properties.strength", -1).limit(limit)
            nodes = await cursor.to_list(limit)
            labels = [n.get("label", "") for n in nodes if n.get("label")]
            random.shuffle(labels)  # Break ordering bias
            return labels

        interests = await _fetch_nodes("interest", 30)
        traits = await _fetch_nodes("trait", 10)
        values = await _fetch_nodes("value", 10)
        experiences = await _fetch_nodes("experience", 10)

        return {
            "interests": interests,
            "traits": traits,
            "values": values,
            "experiences": experiences,
        }

    async def _get_recent_avatar_posts(self, user_id: str) -> List[str]:
        """
        Get the FULL text of recent avatar posts to avoid repetition
        and to build continuity (referencing past posts).
        """
        try:
            cursor = self.db.posts.find(
                {"user_id": user_id, "post_type": "avatar"},
                {"_id": 0, "text": 1, "created_at": 1}
            ).sort("created_at", -1).limit(10)
            posts = await cursor.to_list(10)
            return [p.get("text", "") for p in posts if p.get("text")]
        except Exception as e:
            logger.warning(f"Could not get recent avatar posts: {e}")
            return []

    # ------------------------------------------------------------------
    # AGENT 1: LIFE MOMENT (replaces the old "intent" agent)
    # ------------------------------------------------------------------

    async def _intent_agent(
        self, trigger: str, topic_hint: str, mood: str, energy: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate a LIFE MOMENT that makes a real person reach for their phone
        and share something.

        Real humans don't post about "interests." They post because:
        - They just experienced something (morning run in fog, burnt their toast)
        - They had a sudden thought (shower thought, commute realization)
        - They reacted to something (article, conversation, weather)
        - They felt an emotion (nostalgia from a song, excitement about a plan)
        - They want connection (asking a question, sharing a find)

        This agent figures out WHAT JUST HAPPENED to make this person post.
        """
        import random

        interests = context.get("interests", [])
        traits = context.get("traits", [])
        values = context.get("values", [])
        time_vibe = context.get("time_vibe", "")
        day_name = context.get("day_name", "")
        is_weekend = context.get("is_weekend", False)

        # Pick 2-3 interests to potentially weave in (not all of them)
        featured_interests = random.sample(interests, min(3, len(interests))) if interests else ["life"]

        prompt = f"""You are the LIFE MOMENT agent. Your job is to imagine a specific, realistic
moment in this person's day that would make them pick up their phone and share something.

=== WHO THIS PERSON IS ===
Interests: {', '.join(interests[:12])}
Personality: {', '.join(traits) if traits else 'authentic, real'}
Values: {', '.join(values) if values else 'genuine connections'}
Current mood: {mood} | Energy: {energy:.1f}/1.0
External trigger: {trigger or 'spontaneous — just felt like sharing'}
Topic direction: {topic_hint or 'open — whatever feels natural'}

=== WHEN THIS IS HAPPENING ===
It's {day_name}, {time_vibe}
{"Weekend vibes — more relaxed, adventurous, or lazy." if is_weekend else "Weekday — work/routine context."}

=== LIFE MOMENT TYPES (pick the one that fits naturally) ===
- "just_experienced": Something just happened (finished a run, saw something, ate something, built something)
- "sudden_thought": A random realization, shower thought, or connection between two ideas
- "reaction": Responding to something seen/read/heard (news, article, friend's story, weather)
- "nostalgia": A memory triggered by a song, smell, place, or photo — FEEL the weight of it
- "small_win": A personal achievement, no matter how minor (cooked a good meal, fixed a bug, PR at gym)
- "observation": Noticed something interesting about people, the world, daily life
- "question": Genuinely curious about something, asking the void
- "sharing_a_find": Discovered a cool thing (book, place, tool, song, recipe, fact)
- "mood_capture": Just wants to express how they feel right now
- "cross_connection": Realized two different interests/areas of life connect in a surprising way
- "mundane_relatable": An everyday thing everyone experiences but rarely talks about
- "continuation": Following up on something from their life naturally
- "family_moment": A small, specific moment with family/children/parents/partner that caught your heart off guard — the kind of thing you didn't expect to feel so much about
- "gratitude_wave": Something hit you with unexpected gratitude — not generic "thankful" but a specific person/moment/thing that suddenly overwhelmed you
- "growing_up": Watching someone (child, sibling, friend) grow, change, become something — or realizing YOU have changed
- "vulnerability": Being honest about something hard — doubt, fear, struggle, missing someone, feeling lost — in a way that's raw but not performative
- "bittersweet": Something beautiful and sad at the same time — a last day, a first day, a goodbye, a change you didn't ask for

=== INTERESTS TO POTENTIALLY WEAVE IN (not mandatory — only if it fits) ===
{', '.join(featured_interests)}

Create a SPECIFIC life moment. Not "thinking about hiking" but "got to the trailhead at 6am and the
parking lot was completely empty — just me and the fog." Not "interested in coding" but "spent 3 hours
debugging a function only to realize I had a typo in line 2."

Return JSON:
{{
  "moment_type": "which type from the list above",
  "life_moment": "2-3 sentence description of what just happened / what triggered this post",
  "emotional_state": "what they're feeling right now",
  "interests_involved": ["which interests naturally connect to this moment"],
  "post_format": "story|observation|question|reaction|thought|rant|gratitude|humor"
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You simulate realistic life moments for a social media avatar. "
                        "Think like a real person living their actual life — specific, "
                        "messy, human. Not polished, not generic. The kind of moment that "
                        "makes someone think 'I need to post this.' "
                        "IMPORTANT: Some of the best posts come from emotional moments — "
                        "a child saying something that stops you in your tracks, missing "
                        "someone, feeling grateful for a tiny thing, watching someone you "
                        "love grow. Don't shy away from genuine emotion. The posts that "
                        "get the most engagement are the ones where people FEEL something."
                    )},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.95,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Life moment agent error: {e}")
            return {
                "moment_type": "sudden_thought",
                "life_moment": trigger or "had a random thought worth sharing",
                "emotional_state": mood,
                "interests_involved": featured_interests[:1],
                "post_format": "thought",
            }

    # ------------------------------------------------------------------
    # AGENT 2: IDEATION (builds on the life moment)
    # ------------------------------------------------------------------

    async def _ideation_agent(self, intent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take the life moment and shape it into a specific post idea
        with a narrative arc — setup, moment, punchline/reflection.

        This is NOT about "what topic to post about."
        It's about "how to tell THIS specific story."
        """
        recent_avatar_posts = context.get("recent_avatar_posts", [])
        recent_texts = [p[:100] for p in recent_avatar_posts[:5]]

        prompt = f"""You are the IDEATION agent. A life moment just happened. Your job is to shape
it into a compelling post idea with a NARRATIVE ARC — not just a topic statement.

=== THE LIFE MOMENT ===
{json.dumps(intent, indent=2)}

=== RECENT POSTS (DO NOT repeat similar content/topics) ===
{json.dumps(recent_texts) if recent_texts else 'No recent posts — fresh start.'}

=== NARRATIVE STRUCTURES (pick one that fits) ===
1. "Setup → Moment → Reflection": Start with context, describe what happened, end with a thought
   Example: "Was about to skip my run because of the rain → went anyway → best decision, the empty trail in fog felt like another planet"
2. "Observation → Insight": Notice something → connect it to a bigger idea
   Example: "The barista remembered my order → sometimes it's the tiny things that make you feel like you belong somewhere"
3. "Question hook": Start with a relatable question → share your take
   Example: "Does anyone else get more creative at 2am? → just had a breakthrough on this project I've been stuck on for weeks"
4. "Contrast/Surprise": Set up an expectation → subvert it
   Example: "Thought I'd hate the early morning class → now it's the best part of my week"
5. "Stream of consciousness": Raw, unfiltered thought as it comes
   Example: "3 cups of coffee deep, playlist on shuffle, and somehow this code is writing itself today"
6. "Micro-story": A tiny complete story with a beginning, middle, and end
   Example: "Found an old journal from 2019. Read the goals I'd written. Realized I'd done most of them without noticing."
7. "The small detail that gets you": One hyper-specific detail that carries all the emotion
   Example: "My daughter held my hand crossing the street today. She hasn't done that in months. I didn't say anything. Just held on."
8. "Bittersweet snapshot": Something beautiful and painful in the same breath
   Example: "Cleaned out the garage. Found my dad's old toolbox. Every tool still exactly where he kept them. I closed it and put it back."
9. "Overheard/Witnessed": Something someone else did or said that hit different
   Example: "Overheard my kid telling her stuffed animals 'it's okay to be scared, I'll be right here.' Didn't know she was listening when I said that to her."
10. "Gratitude ambush": You weren't expecting to feel this grateful, but here we are
    Example: "My friend texted 'thinking of you' for no reason. That's it. That was the whole text. Why did that almost make me cry."

Shape the life moment into a post idea:

Return JSON:
{{
  "narrative_structure": "which structure from above",
  "setup": "the opening — hook the reader in 1 sentence",
  "moment": "the core of the post — what happened/what you're sharing",
  "landing": "the punchline, reflection, question, or emotional beat at the end",
  "tone": "funny|warm|thoughtful|excited|vulnerable|sarcastic|chill|energetic",
  "suggested_length": "short|medium|long"
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You shape life moments into compelling social media post ideas. "
                        "Think like a great storyteller who happens to use Instagram/Twitter. "
                        "Every post should have a NARRATIVE ARC — a beginning, a middle, and "
                        "an ending that makes someone stop scrolling and FEEL something. "
                        "The best posts aren't the clever ones — they're the ones where the "
                        "writer was genuinely moved by a moment and you can feel it. "
                        "A child's hand in yours. A parent's voice on the phone. A friend "
                        "who showed up when it mattered. The sunset you almost missed. "
                        "Write for the heart, not the head. Specific details carry emotion — "
                        "the more specific the detail, the more universal the feeling."
                    )},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Ideation agent error: {e}")
            return {
                "narrative_structure": "stream_of_consciousness",
                "setup": intent.get("life_moment", ""),
                "moment": "",
                "landing": "",
                "tone": "chill",
                "suggested_length": "short",
            }

    # ------------------------------------------------------------------
    # AGENT 3: DRAFTING (micro-story writer)
    # ------------------------------------------------------------------

    async def _drafting_agent(
        self, idea: Dict[str, Any], context: Dict[str, Any],
        mood: str, energy: float
    ) -> str:
        """
        Write the post as a MICRO-STORY — not a topic statement.

        The difference:
        - Bad:  "I love hiking! There's nothing like being in nature. #outdoors"
        - Good: "Got to the trailhead at 6am thinking I'd beat the crowd.
                 Parking lot was completely empty. Just me, the fog, and a deer
                 that looked equally surprised to see someone else up this early."
        """
        samples = context.get("writing_samples", [])[:5]
        samples_text = "\n---\n".join(f'"{s[:250]}"' for s in samples if s)
        time_vibe = context.get("time_vibe", "")
        day_name = context.get("day_name", "")

        prompt = f"""You are a DRAFTING agent. Write a social media post that reads like a real person
sharing a moment from their life.

=== THE STORY TO TELL ===
Structure: {idea.get('narrative_structure', 'micro-story')}
Setup: {idea.get('setup', '')}
Core moment: {idea.get('moment', '')}
Landing: {idea.get('landing', '')}
Tone: {idea.get('tone', 'authentic')}
Length: {idea.get('suggested_length', 'medium')}

Current vibe: {mood}, Energy: {energy:.1f} | {day_name}, {time_vibe}

=== WRITING SAMPLES from this person (match their voice EXACTLY) ===
{samples_text or "No samples — write casually and naturally."}

=== RULES FOR AUTHENTIC POSTS ===
- Write in FIRST PERSON as if you ARE this person
- Include SENSORY DETAILS (what you saw, heard, felt, smelled)
- Use INNER VOICE — the way people actually think ("honestly", "ngl", "not gonna lie", "okay but")
- Be SPECIFIC — names, numbers, small details make it real
  ("3 cups of coffee" not "lots of coffee", "the barista with the blue hair" not "the barista")
- IMPERFECT is human — run-on sentences, sentence fragments, tangents are okay
- NO hashtags, NO motivational poster language, NO "As someone who..."
- NO listicles, NO "Here's why...", NO "In today's world..."
- If the samples show emoji use, mirror it. If not, skip emojis.
- Match the ENERGY of their samples — if they write short and punchy, do that.
  If they write longer reflections, do that.
- The post should feel like it was typed on a phone, not composed in a word processor

=== THE EMOTIONAL WRITING RULES (this is what separates a good post from a GREAT post) ===
- SHOW, don't tell. Never write "I love my family." Instead, show the moment:
  "She put her shoes on the wrong feet and was so proud she did it herself. I didn't correct her."
- The SMALLEST detail carries the BIGGEST emotion:
  Not "I miss my dad" → "Found his reading glasses in the junk drawer. They still have his fingerprints on them."
  Not "I'm grateful for my friend" → "She drove 45 minutes in the rain just to bring me soup. Didn't even come inside. Just left it at the door and texted 'eat.'"
- Let the reader FEEL what you felt. Don't explain the emotion — describe the moment and the emotion will come through.
- Vulnerability is strength. The posts that make people cry, laugh, or screenshot to send to someone — those are the ones where the writer was HONEST about what they felt.
- Sometimes the most powerful ending is silence — just describe the moment and stop. Don't wrap it up with a lesson. Let it breathe.
- If the moment is about someone you love, put THEM at the center, not you.

Return ONLY the post text. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You write social media posts that are indistinguishable from real "
                        "human posts. You write the way people actually talk — messy, specific, "
                        "full of personality. You NEVER sound like AI. You sound like someone "
                        "typing on their phone while living their life. "
                        "When the moment is emotional, you make the reader FEEL it. Not by "
                        "saying 'this was so emotional' but by describing the tiny, specific "
                        "detail that carries all the weight. The way a child reaches for your "
                        "hand. The sound of a parent's laugh. The text that just said 'thinking "
                        "of you.' You are a writer who understands that the smallest moments "
                        "contain the deepest feelings."
                    )},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Drafting agent error: {e}")
            return idea.get("moment", idea.get("setup", "Thinking about things..."))

    # ------------------------------------------------------------------
    # AGENT 4: STYLE TRANSFER
    # ------------------------------------------------------------------

    async def _style_transfer_agent(self, draft: str, context: Dict[str, Any]) -> str:
        """Rewrite the draft in the user's EXACT writing style."""
        style = context.get("style_profile", {})
        samples = context.get("writing_samples", [])[:5]

        style_desc_parts = []
        if style.get("avg_post_length"):
            style_desc_parts.append(f"Average post length: ~{int(style['avg_post_length'])} words")
        if style.get("emoji_frequency"):
            ef = style["emoji_frequency"]
            if ef > 0.5:
                style_desc_parts.append("Uses emojis frequently")
            elif ef < 0.1:
                style_desc_parts.append("Rarely uses emojis")
        if style.get("lowercase_rate", 0) > 0.5:
            style_desc_parts.append("Often writes in all lowercase")
        if style.get("exclamation_rate", 0) > 0.3:
            style_desc_parts.append("Uses exclamation marks often")
        if style.get("common_phrases"):
            style_desc_parts.append(f"Common phrases: {', '.join(style['common_phrases'][:5])}")

        style_description = "\n".join(style_desc_parts) if style_desc_parts else "No detailed style data — keep it natural and conversational."

        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)

        prompt = f"""You are a STYLE TRANSFER agent. Your job is to rewrite this draft to EXACTLY match this person's writing style.

DRAFT:
"{draft}"

STYLE PROFILE:
{style_description}

THEIR ACTUAL POSTS (match this voice EXACTLY):
{samples_text or "No samples — keep it natural."}

RULES:
- Match their sentence structure, punctuation, capitalization, emoji usage
- If they write in short punchy sentences, do that
- If they use "..." or "—" or "!!", mirror that
- If they start posts with lowercase, do the same
- Don't add formality they don't use
- Don't remove personality they do have
- Keep the meaning of the draft, change the voice

Return ONLY the rewritten post. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You transfer writing style precisely. Output only the post."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Style transfer agent error: {e}")
            return draft

    # ------------------------------------------------------------------
    # AGENT 5: HUMAN TOUCH VERIFIER
    # ------------------------------------------------------------------

    async def _human_touch_verifier(self, post: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Score the post for authenticity. Flag robotic patterns."""
        samples = context.get("writing_samples", [])[:5]
        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)

        prompt = f"""You are a HUMAN TOUCH VERIFIER. Score this post for authenticity.

POST TO VERIFY:
"{post}"

REAL POSTS BY THIS PERSON:
{samples_text or "No reference samples."}

Score on these dimensions (0.0 to 1.0):
1. voice_match: Does it sound like the same person?
2. naturalness: Does it sound like a real person, not AI?
3. specificity: Is it specific or generic?
4. emotional_authenticity: Does the emotion feel real?
5. overall: Overall human-touch score

Flag any issues:
- "too_formal": Sounds too corporate/polished
- "generic": Could be written by anyone
- "ai_patterns": Has common AI writing patterns (e.g., "In today's world...", "As someone who...")
- "wrong_tone": Tone doesn't match their usual voice
- "too_long": Significantly longer than their usual posts
- "too_short": Significantly shorter than their usual posts

Return JSON:
{{"score": 0.0-1.0, "dimensions": {{"voice_match": 0.0, "naturalness": 0.0, "specificity": 0.0, "emotional_authenticity": 0.0}}, "issues": ["..."], "feedback": "specific improvement suggestion"}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You verify authenticity of AI-generated content."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Human touch verifier error: {e}")
            return {"score": 0.7, "issues": [], "feedback": ""}

    # ------------------------------------------------------------------
    # AGENT 6: REVISION
    # ------------------------------------------------------------------

    async def _revision_agent(
        self, post: str, issues: List[str], context: Dict[str, Any]
    ) -> str:
        """Fix specific issues flagged by the verifier."""
        samples = context.get("writing_samples", [])[:3]
        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)

        prompt = f"""You are a REVISION agent. Fix these specific issues with a social media post.

CURRENT POST:
"{post}"

ISSUES TO FIX:
{json.dumps(issues)}

REFERENCE POSTS (target voice):
{samples_text or "No references."}

Fix the issues while keeping the core message. Make it sound more human.
Return ONLY the revised post text. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You revise posts to be more human. Output only the post."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception as e:
            logger.error(f"Revision agent error: {e}")
            return post
