#!/usr/bin/env python3
"""Quick check of what personality data exists for avatars."""
import asyncio, os, sys, json, boto3

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    raw = boto3.session.Session().client('secretsmanager', region_name='us-west-1').get_secret_value(SecretId='2n1/mongodb/uri')['SecretString']
    try:
        url = json.loads(raw).get('uri', raw)
    except Exception:
        url = raw

    client = AsyncIOMotorClient(url)
    db = client['neurallinks_local']

    avatars = await db.users.find(
        {"avatar_actions_enabled": {"$exists": True}},
        {"_id": 0, "id": 1, "name": 1, "avatar_name": 1, "avatar_character_profile": 1}
    ).to_list(500)

    for av in avatars[:3]:
        uid = av['id']
        name = av.get('name', '?')
        aname = av.get('avatar_name', '?')
        print(f"\n{'='*60}")
        print(f"  {name} ({aname})")
        print(f"{'='*60}")

        # Real posts
        rc = await db.posts.count_documents({"user_id": uid, "post_type": {"$in": ["real", None]}})
        print(f"  Real posts: {rc}")

        # Avatar posts
        ac = await db.posts.count_documents({"user_id": uid, "post_type": "avatar"})
        print(f"  Avatar posts: {ac}")
        avposts = await db.posts.find(
            {"user_id": uid, "post_type": "avatar"}, {"_id": 0, "text": 1}
        ).sort("created_at", -1).to_list(2)
        for p in avposts:
            print(f"    AV: {p.get('text','')[:120]}")

        # Personality prompt
        pp = await db.avatar_personality_prompts.find_one({"user_id": uid}, {"_id": 0})
        prompt_text = pp.get("personality_prompt", "") if pp else ""
        print(f"\n  Personality prompt ({len(prompt_text)} chars):")
        print(f"    {prompt_text[:400]}")

        # Character profile
        cp = av.get("avatar_character_profile", {})
        print(f"\n  Profile keys: {list(cp.keys())}")
        cs = cp.get("communication_style", {})
        if cs:
            print(f"  Comm style: {json.dumps(cs, default=str)[:300]}")
        print(f"  Traits: {cp.get('personality_traits', [])[:5]}")
        print(f"  Interests: {cp.get('interests', [])[:8]}")

        # Style profile
        sp = await db.avatar_style_profiles.find_one({"user_id": uid}, {"_id": 0})
        if sp:
            print(f"\n  Style profile: {json.dumps(sp, default=str)[:300]}")
        else:
            print(f"\n  Style profile: NONE")

    client.close()
    print("\nDone")

if __name__ == "__main__":
    asyncio.run(main())
