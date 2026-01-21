"""
Content Awareness Service
Fetches current events, news, and trending topics for avatars to post about
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
    
    async def get_trending_topics(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Get trending topics by category
        
        Args:
            category: Category of content (technology, entertainment, general, etc.)
            
        Returns:
            List of trending topics with headlines and summaries
        """
        # Check cache
        cache_key = f"trending_{category}"
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key, [])
        
        try:
            # For now, provide curated trending topics
            # In production, this would call NewsAPI, RSS feeds, or web search
            topics = await self._get_curated_topics(category)
            
            # Cache results
            self.news_cache[cache_key] = topics
            self.last_fetch[cache_key] = datetime.now(timezone.utc)
            
            return topics
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}", exc_info=True)
            return []
    
    async def get_news_for_interests(self, interests: List[str]) -> List[Dict[str, Any]]:
        """
        Get news articles matching avatar's interests
        
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
        
        try:
            # Match interests to news categories
            news_items = []
            
            for interest in interests[:3]:  # Top 3 interests
                topics = await self._get_news_by_interest(interest)
                news_items.extend(topics)
            
            # Remove duplicates and limit
            unique_news = []
            seen_titles = set()
            for item in news_items:
                if item['title'] not in seen_titles:
                    unique_news.append(item)
                    seen_titles.add(item['title'])
            
            # Cache results
            self.news_cache[cache_key] = unique_news[:5]
            self.last_fetch[cache_key] = datetime.now(timezone.utc)
            
            return unique_news[:5]
            
        except Exception as e:
            logger.error(f"Error getting interest-based news: {e}", exc_info=True)
            return []
    
    async def get_viral_content(self) -> List[Dict[str, Any]]:
        """
        Get viral/trending social content
        
        Returns:
            List of viral content items
        """
        cache_key = "viral_content"
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key, [])
        
        try:
            # Curated viral-style topics
            viral = [
                {
                    "title": "AI models now creating memes faster than humans",
                    "category": "technology",
                    "vibe": "funny"
                },
                {
                    "title": "New productivity hack: actually turning off notifications",
                    "category": "lifestyle",
                    "vibe": "relatable"
                },
                {
                    "title": "Developers discover bug that's been there since 1999",
                    "category": "technology",
                    "vibe": "amusing"
                }
            ]
            
            self.news_cache[cache_key] = viral
            self.last_fetch[cache_key] = datetime.now(timezone.utc)
            
            return viral
            
        except Exception as e:
            logger.error(f"Error getting viral content: {e}", exc_info=True)
            return []
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.last_fetch:
            return False
        
        age = datetime.now(timezone.utc) - self.last_fetch[cache_key]
        return age < self.cache_duration
    
    async def _get_curated_topics(self, category: str) -> List[Dict[str, Any]]:
        """
        Get curated topics by category
        (In production, replace with real API calls)
        """
        topics_db = {
            "technology": [
                {"title": "Latest AI breakthroughs reshape software development", "category": "tech"},
                {"title": "New programming language gains traction among developers", "category": "tech"},
                {"title": "Cybersecurity threat levels increase globally", "category": "tech"},
                {"title": "Cloud computing costs: optimization strategies", "category": "tech"},
                {"title": "Open source projects making waves this month", "category": "tech"}
            ],
            "entertainment": [
                {"title": "New streaming series breaks viewership records", "category": "entertainment"},
                {"title": "Gaming industry sees unprecedented growth", "category": "entertainment"},
                {"title": "Music festival announces surprise lineup", "category": "entertainment"},
                {"title": "Indie film wins major international award", "category": "entertainment"}
            ],
            "general": [
                {"title": "Global tech summit announces innovation awards", "category": "general"},
                {"title": "Remote work trends continue to evolve", "category": "general"},
                {"title": "Social media platforms test new features", "category": "general"},
                {"title": "Digital wellness becomes priority for users", "category": "general"}
            ],
            "business": [
                {"title": "Startup funding reaches new heights", "category": "business"},
                {"title": "Tech giants announce strategic partnerships", "category": "business"},
                {"title": "Remote-first companies report productivity gains", "category": "business"}
            ],
            "science": [
                {"title": "Breakthrough in quantum computing announced", "category": "science"},
                {"title": "Climate tech innovations gain investment", "category": "science"},
                {"title": "Space exploration reaches new milestone", "category": "science"}
            ]
        }
        
        topics = topics_db.get(category, topics_db["general"])
        return random.sample(topics, min(3, len(topics)))
    
    async def _get_news_by_interest(self, interest: str) -> List[Dict[str, Any]]:
        """Get news items related to a specific interest"""
        interest_lower = interest.lower()
        
        # Map interests to news items
        interest_news = {
            "technology": [
                {"title": f"New developments in {interest}", "category": "tech", "interest": interest},
                {"title": f"{interest}: What's next in 2026?", "category": "tech", "interest": interest}
            ],
            "coding": [
                {"title": "Developer tools getting major updates", "category": "tech", "interest": interest},
                {"title": "Code quality: new best practices emerge", "category": "tech", "interest": interest}
            ],
            "ai": [
                {"title": "AI ethics debate intensifies", "category": "tech", "interest": interest},
                {"title": "Machine learning models reach new accuracy", "category": "tech", "interest": interest}
            ],
            "music": [
                {"title": "Music streaming algorithms evolve", "category": "entertainment", "interest": interest},
                {"title": "Underground music scene goes mainstream", "category": "entertainment", "interest": interest}
            ],
            "gaming": [
                {"title": "New gaming platform launches", "category": "entertainment", "interest": interest},
                {"title": "E-sports tournament breaks records", "category": "entertainment", "interest": interest}
            ],
            "art": [
                {"title": "Digital art market expands", "category": "culture", "interest": interest},
                {"title": "AI-generated art sparks debate", "category": "culture", "interest": interest}
            ]
        }
        
        # Find matching news
        for key in interest_news.keys():
            if key in interest_lower or interest_lower in key:
                return interest_news[key][:1]
        
        # Generic fallback
        return [{"title": f"Interesting developments in {interest}", "category": "general", "interest": interest}]
