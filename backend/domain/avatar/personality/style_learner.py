"""
Style Learner
Analyzes a user's real posts and messages to build a comprehensive writing style profile.
Runs as a background task on new posts and periodically for aggregate analysis.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import re
import logging

logger = logging.getLogger(__name__)


# Emoji regex (simplified — catches most common emoji)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


class StyleLearner:
    """
    Extracts writing-style signals from a user's posts and builds
    an aggregate style profile stored in ``avatar_style_profiles``.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # ------------------------------------------------------------------
    # Per-post analysis (lightweight, no LLM)
    # ------------------------------------------------------------------

    def analyze_post_text(self, text: str) -> Dict[str, Any]:
        """Fast, deterministic extraction of style features from one post."""
        if not text:
            return {}

        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        emoji_matches = _EMOJI_RE.findall(text)
        emoji_count = sum(len(m) for m in emoji_matches)

        question_count = text.count("?")
        exclamation_count = text.count("!")
        ellipsis_count = text.count("...")

        # Common filler / hedge phrases
        hedge_phrases = ["i think", "maybe", "probably", "to be honest",
                         "honestly", "basically", "the thing is",
                         "i mean", "kind of", "sort of", "actually",
                         "to be fair", "in my opinion"]
        found_hedges = [h for h in hedge_phrases if h in text.lower()]

        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_sentence_length": len(words) / max(len(sentences), 1),
            "emoji_count": emoji_count,
            "question_count": question_count,
            "exclamation_count": exclamation_count,
            "ellipsis_count": ellipsis_count,
            "hedge_phrases_found": found_hedges,
            "starts_with_capital": text[0].isupper() if text else False,
            "all_lowercase": text == text.lower(),
            "has_hashtags": "#" in text,
            "hashtag_count": text.count("#"),
        }

    # ------------------------------------------------------------------
    # Aggregate style profile (from ALL posts)
    # ------------------------------------------------------------------

    async def build_aggregate_style_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Analyse up to 200 real posts and build an aggregate style profile.
        Store in ``avatar_style_profiles`` and invalidate personality prompt cache.
        """
        try:
            cursor = self.db.posts.find(
                {"user_id": user_id, "post_type": {"$in": ["real", None]}},
                {"_id": 0, "text": 1, "created_at": 1}
            ).sort("created_at", -1).limit(200)
            posts = await cursor.to_list(200)

            if not posts:
                return {}

            analyses = [self.analyze_post_text(p.get("text", "")) for p in posts if p.get("text")]
            if not analyses:
                return {}

            # Aggregate
            total = len(analyses)
            avg_word_count = sum(a.get("word_count", 0) for a in analyses) / total
            avg_sentence_len = sum(a.get("avg_sentence_length", 0) for a in analyses) / total
            emoji_per_post = sum(a.get("emoji_count", 0) for a in analyses) / total
            question_rate = sum(1 for a in analyses if a.get("question_count", 0) > 0) / total
            exclamation_rate = sum(1 for a in analyses if a.get("exclamation_count", 0) > 0) / total
            ellipsis_rate = sum(1 for a in analyses if a.get("ellipsis_count", 0) > 0) / total
            lowercase_rate = sum(1 for a in analyses if a.get("all_lowercase")) / total

            # Collect common phrases across all posts
            all_hedges: Dict[str, int] = {}
            for a in analyses:
                for h in a.get("hedge_phrases_found", []):
                    all_hedges[h] = all_hedges.get(h, 0) + 1
            common_phrases = sorted(all_hedges, key=all_hedges.get, reverse=True)[:10]

            # Tone estimation
            tone: Dict[str, float] = {}
            if exclamation_rate > 0.4:
                tone["enthusiastic"] = exclamation_rate
            if question_rate > 0.3:
                tone["inquisitive"] = question_rate
            if ellipsis_rate > 0.2:
                tone["contemplative"] = ellipsis_rate
            if lowercase_rate > 0.5:
                tone["casual"] = lowercase_rate
            if not tone:
                tone["balanced"] = 1.0

            # Pick representative writing samples (diverse lengths)
            post_texts = [p.get("text", "") for p in posts if p.get("text")]
            sorted_by_len = sorted(post_texts, key=len)
            samples = []
            if len(sorted_by_len) >= 5:
                indices = [0, len(sorted_by_len) // 4, len(sorted_by_len) // 2,
                           3 * len(sorted_by_len) // 4, -1]
                samples = [sorted_by_len[i] for i in indices]
            else:
                samples = sorted_by_len[:5]

            profile = {
                "user_id": user_id,
                "avg_post_length": round(avg_word_count, 1),
                "avg_sentence_length": round(avg_sentence_len, 1),
                "emoji_frequency": round(emoji_per_post, 2),
                "question_rate": round(question_rate, 2),
                "exclamation_rate": round(exclamation_rate, 2),
                "ellipsis_rate": round(ellipsis_rate, 2),
                "lowercase_rate": round(lowercase_rate, 2),
                "common_phrases": common_phrases,
                "tone_distribution": tone,
                "writing_samples": [s[:300] for s in samples],
                "total_posts_analyzed": total,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Persist
            await self.db.avatar_style_profiles.update_one(
                {"user_id": user_id}, {"$set": profile}, upsert=True
            )

            # Invalidate personality prompt cache so it regenerates with new style
            await self.db.avatar_personality_prompts.delete_one({"user_id": user_id})

            logger.info(f"Built style profile for {user_id}: {total} posts analyzed")
            return profile

        except Exception as e:
            logger.error(f"Error building style profile for {user_id}: {e}")
            return {}

    # ------------------------------------------------------------------
    # Incremental update (after a single new post)
    # ------------------------------------------------------------------

    async def on_new_post(self, user_id: str, post_text: str):
        """
        Called (as background task) after a new post is created.
        Does a lightweight incremental update and triggers full rebuild
        if enough new posts have accumulated.
        """
        try:
            # Check how many posts since last profile build
            profile = await self.db.avatar_style_profiles.find_one(
                {"user_id": user_id}, {"total_posts_analyzed": 1}
            )
            last_count = profile.get("total_posts_analyzed", 0) if profile else 0

            # Count current posts
            current_count = await self.db.posts.count_documents(
                {"user_id": user_id, "post_type": {"$in": ["real", None]}}
            )

            # Rebuild if 5+ new posts since last analysis, or no profile yet
            if current_count - last_count >= 5 or not profile:
                await self.build_aggregate_style_profile(user_id)

        except Exception as e:
            logger.error(f"Error in on_new_post style update: {e}")
