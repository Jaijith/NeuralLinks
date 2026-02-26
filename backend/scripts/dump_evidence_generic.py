#!/usr/bin/env python3
"""Dump ALL raw evidence for a given user to local files."""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

S3_BUCKET = "2n1-uploads-019396192218"


def get_secret(name):
    import boto3
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(SecretId=name)["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw


async def dump_user(user_id, out_dir):
    import boto3
    from motor.motor_asyncio import AsyncIOMotorClient

    os.makedirs(out_dir, exist_ok=True)
    mongo_uri = get_secret("2n1/mongodb/uri")
    client = AsyncIOMotorClient(mongo_uri)
    db = client["neurallinks_local"]
    s3 = boto3.client("s3", region_name="us-west-2")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        print(f"User {user_id} not found!")
        client.close()
        return

    USER_ID = user["id"]
    print(f"Found user: {user.get('name')} (avatar: {user.get('avatar_name')}, id: {USER_ID})")

    q = {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}

    # 1. Full user profile
    with open(os.path.join(out_dir, "03_user_profile.json"), "w") as f:
        json.dump(user, f, indent=2, default=str)
    print(f"  Profile saved")

    # 2. Voice transcripts from S3
    metas = await db.voice_transcripts.find({"user_id": USER_ID}, {"_id": 0}).to_list(1000)
    all_transcripts = []
    for m in metas:
        s3_key = m.get("s3_key", "")
        if not s3_key:
            continue
        try:
            body = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)["Body"].read().decode("utf-8")
            data = json.loads(body)
            lines = []
            for msg in data.get("messages", []):
                role = msg.get("role", "?")
                text = msg.get("text", msg.get("content", ""))
                if text:
                    speaker = "USER" if role in ("user", "human") else "AVATAR"
                    lines.append(f"{speaker}: {text}")
            all_transcripts.append({
                "session_id": m.get("session_id", ""),
                "created_at": str(m.get("created_at", "")),
                "duration": m.get("duration_seconds", 0),
                "text": "\n".join(lines)
            })
        except Exception as e:
            print(f"  S3 error for {s3_key}: {e}")
    with open(os.path.join(out_dir, "01_transcripts.txt"), "w") as f:
        for i, t in enumerate(all_transcripts):
            f.write(f"\n{'='*80}\nTRANSCRIPT {i+1}/{len(all_transcripts)}\n")
            f.write(f"Session: {t['session_id']}\nDate: {t['created_at']}\nDuration: {t['duration']}s\n{'='*80}\n\n")
            f.write(t["text"] + "\n")
    print(f"  {len(all_transcripts)} transcripts")

    # 3. Real posts
    posts = await db.posts.find(
        {"user_id": USER_ID, "post_type": {"$in": ["real", None]}},
        {"_id": 0, "text": 1, "content": 1, "created_at": 1, "id": 1}
    ).sort("created_at", -1).to_list(500)
    with open(os.path.join(out_dir, "02_real_posts.txt"), "w") as f:
        for i, p in enumerate(posts):
            text = p.get("text", p.get("content", ""))
            ts = p.get("created_at", "")
            f.write(f"\n--- POST {i+1}/{len(posts)} [{str(ts)[:19]}] ---\n{text}\n")
    print(f"  {len(posts)} real posts")

    # 4. Conversation index
    conv = await db.conversation_index.find(q, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    with open(os.path.join(out_dir, "04_conversation_index.txt"), "w") as f:
        for c in conv:
            f.write(f"\n--- Session: {str(c.get('session_id',''))[:20]} | {str(c.get('timestamp',''))[:19]} ---\n")
            f.write(f"Summary: {c.get('summary','')}\nTopics: {c.get('topics',[])}\n")
            f.write(f"People: {c.get('people_mentioned',[])}\nEmotion: {c.get('emotional_tone','')}\n")
            f.write(f"Key quotes: {c.get('key_quotes',[])}\n")
    print(f"  {len(conv)} conversation entries")

    # 5. Identity memory
    identity = await db.identity_memory.find(q, {"_id": 0}).to_list(100)
    with open(os.path.join(out_dir, "05_identity_memory.json"), "w") as f:
        json.dump(identity, f, indent=2, default=str)
    print(f"  {len(identity)} identity memory entries")

    # 6. Current graph nodes
    nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)
    with open(os.path.join(out_dir, "06_current_nodes.json"), "w") as f:
        json.dump(nodes, f, indent=2, default=str)
    print(f"  {len(nodes)} graph nodes")

    # 7. Current graph edges
    nids = [n.get("id", "") for n in nodes if n.get("id")]
    edges = await db.graph_edges.find(
        {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": nids}}, {"to_node_id": {"$in": nids}}]},
        {"_id": 0}
    ).to_list(10000)
    with open(os.path.join(out_dir, "07_current_edges.json"), "w") as f:
        json.dump(edges, f, indent=2, default=str)
    print(f"  {len(edges)} graph edges")

    # 8. Episodic memory
    episodic = await db.episodic_memory.find(q, {"_id": 0}).to_list(500)
    with open(os.path.join(out_dir, "08_episodic_memory.json"), "w") as f:
        json.dump(episodic, f, indent=2, default=str)
    print(f"  {len(episodic)} episodic entries")

    # 9. User connections
    if user.get("connections"):
        with open(os.path.join(out_dir, "09_user_connections.json"), "w") as f:
            json.dump(user.get("connections", []), f, indent=2, default=str)
        print(f"  {len(user.get('connections',[]))} connections")

    # 10. All posts (including avatar)
    all_posts = await db.posts.find(
        {"user_id": USER_ID},
        {"_id": 0, "text": 1, "content": 1, "created_at": 1, "post_type": 1, "id": 1, "comments": 1, "liked_by": 1, "has_image": 1, "image_url": 1}
    ).sort("created_at", -1).to_list(500)
    with open(os.path.join(out_dir, "10_all_posts.json"), "w") as f:
        json.dump(all_posts, f, indent=2, default=str)
    with open(os.path.join(out_dir, "10_all_posts.txt"), "w") as f:
        for i, p in enumerate(all_posts):
            text = p.get("text", p.get("content", ""))
            ts = p.get("created_at", "")
            pt = p.get("post_type", "?")
            f.write(f"\n--- POST {i+1}/{len(all_posts)} [{str(ts)[:19]}] type={pt} ---\n{text}\n")
    print(f"  {len(all_posts)} total posts")

    # 11. Style profiles
    styles = await db.avatar_style_profiles.find(q, {"_id": 0}).to_list(10)
    if styles:
        with open(os.path.join(out_dir, "11_style_profiles.json"), "w") as f:
            json.dump(styles, f, indent=2, default=str)
        print(f"  {len(styles)} style profiles")

    # 12. Bond moments
    bonds = await db.bond_moments.find(q, {"_id": 0}).to_list(100)
    if bonds:
        with open(os.path.join(out_dir, "12_bond_moments.json"), "w") as f:
            json.dump(bonds, f, indent=2, default=str)
        print(f"  {len(bonds)} bond moments")

    client.close()
    print(f"  All evidence dumped to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dump_evidence_generic.py <user_id> <output_dir>")
        sys.exit(1)
    asyncio.run(dump_user(sys.argv[1], sys.argv[2]))
