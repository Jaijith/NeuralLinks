"""
Shared STM Ingestion Utility.

Single entry point for writing observations to STM from any source:
voice, posts, chat, platform imports, etc.

Pipeline: Content → Classification Agent → Validation → STM Writer
"""

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .classification_agent import classify_observations
from .stm_writer import STMWriter
from .validation import validate_observations

logger = logging.getLogger(__name__)


async def classify_and_ingest(
    openai_client,
    db: AsyncIOMotorDatabase,
    user_id: str,
    avatar_id: str,
    content: str,
    source: str,
    session_id: str = "",
) -> int:
    """
    Full pipeline: classify content and write observations to STM.

    This is the single entry point that all write paths (voice, posts, chat,
    platform imports) should use instead of writing directly to graph_nodes.

    Args:
        openai_client: AsyncOpenAI client instance.
        db: MongoDB database instance.
        user_id: The user this content is about.
        avatar_id: The avatar processing this content.
        content: The text content to classify (conversation, post, etc.).
        source: Source identifier ("voice", "post", "chat", "platform_spotify", etc.).
        session_id: Optional session/conversation ID for traceability.

    Returns:
        Number of observations written to STM.
    """
    if not content or not content.strip():
        return 0

    try:
        # Step 1: Classification Agent
        result = await classify_observations(
            openai_client=openai_client,
            db=db,
            user_id=user_id,
            content=content,
            source=source,
        )

        if not result.observations:
            logger.debug(f"No observations extracted from {source} for {user_id[:8]}...")
            return 0

        # Step 2: Validation
        valid_observations = validate_observations(result.observations)

        if not valid_observations:
            logger.debug(f"All observations filtered by validation for {user_id[:8]}...")
            return 0

        # Step 3: STM Writer
        writer = STMWriter(db)
        written = await writer.write(
            user_id=user_id,
            avatar_id=avatar_id,
            observations=valid_observations,
            co_mentions=result.co_mentions,
            source=source,
            session_id=session_id,
        )

        logger.info(
            f"Ingestion complete: {written}/{len(result.observations)} observations "
            f"from {source} for {user_id[:8]}..."
        )
        return written

    except Exception as e:
        logger.error(f"STM ingestion error ({source}) for {user_id[:8]}...: {e}")
        return 0
