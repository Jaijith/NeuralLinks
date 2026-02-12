#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  COMPREHENSIVE AVATAR PERSONALIZATION INITIALIZATION SCRIPT
═══════════════════════════════════════════════════════════════════════════

For each user in the production database, this script:

  Stage 1 — Style Learning     → Analyze all real posts → avatar_style_profiles
  Stage 2 — Knowledge Gaps     → Initialize question queue → avatar_knowledge_gaps
  Stage 3 — Voice Indexing     → Index unprocessed voice transcripts → conversation_index
  Stage 4 — Personality Traits → Extract traits/values from transcripts → graph_nodes
  Stage 5 — Personality Prompt → Generate cached personality prompt → avatar_personality_prompts

Idempotent — safe to re-run.  Uses upserts everywhere.
"""

import asyncio
import json
import logging
import os
import sys
import re
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("personalization")

# ---------------------------------------------------------------------------
# AWS helpers
# ---------------------------------------------------------------------------

def get_secret(secret_name: str, region: str = "us-west-2") -> str:
    """Fetch a secret from AWS Secrets Manager."""
    import boto3
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    raw = response["SecretString"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def fetch_transcript_from_s3(s3_client, bucket: str, s3_key: str) -> Optional[str]:
    """Download a voice transcript from S3 and return formatted text."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        body = response["Body"].read().decode("utf-8")
        data = json.loads(body)
        messages = data.get("messages", [])
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("text", msg.get("content", ""))
            if text:
                speaker = "User" if role in ("user", "human") else "Avatar"
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"  S3 fetch failed for {s3_key}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------

async def main():
    import boto3
    from motor.motor_asyncio import AsyncIOMotorClient
    from openai import AsyncOpenAI

    print("═" * 70)
    print("  AVATAR PERSONALIZATION INITIALIZATION")
    print("═" * 70)
    print()

    # ---- 1. Fetch secrets ----
    print("🔑 Fetching secrets from AWS Secrets Manager...")
    mongodb_uri = get_secret("2n1/mongodb/uri")
    openai_key = get_secret("2n1/openai/api-key")

    if not mongodb_uri:
        print("❌ Could not fetch MongoDB URI from Secrets Manager")
        return
    if not openai_key:
        print("❌ Could not fetch OpenAI API Key from Secrets Manager")
        return
    print("   ✅ Secrets loaded\n")

    # ---- 2. Connect ----
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["neurallinks_local"]
    openai_client = AsyncOpenAI(api_key=openai_key)
    s3_client = boto3.client("s3", region_name="us-west-2")
    S3_BUCKET = "2n1-uploads-019396192218"

    # ---- 3. Enumerate users ----
    all_users = await db.users.find(
        {},
        {
            "_id": 0, "id": 1, "name": 1, "email": 1,
            "avatar_name": 1, "avatar_id": 1,
            "avatar_enabled": 1, "is_bot": 1,
        }
    ).to_list(None)

    print(f"👥 Found {len(all_users)} users\n")

    # Summary accumulators
    total_summary = {
        "users_processed": 0,
        "style_profiles_built": 0,
        "post_insights_found": 0,
        "connections_discovered": 0,
        "knowledge_gaps_initialized": 0,
        "transcripts_indexed": 0,
        "traits_extracted": 0,
        "values_extracted": 0,
        "personality_prompts_generated": 0,
        "errors": [],
    }

    for user in all_users:
        user_id = user.get("id")
        name = user.get("name", "?")
        avatar_name = user.get("avatar_name", "?")
        is_bot = user.get("is_bot", False)

        print("─" * 70)
        print(f"👤 {name}  (avatar: {avatar_name})  [{'bot' if is_bot else 'real'}]")
        print(f"   user_id: {user_id}")
        print()

        user_report = {
            "posts_analyzed": 0,
            "post_insights": 0,
            "connections_discovered": 0,
            "knowledge_gaps": "skipped",
            "transcripts_indexed": 0,
            "transcripts_total": 0,
            "traits_extracted": 0,
            "values_extracted": 0,
            "personality_prompt": "no",
        }

        try:
            # ══════════════════════════════════════════════════════════════
            # STAGE 1: Build Writing Style Profile
            # ══════════════════════════════════════════════════════════════
            print("   📝 Stage 1: Building style profile from posts...")

            post_count = await db.posts.count_documents(
                {"user_id": user_id, "post_type": {"$in": ["real", None]}}
            )

            if post_count == 0:
                print(f"      ⏭  No real posts — skipping style profile")
            else:
                style_profile = await _build_style_profile(db, user_id)
                user_report["posts_analyzed"] = style_profile.get("total_posts_analyzed", 0)
                total_summary["style_profiles_built"] += 1
                print(f"      ✅ Style profile built from {user_report['posts_analyzed']} posts")

            # ══════════════════════════════════════════════════════════════
            # STAGE 1.5: Deep Post Insight Analysis
            # ══════════════════════════════════════════════════════════════
            print("   🔍 Stage 1.5: Analyzing posts for deep insights...")

            if post_count == 0:
                print(f"      ⏭  No real posts — skipping post insights")
            else:
                insight_result = await _analyze_post_insights(
                    db, openai_client, user_id
                )
                user_report["post_insights"] = insight_result.get("insights", 0)
                user_report["connections_discovered"] = insight_result.get("connections", 0)
                total_summary["post_insights_found"] += insight_result.get("insights", 0)
                total_summary["connections_discovered"] += insight_result.get("connections", 0)
                print(f"      ✅ Found {insight_result.get('insights', 0)} insights, "
                      f"{insight_result.get('connections', 0)} connections from "
                      f"{insight_result.get('analyzed', 0)} posts")

            # ══════════════════════════════════════════════════════════════
            # STAGE 2: Initialize Knowledge Gap Tracking
            # ══════════════════════════════════════════════════════════════
            print("   🧠 Stage 2: Initializing knowledge gaps...")

            existing_gaps = await db.avatar_knowledge_gaps.find_one(
                {"user_id": user_id}, {"_id": 0, "user_id": 1}
            )
            if existing_gaps:
                user_report["knowledge_gaps"] = "already exists"
                print(f"      ⏭  Already initialized")
            else:
                await _initialize_knowledge_gaps(db, user_id)
                user_report["knowledge_gaps"] = "initialized"
                total_summary["knowledge_gaps_initialized"] += 1
                print(f"      ✅ Knowledge gaps initialized (16 questions across 8 categories)")

            # ══════════════════════════════════════════════════════════════
            # STAGE 3 + 4: Process Voice Transcripts
            # (Index conversations + Extract personality traits)
            # ══════════════════════════════════════════════════════════════
            print("   🎙  Stage 3+4: Processing voice transcripts...")

            transcripts = await db.voice_transcripts.find(
                {"user_id": user_id}
            ).to_list(None)
            user_report["transcripts_total"] = len(transcripts)

            if not transcripts:
                print(f"      ⏭  No voice transcripts")
            else:
                # Check which ones are already indexed
                indexed_sessions = set()
                existing_indices = await db.conversation_index.find(
                    {"user_id": user_id}, {"session_id": 1}
                ).to_list(None)
                for idx in existing_indices:
                    indexed_sessions.add(idx.get("session_id"))

                unindexed = [
                    t for t in transcripts
                    if t.get("session_id") not in indexed_sessions
                ]

                print(f"      📊 {len(transcripts)} total, {len(unindexed)} need indexing")

                for i, transcript in enumerate(unindexed):
                    session_id = transcript.get("session_id", "")
                    s3_key = transcript.get("s3_key", "")
                    avatar_id = transcript.get("avatar_id", "")
                    duration = transcript.get("duration_seconds", 0)

                    if not s3_key:
                        logger.warning(f"      ⚠  Transcript {session_id} has no s3_key, skipping")
                        continue

                    # Fetch transcript text from S3
                    transcript_text = fetch_transcript_from_s3(s3_client, S3_BUCKET, s3_key)
                    if not transcript_text or len(transcript_text.strip()) < 50:
                        logger.warning(f"      ⚠  Transcript {session_id} too short or empty, skipping")
                        continue

                    print(f"      [{i+1}/{len(unindexed)}] Processing {session_id[:20]}...")

                    try:
                        # Stage 3: Index conversation
                        index_result = await _index_conversation(
                            db, openai_client, user_id, avatar_id,
                            session_id, s3_key, transcript_text, duration
                        )
                        if index_result:
                            user_report["transcripts_indexed"] += 1
                            total_summary["transcripts_indexed"] += 1

                        # Stage 4: Extract personality traits + values
                        traits_count, values_count = await _extract_personality(
                            db, openai_client, user_id, transcript_text
                        )
                        user_report["traits_extracted"] += traits_count
                        user_report["values_extracted"] += values_count
                        total_summary["traits_extracted"] += traits_count
                        total_summary["values_extracted"] += values_count

                        # Mark as processed
                        await db.voice_transcripts.update_one(
                            {"session_id": session_id},
                            {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}}
                        )

                        # Update knowledge gap coverage
                        await _update_knowledge_gap_coverage(db, user_id, transcript_text)

                    except Exception as e:
                        logger.error(f"      ❌ Error processing transcript {session_id}: {e}")
                        total_summary["errors"].append(f"{name}/{session_id}: {e}")

                print(f"      ✅ Indexed {user_report['transcripts_indexed']} conversations, "
                      f"extracted {user_report['traits_extracted']} traits, "
                      f"{user_report['values_extracted']} values")

            # ══════════════════════════════════════════════════════════════
            # STAGE 5: Generate Personality Prompt
            # ══════════════════════════════════════════════════════════════
            print("   ✨ Stage 5: Generating personality prompt...")

            prompt = await _generate_personality_prompt(db, user_id)
            if prompt:
                user_report["personality_prompt"] = f"yes ({len(prompt)} chars)"
                total_summary["personality_prompts_generated"] += 1
                # Show first 200 chars as preview
                preview = prompt[:200].replace("\n", " ") + ("..." if len(prompt) > 200 else "")
                print(f"      ✅ Prompt generated ({len(prompt)} chars)")
                print(f"      📄 Preview: {preview}")
            else:
                user_report["personality_prompt"] = "empty (no data)"
                print(f"      ⚠  Prompt empty — user may have very little data")

            total_summary["users_processed"] += 1

        except Exception as e:
            logger.error(f"   ❌ FATAL ERROR for {name}: {e}")
            traceback.print_exc()
            total_summary["errors"].append(f"{name}: {e}")

        # Print user summary
        print()
        print(f"   📊 Summary for {name}:")
        for k, v in user_report.items():
            print(f"      {k}: {v}")
        print()

    # ── Final Summary ──────────────────────────────────────────────────
    print("═" * 70)
    print("  FINAL SUMMARY")
    print("═" * 70)
    for k, v in total_summary.items():
        if k == "errors":
            print(f"  {k}: {len(v)} errors")
            for err in v:
                print(f"    ❌ {err}")
        else:
            print(f"  {k}: {v}")
    print("═" * 70)
    print("  DONE!")
    print("═" * 70)

    client.close()


# ═══════════════════════════════════════════════════════════════════════════
# STAGE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════


async def _build_style_profile(db, user_id: str) -> Dict[str, Any]:
    """Stage 1: Analyze all real posts and build aggregate style profile."""
    # Emoji regex
    emoji_re = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )

    cursor = db.posts.find(
        {"user_id": user_id, "post_type": {"$in": ["real", None]}},
        {"_id": 0, "text": 1, "content": 1, "created_at": 1}
    ).sort("created_at", -1).limit(200)
    posts = await cursor.to_list(200)

    if not posts:
        return {}

    # Analyse each post
    analyses = []
    for p in posts:
        text = p.get("text") or p.get("content") or ""
        if not text:
            continue

        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        emoji_matches = emoji_re.findall(text)
        emoji_count = sum(len(m) for m in emoji_matches)

        hedge_phrases = [
            "i think", "maybe", "probably", "to be honest",
            "honestly", "basically", "the thing is",
            "i mean", "kind of", "sort of", "actually",
            "to be fair", "in my opinion"
        ]
        found_hedges = [h for h in hedge_phrases if h in text.lower()]

        analyses.append({
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_sentence_length": len(words) / max(len(sentences), 1),
            "emoji_count": emoji_count,
            "question_count": text.count("?"),
            "exclamation_count": text.count("!"),
            "ellipsis_count": text.count("..."),
            "hedge_phrases_found": found_hedges,
            "starts_with_capital": text[0].isupper() if text else False,
            "all_lowercase": text == text.lower(),
            "has_hashtags": "#" in text,
            "hashtag_count": text.count("#"),
        })

    if not analyses:
        return {}

    total = len(analyses)
    avg_word_count = sum(a["word_count"] for a in analyses) / total
    avg_sentence_len = sum(a["avg_sentence_length"] for a in analyses) / total
    emoji_per_post = sum(a["emoji_count"] for a in analyses) / total
    question_rate = sum(1 for a in analyses if a["question_count"] > 0) / total
    exclamation_rate = sum(1 for a in analyses if a["exclamation_count"] > 0) / total
    ellipsis_rate = sum(1 for a in analyses if a["ellipsis_count"] > 0) / total
    lowercase_rate = sum(1 for a in analyses if a["all_lowercase"]) / total

    all_hedges: Dict[str, int] = {}
    for a in analyses:
        for h in a["hedge_phrases_found"]:
            all_hedges[h] = all_hedges.get(h, 0) + 1
    common_phrases = sorted(all_hedges, key=all_hedges.get, reverse=True)[:10]

    tone: Dict[str, float] = {}
    if exclamation_rate > 0.4:
        tone["enthusiastic"] = exclamation_rate
    if question_rate > 0.3:
        tone["inquisitive"] = question_rate
    if ellipsis_rate > 0.2:
        tone["contemplative"] = ellipsis_rate
    if lowercase_rate > 0.5:
        tone["casual"] = lowercase_rate
    if not tone:
        tone["balanced"] = 1.0

    post_texts = [p.get("text") or p.get("content") or "" for p in posts if (p.get("text") or p.get("content"))]
    sorted_by_len = sorted(post_texts, key=len)
    samples = []
    if len(sorted_by_len) >= 5:
        indices = [0, len(sorted_by_len) // 4, len(sorted_by_len) // 2,
                   3 * len(sorted_by_len) // 4, -1]
        samples = [sorted_by_len[i] for i in indices]
    else:
        samples = sorted_by_len[:5]

    profile = {
        "user_id": user_id,
        "avg_post_length": round(avg_word_count, 1),
        "avg_sentence_length": round(avg_sentence_len, 1),
        "emoji_frequency": round(emoji_per_post, 2),
        "question_rate": round(question_rate, 2),
        "exclamation_rate": round(exclamation_rate, 2),
        "ellipsis_rate": round(ellipsis_rate, 2),
        "lowercase_rate": round(lowercase_rate, 2),
        "common_phrases": common_phrases,
        "tone_distribution": tone,
        "writing_samples": [s[:300] for s in samples],
        "total_posts_analyzed": total,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.avatar_style_profiles.update_one(
        {"user_id": user_id}, {"$set": profile}, upsert=True
    )
    # Invalidate stale personality prompt cache
    await db.avatar_personality_prompts.delete_one({"user_id": user_id})

    return profile


async def _analyze_post_insights(db, openai_client, user_id: str) -> Dict[str, Any]:
    """Stage 1.5: Analyze posts for deep emotional/relational insights using LLM."""
    import uuid

    # Fetch posts (up to 50 most recent)
    cursor = db.posts.find(
        {"user_id": user_id, "post_type": {"$in": ["real", None]}},
        {"_id": 0, "id": 1, "text": 1, "content": 1, "created_at": 1}
    ).sort("created_at", -1).limit(50)
    posts = await cursor.to_list(50)

    if not posts:
        return {"analyzed": 0, "insights": 0, "connections": 0}

    # Check what we've already analyzed
    existing = await db.avatar_post_insights.find_one(
        {"user_id": user_id}, {"last_analyzed_post_date": 1}
    )
    watermark = existing.get("last_analyzed_post_date") if existing else None

    # Filter to only unanalyzed posts
    post_texts = []
    for p in posts:
        text = p.get("text") or p.get("content") or ""
        if text and len(text.strip()) > 10:
            post_texts.append({
                "post_id": p.get("id", ""),
                "text": text[:500],
                "date": str(p.get("created_at", "")),
            })

    if not post_texts:
        return {"analyzed": 0, "insights": 0, "connections": 0}

    # Batch analyze (up to 10 per LLM call)
    all_insights = []
    batch_size = 10
    for i in range(0, len(post_texts), batch_size):
        batch = post_texts[i:i + batch_size]

        prompt = """You are an EMOTIONAL INTELLIGENCE agent. Analyze these social media posts from ONE person and extract deep personal insights.

For each post that reveals something meaningful, extract:

1. **Connections**: People mentioned or implied (even without names).
   - "Missing this guy" → likely a child, partner, or close friend they're separated from
   - "Mom's cooking" → has a mother they're nostalgic about
   
2. **Emotional threads**: Strong emotions that deserve gentle attention.
   - Sadness, longing, guilt, pride, joy, nostalgia, frustration
   
3. **Life events**: Significant happenings in their life.

For emotional threads, generate a NATURAL, WARM question the avatar could ask.

POSTS:
{posts}

Return JSON:
{{
  "insights": [
    {{
      "post_id": "...",
      "post_text": "exact post text",
      "type": "connection" | "emotional" | "life_event",
      "discovery": {{
        "topic": "brief description",
        "emotion": "the primary emotion or null",
        "implied_connection": {{
          "name_hint": "name or unknown",
          "relationship": "son/mother/friend/etc",
          "evidence": "why you think this"
        }} or null,
        "life_event": "description" or null
      }},
      "thread": {{
        "natural_opener": "warm way to bring this up",
        "priority": 0.0-1.0,
        "sensitivity": "high" | "medium" | "low",
        "approach": "gentle_empathy" | "celebrate" | "curious" | "playful" | "supportive"
      }}
    }}
  ]
}}

RULES:
- Only extract MEANINGFUL insights. Skip generic posts.
- Priority should reflect emotional depth
- Be conservative — only extract what's clearly there"""

        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract deep personal insights from posts with emotional intelligence."},
                    {"role": "user", "content": prompt.format(posts=json.dumps(batch, indent=2))}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            insights = result.get("insights", [])

            for ins in insights:
                ins["id"] = f"insight_{uuid.uuid4().hex[:12]}"
                ins["status"] = "pending"
                ins["raised_at"] = None
                ins["discussed_at"] = None
                ins["session_id"] = None
                ins["user_response_summary"] = None
                pid = ins.get("post_id", "")
                for p in batch:
                    if p["post_id"] == pid:
                        ins["post_date"] = p["date"]
                        break
                else:
                    ins["post_date"] = datetime.now(timezone.utc).isoformat()

            all_insights.extend(insights)
        except Exception as e:
            logger.error(f"      Post insight batch analysis error: {e}")

    # Store insights and write connections
    connections_written = 0
    for insight in all_insights:
        post_id = insight.get("post_id", "")
        ins_type = insight.get("type", "")

        # Check for existing insight on same post + type
        dup = await db.avatar_post_insights.find_one({
            "user_id": user_id,
            "insights": {"$elemMatch": {"post_id": post_id, "type": ins_type}}
        })
        if not dup:
            await db.avatar_post_insights.update_one(
                {"user_id": user_id},
                {
                    "$push": {"insights": insight},
                    "$setOnInsert": {"user_id": user_id},
                },
                upsert=True,
            )

        # Write discovered connections
        if ins_type == "connection":
            discovery = insight.get("discovery", {})
            conn = discovery.get("implied_connection")
            if conn:
                relationship = (conn.get("relationship") or "").strip()
                name_hint = (conn.get("name_hint") or "unknown").strip()
                evidence = conn.get("evidence", "")
                if relationship:
                    display_name = name_hint if name_hint.lower() != "unknown" else f"({relationship})"
                    now = datetime.now(timezone.utc)

                    # Check if connection already exists
                    existing_conn = await db.users.find_one({
                        "id": user_id,
                        "connections.relationship": {"$regex": relationship, "$options": "i"}
                    })
                    if not existing_conn:
                        await db.users.update_one(
                            {"id": user_id},
                            {"$push": {"connections": {
                                "name": display_name,
                                "relationship": relationship,
                                "details": f"Discovered from post: {evidence}",
                                "source": "post_analysis",
                                "discovered_at": now.isoformat(),
                            }}}
                        )

                    # Check graph_nodes
                    existing_node = await db.graph_nodes.find_one({
                        "user_id": user_id,
                        "node_type": "connection",
                        "properties.relationship": {"$regex": relationship, "$options": "i"},
                    })
                    if not existing_node:
                        node_id = f"connection_{user_id}_{relationship.replace(' ', '_')}"
                        await db.graph_nodes.insert_one({
                            "id": node_id,
                            "user_id": user_id,
                            "node_type": "connection",
                            "label": display_name.lower(),
                            "display_label": display_name,
                            "strength": 0.8,
                            "properties": {
                                "relationship": relationship,
                                "source": "post_analysis",
                                "evidence": evidence,
                            },
                            "mention_count": 1,
                            "created_at": now,
                            "updated_at": now,
                        })
                        connections_written += 1

    # Update watermark
    if post_texts:
        await db.avatar_post_insights.update_one(
            {"user_id": user_id},
            {
                "$set": {"last_analyzed_post_date": post_texts[0]["date"]},
                "$setOnInsert": {"user_id": user_id},
            },
            upsert=True,
        )

    return {
        "analyzed": len(post_texts),
        "insights": len(all_insights),
        "connections": connections_written,
    }


async def _initialize_knowledge_gaps(db, user_id: str):
    """Stage 2: Initialize knowledge gap tracking with default questions."""
    import uuid

    DEFAULT_QUESTIONS = [
        {"question": "What got you into what you do for work?",
         "category": "life_narrative", "priority": 0.9,
         "natural_phrasing": "I was thinking... you've never really told me how you ended up doing what you do. What's the story there?"},
        {"question": "Tell me about where you grew up.",
         "category": "life_narrative", "priority": 0.85,
         "natural_phrasing": "Hey, I realized I don't really know where you grew up. What was that like?"},
        {"question": "What's the biggest turning point in your life so far?",
         "category": "life_narrative", "priority": 0.8,
         "natural_phrasing": "I've been wondering... if you had to pick one moment that really changed everything for you, what would it be?"},
        {"question": "What do you feel really strongly about?",
         "category": "values_beliefs", "priority": 0.85,
         "natural_phrasing": "What's something you feel really passionate about? Like something you'd defend no matter what?"},
        {"question": "What does success look like to you?",
         "category": "values_beliefs", "priority": 0.75,
         "natural_phrasing": "I'm curious... what does success actually mean to you? Like your version of it."},
        {"question": "How do you usually handle disagreements?",
         "category": "communication_style", "priority": 0.7,
         "natural_phrasing": "When someone says something you totally disagree with, what do you usually do? Speak up or let it go?"},
        {"question": "Would people describe you as funny?",
         "category": "humor_personality", "priority": 0.65,
         "natural_phrasing": "So... would your friends say you're the funny one in the group? What's your kind of humor?"},
        {"question": "Who are the people that matter most to you?",
         "category": "social_patterns", "priority": 0.8,
         "natural_phrasing": "Who are the people that really matter to you? Like, your inner circle."},
        {"question": "Do you prefer deep one-on-one conversations or group hangouts?",
         "category": "social_patterns", "priority": 0.6,
         "natural_phrasing": "Are you more of a one-on-one deep conversations person or do you thrive in group settings?"},
        {"question": "What genuinely makes you happy?",
         "category": "emotional_patterns", "priority": 0.85,
         "natural_phrasing": "What genuinely lights you up? Like, that thing that makes you forget about everything else."},
        {"question": "What frustrates you the most?",
         "category": "emotional_patterns", "priority": 0.7,
         "natural_phrasing": "Okay, real talk — what gets under your skin? What's the thing that just frustrates you?"},
        {"question": "How do you deal with tough times?",
         "category": "emotional_patterns", "priority": 0.65,
         "natural_phrasing": "When things get really tough, what do you do? Like, your go-to way of dealing with it."},
        {"question": "What could you talk about for hours?",
         "category": "interests_passions", "priority": 0.8,
         "natural_phrasing": "What's that thing you could talk about for hours without getting bored? Everyone has one."},
        {"question": "Is there something you're secretly nerdy about?",
         "category": "interests_passions", "priority": 0.6,
         "natural_phrasing": "Come on, tell me — what's your secret nerdy obsession? The thing most people don't know about?"},
        {"question": "What does a typical day look like for you?",
         "category": "daily_life", "priority": 0.7,
         "natural_phrasing": "Walk me through your typical day. Like, from when you wake up — what does it look like?"},
        {"question": "Are you a morning person or a night owl?",
         "category": "daily_life", "priority": 0.5,
         "natural_phrasing": "So are you an early riser or do you come alive at night? I feel like I should know this by now."},
    ]

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
    await db.avatar_knowledge_gaps.update_one(
        {"user_id": user_id},
        {"$setOnInsert": doc},
        upsert=True,
    )


async def _index_conversation(
    db, openai_client, user_id: str, avatar_id: str,
    session_id: str, s3_key: str, transcript_text: str, duration_seconds: int
) -> bool:
    """Stage 3: Use LLM to summarise & index a voice conversation."""
    try:
        # First run extraction to get topics/people
        extraction = await _run_extraction(openai_client, transcript_text)
        topics = [i.get("topic", "") for i in extraction.get("interests", []) if i.get("topic")]
        people = [p.get("name", "") for p in extraction.get("people", []) if p.get("name")]

        # Generate summary
        summary_prompt = f"""Summarize this conversation in 1-2 sentences (what was discussed, key points):
---
{transcript_text[:3000]}
---

Also extract 2-3 notable quotes from the USER (not the AI).

Return JSON:
{{"summary": "...", "key_quotes": ["...", "..."], "emotional_tone": "happy|sad|neutral|excited|contemplative|anxious"}}"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize conversations concisely."},
                {"role": "user", "content": summary_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        summary_data = json.loads(response.choices[0].message.content)

        doc = {
            "user_id": user_id,
            "avatar_id": avatar_id,
            "session_id": session_id,
            "s3_key": s3_key,
            "summary": summary_data.get("summary", ""),
            "topics": topics,
            "people_mentioned": people,
            "emotional_tone": summary_data.get("emotional_tone", "neutral"),
            "key_quotes": summary_data.get("key_quotes", []),
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc),
        }
        await db.conversation_index.update_one(
            {"session_id": session_id},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"      Indexing error: {e}")
        return False


async def _extract_personality(
    db, openai_client, user_id: str, transcript_text: str
) -> tuple:
    """Stage 4: Extract personality traits & values from a transcript."""
    traits_added = 0
    values_added = 0

    try:
        prompt = """You are a PERSONALITY EXTRACTION agent. Analyze this conversation to extract personality signals about the USER (not the AI).

Focus on:
1. TRAITS: How do they communicate? Are they direct/indirect? Confident/uncertain? Analytical/intuitive? Warm/reserved?
2. VALUES: What do they seem to care about? What priorities emerge?

IMPORTANT: Only extract what is CLEARLY demonstrated in the conversation. Don't infer from nothing.

Conversation:
---
{conversation}
---

Return JSON:
{{
  "traits": [
    {{"label": "trait name", "evidence": "brief quote/observation", "confidence": 0.0-1.0}}
  ],
  "values": [
    {{"label": "value name", "evidence": "brief observation", "confidence": 0.0-1.0}}
  ]
}}"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract personality signals precisely."},
                {"role": "user", "content": prompt.format(conversation=transcript_text[:4000])}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        result = json.loads(response.choices[0].message.content)
        now = datetime.now(timezone.utc)

        for trait in result.get("traits", []):
            if trait.get("confidence", 0) < 0.6:
                continue
            label = trait.get("label", "").lower().strip()
            if not label:
                continue

            existing = await db.graph_nodes.find_one({
                "user_id": user_id, "node_type": "trait", "label": label
            })
            if existing:
                await db.graph_nodes.update_one(
                    {"_id": existing["_id"]},
                    {"$inc": {"mention_count": 1}, "$set": {"updated_at": now}}
                )
            else:
                await db.graph_nodes.insert_one({
                    "id": f"trait_{user_id}_{label.replace(' ', '_')}",
                    "user_id": user_id,
                    "node_type": "trait",
                    "label": label,
                    "display_label": label.title(),
                    "strength": trait.get("confidence", 0.7),
                    "properties": {"evidence": trait.get("evidence", ""), "source": "conversation"},
                    "mention_count": 1,
                    "created_at": now,
                    "updated_at": now,
                })
            traits_added += 1

        for value in result.get("values", []):
            if value.get("confidence", 0) < 0.6:
                continue
            label = value.get("label", "").lower().strip()
            if not label:
                continue

            existing = await db.graph_nodes.find_one({
                "user_id": user_id, "node_type": "value", "label": label
            })
            if existing:
                await db.graph_nodes.update_one(
                    {"_id": existing["_id"]},
                    {"$inc": {"mention_count": 1}, "$set": {"updated_at": now}}
                )
            else:
                await db.graph_nodes.insert_one({
                    "id": f"value_{user_id}_{label.replace(' ', '_')}",
                    "user_id": user_id,
                    "node_type": "value",
                    "label": label,
                    "display_label": label.title(),
                    "strength": value.get("confidence", 0.7),
                    "properties": {"evidence": value.get("evidence", ""), "source": "conversation"},
                    "mention_count": 1,
                    "created_at": now,
                    "updated_at": now,
                })
            values_added += 1

    except Exception as e:
        logger.error(f"      Personality extraction error: {e}")

    return traits_added, values_added


async def _run_extraction(openai_client, conversation: str) -> Dict[str, Any]:
    """Run the extraction agent to get entities from a conversation."""
    prompt = """You are an EXTRACTION agent. Extract entities mentioned in the conversation.

Extract:
1. PEOPLE - Anyone mentioned (name, relationship to user)
2. INTERESTS - Topics, hobbies, activities the user expresses interest in
3. FACTS - Factual information about the user

Conversation:
---
{conversation}
---

Return JSON:
{{
  "people": [{{"name": "...", "relationship": "..."}}],
  "interests": [{{"topic": "..."}}],
  "facts": [{{"fact": "..."}}]
}}"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract entities precisely."},
                {"role": "user", "content": prompt.format(conversation=conversation[:3000])}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"      Extraction error: {e}")
        return {}


async def _update_knowledge_gap_coverage(db, user_id: str, conversation: str):
    """Update knowledge gap coverage scores based on conversation content."""
    category_keywords = {
        "life_narrative": ["grew up", "childhood", "story", "career", "history", "started"],
        "values_beliefs": ["believe", "important", "value", "passionate", "feel strongly"],
        "communication_style": ["disagree", "argue", "conflict", "express"],
        "social_patterns": ["friends", "family", "people", "inner circle", "social"],
        "interests_passions": ["love", "hobby", "passionate", "obsessed", "into"],
        "emotional_patterns": ["happy", "frustrated", "upset", "excited", "anxious"],
        "daily_life": ["morning", "routine", "typical day", "everyday", "wake up"],
        "humor_personality": ["funny", "joke", "laugh", "humor", "silly"],
    }

    conv_lower = conversation.lower()
    for category, keywords in category_keywords.items():
        if any(kw in conv_lower for kw in keywords):
            field = f"coverage_scores.{category}"
            doc = await db.avatar_knowledge_gaps.find_one(
                {"user_id": user_id}, {field: 1}
            )
            current = 0.1
            if doc:
                current = doc.get("coverage_scores", {}).get(category, 0.1)
            new_val = min(1.0, current + 0.05)
            await db.avatar_knowledge_gaps.update_one(
                {"user_id": user_id},
                {"$set": {field: new_val}},
                upsert=True,
            )

    # Increment conversation count
    await db.avatar_knowledge_gaps.update_one(
        {"user_id": user_id},
        {"$inc": {"conversations_since_last_question": 1}},
        upsert=True,
    )


async def _generate_personality_prompt(db, user_id: str) -> str:
    """Stage 5: Generate full personality prompt from all data sources."""
    try:
        # Fetch everything in parallel
        (
            graph_ctx,
            user_doc,
            identity_mem,
            recent_posts,
            connections,
            style_profile,
            episodic_summary,
        ) = await asyncio.gather(
            _get_graph_context(db, user_id),
            _get_user_document(db, user_id),
            _get_identity_memory(db, user_id),
            _get_recent_posts(db, user_id, limit=30),
            _get_all_connections(db, user_id),
            _get_style_profile(db, user_id),
            _get_episodic_summary(db, user_id),
            return_exceptions=False,
        )

        sections: List[str] = []

        # 1. Who this person is
        if user_doc:
            parts = []
            for key in ["name", "bio", "job_title", "avatar_job_title", "location", "avatar_location", "age"]:
                v = user_doc.get(key)
                if v:
                    label = key.replace("avatar_", "").replace("_", " ").title()
                    parts.append(f"  {label}: {v}")
            if parts:
                sections.append("**Who they are:**\n" + "\n".join(parts))

        # 2. Interests
        interests = graph_ctx.get("interests", [])
        profile_interests = user_doc.get("interests", []) if user_doc else []
        seen = {i.get("label", "").lower() for i in interests}
        for pi in profile_interests:
            if isinstance(pi, str) and pi.lower() not in seen:
                interests.append({"label": pi, "strength": 0.6})
                seen.add(pi.lower())
        if interests:
            core = [i for i in interests if i.get("strength", 0) >= 0.8]
            strong = [i for i in interests if 0.5 <= i.get("strength", 0) < 0.8]
            casual = [i for i in interests if i.get("strength", 0) < 0.5]
            lines = ["**Their interests:**"]
            if core:
                lines.append(f"  Core passions: {', '.join(i.get('label', '') for i in core)}")
            if strong:
                lines.append(f"  Strong interests: {', '.join(i.get('label', '') for i in strong)}")
            if casual:
                lines.append(f"  Also into: {', '.join(i.get('label', '') for i in casual[:15])}")
            sections.append("\n".join(lines))

        # 3. Traits & values
        traits = graph_ctx.get("traits", [])
        values = graph_ctx.get("values", [])
        if traits or values:
            lines = ["**Personality traits & values:**"]
            if traits:
                lines.append(f"  Traits: {', '.join(t.get('label', '') for t in traits[:10])}")
            if values:
                lines.append(f"  Values: {', '.join(v.get('label', '') for v in values[:10])}")
            sections.append("\n".join(lines))

        # 4. Connections
        if connections:
            family_kw = {"wife", "husband", "daughter", "son", "mother", "father",
                         "sister", "brother", "parent", "child", "spouse", "partner", "mom", "dad"}
            friend_kw = {"friend", "best friend", "close friend", "buddy", "pal"}
            work_kw = {"colleague", "coworker", "boss", "manager", "teammate", "mentor"}

            def classify(c):
                r = (c.get("relationship") or "").lower()
                if any(k in r for k in family_kw):
                    return "family"
                if any(k in r for k in friend_kw):
                    return "friends"
                if any(k in r for k in work_kw):
                    return "work"
                return "other"

            groups = {"family": [], "friends": [], "work": [], "other": []}
            for c in connections:
                groups[classify(c)].append(c)

            lines = ["**People in their life:**"]
            for label, members in [("Family", groups["family"]), ("Friends", groups["friends"]),
                                   ("Work", groups["work"]), ("Others", groups["other"])]:
                if members:
                    parts = []
                    for m in members:
                        entry = f"{m.get('name', '')} ({m.get('relationship', '')})" if m.get('relationship') else m.get('name', '')
                        if m.get('details'):
                            entry += f" — {m.get('details')}"
                        parts.append(entry)
                    lines.append(f"  {label}: {', '.join(parts)}")
            sections.append("\n".join(lines))

        # 5. Communication style
        style_lines = ["**How they communicate:**"]
        has_style = False
        if style_profile:
            avg_len = style_profile.get("avg_post_length")
            if avg_len:
                style_lines.append(f"  Average post length: ~{int(avg_len)} words")
                has_style = True
            tone = style_profile.get("tone_distribution", {})
            if tone:
                dominant = max(tone, key=tone.get)
                style_lines.append(f"  Dominant tone: {dominant}")
                has_style = True
            phrases = style_profile.get("common_phrases", [])
            if phrases:
                style_lines.append(f"  Phrases they use: {', '.join(phrases[:8])}")
                has_style = True
            emoji_freq = style_profile.get("emoji_frequency")
            if emoji_freq is not None:
                if emoji_freq > 0.5:
                    style_lines.append("  Uses emojis frequently")
                elif emoji_freq < 0.1:
                    style_lines.append("  Rarely uses emojis")
                has_style = True
        if recent_posts:
            samples = [p.get("text", "") for p in recent_posts[:5] if p.get("text")]
            if samples:
                style_lines.append("  Recent post examples (match this voice):")
                for s in samples:
                    truncated = s[:200] + ("..." if len(s) > 200 else "")
                    style_lines.append(f'    "{truncated}"')
                has_style = True
        if has_style:
            sections.append("\n".join(style_lines))

        # 6. Facts & preferences
        facts = identity_mem.get("facts", []) if identity_mem else []
        prefs = identity_mem.get("preferences", []) if identity_mem else []
        if facts or prefs:
            lines = ["**Things known about them (from conversations):**"]
            for f in facts[:15]:
                ft = f.get("fact", "") if isinstance(f, dict) else str(f)
                if ft:
                    lines.append(f"  - {ft}")
            for p in prefs[:10]:
                pt = p.get("preference", "") if isinstance(p, dict) else str(p)
                if pt:
                    lines.append(f"  - Preference: {pt}")
            if len(lines) > 1:
                sections.append("\n".join(lines))

        # 7. Emotional patterns
        if episodic_summary:
            trend = episodic_summary.get("emotional_trend", "stable")
            avg = episodic_summary.get("avg_emotional_valence", 0)
            highlights = episodic_summary.get("recent_highlights", [])
            if highlights or avg != 0:
                lines = ["**Recent emotional patterns:**"]
                lines.append(f"  Trend: {trend}")
                if avg > 0.3:
                    lines.append("  Generally in a positive state recently")
                elif avg < -0.3:
                    lines.append("  Has been going through a tougher time recently")
                if highlights:
                    lines.append("  Recent positive moments: " + ", ".join(
                        h.get("type", "") for h in highlights[:3]
                    ))
                sections.append("\n".join(lines))

        personality_prompt = "\n\n".join(sections)

        # Cache it
        cache_doc = {
            "user_id": user_id,
            "personality_prompt": personality_prompt,
            "generated_at": datetime.now(timezone.utc),
            "generation_sources": {
                "graph_nodes_count": sum(len(v) for v in graph_ctx.values()) if isinstance(graph_ctx, dict) else 0,
                "connections_count": len(connections) if connections else 0,
                "has_style_profile": style_profile is not None,
            }
        }
        await db.avatar_personality_prompts.update_one(
            {"user_id": user_id}, {"$set": cache_doc}, upsert=True
        )
        return personality_prompt

    except Exception as e:
        logger.error(f"Personality prompt generation error: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# DATA FETCHING HELPERS (for personality prompt)
# ═══════════════════════════════════════════════════════════════════════════

async def _get_graph_context(db, user_id: str) -> Dict[str, Any]:
    cursor = db.graph_nodes.find(
        {"user_id": user_id},
        {"_id": 0, "node_type": 1, "label": 1, "strength": 1, "properties": 1, "mention_count": 1}
    ).sort("strength", -1).limit(200)
    nodes = await cursor.to_list(200)
    organized = {"interests": [], "traits": [], "values": [], "preferences": [], "experiences": [], "connections": []}
    for n in nodes:
        ntype = n.get("node_type", "interest")
        bucket = organized.get(ntype, organized.get("interests"))
        if bucket is not None:
            bucket.append(n)
    return organized


async def _get_user_document(db, user_id: str) -> Dict[str, Any]:
    return await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "name": 1, "bio": 1, "interests": 1,
         "avatar_name": 1, "avatar_bio": 1, "avatar_interests": 1,
         "job_title": 1, "avatar_job_title": 1,
         "location": 1, "avatar_location": 1, "age": 1}
    ) or {}


async def _get_identity_memory(db, user_id: str) -> Dict[str, Any]:
    return await db.identity_memory.find_one(
        {"user_id": user_id}, {"_id": 0}
    ) or {}


async def _get_recent_posts(db, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    cursor = db.posts.find(
        {"user_id": user_id, "post_type": {"$in": ["real", None]}},
        {"_id": 0, "text": 1, "created_at": 1, "likes": 1, "comment_count": 1}
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)


async def _get_all_connections(db, user_id: str) -> List[Dict[str, Any]]:
    user = await db.users.find_one({"id": user_id}, {"connections": 1})
    return user.get("connections", []) if user else []


async def _get_style_profile(db, user_id: str) -> Optional[Dict[str, Any]]:
    return await db.avatar_style_profiles.find_one(
        {"user_id": user_id}, {"_id": 0}
    )


async def _get_episodic_summary(db, user_id: str) -> Dict[str, Any]:
    """Build a simple emotional summary from recent episodic memories."""
    try:
        cursor = db.episodic_memory.find(
            {"user_id": user_id, "episode_type": "voice_conversation"},
            {"_id": 0, "emotional_tone": 1, "significance": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(10)
        episodes = await cursor.to_list(10)

        if not episodes:
            return {}

        # Simple emotional valence mapping
        valence_map = {
            "happy": 0.8, "excited": 0.9, "neutral": 0.0,
            "contemplative": 0.1, "sad": -0.6, "anxious": -0.4,
        }
        tones = [e.get("emotional_tone", "neutral") for e in episodes]
        avg_valence = sum(valence_map.get(t, 0) for t in tones) / max(len(tones), 1)

        trend = "stable"
        if avg_valence > 0.3:
            trend = "positive"
        elif avg_valence < -0.3:
            trend = "challenging"

        return {
            "emotional_trend": trend,
            "avg_emotional_valence": round(avg_valence, 2),
            "recent_highlights": [],
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(main())
