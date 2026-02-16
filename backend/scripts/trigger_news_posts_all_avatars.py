#!/usr/bin/env python3
"""
Trigger a news reaction post for every avatar.

For each avatar:
1. Fetches real news based on their interests
2. Picks the most relevant story
3. Generates an emotional reaction post with the source link
4. Saves the post to the database

Includes rate-limiting delays between avatars to respect DuckDuckGo limits.
"""
import asyncio
import os
import sys
import json
import boto3
import time
import warnings

# Suppress duckduckgo_search deprecation warnings
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Force unbuffered output
def log(msg):
    print(msg, flush=True)

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone


def get_secrets():
    """Get MongoDB URL and OpenAI key from AWS Secrets Manager"""
    session = boto3.session.Session()
    sm = session.client(service_name='secretsmanager', region_name='us-west-1')

    # MongoDB
    mongo_resp = sm.get_secret_value(SecretId='2n1/mongodb/uri')
    mongo_secret = mongo_resp['SecretString']
    try:
        d = json.loads(mongo_secret)
        mongo_url = d.get('uri') or d.get('MONGO_URL') or mongo_secret
    except Exception:
        mongo_url = mongo_secret

    # OpenAI
    openai_resp = sm.get_secret_value(SecretId='2n1/openai/api-key')
    openai_key = openai_resp['SecretString']
    try:
        d = json.loads(openai_key)
        openai_key = d.get('api_key') or d.get('OPENAI_API_KEY') or openai_key
    except Exception:
        pass

    return mongo_url, openai_key


async def trigger_news_post(db, openai_client, avatar, index, total):
    """Generate a news reaction post for one avatar."""
    import random

    user_id = avatar.get('id')
    name = avatar.get('name', '?')
    avatar_name = avatar.get('avatar_name', '—')

    log(f"\n{'─' * 60}")
    log(f"  [{index}/{total}] {name} ({avatar_name})")
    log(f"{'─' * 60}")

    try:
        # Step 1: Fetch shareable news
        from services.web_browsing_service import WebBrowsingService
        web_service = WebBrowsingService(db)

        news_items = await web_service.get_shareable_news_for_avatar(user_id, max_results=5)

        if not news_items:
            log(f"  ⚠️  No news found — trying general news...")
            # Fallback: get interests and search directly
            interests = avatar.get('avatar_character_profile', {}).get('interests', [])
            if interests:
                query = f"{random.choice(interests)} news today"
                news_items = await web_service.search_news(query, max_results=3, timelimit="w")

        if not news_items:
            log(f"  ❌ Could not find any news. Skipping.")
            return {"name": name, "avatar": avatar_name, "status": "no_news"}

        # Pick a random news item for variety
        chosen = random.choice(news_items)
        news_title = chosen.get('title', '')
        news_url = chosen.get('url', '')
        news_snippet = chosen.get('snippet', '')
        news_source = chosen.get('source', '')

        log(f"  📰 News: {news_title[:70]}...")
        log(f"  🔗 Source: {news_source} | URL: {news_url[:60]}...")

        # Step 2: Get an image for this news
        # Priority: news item's own image > image search fallback
        news_image = chosen.get('image', '')
        if not news_image or not news_image.startswith('http'):
            log(f"  🖼️  No image from news — searching for one...")
            try:
                # Search for a relevant image based on the news title
                search_q = news_title[:60] if news_title else news_source
                img_results = await web_service.search_images(
                    search_q, max_results=3, type_image="photo", size="Medium"
                )
                if img_results:
                    news_image = img_results[0].get('image_url', '')
                    log(f"  🖼️  Found image: {news_image[:60]}...")
            except Exception as img_err:
                log(f"  ⚠️  Image search failed: {img_err}")

        news_context = {
            "title": news_title,
            "url": news_url,
            "snippet": news_snippet,
            "source": news_source,
        }

        # Step 3: Generate reaction post via PostOrchestrator
        from domain.avatar.orchestration.post_orchestrator import PostOrchestrator

        orchestrator = PostOrchestrator(db, openai_client)

        moods = ['curious', 'excited', 'happy', 'neutral', 'contemplative']
        mood = random.choice(moods)

        result = await orchestrator.generate_post(
            user_id=user_id,
            avatar_id=user_id,
            trigger=f"came across: {news_title}",
            mood=mood,
            energy_level=round(random.uniform(0.5, 0.9), 2),
            news_context=news_context,
        )

        post_text = result.get('text', '')
        if not post_text:
            log(f"  ❌ Empty post generated. Skipping.")
            return {"name": name, "avatar": avatar_name, "status": "empty_post"}

        pipeline = result.get('metadata', {}).get('pipeline', '?')
        reaction_style = result.get('metadata', {}).get('reaction_style', '?')

        log(f"  🎭 Pipeline: {pipeline} | Reaction: {reaction_style}")
        log(f"  📝 Post ({len(post_text)} chars):")
        # Print first 200 chars
        preview = post_text[:200].replace('\n', ' ')
        log(f"     \"{preview}...\"")

        # Step 4: Save the post
        import uuid
        post_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "text": post_text,
            "post_type": "avatar",
            "created_at": datetime.now(timezone.utc),
            "likes": [],
            "comments": [],
            "metadata": {
                "news_title": news_title,
                "news_url": news_url,
                "news_source": news_source,
                "pipeline": pipeline,
                "reaction_style": reaction_style,
                "triggered_by": "trigger_news_posts_all_avatars_v3",
            },
        }

        # Always set image_url if we have one
        if news_image and news_image.startswith('http'):
            post_data["image_url"] = news_image
            log(f"  🖼️  Image attached: ✅")
        else:
            log(f"  🖼️  Image attached: ⚠️ none found")

        await db.posts.insert_one(post_data)
        log(f"  ✅ Post saved! (ID: {post_data['id'][:12]}...)")

        # Check URL is in the post
        has_url = news_url and news_url in post_text
        log(f"  🔗 Link included: {'✅' if has_url else '⚠️ missing'}")

        has_image = bool(post_data.get("image_url"))

        return {
            "name": name,
            "avatar": avatar_name,
            "status": "success",
            "post_id": post_data["id"],
            "news_title": news_title[:50],
            "has_url": has_url,
            "has_image": has_image,
        }

    except Exception as e:
        log(f"  ❌ Error: {e}")
        return {"name": name, "avatar": avatar_name, "status": f"error: {str(e)[:60]}"}


async def main():
    log("=" * 60)
    log("  TRIGGER NEWS REACTION POSTS FOR ALL AVATARS")
    log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    mongo_url, openai_key = get_secrets()

    os.environ["OPENAI_API_KEY"] = openai_key
    os.environ["MONGODB_URI"] = mongo_url

    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=openai_key)

    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']

    try:
        await db.command("ping")
        log("✅ Connected to MongoDB\n")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        sys.exit(1)

    # Delete old triggered posts (clean slate)
    del_result = await db.posts.delete_many({
        "metadata.triggered_by": {"$regex": "^trigger_news_posts_all_avatars"}
    })
    log(f"🗑️  Deleted {del_result.deleted_count} old triggered posts\n")

    # Get all avatars with action permissions
    avatars = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {
            "_id": 0, "id": 1, "name": 1, "avatar_name": 1,
            "avatar_character_profile": 1, "avatar_internal_state": 1,
        }
    ).to_list(500)

    total = len(avatars)
    log(f"📋 Found {total} avatars. Generating news posts...\n")

    results = []
    for i, avatar in enumerate(avatars, 1):
        result = await trigger_news_post(db, openai_client, avatar, i, total)
        results.append(result)

        # Rate-limit delay: 8s between avatars to avoid DuckDuckGo throttling
        if i < total:
            delay = 8
            log(f"\n  ⏳ Waiting {delay}s (rate limit)...")
            await asyncio.sleep(delay)

    # Summary
    success = sum(1 for r in results if r.get('status') == 'success')
    no_news = sum(1 for r in results if r.get('status') == 'no_news')
    errors = sum(1 for r in results if r.get('status', '').startswith('error'))

    log(f"\n\n{'=' * 60}")
    log(f"  SUMMARY")
    log(f"{'=' * 60}")
    log(f"  Total avatars: {total}")
    log(f"  ✅ Posts created: {success}")
    log(f"  ⚠️  No news found: {no_news}")
    log(f"  ❌ Errors: {errors}")
    log(f"{'=' * 60}")

    images_ok = sum(1 for r in results if r.get('has_image'))
    log(f"  🖼️  Posts with images: {images_ok}")

    if success > 0:
        log(f"\n  Posts created:")
        for r in results:
            if r.get('status') == 'success':
                url_icon = "🔗" if r.get('has_url') else "⚠️"
                img_icon = "🖼️" if r.get('has_image') else "  "
                log(f"    {img_icon} {url_icon} {r['avatar']}: \"{r.get('news_title', '?')}...\"")

    client.close()
    log(f"\n✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
