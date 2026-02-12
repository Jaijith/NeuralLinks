"""
Web Browsing Service
Provides real web search, news, and image search capabilities for avatars.
Uses DuckDuckGo as the search engine (no API key required).

Features:
- Text/web search
- News search
- Image search
- Personality-aware browsing (based on avatar interests from knowledge graph)
- TTL caching to avoid excessive requests
- Rate limiting
- Graceful fallback on errors
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class WebBrowsingService:
    """
    Web browsing service for avatar agents.
    Searches the real web for news, articles, and images based on avatar personality.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db
        # Cache: key -> (timestamp, results)
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = timedelta(hours=1)
        # Rate limiting: track last search time
        self._last_search_time = 0.0
        self._min_search_interval = 2.0  # seconds between searches

    def _get_ddgs(self):
        """Get a DuckDuckGo search instance."""
        from duckduckgo_search import DDGS
        return DDGS(timeout=15)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache:
            return False
        cached_time, _ = self._cache[cache_key]
        return (datetime.now(timezone.utc) - cached_time) < self._cache_ttl

    def _get_cached(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached results if valid."""
        if self._is_cache_valid(cache_key):
            _, results = self._cache[cache_key]
            return results
        return None

    def _set_cache(self, cache_key: str, results: List[Dict]):
        """Cache results with timestamp."""
        self._cache[cache_key] = (datetime.now(timezone.utc), results)

    async def _rate_limit(self):
        """Ensure minimum interval between searches."""
        now = time.time()
        elapsed = now - self._last_search_time
        if elapsed < self._min_search_interval:
            await asyncio.sleep(self._min_search_interval - elapsed)
        self._last_search_time = time.time()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous DuckDuckGo search in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ------------------------------------------------------------------
    # CORE SEARCH METHODS
    # ------------------------------------------------------------------

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        timelimit: Optional[str] = None,
        region: str = "wt-wt",
    ) -> List[Dict[str, Any]]:
        """
        Search the web for articles and pages.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            timelimit: Time limit (d=day, w=week, m=month, y=year)
            region: Region for results (wt-wt = no region)

        Returns:
            List of search results with title, href, body
        """
        cache_key = f"web_{query}_{max_results}_{timelimit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"Web search cache hit for: {query}")
            return cached

        try:
            await self._rate_limit()
            ddgs = self._get_ddgs()
            results = await self._run_in_executor(
                ddgs.text,
                query,
                region=region,
                safesearch="moderate",
                timelimit=timelimit,
                max_results=max_results,
            )

            # Normalize results
            normalized = []
            for r in (results or []):
                normalized.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "web_search",
                })

            self._set_cache(cache_key, normalized)
            logger.info(f"Web search returned {len(normalized)} results for: {query}")
            return normalized

        except Exception as e:
            logger.error(f"Web search error for '{query}': {e}")
            return []

    async def search_news(
        self,
        query: str,
        max_results: int = 5,
        timelimit: Optional[str] = "w",
        region: str = "wt-wt",
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles.

        Args:
            query: News search query
            max_results: Maximum results
            timelimit: Time limit (d=day, w=week, m=month)
            region: Region

        Returns:
            List of news results with title, url, snippet, date, source, image
        """
        cache_key = f"news_{query}_{max_results}_{timelimit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"News search cache hit for: {query}")
            return cached

        try:
            await self._rate_limit()
            ddgs = self._get_ddgs()
            results = await self._run_in_executor(
                ddgs.news,
                query,
                region=region,
                safesearch="moderate",
                timelimit=timelimit,
                max_results=max_results,
            )

            normalized = []
            for r in (results or []):
                normalized.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("body", ""),
                    "date": r.get("date", ""),
                    "source": r.get("source", ""),
                    "image": r.get("image", ""),
                    "type": "news",
                })

            self._set_cache(cache_key, normalized)
            logger.info(f"News search returned {len(normalized)} results for: {query}")
            return normalized

        except Exception as e:
            logger.error(f"News search error for '{query}': {e}")
            return []

    async def search_images(
        self,
        query: str,
        max_results: int = 5,
        size: Optional[str] = None,
        type_image: Optional[str] = "photo",
        layout: Optional[str] = None,
        license_image: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for images.

        Args:
            query: Image search query
            max_results: Maximum results
            size: Image size (Small, Medium, Large, Wallpaper)
            type_image: Type (photo, clipart, gif, transparent, line)
            layout: Layout (Square, Tall, Wide)
            license_image: License type

        Returns:
            List of image results with title, image_url, thumbnail, source_url, dimensions
        """
        cache_key = f"images_{query}_{max_results}_{type_image}_{size}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"Image search cache hit for: {query}")
            return cached

        try:
            await self._rate_limit()
            ddgs = self._get_ddgs()
            results = await self._run_in_executor(
                ddgs.images,
                query,
                region="wt-wt",
                safesearch="moderate",
                size=size,
                type_image=type_image,
                layout=layout,
                license_image=license_image,
                max_results=max_results,
            )

            normalized = []
            for r in (results or []):
                image_url = r.get("image", "")
                # Skip results without valid image URLs
                if not image_url or not image_url.startswith("http"):
                    continue
                normalized.append({
                    "title": r.get("title", ""),
                    "image_url": image_url,
                    "thumbnail": r.get("thumbnail", ""),
                    "source_url": r.get("url", ""),
                    "width": r.get("width", 0),
                    "height": r.get("height", 0),
                    "source": r.get("source", "image_search"),
                    "type": "image",
                })

            self._set_cache(cache_key, normalized)
            logger.info(f"Image search returned {len(normalized)} results for: {query}")
            return normalized

        except Exception as e:
            logger.error(f"Image search error for '{query}': {e}")
            return []

    # ------------------------------------------------------------------
    # PERSONALITY-AWARE BROWSING
    # ------------------------------------------------------------------

    async def browse_for_avatar(
        self,
        avatar_id: str,
        browse_type: str = "auto",
        custom_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Browse the web based on the avatar's personality, interests, and current state.

        Args:
            avatar_id: Avatar user ID
            browse_type: Type of browsing (auto, news, images, explore)
            custom_query: Optional custom search query

        Returns:
            Dict with browsing results organized by type
        """
        if self.db is None:
            return {"success": False, "error": "Database not available"}

        try:
            # Get avatar's interests and personality
            interests = await self._get_avatar_interests(avatar_id)
            mood = await self._get_avatar_mood(avatar_id)

            if not interests and not custom_query:
                return {
                    "success": False,
                    "error": "No interests found for avatar. Cannot generate search queries.",
                }

            # Generate search queries based on interests and mood
            queries = self._generate_search_queries(interests, mood, custom_query)

            # Determine what to browse
            if browse_type == "auto":
                browse_type = self._select_browse_type(mood)

            results = {
                "success": True,
                "browse_type": browse_type,
                "queries_used": queries,
                "articles": [],
                "news": [],
                "images": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if browse_type in ("auto", "news", "explore"):
                # Search for news on primary interest
                if queries:
                    news = await self.search_news(queries[0], max_results=5, timelimit="w")
                    results["news"] = news

            if browse_type in ("auto", "explore"):
                # Search for articles on another interest
                query = queries[1] if len(queries) > 1 else queries[0]
                articles = await self.search_web(query, max_results=5, timelimit="m")
                results["articles"] = articles

            if browse_type in ("auto", "images"):
                # Search for images based on interests
                img_query = queries[0] if queries else "aesthetic photography"
                images = await self.search_images(
                    img_query, max_results=8, type_image="photo"
                )
                results["images"] = images

            total = len(results["articles"]) + len(results["news"]) + len(results["images"])
            results["total_results"] = total
            logger.info(
                f"Avatar {avatar_id} browsed web: {total} results "
                f"({len(results['news'])} news, {len(results['articles'])} articles, "
                f"{len(results['images'])} images)"
            )

            return results

        except Exception as e:
            logger.error(f"Error browsing for avatar {avatar_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_news_for_interests(
        self,
        interests: List[str],
        max_per_interest: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get real news articles matching a list of interests.

        Args:
            interests: List of interest keywords
            max_per_interest: Max results per interest

        Returns:
            List of news articles
        """
        all_news = []
        seen_titles = set()

        for interest in interests[:3]:  # Limit to top 3 interests
            news = await self.search_news(
                f"{interest} latest",
                max_results=max_per_interest,
                timelimit="w",
            )
            for item in news:
                title = item.get("title", "")
                if title and title not in seen_titles:
                    item["interest"] = interest
                    all_news.append(item)
                    seen_titles.add(title)

        return all_news[:10]  # Cap at 10 total

    async def get_trending_topics_real(
        self,
        category: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        Get real trending topics/news by category.

        Args:
            category: Category (general, technology, entertainment, business, science)

        Returns:
            List of trending topics with titles and details
        """
        category_queries = {
            "technology": "technology news today",
            "entertainment": "entertainment news trending",
            "business": "business news trending",
            "science": "science discoveries news",
            "general": "trending news today",
        }

        query = category_queries.get(category, category_queries["general"])
        news = await self.search_news(query, max_results=5, timelimit="d")

        # Format as trending topics
        topics = []
        for item in news:
            topics.append({
                "title": item.get("title", ""),
                "category": category,
                "url": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "image": item.get("image", ""),
                "source": item.get("source", ""),
                "date": item.get("date", ""),
            })

        return topics

    async def find_image_for_topic(
        self,
        topic: str,
        style: str = "photo",
        count: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find images suitable for a social media post about a topic.

        Args:
            topic: The topic to find images for
            style: Image style preference (photo, aesthetic, artistic)
            count: Number of images to return

        Returns:
            List of image results with URLs
        """
        # Craft a search query that yields good social media images
        search_query = f"{topic} {style} high quality"

        images = await self.search_images(
            search_query,
            max_results=count * 2,  # Fetch extra for filtering
            type_image="photo",
            size="Medium",
        )

        # Filter for reasonable sizes and quality
        filtered = []
        for img in images:
            w = img.get("width", 0)
            h = img.get("height", 0)
            # Prefer images that are at least 400px wide
            if w >= 400 or (w == 0 and h == 0):
                filtered.append(img)
                if len(filtered) >= count:
                    break

        return filtered if filtered else images[:count]

    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------

    async def _get_avatar_interests(self, avatar_id: str) -> List[str]:
        """Get avatar's interests from the knowledge graph."""
        if self.db is None:
            return []

        try:
            cursor = self.db.graph_nodes.find(
                {"user_id": avatar_id, "node_type": "interest"},
                {"_id": 0, "label": 1, "strength": 1},
            ).sort("strength", -1).limit(15)
            nodes = await cursor.to_list(15)
            return [n.get("label", "") for n in nodes if n.get("label")]
        except Exception as e:
            logger.error(f"Error getting interests for {avatar_id}: {e}")
            return []

    async def _get_avatar_mood(self, avatar_id: str) -> str:
        """Get avatar's current mood from internal state."""
        if self.db is None:
            return "neutral"

        try:
            state = await self.db.avatar_internal_states.find_one(
                {"avatar_id": avatar_id},
                {"_id": 0, "mood": 1},
            )
            if state:
                return state.get("mood", "neutral")

            # Try from user document
            user = await self.db.users.find_one(
                {"id": avatar_id},
                {"_id": 0, "avatar_internal_state": 1},
            )
            if user:
                return user.get("avatar_internal_state", {}).get("mood", "neutral")

            return "neutral"
        except Exception as e:
            logger.error(f"Error getting mood for {avatar_id}: {e}")
            return "neutral"

    async def get_shareable_news_for_avatar(
        self,
        avatar_id: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get REAL, big, shareable news stories filtered by avatar interests.
        These are the kind of stories people actually share on social media —
        not generic news, but impactful/surprising/emotional stories.

        Returns news items with full metadata (title, url, snippet, source)
        ready to be passed as news_context to PostOrchestrator.

        Args:
            avatar_id: Avatar user ID
            max_results: Max news items to return

        Returns:
            List of shareable news items sorted by relevance/impact
        """
        if self.db is None:
            return []

        interests = await self._get_avatar_interests(avatar_id)
        if not interests:
            interests = ["technology", "science", "world"]

        all_news: List[Dict[str, Any]] = []
        seen_titles: set = set()

        # Strategy 1: Big news for each interest
        selected = interests[:6]
        random.shuffle(selected)
        for interest in selected[:3]:
            queries = [
                f"{interest} breaking news today",
                f"{interest} major development 2026",
                f"{interest} surprising discovery",
            ]
            query = random.choice(queries)
            try:
                news = await self.search_news(query, max_results=3, timelimit="w")
                for item in news:
                    title = item.get("title", "")
                    if title and title not in seen_titles:
                        item["interest"] = interest
                        item["shareability"] = "interest_news"
                        all_news.append(item)
                        seen_titles.add(title)
            except Exception as e:
                logger.warning(f"News fetch failed for '{query}': {e}")

        # Strategy 2: Rare/amazing facts
        fact_queries = [
            f"{random.choice(interests)} incredible fact",
            f"{random.choice(interests)} you won't believe",
            f"{random.choice(interests)} mind blowing discovery",
            "rare facts nobody knows about",
            "amazing discovery this week",
        ]
        try:
            fact_query = random.choice(fact_queries)
            facts = await self.search_web(fact_query, max_results=3, timelimit="m")
            for item in facts:
                title = item.get("title", "")
                if title and title not in seen_titles:
                    item["shareability"] = "rare_fact"
                    all_news.append(item)
                    seen_titles.add(title)
        except Exception as e:
            logger.warning(f"Fact search failed: {e}")

        # Strategy 3: Trending / viral stories
        try:
            trending = await self.search_news(
                "trending viral story today",
                max_results=3,
                timelimit="d",
            )
            for item in trending:
                title = item.get("title", "")
                if title and title not in seen_titles:
                    item["shareability"] = "trending"
                    all_news.append(item)
                    seen_titles.add(title)
        except Exception as e:
            logger.warning(f"Trending fetch failed: {e}")

        # Shuffle and limit — variety > exhaustiveness
        random.shuffle(all_news)
        return all_news[:max_results]

    def _generate_search_queries(
        self,
        interests: List[str],
        mood: str,
        custom_query: Optional[str] = None,
    ) -> List[str]:
        """
        Generate personality-aware search queries from interests and mood.
        Prioritises BIG news and impactful stories over generic searches.
        """
        queries = []

        if custom_query:
            queries.append(custom_query)

        if not interests:
            return queries or ["biggest news today", "trending stories today"]

        # Pick 2-3 interests for variety, weighted by position (top = stronger)
        selected = interests[:5]
        random.shuffle(selected)
        selected = selected[:3]

        # Mood-influenced query templates — biased towards BIG news
        mood_modifiers = {
            "curious": [
                "{interest} latest breakthrough",
                "{interest} new discovery this week",
            ],
            "creative": [
                "{interest} innovative breakthrough",
                "{interest} creative milestone",
            ],
            "bored": [
                "{interest} incredible facts most people don't know",
                "{interest} mind-blowing stories",
            ],
            "excited": [
                "{interest} breaking news today",
                "{interest} biggest news this week",
            ],
            "social": [
                "{interest} viral story today",
                "{interest} people are talking about",
            ],
            "contemplative": [
                "{interest} deep investigation",
                "{interest} surprising truth",
            ],
            "happy": [
                "{interest} uplifting news today",
                "{interest} good news this week",
            ],
            "neutral": [
                "{interest} biggest news today",
                "{interest} major development this week",
            ],
        }

        templates = mood_modifiers.get(mood, mood_modifiers["neutral"])

        for interest in selected:
            template = random.choice(templates)
            query = template.format(interest=interest)
            queries.append(query)

        return queries[:3]

    def _select_browse_type(self, mood: str) -> str:
        """Select browsing type based on avatar mood."""
        mood_to_browse = {
            "curious": "explore",
            "creative": "images",
            "bored": "news",
            "excited": "news",
            "social": "news",
            "contemplative": "explore",
            "happy": "images",
            "neutral": "auto",
        }
        return mood_to_browse.get(mood, "auto")
