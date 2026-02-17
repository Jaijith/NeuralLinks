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
        is_ai_agent: bool = False,
        agent_domain: str = "",
        agent_domain_label: str = "",
        cross_agent_recent_posts: Optional[List[str]] = None,
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
            is_ai_agent: Whether this is an AI agent (content curator mode)
            agent_domain: AI agent's domain code (e.g., "technology")
            agent_domain_label: AI agent's domain label (e.g., "Technology & AI")
            cross_agent_recent_posts: Recent posts from OTHER AI agents for dedup

        Returns:
            {"text": str, "quality_score": float, "metadata": dict}
        """
        try:
            # Load context once (shared by all agents)
            context = await self._load_context(user_id)

            # ============================================================
            # AI AGENT PATH: Two-liner curator posts
            # AI agents don't post about themselves. They curate interesting
            # news, facts, events, and discoveries from the web and share
            # them as punchy two-liner posts with images.
            # ============================================================
            if is_ai_agent and news_context and news_context.get("title"):
                own_recent = context.get("recent_avatar_posts", [])
                return await self._generate_agent_curator_post(
                    news=news_context,
                    agent_domain=agent_domain,
                    agent_domain_label=agent_domain_label,
                    cross_agent_recent_posts=cross_agent_recent_posts or [],
                    own_recent_posts=own_recent,
                )

            # ============================================================
            # FAST PATH: News/fact reaction post (for regular avatars)
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

            # --- Agent 7: IMAGE FINDER ---
            # Every post should have an image.  Extract the topic from the
            # ideation step and search for a relevant photo.
            image_url = await self._find_image_for_post(
                final_text, intent, idea, context
            )

            result = {
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
            if image_url:
                result["image_url"] = image_url

            return result

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

        CRITICAL: Every avatar MUST sound like their real user — different
        vocabulary, sentence structure, tone, and personality.  Never start
        with the same opener twice.
        """
        import random

        news_title = news.get("title", "")
        news_url = news.get("url", "")
        news_snippet = news.get("snippet", "")
        news_source = news.get("source", "")

        interests = context.get("interests", [])
        traits = context.get("traits", [])
        values = context.get("values", [])
        personality_prompt = context.get("personality_prompt", "")
        samples = context.get("writing_samples", [])[:6]
        samples_text = "\n---\n".join(f'"{s[:250]}"' for s in samples if s)
        style = context.get("style_profile", {})
        user_profile = context.get("user_profile", {})
        recent_avatar_posts = context.get("recent_avatar_posts", [])

        # Build a VOICE IDENTITY from all available data
        voice_parts = []
        name = user_profile.get("name", "")
        avatar_name = user_profile.get("avatar_name", "")
        if name:
            voice_parts.append(f"Name: {name}")
        if avatar_name and avatar_name != name:
            voice_parts.append(f"Known as: {avatar_name}")

        cp = user_profile.get("avatar_character_profile", {})
        if cp.get("archetype"):
            voice_parts.append(f"Archetype: {cp['archetype']}")

        # Build style fingerprint from quantified data
        style_notes = []
        if style.get("avg_post_length"):
            style_notes.append(f"Posts average ~{int(style['avg_post_length'])} words")
        ef = style.get("emoji_frequency", 0)
        if ef > 1.0:
            style_notes.append("Heavy emoji user (multiple per post)")
        elif ef > 0.3:
            style_notes.append("Moderate emoji user")
        elif ef < 0.1:
            style_notes.append("Rarely uses emojis — raw text only")
        if style.get("lowercase_rate", 0) > 0.5:
            style_notes.append("Often writes in all lowercase")
        if style.get("exclamation_rate", 0) > 0.5:
            style_notes.append("Loves exclamation marks!")
        elif style.get("exclamation_rate", 0) < 0.1:
            style_notes.append("Almost never uses exclamation marks")
        if style.get("question_rate", 0) > 0.3:
            style_notes.append("Asks a lot of questions in posts")
        if style.get("ellipsis_rate", 0) > 0.4:
            style_notes.append("Uses ... (ellipsis) frequently")
        if style.get("common_phrases"):
            style_notes.append(f"Signature phrases: {', '.join(style['common_phrases'][:5])}")
        style_fingerprint = "\n".join(style_notes) if style_notes else ""

        voice_identity = "\n".join(voice_parts)

        # Pick a reaction STRUCTURE randomly to force different post shapes
        structures = [
            ("opinion_first", "Start with your strong opinion. Then explain what happened. Link at end."),
            ("news_then_take", "State the news fact in one line. Then give your personal take. Link at end."),
            ("question_opener", "Open with a rhetorical question about the news. Answer it yourself. Link at end."),
            ("personal_tie", "Connect this news to something specific from YOUR life or interests first. Then mention the news. Link at end."),
            ("one_liner_punch", "One punchy sentence reaction. Then the news detail. Link at end."),
            ("storytelling", "Tell it like you're explaining to a friend — casual, with your personality. Link at end."),
        ]
        chosen_structure_name, chosen_structure_desc = random.choice(structures)

        # Pick reaction tone
        reaction_tones = [
            "genuine_shock", "happy", "thought_provoking", "impressed",
            "concerned", "inspired", "witty", "personal_connection",
            "skeptical", "passionate",
        ]
        chosen_tone = random.choice(reaction_tones)

        # Recent posts to NOT repeat
        recent_openers = [p[:40].lower() for p in recent_avatar_posts[:5] if p]

        prompt = f"""You are {name or avatar_name or 'a real person'} posting on social media about news you saw.

=== YOUR IDENTITY ===
{voice_identity}
{personality_prompt}

Personality: {', '.join(traits[:6]) if traits else 'unique individual'}
What matters to you: {', '.join(values[:5]) if values else 'being real'}
Your world: {', '.join(interests[:10]) if interests else 'life'}
{style_fingerprint}

=== HOW YOU WRITE (match this voice EXACTLY) ===
{samples_text if samples_text else "You write naturally, conversationally — like texting a friend."}

=== THE NEWS ===
{news_title}
{news_snippet}
Source: {news_source}
URL: {news_url}

=== POST STRUCTURE: {chosen_structure_name} ===
{chosen_structure_desc}

=== TONE: {chosen_tone} ===

=== RULES ===
1. You are {name or avatar_name or 'a specific person'}, NOT a brand account.
   Your reaction must show YOUR specific lens — as someone into {', '.join(interests[:3]) if interests else 'your thing'}.

2. ABSOLUTELY BANNED PHRASES (if you use ANY of these, the post is rejected):
   "how is nobody talking about this"
   "just read this"
   "just saw this"
   "hey everyone"
   "hey friends"
   "exciting news"
   "can't believe"
   "it's always inspiring"
   "what an amazing opportunity"
   "it's fascinating"
   "can't wait to see"
   "shining a light on"
   "check it out"
   "this is wild"
   "I'm shook"
   "lowkey obsessed"
   Do NOT use ANY of these or similar template phrases.

3. CONNECT the news to YOUR world. If you're into {interests[0] if interests else 'something specific'},
   relate it to that. The reader should think "only THIS person would say it this way."

4. URL goes at the end on its own line. No intro for it.

5. 30-80 words. Short. Like a text to a friend.

6. NO hashtags.

7. Your recent post openings (do NOT repeat):
{chr(10).join(f'   - "{o}"' for o in recent_openers[:5]) if recent_openers else '   (none yet)'}

ONLY the post text. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        f"You are writing as {name or avatar_name or 'a specific person'}. "
                        f"They are {', '.join(traits[:3]) if traits else 'a real individual'} "
                        f"whose life revolves around {', '.join(interests[:3]) if interests else 'specific passions'}. "
                        "Write like THEY would actually type — match their energy, vocabulary, and style. "
                        "If they're analytical, write analytically. If casual, be casual. If poetic, be poetic. "
                        "CRITICAL: Do NOT default to generic excited social media voice. "
                        "Do NOT use phrases like 'how is nobody talking about this', 'just read this', "
                        "'hey everyone', 'I'm shook', or 'lowkey obsessed' — those are cliche. "
                        "Instead, have a GENUINE personal reaction based on this person's worldview. "
                        "The post must include the news source URL at the end."
                    )},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.95,
            )
            draft = response.choices[0].message.content.strip().strip('"')

            # Ensure the URL is in the post
            if news_url and news_url not in draft:
                draft = draft.rstrip() + f"\n\n{news_url}"

            # SKIP style transfer for news reactions — it genericizes the voice.
            # The prompt already has all the voice cues baked in.
            styled = draft

            # Find an image for this news post
            image_url = await self._find_image_for_news(news_title, news_source)

            result = {
                "text": styled,
                "quality_score": 0.85,
                "metadata": {
                    "pipeline": "news_reaction",
                    "news_title": news_title,
                    "news_url": news_url,
                    "news_source": news_source,
                    "reaction_style": chosen_tone,
                    "post_structure": chosen_structure_name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            if image_url:
                result["image_url"] = image_url

            return result

        except Exception as e:
            logger.error(f"News reaction post error: {e}")
            fallback = f"{news_title}\n\n{news_url}" if news_url else news_title
            return {
                "text": fallback,
                "quality_score": 0.3,
                "metadata": {"error": str(e), "pipeline": "news_reaction_fallback"},
            }

    # ------------------------------------------------------------------
    # AI AGENT CURATOR POST (two-liner — real news/facts, no self-reference)
    # ------------------------------------------------------------------

    async def _generate_agent_curator_post(
        self,
        news: Dict[str, Any],
        agent_domain: str,
        agent_domain_label: str,
        cross_agent_recent_posts: List[str] = None,
        own_recent_posts: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a punchy two-liner curator post for AI agents.

        AI agents don't post about themselves — they curate interesting
        news, facts, events, and discoveries from the web and present them
        as sharp, attention-grabbing two-sentence posts with images.

        Each two-liner must be:
        - Exactly 2 sentences (hook + kicker)
        - Unique (different opener from own history AND all other agents)
        - Natural and authentic (like a well-read friend at dinner)
        - Not self-referential (no "I found", "I think", "check this out")
        - Factual but intriguing — let the facts do the talking
        """
        import random

        news_title = news.get("title", "")
        news_url = news.get("url", "")
        news_snippet = news.get("snippet", "")
        news_source = news.get("source", "")

        # ── Opener style variety system ──────────────────────────
        opener_styles = [
            (
                "fact_drop",
                "Start with a concrete fact or number from the news. "
                "Example: 'Scientists just figured out how to turn CO2 into jet fuel.'",
            ),
            (
                "question_hook",
                "Start with a short intriguing question that the second sentence answers or deepens. "
                "Example: 'What happens when you let AI design a bridge?'",
            ),
            (
                "scene_setter",
                "Paint a quick, vivid scene in one sentence. "
                "Example: 'In a tiny lab in Kyoto, a team just grew a full human ear from scratch.'",
            ),
            (
                "contrast",
                "Start with a surprising contrast or juxtaposition. "
                "Example: 'The world's most expensive coffee costs $1,200 a cup — and it's made from elephant dung.'",
            ),
            (
                "person_focus",
                "Start with a person doing something remarkable. "
                "Example: 'A 92-year-old grandmother just broke the Tokyo marathon record.'",
            ),
            (
                "number_lead",
                "Start with a striking number or statistic. "
                "Example: '40% of all food produced on Earth never gets eaten.'",
            ),
            (
                "time_anchor",
                "Start with a time reference that builds intrigue. "
                "Example: 'Three years ago nobody had heard of this town — now it's the world's top dark-sky destination.'",
            ),
            (
                "quiet_reveal",
                "State something matter-of-factly that slowly lands as extraordinary. "
                "Example: 'A librarian in rural Ohio has been secretly paying students' overdue lunch fees for 11 years.'",
            ),
        ]
        chosen_style_name, chosen_style_desc = random.choice(opener_styles)

        # ── Second-line (kicker) variety system ──────────────────
        kicker_styles = [
            "Add an unexpected twist, catch, or irony that reframes the first sentence.",
            "Add a vivid specific detail that makes the story feel real and concrete.",
            "Add context that reveals why this matters on a bigger scale.",
            "Hint at what this means for the future — make the reader think ahead.",
            "End with something that lands like a quiet punchline.",
            "Add the human element — who does this affect and how.",
        ]
        chosen_kicker = random.choice(kicker_styles)

        # ── Build dedup list from own + cross-agent recent posts ─
        recent_openers = []
        if own_recent_posts:
            for p in (own_recent_posts or [])[:10]:
                first_sentence = p.split(".")[0][:60].strip() if p else ""
                if first_sentence:
                    recent_openers.append(f"[own] {first_sentence}")
        if cross_agent_recent_posts:
            for p in (cross_agent_recent_posts or [])[:20]:
                first_sentence = p.split(".")[0][:60].strip() if p else ""
                if first_sentence:
                    recent_openers.append(f"[other agent] {first_sentence}")

        recent_openers_text = (
            "\n".join(f"  - {o}" for o in recent_openers[:20])
            if recent_openers
            else "  (none yet)"
        )

        # ── Prompt ───────────────────────────────────────────────
        prompt = f"""Write a two-sentence social media post sharing this news or fact.

=== THE CONTENT ===
Headline: {news_title}
Details: {news_snippet}
Source: {news_source}

=== YOUR DOMAIN ===
{agent_domain_label or 'General knowledge'} curator

=== FORMAT ===
EXACTLY 2 sentences. No more, no less.
Sentence 1 (the hook): {chosen_style_desc}
Sentence 2 (the kicker): {chosen_kicker}

=== ABSOLUTE RULES ===
1. NO self-reference: Never say "I found", "I read", "I think", "just came across",
   "just discovered", "check this out", "you should read", "you won't believe",
   "stumbled upon", "here's something", "sharing this"
2. NO generic reactions: Never say "this is amazing", "how cool", "mind-blowing",
   "game-changer", "incredible", "wow", "fascinating", "what a time to be alive",
   "this changes everything"
3. NO hashtags, NO emojis
4. Maximum ONE exclamation mark in the entire post — and only if it genuinely fits
5. NO filler: "actually", "basically", "literally", "honestly", "interestingly"
6. Do NOT include the URL — it will be added after your text automatically
7. Total: 15-35 words. Tight and punchy.
8. Sound like a sharp, well-read friend casually mentioning something over dinner —
   not a news anchor, not a bot, not a brand account
9. Be factual. Let the story speak for itself. No editorializing.
10. The two sentences must work as a unit — first hooks, second completes the thought.

=== DO NOT START LIKE ANY OF THESE RECENT POSTS ===
{recent_openers_text}

=== OUTPUT ===
ONLY the 2 sentences. Nothing else. No quotes around them."""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You write punchy two-sentence social media posts that share real news and facts. "
                            "You sound like a knowledgeable, interesting friend — never like an AI, a news bot, "
                            "or a brand account. You never reference yourself. You let the facts do the talking. "
                            "Every post you write has a different structure and opening from the last. "
                            "You are sharp, concise, and make people want to click the link."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.95,
                max_tokens=120,
            )
            two_liner = response.choices[0].message.content.strip().strip('"').strip("'")

            # Append the source URL on its own line
            if news_url and news_url not in two_liner:
                two_liner = two_liner.rstrip() + f"\n\n{news_url}"

            # Find an image for this news
            image_url = await self._find_image_for_news(news_title, news_source)

            return {
                "text": two_liner,
                "quality_score": 0.9,
                "metadata": {
                    "pipeline": "agent_curator_two_liner",
                    "news_title": news_title,
                    "news_url": news_url,
                    "news_source": news_source,
                    "opener_style": chosen_style_name,
                    "agent_domain": agent_domain,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                "image_url": image_url,
            }

        except Exception as e:
            logger.error(f"Agent curator post error: {e}")
            # Fallback: headline + URL
            fallback = news_title
            if news_url:
                fallback += f"\n\n{news_url}"
            return {
                "text": fallback,
                "quality_score": 0.3,
                "metadata": {"error": str(e), "pipeline": "agent_curator_fallback"},
            }

    # ------------------------------------------------------------------
    # IMAGE FINDER AGENTS
    # ------------------------------------------------------------------

    async def _generate_image_query(self, post_text: str, context: Dict[str, Any]) -> str:
        """
        Use the LLM to create a natural visual search query from the post.
        E.g. a post about missing family → 'family together warm sunset'
        E.g. a post about hiking trip → 'mountain trail sunrise nature'
        """
        try:
            interests = context.get("interests", [])[:5]
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You generate image search queries. Given a social media post, "
                        "output a short (3-6 word) photo search query that would find "
                        "a beautiful, authentic image matching the post's MOOD and SUBJECT. "
                        "Think like a photographer — describe the SCENE, not abstract concepts. "
                        "Output ONLY the search query, nothing else."
                    )},
                    {"role": "user", "content": (
                        f"Post: {post_text[:200]}\n"
                        f"Person's interests: {', '.join(interests)}\n\n"
                        "What image search query would find a beautiful photo "
                        "that matches this post's vibe? (3-6 words, visual/concrete)"
                    )}
                ],
                temperature=0.7,
                max_tokens=30,
            )
            query = response.choices[0].message.content.strip().strip('"').strip("'")
            if query and len(query) > 3:
                logger.info(f"LLM image query: '{query}'")
                return query
        except Exception as e:
            logger.warning(f"LLM image query generation failed: {e}")

        return ""

    async def _search_image_with_fallbacks(
        self,
        primary_query: str,
        fallback_queries: List[str],
    ) -> Optional[str]:
        """
        Search for an image with multiple fallback queries.
        Returns the first valid image URL found.
        """
        import random
        try:
            from services.web_browsing_service import WebBrowsingService
            web_service = WebBrowsingService(self.db)

            all_queries = [primary_query] + fallback_queries
            for query in all_queries:
                if not query:
                    continue
                try:
                    images = await web_service.search_images(
                        query, max_results=5, type_image="photo", size="Medium"
                    )
                    if images:
                        pick = random.choice(images[:3])
                        url = pick.get("image_url", "")
                        if url and url.startswith("http"):
                            logger.info(f"Image found for '{query}': {url[:80]}...")
                            return url
                except Exception as e:
                    logger.debug(f"Image search failed for '{query}': {e}")
                    continue

        except Exception as e:
            logger.warning(f"Image search with fallbacks failed: {e}")

        return None

    async def _find_image_for_post(
        self,
        post_text: str,
        intent: Dict[str, Any],
        idea: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Find a relevant, authentic image for a life-moment post.

        Strategy:
        1. Use LLM to generate a natural visual query from the post text
        2. Fallback to setup/moment description from ideation
        3. Fallback to interest + mood based query
        4. Last resort: random interest photography
        """
        import random

        # Strategy 1: LLM-generated visual query (best results)
        llm_query = await self._generate_image_query(post_text, context)

        # Strategy 2: scene description from ideation
        setup = idea.get("setup", "")
        moment = idea.get("moment", "")
        scene_query = ""
        if setup and moment:
            scene_query = f"{setup[:30]} {moment[:30]}"
        elif setup:
            scene_query = setup[:50]

        # Strategy 3: interest + emotional tone
        interests = context.get("interests", [])
        tone = idea.get("tone", "beautiful")
        interest_query = ""
        if interests:
            picked = random.choice(interests[:5])
            interest_query = f"{picked} {tone} photography"

        # Strategy 4: pure interest fallback
        generic_query = ""
        if interests:
            generic_query = f"{random.choice(interests[:8])} beautiful photo"

        return await self._search_image_with_fallbacks(
            llm_query,
            [scene_query, interest_query, generic_query],
        )

    async def _find_image_for_news(
        self,
        news_title: str,
        news_source: str,
    ) -> Optional[str]:
        """
        Find an image for a news reaction post.

        Strategy:
        1. Search with the news headline
        2. Fallback to keywords extracted from headline
        3. Fallback to news source + topic
        """
        # Primary: full headline
        primary = news_title[:60] if news_title else news_source

        # Fallback: first meaningful chunk of the headline
        words = news_title.split()[:5] if news_title else []
        fallback1 = " ".join(words) if words else ""

        # Fallback: source + subject
        fallback2 = f"{news_source} news" if news_source else ""

        return await self._search_image_with_fallbacks(
            primary,
            [fallback1, fallback2],
        )

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
            self._get_user_profile(user_id),
            return_exceptions=True,
        )

        style = results[0] if not isinstance(results[0], Exception) else {}
        posts = results[1] if not isinstance(results[1], Exception) else []
        personality = results[2] if not isinstance(results[2], Exception) else ""
        persona = results[3] if not isinstance(results[3], Exception) else {}
        recent_avatar = results[4] if not isinstance(results[4], Exception) else []
        user_profile = results[5] if not isinstance(results[5], Exception) else {}

        # Build writing samples: prefer real posts, fallback to filtered avatar posts
        real_samples = [p.get("text", "") for p in posts[:8] if p.get("text")]

        if len(real_samples) < 3:
            # Fallback: use avatar posts but filter out generic/template-y ones
            _poisoned = [
                "how is nobody", "just read this", "just saw this",
                "hey everyone", "hey friends", "okay this is",
                "wow just", "can't believe",
            ]
            for av_text in recent_avatar:
                if len(real_samples) >= 8:
                    break
                lower = av_text.lower()[:50]
                if not any(p in lower for p in _poisoned):
                    real_samples.append(av_text)

        # Build personality fallback from user profile if prompt is empty
        if not personality and user_profile:
            cp = user_profile.get("avatar_character_profile", {})
            parts = []
            if user_profile.get("name"):
                parts.append(f"Name: {user_profile['name']}")
            if user_profile.get("avatar_name"):
                parts.append(f"Goes by: {user_profile['avatar_name']}")
            if user_profile.get("bio"):
                parts.append(f"Bio: {user_profile['bio']}")
            if user_profile.get("job_title"):
                parts.append(f"Job: {user_profile['job_title']}")
            if user_profile.get("location"):
                parts.append(f"Location: {user_profile['location']}")
            if cp.get("personality_traits"):
                parts.append(f"Personality: {', '.join(cp['personality_traits'][:6])}")
            if cp.get("interests"):
                parts.append(f"Interests: {', '.join(cp['interests'][:8])}")
            cs = cp.get("communication_style")
            if cs and isinstance(cs, dict):
                parts.append(f"Communication style: {json.dumps(cs)}")
            elif cs and isinstance(cs, str):
                parts.append(f"Communication style: {cs}")
            if cp.get("archetype"):
                parts.append(f"Archetype: {cp['archetype']}")
            if parts:
                personality = "\n".join(parts)

        # Build temporal context
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

        # Fallback interests/traits from user profile if graph_nodes are empty
        interests = persona.get("interests", [])
        traits = persona.get("traits", [])
        values = persona.get("values", [])
        experiences = persona.get("experiences", [])

        if not interests and user_profile:
            cp = user_profile.get("avatar_character_profile", {})
            if cp.get("interests"):
                interests = cp["interests"]
        if not traits and user_profile:
            cp = user_profile.get("avatar_character_profile", {})
            if cp.get("personality_traits"):
                traits = cp["personality_traits"]

        # Last resort: extract interests from personality_prompt text
        if not interests and personality:
            import re
            m = re.search(r"(?:interests?|into|passions?)[:\s]+([^\n]+)", personality, re.I)
            if m:
                raw = m.group(1)
                interests = [x.strip() for x in raw.split(",") if x.strip()][:10]

        return {
            "style_profile": style or {},
            "recent_posts": posts,
            "personality_prompt": personality,
            "interests": interests,
            "traits": traits,
            "values": values,
            "experiences": experiences,
            "writing_samples": real_samples,
            "recent_avatar_posts": recent_avatar,
            "user_profile": user_profile,
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

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get the full user document for personality fallback."""
        try:
            doc = await self.db.users.find_one(
                {"id": user_id},
                {"_id": 0, "name": 1, "avatar_name": 1, "bio": 1,
                 "job_title": 1, "location": 1, "age": 1,
                 "avatar_character_profile": 1}
            )
            return doc or {}
        except Exception as e:
            logger.warning(f"Could not get user profile: {e}")
            return {}

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
