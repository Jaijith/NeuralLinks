"""
Content Awareness Service
Fetches current events, news, and trending topics for avatars to post about.

NOW POWERED BY REAL WEB SEARCH (DuckDuckGo) with fallback to curated content.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging
import random

logger = logging.getLogger(__name__)


class ContentAwarenessService:
    """Fetches real-world content for avatars to be aware of"""

    def __init__(self):
        self.news_cache = {}
        self.cache_duration = timedelta(hours=1)
        self.last_fetch = {}
        # Initialize web browsing service (lazy)
        self._web_browsing_service = None

    def _get_web_service(self):
        """Lazy-load the web browsing service."""
        if self._web_browsing_service is None:
            try:
                from services.web_browsing_service import WebBrowsingService
                self._web_browsing_service = WebBrowsingService()
            except Exception as e:
                logger.warning(f"Could not initialize WebBrowsingService: {e}")
        return self._web_browsing_service

    async def get_trending_topics(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Get trending topics by category.
        Uses real web search with fallback to curated content.

        Args:
            category: Category of content (technology, entertainment, general, etc.)

        Returns:
            List of trending topics with headlines and summaries
        """
        # Check cache
        cache_key = f"trending_{category}"
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key, [])

        topics = []

        # Try real web search first
        web_service = self._get_web_service()
        if web_service:
            try:
                real_topics = await web_service.get_trending_topics_real(category)
                if real_topics:
                    topics = real_topics
                    logger.info(f"Got {len(topics)} real trending topics for '{category}'")
            except Exception as e:
                logger.warning(f"Real trending topics failed, falling back to curated: {e}")

        # Fallback to curated if web search failed or returned nothing
        if not topics:
            topics = await self._get_curated_topics(category)
            logger.info(f"Using {len(topics)} curated topics for '{category}'")

        # Cache results
        self.news_cache[cache_key] = topics
        self.last_fetch[cache_key] = datetime.now(timezone.utc)

        return topics

    async def get_news_for_interests(self, interests: List[str]) -> List[Dict[str, Any]]:
        """
        Get news articles matching avatar's interests.
        Uses real web search with fallback to curated content.

        Args:
            interests: List of avatar's interests

        Returns:
            List of relevant news items
        """
        if not interests:
            return []

        # Check cache
        cache_key = f"interests_{','.join(sorted(interests[:3]))}"
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key, [])

        news_items = []

        # Try real web search first
        web_service = self._get_web_service()
        if web_service:
            try:
                real_news = await web_service.get_news_for_interests(interests)
                if real_news:
                    news_items = real_news
                    logger.info(f"Got {len(news_items)} real news items for interests")
            except Exception as e:
                logger.warning(f"Real interest news failed, falling back to curated: {e}")

        # Fallback to curated if web search failed
        if not news_items:
            for interest in interests[:3]:
                curated = await self._get_news_by_interest(interest)
                news_items.extend(curated)

        # Remove duplicates and limit
        unique_news = []
        seen_titles = set()
        for item in news_items:
            title = item.get("title", "")
            if title and title not in seen_titles:
                unique_news.append(item)
                seen_titles.add(title)

        # Cache results
        result = unique_news[:5]
        self.news_cache[cache_key] = result
        self.last_fetch[cache_key] = datetime.now(timezone.utc)

        return result

    async def get_viral_content(self) -> List[Dict[str, Any]]:
        """
        Get viral/trending social content.
        Uses real web search with fallback to curated content.

        Returns:
            List of viral content items
        """
        cache_key = "viral_content"
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key, [])

        viral = []

        # Try real web search first
        web_service = self._get_web_service()
        if web_service:
            try:
                results = await web_service.search_news(
                    "viral trending social media today",
                    max_results=5,
                    timelimit="d",
                )
                if results:
                    viral = [
                        {
                            "title": r.get("title", ""),
                            "category": "viral",
                            "vibe": "trending",
                            "url": r.get("url", ""),
                            "snippet": r.get("snippet", ""),
                        }
                        for r in results
                    ]
            except Exception as e:
                logger.warning(f"Real viral content failed: {e}")

        # Fallback to curated
        if not viral:
            viral = [
                {
                    "title": "AI models now creating memes faster than humans",
                    "category": "technology",
                    "vibe": "funny",
                },
                {
                    "title": "New productivity hack: actually turning off notifications",
                    "category": "lifestyle",
                    "vibe": "relatable",
                },
                {
                    "title": "Developers discover bug that's been there since 1999",
                    "category": "technology",
                    "vibe": "amusing",
                },
            ]

        self.news_cache[cache_key] = viral
        self.last_fetch[cache_key] = datetime.now(timezone.utc)

        return viral

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.last_fetch:
            return False

        age = datetime.now(timezone.utc) - self.last_fetch[cache_key]
        return age < self.cache_duration

    async def _get_curated_topics(self, category: str) -> List[Dict[str, Any]]:
        """
        Get curated topics by category (fallback when web search is unavailable).
        """
        topics_db = {
            "technology": [
                {"title": "Latest AI breakthroughs reshape software development", "category": "tech"},
                {"title": "New programming language gains traction among developers", "category": "tech"},
                {"title": "Cybersecurity threat levels increase globally", "category": "tech"},
                {"title": "Cloud computing costs: optimization strategies", "category": "tech"},
                {"title": "Open source projects making waves this month", "category": "tech"},
            ],
            "entertainment": [
                {"title": "New streaming series breaks viewership records", "category": "entertainment"},
                {"title": "Gaming industry sees unprecedented growth", "category": "entertainment"},
                {"title": "Music festival announces surprise lineup", "category": "entertainment"},
                {"title": "Indie film wins major international award", "category": "entertainment"},
            ],
            "general": [
                {"title": "Global tech summit announces innovation awards", "category": "general"},
                {"title": "Remote work trends continue to evolve", "category": "general"},
                {"title": "Social media platforms test new features", "category": "general"},
                {"title": "Digital wellness becomes priority for users", "category": "general"},
            ],
            "business": [
                {"title": "Startup funding reaches new heights", "category": "business"},
                {"title": "Tech giants announce strategic partnerships", "category": "business"},
                {"title": "Remote-first companies report productivity gains", "category": "business"},
            ],
            "science": [
                {"title": "Breakthrough in quantum computing announced", "category": "science"},
                {"title": "Climate tech innovations gain investment", "category": "science"},
                {"title": "Space exploration reaches new milestone", "category": "science"},
            ],
        }

        topics = topics_db.get(category, topics_db["general"])
        return random.sample(topics, min(3, len(topics)))

    async def _get_news_by_interest(self, interest: str) -> List[Dict[str, Any]]:
        """Get news items related to a specific interest (curated fallback)."""
        interest_lower = interest.lower()

        interest_news = {
            "technology": [
                {"title": f"New developments in {interest}", "category": "tech", "interest": interest},
                {"title": f"{interest}: What's next in 2026?", "category": "tech", "interest": interest},
            ],
            "coding": [
                {"title": "Developer tools getting major updates", "category": "tech", "interest": interest},
                {"title": "Code quality: new best practices emerge", "category": "tech", "interest": interest},
            ],
            "ai": [
                {"title": "AI ethics debate intensifies", "category": "tech", "interest": interest},
                {"title": "Machine learning models reach new accuracy", "category": "tech", "interest": interest},
            ],
            "music": [
                {"title": "Music streaming algorithms evolve", "category": "entertainment", "interest": interest},
                {"title": "Underground music scene goes mainstream", "category": "entertainment", "interest": interest},
            ],
            "gaming": [
                {"title": "New gaming platform launches", "category": "entertainment", "interest": interest},
                {"title": "E-sports tournament breaks records", "category": "entertainment", "interest": interest},
            ],
            "art": [
                {"title": "Digital art market expands", "category": "culture", "interest": interest},
                {"title": "AI-generated art sparks debate", "category": "culture", "interest": interest},
            ],
        }

        # Find matching news
        for key in interest_news.keys():
            if key in interest_lower or interest_lower in key:
                return interest_news[key][:1]

        # Generic fallback
        return [{"title": f"Interesting developments in {interest}", "category": "general", "interest": interest}]
