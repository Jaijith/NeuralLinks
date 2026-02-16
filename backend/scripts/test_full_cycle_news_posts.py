#!/usr/bin/env python3
"""
Test the FULL state-aware agent pipeline for news posting.

For each avatar, runs a single cycle with force_action="browse_and_share_news"
through the complete orchestration:
  StateAwareAgent._run_single_cycle()
    → DecisionEngine (bypassed via force_action)
    → _map_action_to_tool("browse_and_share_news")
    → MCP BrowseAndShareNewsTool._execute_action()
      → WebBrowsingService.get_shareable_news_for_avatar()
      → PostOrchestrator.generate_post(news_context=...)
        → _generate_news_reaction_post()
        → _find_image_for_news()
      → Save post with image_url + metadata

This verifies the entire chain works end-to-end.
"""
import asyncio
import os
import sys
import json
import warnings
import logging

warnings.filterwarnings("ignore", category=RuntimeWarning)

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def log(msg):
    print(msg, flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Quiet down noisy loggers but keep our pipeline visible
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)

logger = logging.getLogger("test_full_cycle")


async def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(backend_dir, '.env'))

    mongo_url = os.getenv("MONGO_URL")
    openai_key = os.getenv("OPENAI_API_KEY")

    # If no local env, try AWS Secrets Manager
    if not mongo_url or not openai_key:
        log("No local .env found, trying AWS Secrets Manager...")
        import boto3
        sm = boto3.session.Session().client('secretsmanager', region_name='us-west-1')
        try:
            resp = sm.get_secret_value(SecretId='2n1/mongodb/uri')
            secret = resp['SecretString']
            try:
                d = json.loads(secret)
                mongo_url = d.get('uri') or d.get('MONGO_URL') or secret
            except Exception:
                mongo_url = secret
        except Exception as e:
            log(f"❌ Could not get MongoDB URI: {e}")
            return

        try:
            resp = sm.get_secret_value(SecretId='2n1/openai/api-key')
            secret = resp['SecretString']
            try:
                d = json.loads(secret)
                openai_key = d.get('api_key') or d.get('OPENAI_API_KEY') or secret
            except Exception:
                openai_key = secret
        except Exception as e:
            log(f"❌ Could not get OpenAI key: {e}")
            return

    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["MONGODB_URI"] = mongo_url
    os.environ["MONGO_URL"] = mongo_url

    from motor.motor_asyncio import AsyncIOMotorClient
    from datetime import datetime, timezone

    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']

    try:
        await db.command("ping")
        log("✅ Connected to MongoDB\n")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        return

    # Get all avatars (full documents needed for StateAwareAgent)
    avatars = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {"_id": 0}
    ).to_list(500)

    total = len(avatars)
    log(f"=" * 60)
    log(f"  FULL PIPELINE TEST: browse_and_share_news")
    log(f"  {total} avatars | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"=" * 60)

    # Import the state-aware agent and dependencies
    from domain.avatar.state_aware_agent import StateAwareAgent

    results = []

    for i, avatar in enumerate(avatars, 1):
        user_id = avatar.get('id')
        name = avatar.get('name', '?')
        avatar_name = avatar.get('avatar_name', '—')

        log(f"\n{'─' * 60}")
        log(f"  [{i}/{total}] {name} ({avatar_name})")
        log(f"{'─' * 60}")

        try:
            # Create a StateAwareAgent for this avatar (needs full user doc)
            agent = StateAwareAgent(
                bot=avatar,
                db=db,
            )
            await agent.initialize()

            # Run a single cycle forcing browse_and_share_news
            await agent._run_single_cycle(force_action="browse_and_share_news")

            # Check if a post was created
            latest_post = await db.posts.find_one(
                {"user_id": user_id, "post_type": "avatar"},
                sort=[("created_at", -1)]
            )

            if latest_post:
                text = latest_post.get("text", "")[:150]
                has_image = bool(latest_post.get("image_url"))
                has_url = "http" in latest_post.get("text", "")
                news_title = latest_post.get("metadata", {}).get("news_title", "")

                log(f"  ✅ Post created!")
                log(f"  🖼️  Image: {'✅' if has_image else '❌ missing'}")
                log(f"  🔗 Link in text: {'✅' if has_url else '⚠️'}")
                log(f"  📰 News: {news_title[:60]}...")
                log(f"  📝 \"{text}...\"")

                results.append({
                    "avatar": avatar_name,
                    "status": "success",
                    "has_image": has_image,
                    "has_url": has_url,
                })
            else:
                log(f"  ⚠️  No post found after cycle")
                results.append({"avatar": avatar_name, "status": "no_post"})

        except Exception as e:
            log(f"  ❌ Error: {e}")
            results.append({"avatar": avatar_name, "status": f"error: {str(e)[:50]}"})

        # Rate limit between avatars
        if i < total:
            log(f"\n  ⏳ Waiting 8s (rate limit)...")
            await asyncio.sleep(8)

    # Summary
    success = sum(1 for r in results if r.get('status') == 'success')
    with_images = sum(1 for r in results if r.get('has_image'))
    with_urls = sum(1 for r in results if r.get('has_url'))
    errors = sum(1 for r in results if r.get('status', '').startswith('error'))

    log(f"\n\n{'=' * 60}")
    log(f"  SUMMARY")
    log(f"{'=' * 60}")
    log(f"  Total avatars:    {total}")
    log(f"  ✅ Posts created:  {success}")
    log(f"  🖼️  With images:   {with_images}")
    log(f"  🔗 With links:    {with_urls}")
    log(f"  ❌ Errors:         {errors}")
    log(f"{'=' * 60}")

    for r in results:
        img = "🖼️" if r.get('has_image') else "  "
        url = "🔗" if r.get('has_url') else "  "
        status = "✅" if r.get('status') == 'success' else "❌"
        log(f"  {status} {img} {url} {r['avatar']}")

    client.close()
    log(f"\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n❌ Interrupted")
    except Exception as e:
        log(f"\n❌ Fatal: {e}")
        import traceback
        traceback.print_exc()
