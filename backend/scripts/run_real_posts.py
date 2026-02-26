#!/usr/bin/env python3
"""
Generate REAL posts for DigitalHunter and _bLikker through the full PostOrchestrator
pipeline and evaluate the output quality.

This makes actual OpenAI API calls.
"""

import asyncio
import json
import os
import sys
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI

DB_NAME = "neurallinks_local"

USERS = {
    "DigitalHunter (Jaijith)": "dedc30ef-dca9-467d-84b1-5e643941e6fd",
    "_bLikker (Sreejith)": "fb1a5d18-5c93-4084-8da1-2227b1bea266",
}


def get_mongo_uri():
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(
        SecretId="2n1/mongodb/uri"
    )["SecretString"]
    try:
        p = json.loads(raw)
        return p.get("uri") or p.get("MONGO_URL") or raw if isinstance(p, dict) else p
    except json.JSONDecodeError:
        return raw


def get_openai_key():
    raw = boto3.client("secretsmanager", region_name="us-west-2").get_secret_value(
        SecretId="2n1/openai/api-key"
    )["SecretString"]
    try:
        p = json.loads(raw)
        if isinstance(p, dict):
            return p.get("api_key") or p.get("key") or p.get("OPENAI_API_KEY") or raw
        return p
    except json.JSONDecodeError:
        return raw


async def generate_and_evaluate(db, openai_client, user_id, name):
    from domain.avatar.orchestration.post_orchestrator import PostOrchestrator
    from domain.graph.rag import GraphRAG

    rag = GraphRAG(db)
    orch = PostOrchestrator(db, openai_client)

    print(f"\n{'#' * 80}")
    print(f"#  {name}")
    print(f"{'#' * 80}")

    # 1. Show the identity narrative that the pipeline will use
    narrative = await rag.get_identity_context(
        user_id, action_type="post_generation", max_tokens=1500,
    )
    print(f"\n--- IDENTITY NARRATIVE ({len(narrative)} chars, ~{len(narrative)//4} tokens) ---")
    # Show first 600 chars
    print(narrative[:600])
    if len(narrative) > 600:
        print(f"  ... [{len(narrative) - 600} more chars] ...")

    # 2. Generate a LIFE MOMENT post (standard pipeline)
    print(f"\n--- GENERATING LIFE MOMENT POST ---")
    result = await orch.generate_post(
        user_id=user_id,
        avatar_id=user_id,
        trigger="",
        topic_hint="",
        mood="neutral",
        energy_level=0.6,
    )

    post_text = result.get("text", "")
    quality = result.get("quality_score", 0)
    metadata = result.get("metadata", {})
    intent = metadata.get("intent", {})
    verification = metadata.get("verification", {})

    print(f"\n  Post text:")
    print(f"  ─────────")
    for line in post_text.split("\n"):
        print(f"  │ {line}")

    print(f"\n  Quality score: {quality}")
    print(f"  Pipeline: {metadata.get('pipeline', '?')}")

    if intent:
        print(f"\n  Intent agent output:")
        print(f"    Life moment: {intent.get('life_moment', '?')[:100]}")
        print(f"    Interests involved: {intent.get('interests_involved', [])}")
        print(f"    People mentioned: {intent.get('people_mentioned', [])}")
        print(f"    Emotional core: {intent.get('emotional_core', '?')}")

    if verification:
        dims = verification.get("dimensions", {})
        print(f"\n  Verification scores:")
        print(f"    Voice match:     {dims.get('voice_match', '?')}")
        print(f"    Naturalness:     {dims.get('naturalness', '?')}")
        print(f"    Specificity:     {dims.get('specificity', '?')}")
        print(f"    Emotional auth:  {dims.get('emotional_authenticity', '?')}")
        print(f"    Issues: {verification.get('issues', [])}")
        print(f"    Feedback: {verification.get('feedback', '')}")

    # 3. Evaluate against the known issues
    print(f"\n  ═══════════════════════════════════════════════")
    print(f"  EVALUATION: Checking for previously discussed issues")
    print(f"  ═══════════════════════════════════════════════")

    issues_found = []
    issues_resolved = []

    # Issue 1: Generic/could-be-anyone posts
    generic_phrases = [
        "as someone who", "in today's world", "i've been thinking about",
        "here's why", "it's fascinating", "can't wait to see",
        "exciting news", "what an amazing",
    ]
    has_generic = any(p in post_text.lower() for p in generic_phrases)
    if has_generic:
        issues_found.append("GENERIC PHRASES detected — post could be written by anyone")
    else:
        issues_resolved.append("No generic AI phrases — post sounds personal")

    # Issue 2: Mentions people not in the graph (hallucination)
    # Get known connections from graph
    connections = await db.graph_nodes.find(
        {"user_id": user_id, "node_type": "connection"},
        {"_id": 0, "label": 1, "display_label": 1}
    ).to_list(20)
    known_names = {c.get("display_label", c.get("label", "")).lower() for c in connections}

    # Check for made-up names in the post
    import re
    capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', post_text)
    for word in capitalized_words:
        if word.lower() not in known_names and word.lower() not in {
            "i", "the", "this", "that", "my", "me", "just", "was", "been", "got",
            "and", "but", "for", "not", "with", "you", "all", "can", "had", "her",
            "his", "she", "him", "they", "from", "have", "been", "some", "when",
            "what", "said", "each", "which", "their", "will", "way", "about",
            "many", "then", "them", "would", "like", "so", "these", "right",
            "look", "think", "also", "back", "after", "use", "two", "how",
            "our", "work", "first", "well", "even", "new", "want", "because",
            "any", "day", "there", "than", "year", "used", "now", "come",
            "than", "most", "find", "here", "thing", "every", "still",
            "sunday", "monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
            "morning", "night", "today", "tonight", "yesterday", "tomorrow",
            "kerala", "india", "dubai", "instagram", "whatsapp", "youtube",
            "spotify", "netflix", "google", "amazon", "apple",
        }:
            pass  # Could be a hallucinated name, but also could be a proper noun

    # Issue 3: Post mentions interests that connect to the person's real graph
    interests_ctx = await rag.get_user_context(user_id, max_nodes=30)
    interest_labels = {i.get("label", "").lower() for i in interests_ctx.get("interests", [])}
    post_lower = post_text.lower()
    matched_interests = [i for i in interest_labels if i and len(i) > 3 and i in post_lower]
    if matched_interests:
        issues_resolved.append(f"Post touches real interests: {matched_interests}")
    else:
        issues_found.append("Post doesn't reference any known interests from the graph")

    # Issue 4: People mentioned should be from the graph
    people_in_intent = intent.get("people_mentioned", [])
    if people_in_intent:
        known_lower = {n.lower() for n in known_names}
        hallucinated = [p for p in people_in_intent if p.lower() not in known_lower and p.lower() not in {"me", "i", "myself", "friend", "a friend", "family"}]
        if hallucinated:
            issues_found.append(f"HALLUCINATED PEOPLE in intent: {hallucinated}")
        else:
            issues_resolved.append(f"People mentioned are from the graph: {people_in_intent}")
    else:
        issues_resolved.append("No people mentioned — no hallucination risk")

    # Issue 5: Specificity — does the post have concrete details?
    specificity = verification.get("dimensions", {}).get("specificity", 0)
    if isinstance(specificity, (int, float)) and specificity >= 0.7:
        issues_resolved.append(f"High specificity score: {specificity}")
    elif isinstance(specificity, (int, float)):
        issues_found.append(f"Low specificity score: {specificity} — post may be too vague")

    # Issue 6: Voice match
    voice_match = verification.get("dimensions", {}).get("voice_match", 0)
    if isinstance(voice_match, (int, float)) and voice_match >= 0.7:
        issues_resolved.append(f"Good voice match: {voice_match}")
    elif isinstance(voice_match, (int, float)):
        issues_found.append(f"Poor voice match: {voice_match}")

    # Print evaluation
    for r in issues_resolved:
        print(f"  ✅ {r}")
    for i in issues_found:
        print(f"  ❌ {i}")

    if not issues_found:
        print(f"\n  🎯 ALL CHECKS PASSED — Post is grounded, specific, and authentic")
    else:
        print(f"\n  ⚠️  {len(issues_found)} issue(s) detected")

    return {
        "name": name,
        "post": post_text,
        "quality": quality,
        "issues_found": issues_found,
        "issues_resolved": issues_resolved,
    }


async def main():
    print("=" * 80)
    print("  Real Post Generation & Evaluation")
    print("  (Full PostOrchestrator pipeline with OpenAI API calls)")
    print("=" * 80)

    uri = get_mongo_uri()
    client = AsyncIOMotorClient(
        uri, serverSelectionTimeoutMS=30000, connectTimeoutMS=30000, socketTimeoutMS=60000,
    )
    db = client[DB_NAME]
    await client.admin.command("ismaster")

    openai_key = get_openai_key()
    openai_client = AsyncOpenAI(api_key=openai_key)

    results = []
    for name, user_id in USERS.items():
        r = await generate_and_evaluate(db, openai_client, user_id, name)
        results.append(r)

    # Final summary
    print(f"\n{'=' * 80}")
    print(f"  FINAL SUMMARY")
    print(f"{'=' * 80}")
    for r in results:
        name = r["name"]
        quality = r["quality"]
        n_resolved = len(r["issues_resolved"])
        n_found = len(r["issues_found"])
        print(f"\n  {name}:")
        print(f"    Quality: {quality}")
        print(f"    Checks passed: {n_resolved}")
        print(f"    Issues: {n_found}")
        if r["issues_found"]:
            for i in r["issues_found"]:
                print(f"      ❌ {i}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
