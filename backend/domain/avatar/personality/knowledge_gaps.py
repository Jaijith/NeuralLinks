"""
Knowledge Gap Tracker
Tracks what the avatar doesn't yet know about the user and surfaces
questions naturally during voice conversations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
import logging

logger = logging.getLogger(__name__)


# The master list of things we want to learn about every user.
# Each item maps to a coverage dimension.
DEFAULT_QUESTIONS = [
    # Life narrative
    {"question": "What got you into what you do for work?",
     "category": "life_narrative", "priority": 0.9,
     "natural_phrasing": "I was thinking... you've never really told me how you ended up doing what you do. What's the story there?"},
    {"question": "Tell me about where you grew up.",
     "category": "life_narrative", "priority": 0.85,
     "natural_phrasing": "Hey, I realized I don't really know where you grew up. What was that like?"},
    {"question": "What's the biggest turning point in your life so far?",
     "category": "life_narrative", "priority": 0.8,
     "natural_phrasing": "I've been wondering... if you had to pick one moment that really changed everything for you, what would it be?"},

    # Values & beliefs
    {"question": "What do you feel really strongly about?",
     "category": "values_beliefs", "priority": 0.85,
     "natural_phrasing": "What's something you feel really passionate about? Like something you'd defend no matter what?"},
    {"question": "What does success look like to you?",
     "category": "values_beliefs", "priority": 0.75,
     "natural_phrasing": "I'm curious... what does success actually mean to you? Like your version of it."},

    # Communication style
    {"question": "How do you usually handle disagreements?",
     "category": "communication_style", "priority": 0.7,
     "natural_phrasing": "When someone says something you totally disagree with, what do you usually do? Speak up or let it go?"},
    {"question": "Would people describe you as funny?",
     "category": "humor_personality", "priority": 0.65,
     "natural_phrasing": "So... would your friends say you're the funny one in the group? What's your kind of humor?"},

    # Social patterns
    {"question": "Who are the people that matter most to you?",
     "category": "social_patterns", "priority": 0.8,
     "natural_phrasing": "Who are the people that really matter to you? Like, your inner circle."},
    {"question": "Do you prefer deep one-on-one conversations or group hangouts?",
     "category": "social_patterns", "priority": 0.6,
     "natural_phrasing": "Are you more of a one-on-one deep conversations person or do you thrive in group settings?"},

    # Emotional patterns
    {"question": "What genuinely makes you happy?",
     "category": "emotional_patterns", "priority": 0.85,
     "natural_phrasing": "What genuinely lights you up? Like, that thing that makes you forget about everything else."},
    {"question": "What frustrates you the most?",
     "category": "emotional_patterns", "priority": 0.7,
     "natural_phrasing": "Okay, real talk — what gets under your skin? What's the thing that just frustrates you?"},
    {"question": "How do you deal with tough times?",
     "category": "emotional_patterns", "priority": 0.65,
     "natural_phrasing": "When things get really tough, what do you do? Like, your go-to way of dealing with it."},

    # Interests & passions
    {"question": "What could you talk about for hours?",
     "category": "interests_passions", "priority": 0.8,
     "natural_phrasing": "What's that thing you could talk about for hours without getting bored? Everyone has one."},
    {"question": "Is there something you're secretly nerdy about?",
     "category": "interests_passions", "priority": 0.6,
     "natural_phrasing": "Come on, tell me — what's your secret nerdy obsession? The thing most people don't know about?"},

    # Daily life
    {"question": "What does a typical day look like for you?",
     "category": "daily_life", "priority": 0.7,
     "natural_phrasing": "Walk me through your typical day. Like, from when you wake up — what does it look like?"},
    {"question": "Are you a morning person or a night owl?",
     "category": "daily_life", "priority": 0.5,
     "natural_phrasing": "So are you an early riser or do you come alive at night? I feel like I should know this by now."},
]


class KnowledgeGapTracker:
    """
    Tracks knowledge gaps and surfaces questions in voice conversations.
    Collection: ``avatar_knowledge_gaps``
    """

    MIN_CONVERSATIONS_BETWEEN_QUESTIONS = 2

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_or_create(self, user_id: str) -> Dict[str, Any]:
        """Get or initialize the knowledge gap document."""
        doc = await self.db.avatar_knowledge_gaps.find_one({"user_id": user_id}, {"_id": 0})
        if doc:
            return doc

        # Initialize
        questions = []
        for q in DEFAULT_QUESTIONS:
            questions.append({
                "id": str(uuid.uuid4()),
                "question": q["question"],
                "category": q["category"],
                "priority": q["priority"],
                "natural_phrasing": q["natural_phrasing"],
                "asked": False,
                "asked_at": None,
                "answer_extracted": False,
            })

        doc = {
            "user_id": user_id,
            "coverage_scores": {
                "life_narrative": 0.1,
                "values_beliefs": 0.1,
                "communication_style": 0.1,
                "social_patterns": 0.1,
                "interests_passions": 0.2,
                "emotional_patterns": 0.1,
                "daily_life": 0.1,
                "humor_personality": 0.1,
            },
            "questions_queue": questions,
            "last_question_asked_at": None,
            "conversations_since_last_question": 0,
        }
        # Use upsert to avoid duplicate key issues
        await self.db.avatar_knowledge_gaps.update_one(
            {"user_id": user_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return doc

    async def get_next_question(self, user_id: str) -> Optional[str]:
        """
        Return the natural phrasing of the next question to ask,
        or None if we should wait.
        """
        doc = await self.get_or_create(user_id)

        convos_since = doc.get("conversations_since_last_question", 0)
        if convos_since < self.MIN_CONVERSATIONS_BETWEEN_QUESTIONS:
            return None

        queue = doc.get("questions_queue", [])
        # Pick highest-priority unasked question
        candidates = [q for q in queue if not q.get("asked")]
        if not candidates:
            return None

        candidates.sort(key=lambda q: q.get("priority", 0), reverse=True)
        chosen = candidates[0]
        return chosen.get("natural_phrasing", chosen.get("question"))

    async def mark_question_asked(self, user_id: str, question_text: str):
        """Mark a question as asked (called after voice session with that question)."""
        now = datetime.now(timezone.utc).isoformat()
        await self.db.avatar_knowledge_gaps.update_one(
            {"user_id": user_id, "questions_queue.natural_phrasing": question_text},
            {
                "$set": {
                    "questions_queue.$.asked": True,
                    "questions_queue.$.asked_at": now,
                    "last_question_asked_at": now,
                    "conversations_since_last_question": 0,
                }
            }
        )

    async def increment_conversation_count(self, user_id: str):
        """Call after every voice session ends."""
        await self.db.avatar_knowledge_gaps.update_one(
            {"user_id": user_id},
            {"$inc": {"conversations_since_last_question": 1}},
            upsert=True,
        )

    async def update_coverage(self, user_id: str, category: str, delta: float = 0.1):
        """Increase coverage score for a category (capped at 1.0)."""
        field = f"coverage_scores.{category}"
        doc = await self.db.avatar_knowledge_gaps.find_one({"user_id": user_id}, {field: 1})
        current = 0.1
        if doc:
            current = doc.get("coverage_scores", {}).get(category, 0.1)
        new_val = min(1.0, current + delta)
        await self.db.avatar_knowledge_gaps.update_one(
            {"user_id": user_id},
            {"$set": {field: new_val}},
            upsert=True,
        )
