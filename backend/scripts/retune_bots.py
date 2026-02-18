"""
Retune existing AI bots to specialized domain agents.
Updates avatar_bio, avatar_interests, and adds agent_domain/expertise/agent_card fields.
Preserves all existing data (posts, friends, profile picture, etc).
"""

import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.motor_asyncio import AsyncIOMotorClient
from domain.marketplace.agents_catalog import AGENT_DEFINITIONS
from domain.marketplace.models import make_agent_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("PROD_MONGO_URI") or os.environ.get("MONGO_URI") or os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME", "neurallinks_local")

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"


async def retune_bots():
    """Update bot user documents with domain specialization fields."""
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    logger.info(f"Connected to: {MONGO_URI[:30]}... / {DB_NAME}")
    logger.info(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE UPDATE'}")
    logger.info(f"Agent definitions: {len(AGENT_DEFINITIONS)}")

    updated = 0
    skipped = 0
    not_found = 0

    for defn in AGENT_DEFINITIONS:
        bot_id = defn["bot_id"]
        bot = await db.users.find_one({"id": bot_id})

        if not bot:
            logger.warning(f"  Bot NOT FOUND: {defn['bot_name']} ({bot_id})")
            not_found += 1
            continue

        current_name = bot.get("avatar_name", "?")
        logger.info(f"\n  Bot: {current_name} ({bot_id})")
        logger.info(f"    Domain: {defn['domain_label']}")
        logger.info(f"    Current bio: {str(bot.get('avatar_bio', ''))[:60]}...")
        logger.info(f"    New bio: {defn['bio'][:60]}...")

        agent_card = make_agent_card(
            name=defn["bot_name"],
            description=defn["domain_label"],
            agent_user_id=bot_id,
            domain=defn["domain"],
            skills=defn["skills"],
        )

        update_fields = {
            "avatar_bio": defn["bio"],
            "avatar_interests": defn["interests"],
            "one_liner": defn["tagline"],
            "agent_domain": defn["domain"],
            "agent_domain_label": defn["domain_label"],
            "agent_expertise": defn["expertise"],
            "agent_card": agent_card,
            "is_ai_agent": True,
            "is_bot": True,
            "avatar_autonomous": True,
            "avatar_activity_level": "bot_hourly",
            "agent_consultation_prompt": defn["consultation_prompt"],
        }

        if DRY_RUN:
            logger.info(f"    [DRY RUN] Would update {len(update_fields)} fields")
        else:
            result = await db.users.update_one(
                {"id": bot_id},
                {"$set": update_fields}
            )
            if result.modified_count > 0:
                logger.info(f"    Updated {result.modified_count} fields")
                updated += 1
            else:
                logger.info(f"    Already up to date (no changes)")
                skipped += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"RESULTS: Updated={updated}, Skipped={skipped}, NotFound={not_found}")
    logger.info(f"Total agents defined: {len(AGENT_DEFINITIONS)}")

    if DRY_RUN:
        logger.info("\nRe-run with DRY_RUN=false to apply changes.")

    client.close()


if __name__ == "__main__":
    asyncio.run(retune_bots())
