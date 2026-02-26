#!/usr/bin/env python3
"""Dump ALL raw evidence for Jaijith/DigitalHunter to local text files for manual review."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

USER_ID = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
S3_BUCKET = "2n1-uploads-019396192218"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence_dump")


def get_secret(name):
    import boto3
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(SecretId=name)["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw


async def main():
    import boto3
    from motor.motor_asyncio import AsyncIOMotorClient

    os.makedirs(OUT_DIR, exist_ok=True)
    mongo_uri = get_secret("2n1/mongodb/uri")
    client = AsyncIOMotorClient(mongo_uri)
    db = client["neurallinks_local"]
    s3 = boto3.client("s3", region_name="us-west-2")
    q = {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}

    # 1. ALL voice transcripts from S3
    print("Fetching voice transcripts from S3...")
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
    with open(os.path.join(OUT_DIR, "01_transcripts.txt"), "w") as f:
        for i, t in enumerate(all_transcripts):
            f.write(f"\n{'='*80}\n")
            f.write(f"TRANSCRIPT {i+1}/{len(all_transcripts)}\n")
            f.write(f"Session: {t['session_id']}\n")
            f.write(f"Date: {t['created_at']}\n")
            f.write(f"Duration: {t['duration']}s\n")
            f.write(f"{'='*80}\n\n")
            f.write(t["text"])
            f.write("\n")
    print(f"  {len(all_transcripts)} transcripts -> 01_transcripts.txt")

    # 2. ALL real posts
    print("Fetching real posts...")
    posts = await db.posts.find(
        {"user_id": USER_ID, "post_type": {"$in": ["real", None]}},
        {"_id": 0, "text": 1, "content": 1, "created_at": 1, "timestamp": 1, "id": 1}
    ).sort("created_at", -1).to_list(500)
    with open(os.path.join(OUT_DIR, "02_real_posts.txt"), "w") as f:
        for i, p in enumerate(posts):
            text = p.get("text", p.get("content", ""))
            ts = p.get("created_at", p.get("timestamp", ""))
            f.write(f"\n--- POST {i+1}/{len(posts)} [{str(ts)[:19]}] ---\n")
            f.write(f"{text}\n")
    print(f"  {len(posts)} posts -> 02_real_posts.txt")

    # 3. User profile
    print("Fetching user profile...")
    user = await db.users.find_one({"id": USER_ID}, {"_id": 0})
    with open(os.path.join(OUT_DIR, "03_user_profile.json"), "w") as f:
        json.dump(user, f, indent=2, default=str)
    print(f"  Profile saved -> 03_user_profile.json")

    # 4. Conversation index
    print("Fetching conversation index...")
    conv = await db.conversation_index.find(q, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    with open(os.path.join(OUT_DIR, "04_conversation_index.txt"), "w") as f:
        for c in conv:
            f.write(f"\n--- Session: {c.get('session_id','')[:20]} | {str(c.get('timestamp',''))[:19]} ---\n")
            f.write(f"Summary: {c.get('summary','')}\n")
            f.write(f"Topics: {c.get('topics',[])}\n")
            f.write(f"People: {c.get('people_mentioned',[])}\n")
            f.write(f"Emotion: {c.get('emotional_tone','')}\n")
            f.write(f"Key quotes: {c.get('key_quotes',[])}\n")
    print(f"  {len(conv)} entries -> 04_conversation_index.txt")

    # 5. Identity memory
    print("Fetching identity memory...")
    identity = await db.identity_memory.find(q, {"_id": 0}).to_list(100)
    with open(os.path.join(OUT_DIR, "05_identity_memory.json"), "w") as f:
        json.dump(identity, f, indent=2, default=str)
    print(f"  {len(identity)} entries -> 05_identity_memory.json")

    # 6. Current graph nodes
    print("Fetching current graph nodes...")
    nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)
    with open(os.path.join(OUT_DIR, "06_current_nodes.json"), "w") as f:
        json.dump(nodes, f, indent=2, default=str)
    print(f"  {len(nodes)} nodes -> 06_current_nodes.json")

    # 7. Current graph edges
    print("Fetching current graph edges...")
    nids = [n.get("id","") for n in nodes if n.get("id")]
    edges = await db.graph_edges.find(
        {"$or": [{"user_id": USER_ID}, {"from_node_id": {"$in": nids}}, {"to_node_id": {"$in": nids}}]},
        {"_id": 0}
    ).to_list(10000)
    with open(os.path.join(OUT_DIR, "07_current_edges.json"), "w") as f:
        json.dump(edges, f, indent=2, default=str)
    print(f"  {len(edges)} edges -> 07_current_edges.json")

    # 8. Episodic memory
    print("Fetching episodic memory...")
    episodic = await db.episodic_memory.find(q, {"_id": 0}).to_list(500)
    with open(os.path.join(OUT_DIR, "08_episodic_memory.json"), "w") as f:
        json.dump(episodic, f, indent=2, default=str)
    print(f"  {len(episodic)} entries -> 08_episodic_memory.json")

    # 9. Users.connections
    if user and user.get("connections"):
        with open(os.path.join(OUT_DIR, "09_user_connections.json"), "w") as f:
            json.dump(user.get("connections", []), f, indent=2, default=str)
        print(f"  {len(user.get('connections',[]))} connections -> 09_user_connections.json")

    client.close()
    print(f"\nAll evidence dumped to {OUT_DIR}/")

asyncio.run(main())
