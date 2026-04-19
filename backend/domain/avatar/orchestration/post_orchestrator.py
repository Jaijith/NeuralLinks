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

from core.config import OPENAI_MODEL

logger = logging.getLogger(__name__)


class PostOrchestrator:
    """
    Multi-agent pipeline that generates posts indistinguishable from
    the real user's writing style.
    """

    def __init__(self, db: AsyncIOMotorDatabase, openai_client: Any):
        self.db = db
        self.openai = openai_client
        self._graph_rag = None

    @property
    def graph_rag(self):
        if self._graph_rag is None:
            from domain.graph.rag import GraphRAG
            self._graph_rag = GraphRAG(self.db)
        return self._graph_rag

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

            # --- Agent 6.5: FRIEND TAGGING (occasional) ---
            final_text = await self._maybe_tag_friend(
                final_text, intent, context
            )

            # --- Agent 7: IMAGE FINDER ---
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
        identity_narrative = context.get("identity_narrative", "")
        personality_prompt = context.get("personality_prompt", "")
        samples = context.get("writing_samples", [])[:6]
        samples_text = "\n---\n".join(f'"{s[:250]}"' for s in samples if s)
        style = context.get("style_profile", {})
        user_profile = context.get("user_profile", {})
        recent_avatar_posts = context.get("recent_avatar_posts", [])

        # Build a VOICE IDENTITY — prefer graph narrative, fallback to flat labels
        name = user_profile.get("name", "")
        avatar_name = user_profile.get("avatar_name", "")

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

=== WHO YOU ARE (identity graph — shows how your interests, experiences, and relationships connect) ===
{identity_narrative if identity_narrative else f"Personality: {', '.join(traits[:6]) if traits else 'unique individual'}" + chr(10) + f"What matters to you: {', '.join(values[:5]) if values else 'being real'}" + chr(10) + f"Your world: {', '.join(interests[:10]) if interests else 'life'}"}
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
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        f"You are writing as {name or avatar_name or 'a specific person'}. "
                        f"Their personality: {', '.join(traits[:3]) if traits else 'a real individual'}. "
                        f"Their world: {', '.join(interests[:5]) if interests else 'specific passions'}. "
                        "Write like THEY would actually type — match their energy, vocabulary, and style. "
                        "If they're analytical, write analytically. If casual, be casual. If poetic, be poetic. "
                        "CRITICAL: Do NOT default to generic excited social media voice. "
                        "Do NOT use phrases like 'how is nobody talking about this', 'just read this', "
                        "'hey everyone', 'I'm shook', or 'lowkey obsessed' — those are cliche. "
                        "Instead, have a GENUINE personal reaction based on this person's identity and worldview. "
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
            styled = draft

            # Occasionally tag a friend
            styled = await self._maybe_tag_friend(
                styled,
                {"interests_involved": interests[:3]},
                context,
            )

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
                model=OPENAI_MODEL,
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
                model=OPENAI_MODEL,
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

    async def _maybe_tag_friend(
        self,
        post_text: str,
        intent: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """
        ~25% of posts: append a natural friend tag like "your thoughts @FriendName?"
        Only tag human friends whose interests overlap with the post topic.
        """
        import random

        if random.random() > 0.25:
            return post_text

        friends = context.get("friends", [])
        human_friends = [f for f in friends if not f.get("is_ai_agent") and f.get("name")]
        if not human_friends:
            return post_text

        interests_involved = intent.get("interests_involved", [])
        post_lower = post_text.lower()

        # Score friends by interest overlap with the post
        scored = []
        for f in human_friends:
            friend_interests = f.get("interests", [])
            if isinstance(friend_interests, str):
                friend_interests = [x.strip() for x in friend_interests.split(",")]
            overlap = sum(
                1 for fi in friend_interests
                if fi.lower() in post_lower or fi.lower() in " ".join(interests_involved).lower()
            )
            if overlap > 0:
                scored.append((f, overlap))

        # If no interest overlap, pick a random friend sometimes
        if not scored:
            if random.random() < 0.3:
                chosen = random.choice(human_friends)
            else:
                return post_text
        else:
            scored.sort(key=lambda x: x[1], reverse=True)
            chosen = scored[0][0]

        name = chosen["name"]
        tag_styles = [
            f"\n\n@{name} thoughts?",
            f"\n\n@{name} you'd love this",
            f"\n\ncc @{name}",
            f"\n\n@{name} this reminded me of you",
            f"\n\nwhat do you think @{name}?",
            f"\n\n@{name} 👀",
        ]
        return post_text + random.choice(tag_styles)

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

        # Parallel fetch — includes friends/connections for relationship accuracy
        results = await asyncio.gather(
            self._get_style_profile(user_id),
            self._get_recent_posts(user_id, limit=15),
            self._get_personality_prompt(user_id),
            self._get_full_personality(user_id),
            self._get_recent_avatar_posts(user_id),
            self._get_user_profile(user_id),
            self._get_friends_with_interests(user_id),
            self._get_connections(user_id),
            return_exceptions=True,
        )

        style = results[0] if not isinstance(results[0], Exception) else {}
        posts = results[1] if not isinstance(results[1], Exception) else []
        personality = results[2] if not isinstance(results[2], Exception) else ""
        persona = results[3] if not isinstance(results[3], Exception) else {}
        recent_avatar = results[4] if not isinstance(results[4], Exception) else []
        user_profile = results[5] if not isinstance(results[5], Exception) else {}
        friends = results[6] if not isinstance(results[6], Exception) else []
        connections = results[7] if not isinstance(results[7], Exception) else []

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
            "time_vibe": time_vibe,
            "day_name": day_name,
            "is_weekend": is_weekend,
            "hour": hour,
            "friends": friends,
            "connections": connections,
            "identity_narrative": persona.get("identity_narrative", ""),
        }

    async def _get_style_profile(self, user_id: str) -> Dict[str, Any]:
        doc = await self.db.avatar_style_profiles.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        return doc or {}

    @staticmethod
    def _build_strict_style_rules(style: Dict[str, Any], samples: List[str]) -> str:
        """
        Build hard style constraints from quantified data.
        These are NON-NEGOTIABLE rules the LLM must follow.
        """
        rules = []
        avg_len = style.get("avg_post_length")
        if avg_len:
            avg = int(avg_len)
            lo = max(8, int(avg * 0.5))
            hi = int(avg * 2.0)
            rules.append(f"WORD COUNT: {lo}–{hi} words (average is {avg}). Posts longer than {hi} words will be REJECTED.")
        else:
            rules.append("WORD COUNT: 30–100 words.")

        ef = style.get("emoji_frequency", 0)
        if ef > 1.0:
            rules.append("EMOJIS: Use emojis freely (multiple per post). This person loves emojis.")
        elif ef > 0.3:
            rules.append("EMOJIS: Use 1–2 emojis if they fit naturally.")
        elif ef > 0:
            rules.append("EMOJIS: Rarely use emojis — only if absolutely natural.")
        else:
            rules.append("EMOJIS: NEVER use emojis. This person does not use them.")

        lr = style.get("lowercase_rate", 0)
        if lr > 0.6:
            rules.append("CAPITALIZATION: Write in all lowercase — no capital letters.")
        elif lr > 0.3:
            rules.append("CAPITALIZATION: Mix of lowercase and normal. Don't over-capitalize.")

        er = style.get("exclamation_rate", 0)
        if er > 0.5:
            rules.append("EXCLAMATIONS: Use !! freely — this person is expressive.")
        elif er < 0.1:
            rules.append("EXCLAMATIONS: Almost never use ! — this person is understated.")

        elr = style.get("ellipsis_rate", 0)
        if elr > 0.3:
            rules.append("ELLIPSIS: Use ... frequently — it's a signature pattern.")

        qr = style.get("question_rate", 0)
        if qr > 0.3:
            rules.append("QUESTIONS: Often asks questions in posts.")
        elif qr < 0.1:
            rules.append("QUESTIONS: Rarely asks questions — makes statements instead.")

        cp = style.get("common_phrases", [])
        if cp:
            rules.append(f"SIGNATURE PHRASES: Try to use: {', '.join(cp[:5])}")

        avg_sent = style.get("avg_sentence_length")
        if avg_sent and avg_sent < 10:
            rules.append(f"SENTENCES: Keep sentences SHORT (~{int(avg_sent)} words). Punchy fragments are fine.")
        elif avg_sent and avg_sent > 20:
            rules.append(f"SENTENCES: Longer, flowing sentences (~{int(avg_sent)} words).")

        if samples:
            sample_lens = [len(s.split()) for s in samples if s]
            if sample_lens:
                actual_avg = sum(sample_lens) / len(sample_lens)
                rules.append(f"REFERENCE: Their actual posts average {int(actual_avg)} words.")

        return "\n".join(f"• {r}" for r in rules)

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

    async def _get_full_personality(self, user_id: str) -> Dict[str, Any]:
        """
        Get the FULL personality from the identity graph.

        Uses GraphRAG for graph-traversal-based retrieval instead of
        flat DB queries. Returns both label lists (for programmatic use)
        and the identity narrative (for LLM prompts).
        """
        import random

        ctx = await self.graph_rag.get_user_context(user_id, max_nodes=30)

        def _extract_shuffled(key: str, limit: int) -> List[str]:
            labels = [i.get("label", "") for i in ctx.get(key, [])[:limit] if i.get("label")]
            random.shuffle(labels)
            return labels

        identity_narrative = await self.graph_rag.get_identity_context(
            user_id, action_type="post_generation", max_tokens=1500,
        )

        return {
            "interests": _extract_shuffled("interests", 30),
            "traits": _extract_shuffled("traits", 10),
            "values": _extract_shuffled("values", 10),
            "experiences": _extract_shuffled("experiences", 10),
            "connections": _extract_shuffled("connections", 10),
            "identity_narrative": identity_narrative,
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

    async def _get_friends_with_interests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get the user's accepted friends with their names and interests."""
        try:
            from services.friend_service import FriendService
            fs = FriendService(self.db)
            friends = await fs.get_friends(user_id)
            return [
                {
                    "id": f.get("id"),
                    "name": f.get("avatar_name") or f.get("name", ""),
                    "interests": f.get("avatar_interests") or f.get("interests", []),
                    "is_bot": f.get("is_bot", False),
                    "is_ai_agent": f.get("is_ai_agent", False),
                    "bio": f.get("avatar_bio") or f.get("bio", ""),
                }
                for f in friends
            ]
        except Exception as e:
            logger.warning(f"Could not get friends: {e}")
            return []

    async def _get_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get personal connections (family, colleagues, etc.) from user document."""
        try:
            user = await self.db.users.find_one({"id": user_id}, {"connections": 1})
            return user.get("connections", []) if user else []
        except Exception as e:
            logger.warning(f"Could not get connections: {e}")
            return []

    # ------------------------------------------------------------------
    # AGENT 1: LIFE MOMENT (replaces the old "intent" agent)
    # ------------------------------------------------------------------

    async def _intent_agent(
        self, trigger: str, topic_hint: str, mood: str, energy: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate a LIFE MOMENT grounded in the person's REAL relationships,
        connections, and memory.  Never fabricate people or facts that don't
        exist in the data.
        """
        import random

        interests = context.get("interests", [])
        traits = context.get("traits", [])
        values = context.get("values", [])
        time_vibe = context.get("time_vibe", "")
        day_name = context.get("day_name", "")
        is_weekend = context.get("is_weekend", False)
        friends = context.get("friends", [])
        connections = context.get("connections", [])
        identity_narrative = context.get("identity_narrative", "")

        featured_interests = random.sample(interests, min(3, len(interests))) if interests else ["life"]

        # Build the REAL relationships section from connections
        real_people_lines = []
        family = [c for c in connections if c.get("relationship", "").lower() in (
            "spouse", "wife", "husband", "partner", "son", "daughter", "child",
            "mother", "father", "parent", "brother", "sister", "sibling",
        )]
        if family:
            real_people_lines.append("Family: " + ", ".join(
                f"{c.get('name', 'someone')} ({c.get('relationship', '')})" for c in family
            ))

        human_friends = [f for f in friends if not f.get("is_ai_agent")]
        if human_friends:
            sample_friends = random.sample(human_friends, min(5, len(human_friends)))
            real_people_lines.append("Friends on the platform: " + ", ".join(
                f.get("name", "") for f in sample_friends if f.get("name")
            ))

        colleagues = [c for c in connections if c.get("relationship", "").lower() in (
            "colleague", "coworker", "boss", "manager", "mentor", "mentee",
        )]
        if colleagues:
            real_people_lines.append("Work: " + ", ".join(
                f"{c.get('name', '')} ({c.get('relationship', '')})" for c in colleagues
            ))

        relationships_text = "\n".join(real_people_lines) if real_people_lines else "No family or personal connections on record — do NOT invent any."
        has_children = any(c.get("relationship", "").lower() in ("son", "daughter", "child") for c in connections)
        has_partner = any(c.get("relationship", "").lower() in ("spouse", "wife", "husband", "partner") for c in connections)

        prompt = f"""You are the LIFE MOMENT agent. Your job is to imagine a specific, realistic
moment in this person's day that would make them pick up their phone and share something.

=== WHO THIS PERSON IS (identity graph — shows how their interests, experiences, traits, and relationships connect) ===
{identity_narrative if identity_narrative else f"Interests: {', '.join(interests[:12])}" + chr(10) + f"Personality: {', '.join(traits) if traits else 'authentic, real'}" + chr(10) + f"Values: {', '.join(values) if values else 'genuine connections'}"}

Current mood: {mood} | Energy: {energy:.1f}/1.0
External trigger: {trigger or 'spontaneous — just felt like sharing'}
Topic direction: {topic_hint or 'open — whatever feels natural'}

=== REAL RELATIONSHIPS (use ONLY these — DO NOT invent people) ===
{relationships_text}
{"Has children: YES — you may reference child-related moments using the names above." if has_children else "Has children: NO — NEVER mention sons, daughters, or children."}
{"Has a partner: YES — you may reference partner moments." if has_partner else "Has a partner: NOT ON RECORD — do not reference a spouse/partner."}

=== WHEN THIS IS HAPPENING ===
It's {day_name}, {time_vibe}
{"Weekend vibes — more relaxed, adventurous, or lazy." if is_weekend else "Weekday — work/routine context."}

=== LIFE MOMENT TYPES (pick the one that fits naturally) ===
- "just_experienced": Something just happened (finished a run, saw something, ate something, built something)
- "sudden_thought": A random realization, shower thought, or connection between two ideas
- "reaction": Responding to something seen/read/heard (news, article, friend's story, weather)
- "nostalgia": A memory triggered by a song, smell, place, or photo
- "small_win": A personal achievement, no matter how minor
- "observation": Noticed something interesting about people, the world, daily life
- "question": Genuinely curious about something, asking the void
- "sharing_a_find": Discovered a cool thing (book, place, tool, song, recipe, fact)
- "mood_capture": Just wants to express how they feel right now
- "cross_connection": Realized two different interests connect in a surprising way
- "mundane_relatable": An everyday thing everyone experiences but rarely talks about
- "continuation": Following up on something from their life naturally
- "family_moment": ONLY if the person actually has family listed above
- "gratitude_wave": Unexpected gratitude for a specific person or moment
- "vulnerability": Being honest about something hard — in a raw but non-performative way
- "bittersweet": Something beautiful and sad at the same time
- "friend_shoutout": Tagging or referencing a real friend from the list above

=== INTERESTS TO POTENTIALLY WEAVE IN (not mandatory) ===
{', '.join(featured_interests)}

=== HARD RULES ===
1. ONLY reference people who appear in the REAL RELATIONSHIPS section above.
2. If there are no children listed, NEVER mention sons/daughters/kids.
3. If there is no partner listed, NEVER mention a spouse/wife/husband/partner.
4. When in doubt, stick to personal experiences, observations, or interests.
5. Be SPECIFIC — not "thinking about hiking" but "got to the trailhead at 6am, parking lot empty, just me and the fog."
6. Keep the life moment SIMPLE and BRIEF. This person's posts average ~{int(context.get('style_profile', {}).get('avg_post_length', 40))} words — so the moment should be a small, punchy observation, not an elaborate story.

Return JSON:
{{
  "moment_type": "which type from the list above",
  "life_moment": "1-2 sentence description of what just happened / what triggered this post — keep it SMALL and specific",
  "emotional_state": "what they're feeling right now",
  "interests_involved": ["which interests naturally connect to this moment"],
  "post_format": "story|observation|question|reaction|thought|rant|gratitude|humor",
  "people_referenced": ["names of real people mentioned, if any"],
  "target_word_count": {int(context.get('style_profile', {}).get('avg_post_length', 40))}
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "You simulate realistic life moments for a social media avatar. "
                        "Think like a real person living their actual life — specific, "
                        "messy, human. Not polished, not generic. "
                        "CRITICAL: You must ONLY reference real people listed in the "
                        "REAL RELATIONSHIPS section. Never invent family members, children, "
                        "or partners that don't exist. If no family is listed, the person "
                        "is single/has no kids — focus on friends, personal experiences, "
                        "and interests instead."
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

        avg_len = int(context.get("style_profile", {}).get("avg_post_length", 40))
        length_guide = "short (1-2 sentences)" if avg_len < 25 else ("medium (2-4 sentences)" if avg_len < 60 else "long (4+ sentences)")

        prompt = f"""You are the IDEATION agent. A life moment just happened. Shape it into a post idea.

=== THE LIFE MOMENT ===
{json.dumps(intent, indent=2)}

=== RECENT POSTS (DO NOT repeat similar content/topics) ===
{json.dumps(recent_texts) if recent_texts else 'No recent posts — fresh start.'}

=== THIS PERSON'S POST LENGTH: ~{avg_len} words → target: {length_guide} ===

=== NARRATIVE STRUCTURES (pick one that fits the target length) ===
1. "Stream of consciousness": Raw, unfiltered thought. Best for short posts.
   Example: "3 cups of coffee deep and somehow this code is writing itself today"
2. "Contrast/Surprise": Set up an expectation → subvert it
   Example: "Thought I'd hate the early morning class → now it's the best part of my week"
3. "The small detail": One hyper-specific detail that carries everything
   Example: "She held my hand crossing the street. Hasn't done that in months. Just held on."
4. "Observation → Insight": Notice something → connect it
   Example: "barista remembered my order.. tiny things that make you feel like you belong"
5. "Micro-story": Tiny complete story with beginning, middle, end
   Example: "Found an old journal from 2019. Read the goals. Done most of them without noticing."
6. "Question hook": Relatable question → your take
   Example: "anyone else get more creative at 2am?"
7. "Mood capture": Just express the vibe. No story needed.
   Example: "tired...."

Shape the life moment into a post idea that fits in ~{avg_len} words:

Return JSON:
{{
  "narrative_structure": "which structure from above",
  "setup": "the opening — 1 sentence max",
  "moment": "the core — what happened (keep it brief)",
  "landing": "the ending beat — or empty string if the moment speaks for itself",
  "tone": "funny|warm|thoughtful|excited|vulnerable|sarcastic|chill|energetic",
  "suggested_length": "{length_guide}"
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
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
        style = context.get("style_profile", {})
        strict_style = self._build_strict_style_rules(style, samples)

        prompt = f"""You are a DRAFTING agent. Write a social media post that reads like a real person
sharing a moment from their life.

=== THE STORY TO TELL ===
Structure: {idea.get('narrative_structure', 'micro-story')}
Setup: {idea.get('setup', '')}
Core moment: {idea.get('moment', '')}
Landing: {idea.get('landing', '')}
Tone: {idea.get('tone', 'authentic')}

Current vibe: {mood}, Energy: {energy:.1f} | {day_name}, {time_vibe}

=== NON-NEGOTIABLE STYLE RULES (violating these = post rejected) ===
{strict_style}

=== WRITING SAMPLES from this person (match their voice EXACTLY) ===
{samples_text or "No samples — write casually and naturally."}

=== RULES FOR AUTHENTIC POSTS ===
- Write in FIRST PERSON as if you ARE this person
- Match the LENGTH and ENERGY of their samples — if they write 15-word posts, you write 15-word posts.
- IMPERFECT is human — run-on sentences, sentence fragments, tangents are okay
- NO hashtags, NO motivational poster language, NO "As someone who..."
- NO listicles, NO "Here's why...", NO "In today's world..."
- NO lesson at the end. NO "and that's what life is about." Just the moment and stop.
- The post should feel like it was typed on a phone, not composed in a word processor
- CRITICAL: Only reference people/family mentioned in the story above. Do NOT add new people.

Return ONLY the post text. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "You write social media posts that are indistinguishable from real "
                        "human posts. You write the way people actually talk — messy, specific, "
                        "full of personality. You NEVER sound like AI. You sound like someone "
                        "typing on their phone while living their life. "
                        "CRITICAL: Match the WORD COUNT and STYLE RULES exactly. If the rules "
                        "say 15-40 words, your post MUST be 15-40 words. If they say no emojis, "
                        "use zero emojis. Length and style violations are automatic failures. "
                        "Never wrap up with a lesson or moral. Just the moment. Stop."
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
        """Rewrite the draft in the user's EXACT writing style — ruthlessly enforced."""
        style = context.get("style_profile", {})
        samples = context.get("writing_samples", [])[:5]
        strict_style = self._build_strict_style_rules(style, samples)

        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)

        avg_len = int(style.get("avg_post_length", 40))
        word_limit = int(avg_len * 2.0)
        draft_words = len(draft.split())

        prompt = f"""You are a STYLE TRANSFER agent. Your ONLY job: rewrite this draft to EXACTLY
match this person's writing style. Same meaning, completely different voice.

DRAFT ({draft_words} words):
"{draft}"

=== NON-NEGOTIABLE STYLE RULES ===
{strict_style}

=== THEIR ACTUAL POSTS (your output must look like these) ===
{samples_text or "No samples available."}

=== WHAT YOU MUST DO ===
1. CUT the post to fit the word count above. If the draft is {draft_words} words but their average is {avg_len}, you MUST cut it down. Remove filler, merge sentences, drop unnecessary detail.
2. Match their punctuation EXACTLY — if they use ".." or "....", you use ".." or "....". If they use !!, you use !!
3. Match their capitalization — if they write lowercase, you write lowercase
4. Match their emoji usage — if emoji_frequency is 0, REMOVE ALL EMOJIS
5. Match their sentence length — short fragments if they write short, flowing if they write long
6. NO lessons, NO wrapping up with a moral, NO "and that's what it's all about"
7. The output must read like THEIR ACTUAL POSTS above, not like a polished essay

Return ONLY the rewritten post. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
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
        """Score the post for authenticity — calibrated against real style data."""
        samples = context.get("writing_samples", [])[:5]
        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)
        style = context.get("style_profile", {})
        strict_style = self._build_strict_style_rules(style, samples)
        post_word_count = len(post.split())

        prompt = f"""You are a HUMAN TOUCH VERIFIER. Score this post for authenticity against REAL data.

POST TO VERIFY ({post_word_count} words):
"{post}"

REAL POSTS BY THIS PERSON:
{samples_text or "No reference samples."}

THEIR MEASURED STYLE:
{strict_style}

Score on these dimensions (0.0 to 1.0):
1. voice_match: Does it sound like the SAME PERSON who wrote the samples above? Match vocabulary, sentence length, punctuation, capitalization.
2. naturalness: Does it sound like a real person, not AI?
3. specificity: Is it specific or generic?
4. emotional_authenticity: Does the emotion feel real, not performed?
5. length_match: Is the word count close to their average? (post={post_word_count}w, avg={int(style.get('avg_post_length', 40))}w)
6. overall: Overall human-touch score

Flag any issues:
- "too_formal": Sounds too corporate/polished
- "generic": Could be written by anyone
- "ai_patterns": Has common AI writing patterns
- "wrong_tone": Tone doesn't match their usual voice
- "too_long": Post is {post_word_count} words, average is {int(style.get('avg_post_length', 40))} — WAY too long
- "too_short": Significantly shorter than their usual posts
- "wrong_emoji": Uses emojis when they don't, or vice versa
- "lesson_ending": Post ends with a moral/lesson — real people don't do this

Return JSON:
{{"score": 0.0-1.0, "dimensions": {{"voice_match": 0.0, "naturalness": 0.0, "specificity": 0.0, "emotional_authenticity": 0.0, "length_match": 0.0}}, "issues": ["..."], "feedback": "specific improvement suggestion"}}"""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
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
        """Fix specific issues flagged by the verifier — with strict style enforcement."""
        samples = context.get("writing_samples", [])[:5]
        samples_text = "\n---\n".join(f'"{s[:200]}"' for s in samples if s)
        style = context.get("style_profile", {})
        strict_style = self._build_strict_style_rules(style, samples)

        prompt = f"""You are a REVISION agent. The post below failed voice-matching checks.
Your job: REWRITE it to sound like this specific person wrote it.

CURRENT POST:
"{post}"

ISSUES FLAGGED:
{json.dumps(issues)}

=== NON-NEGOTIABLE STYLE RULES ===
{strict_style}

=== THIS PERSON'S ACTUAL POSTS (your output MUST sound like these) ===
{samples_text or "No references."}

=== WHAT TO DO ===
- Keep the core MOMENT or IDEA from the post
- Completely rewrite the VOICE to match the samples above
- If the post is too long, CUT IT DOWN to fit their word count
- If it has emojis and they don't use them, REMOVE THEM
- If it sounds like an essay, make it sound like a text message
- NO lessons, NO "and that's what matters", NO inspirational endings

Return ONLY the revised post text. Nothing else."""

        try:
            response = await self.openai.chat.completions.create(
                model=OPENAI_MODEL,
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
