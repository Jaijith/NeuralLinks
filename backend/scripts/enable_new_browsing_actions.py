#!/usr/bin/env python3
"""
Enable new browsing/news actions for ALL existing avatars.

This script adds the following new actions to every avatar that has
avatar_actions_enabled configured:
  - browse_web: Real web browsing for news/articles/images
  - search_images: Image search for visual posts
  - browse_and_share_news: Browse news + create reaction post with link

It does NOT overwrite any existing permissions — only adds the new ones.
"""
import asyncio
import os
import sys
import json
import boto3

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient


def get_production_mongo_url():
    """Get MongoDB URL from AWS Secrets Manager"""
    session = boto3.session.Session()
    sm = session.client(service_name='secretsmanager', region_name='us-west-1')
    resp = sm.get_secret_value(SecretId='2n1/mongodb/uri')
    secret = resp['SecretString']
    try:
        d = json.loads(secret)
        return d.get('uri') or d.get('MONGO_URL') or secret
    except Exception:
        return secret


# The new actions to enable
NEW_ACTIONS = [
    'browse_web',
    'search_images',
    'browse_and_share_news',
]

# Also ensure these older actions exist (some avatars might be missing them)
ENSURE_ACTIONS = [
    'browse_feed',
    'get_friend_activities',
    'get_trending_topics',
]


async def main():
    print("=" * 70)
    print("  ENABLE NEW BROWSING/NEWS ACTIONS FOR ALL AVATARS")
    print("=" * 70)

    mongo_url = get_production_mongo_url()
    client = AsyncIOMotorClient(mongo_url)
    db = client['neurallinks_local']

    try:
        await db.command("ping")
        print("✅ Connected to production MongoDB\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    # Find ALL users that have avatar configuration
    avatars = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "avatar_actions_enabled": 1, "avatar_enabled_actions": 1}
    ).to_list(500)

    print(f"📋 Found {len(avatars)} avatars with action permissions\n")

    if not avatars:
        print("⚠️  No avatars found. Nothing to update.")
        client.close()
        return

    updated = 0
    already_ok = 0

    for avatar in avatars:
        user_id = avatar.get('id', '?')
        name = avatar.get('name', '?')
        avatar_name = avatar.get('avatar_name', '—')
        current_actions = avatar.get('avatar_actions_enabled', {})
        current_list = avatar.get('avatar_enabled_actions', [])

        # Check which new actions are missing
        missing_obj = [a for a in NEW_ACTIONS + ENSURE_ACTIONS if a not in current_actions]
        missing_list = [a for a in NEW_ACTIONS + ENSURE_ACTIONS if a not in current_list]

        if not missing_obj and not missing_list:
            print(f"  ✅ {name} ({avatar_name}) — already has all actions")
            already_ok += 1
            continue

        # Build update
        set_doc = {}
        for action in missing_obj:
            set_doc[f"avatar_actions_enabled.{action}"] = True

        # Build the full list (existing + new)
        full_list = list(set(current_list + NEW_ACTIONS + ENSURE_ACTIONS))
        set_doc["avatar_enabled_actions"] = full_list

        result = await db.users.update_one(
            {"id": user_id},
            {"$set": set_doc}
        )

        if result.modified_count > 0:
            print(f"  🔧 {name} ({avatar_name}) — UPDATED (+{len(missing_obj)} actions)")
            for a in missing_obj:
                print(f"       + {a}")
            updated += 1
        else:
            print(f"  ℹ️  {name} ({avatar_name}) — no changes needed")
            already_ok += 1

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total avatars:   {len(avatars)}")
    print(f"  Updated:         {updated}")
    print(f"  Already current: {already_ok}")
    print(f"{'=' * 70}")

    # Verification pass
    print(f"\n📋 VERIFICATION — All avatars and their browsing actions:\n")
    avatars_updated = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "avatar_actions_enabled": 1}
    ).to_list(500)

    for avatar in avatars_updated:
        name = avatar.get('name', '?')
        avatar_name = avatar.get('avatar_name', '—')
        actions = avatar.get('avatar_actions_enabled', {})

        browse = "✅" if actions.get('browse_web') else "❌"
        images = "✅" if actions.get('search_images') else "❌"
        news = "✅" if actions.get('browse_and_share_news') else "❌"
        feed = "✅" if actions.get('browse_feed') else "❌"
        friends = "✅" if actions.get('get_friend_activities') else "❌"
        trending = "✅" if actions.get('get_trending_topics') else "❌"

        print(f"  {name} ({avatar_name})")
        print(f"    browse_web: {browse}  search_images: {images}  browse_and_share_news: {news}")
        print(f"    browse_feed: {feed}  get_friend_activities: {friends}  get_trending_topics: {trending}")
        print()

    client.close()
    print("✅ Done!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
