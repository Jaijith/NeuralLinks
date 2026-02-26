#!/usr/bin/env python3
"""
One-time graph cleanup & augmentation for DigitalHunter (Jaijith).

Phases:
  0 — Backup existing graph data to JSON
  1 — Collect ALL evidence (S3 transcripts, posts, profile, memories)
  2 — LLM-powered comprehensive identity extraction & synthesis
  3 — Node cleanup (dedup, fix labels, remove garbage)
  4 — Node augmentation (add missing, enrich with evidence)
  5 — Edge rebuilding (meaningful cross-type relationships)
  6 — Validation & cache invalidation

Usage:
  python cleanup_graph_digitalhunter.py            # dry-run (preview changes)
  python cleanup_graph_digitalhunter.py --live      # apply changes
  python cleanup_graph_digitalhunter.py --model gpt-4.1-mini  # use specific model
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import traceback
import uuid as uuid_mod
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("graph_cleanup")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

USER_ID = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
USER_NAME = "Jaijith"
AVATAR_NAME = "DigitalHunter"
DB_NAME = "neurallinks_local"
S3_BUCKET = "2n1-uploads-019396192218"
S3_REGION = "us-west-2"
SECRETS_REGION = "us-west-2"
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")

# Set via CLI args
DRY_RUN = True
LLM_MODEL = "gpt-4o"


# ═══════════════════════════════════════════════════════════════════════════════
# AWS / S3 / LLM HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_secret(secret_name: str):
    """Fetch from AWS Secrets Manager, handling both JSON-object and plain-string secrets."""
    import boto3
    client = boto3.client("secretsmanager", region_name=SECRETS_REGION)
    raw = client.get_secret_value(SecretId=secret_name)["SecretString"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def get_mongo_uri() -> str:
    secret = get_secret("2n1/mongodb/uri")
    if isinstance(secret, dict):
        return secret.get("uri") or secret.get("MONGO_URL") or secret.get("connection_string", "")
    return secret


def get_openai_key() -> str:
    secret = get_secret("2n1/openai/api-key")
    if isinstance(secret, dict):
        return secret.get("api_key") or secret.get("key") or secret.get("OPENAI_API_KEY", "")
    return secret


def fetch_transcript_from_s3(s3_client, s3_key: str) -> Optional[str]:
    """Download a voice transcript from S3, return formatted user/avatar dialogue."""
    try:
        body = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)["Body"].read().decode("utf-8")
        data = json.loads(body)
        lines = []
        for msg in data.get("messages", []):
            role = msg.get("role", "unknown")
            text = msg.get("text", msg.get("content", ""))
            if text:
                speaker = "User" if role in ("user", "human") else "Avatar"
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning(f"  S3 fetch failed for {s3_key}: {exc}")
        return None


async def call_llm(
    client,
    prompt: str,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """Call LLM with retry + back-off. Handles both chat-completions and responses API."""
    for attempt in range(retries):
        try:
            if "gpt-5" in LLM_MODEL.lower():
                resp = await client.responses.create(model=LLM_MODEL, input=prompt)
                return (resp.output_text or "").strip()
            else:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                resp = await client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            err = str(exc).lower()
            if "rate" in err or "429" in err:
                wait = (attempt + 1) * 5
                logger.warning(f"  Rate-limited, waiting {wait}s (attempt {attempt+1}/{retries})")
                await asyncio.sleep(wait)
            elif attempt < retries - 1:
                logger.warning(f"  LLM call failed (attempt {attempt+1}): {exc}")
                await asyncio.sleep(2)
            else:
                raise
    return ""


def parse_json_response(text: str) -> Any:
    """Robustly extract JSON from an LLM response."""
    text = text.strip()
    # Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Markdown fences
    for fence in ("```json", "```"):
        if fence in text:
            extracted = text.split(fence, 1)[1].rsplit("```", 1)[0].strip()
            try:
                return json.loads(extracted)
            except (json.JSONDecodeError, ValueError):
                pass
    # Find outermost JSON structure
    for open_ch, close_ch in [("[", "]"), ("{", "}")]:
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
    raise ValueError(f"Could not parse JSON from: {text[:300]}...")


# ═══════════════════════════════════════════════════════════════════════════════
# NODE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

_PREFIX_STRIP = sorted(
    [
        "interest:youtube_channel_",
        "interest:youtube_",
        "interest:",
        "trait:",
        "value:",
        "preference:",
        "experience:",
        "music:",
        "skill:",
    ],
    key=len,
    reverse=True,
)


def normalize_label(label: str) -> str:
    """Strip type-prefixes, underscores, extra whitespace."""
    label = label.strip().lower()
    for prefix in _PREFIX_STRIP:
        if label.startswith(prefix):
            label = label[len(prefix) :].strip()
            break
    label = label.replace("_", " ").strip()
    label = re.sub(r"\s+", " ", label)
    return label


def is_garbage_node(label: str, node_type: str = "") -> bool:
    if len(label) < 2:
        return True
    if label in ("?", "unknown", "none", "n/a", "null", "undefined", "nan", "-"):
        return True
    if len(label) > 150:
        return True
    return False


def make_node_id(node_type: str, label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower().strip())[:50].strip("_")
    return f"{node_type}_{USER_ID}_{slug}"


def calculate_strength(mention_count: int, source_count: int, from_profile: bool = False) -> float:
    strength = 0.3 + 0.08 * mention_count + 0.05 * source_count
    if from_profile:
        strength += 0.15
    if mention_count >= 5:
        strength += 0.10
    return round(min(1.0, strength), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 0 — BACKUP
# ═══════════════════════════════════════════════════════════════════════════════

async def phase0_backup(db) -> Tuple[List[Dict], List[Dict]]:
    logger.info("=" * 70)
    logger.info("  PHASE 0: Backing up existing graph data")
    logger.info("=" * 70)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)
    node_ids = [n.get("id", "") for n in nodes if n.get("id")]

    edges = await db.graph_edges.find(
        {
            "$or": [
                {"user_id": USER_ID},
                {"from_node_id": {"$in": node_ids}},
                {"to_node_id": {"$in": node_ids}},
            ]
        },
        {"_id": 0},
    ).to_list(10000)

    nodes_path = os.path.join(BACKUP_DIR, f"graph_nodes_{ts}.json")
    edges_path = os.path.join(BACKUP_DIR, f"graph_edges_{ts}.json")

    with open(nodes_path, "w") as f:
        json.dump(nodes, f, indent=2, default=str)
    with open(edges_path, "w") as f:
        json.dump(edges, f, indent=2, default=str)

    logger.info(f"  Backed up {len(nodes)} nodes -> {nodes_path}")
    logger.info(f"  Backed up {len(edges)} edges -> {edges_path}")
    return nodes, edges


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — EVIDENCE COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════

async def phase1_collect_evidence(db, s3_client) -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("  PHASE 1: Collecting ALL evidence")
    logger.info("=" * 70)

    evidence: Dict[str, Any] = {}

    # 1. S3 voice transcripts
    logger.info("  [1/8] Fetching voice transcripts from S3...")
    transcript_metas = await db.voice_transcripts.find(
        {"user_id": USER_ID}, {"_id": 0}
    ).to_list(1000)

    transcripts: List[Dict] = []
    for meta in transcript_metas:
        s3_key = meta.get("s3_key", "")
        if not s3_key:
            continue
        text = await asyncio.to_thread(fetch_transcript_from_s3, s3_client, s3_key)
        if text and len(text.strip()) > 50:
            transcripts.append(
                {
                    "session_id": meta.get("session_id", ""),
                    "text": text,
                    "created_at": str(meta.get("created_at", "")),
                    "duration_seconds": meta.get("duration_seconds", 0),
                }
            )
    logger.info(f"        {len(transcripts)} of {len(transcript_metas)} transcripts fetched from S3")
    evidence["transcripts"] = transcripts

    # 2. Conversation index
    logger.info("  [2/8] Fetching conversation index...")
    conv_index = await db.conversation_index.find(
        {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}, {"_id": 0}
    ).to_list(1000)
    logger.info(f"        {len(conv_index)} entries")
    evidence["conversation_index"] = conv_index

    # 3. Real posts
    logger.info("  [3/8] Fetching real posts...")
    posts = (
        await db.posts.find(
            {"user_id": USER_ID, "post_type": {"$in": ["real", None]}},
            {"_id": 0, "text": 1, "content": 1, "created_at": 1, "timestamp": 1},
        )
        .sort("created_at", -1)
        .to_list(500)
    )
    logger.info(f"        {len(posts)} real posts")
    evidence["posts"] = posts

    # 4. User profile
    logger.info("  [4/8] Fetching user profile...")
    user = await db.users.find_one({"id": USER_ID}, {"_id": 0})
    evidence["user_profile"] = user or {}
    logger.info(f"        Profile: {user.get('name', '?') if user else 'NOT FOUND'}")

    # 5. Identity memory
    logger.info("  [5/8] Fetching identity memory...")
    identity = await db.identity_memory.find(
        {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}, {"_id": 0}
    ).to_list(100)
    logger.info(f"        {len(identity)} entries")
    evidence["identity_memory"] = identity

    # 6. Bond moments + reflections
    logger.info("  [6/8] Fetching bond moments & reflections...")
    user_or_avatar = {"$or": [{"user_id": USER_ID}, {"avatar_id": USER_ID}]}
    bond_moments = await db.bond_moments.find(user_or_avatar, {"_id": 0}).to_list(500)
    reflections = await db.reflection_logs.find(user_or_avatar, {"_id": 0}).to_list(500)
    logger.info(f"        Bond moments: {len(bond_moments)}, Reflections: {len(reflections)}")
    evidence["bond_moments"] = bond_moments
    evidence["reflections"] = reflections

    # 7. Episodic memory
    logger.info("  [7/8] Fetching episodic memory...")
    episodic = await db.episodic_memory.find(user_or_avatar, {"_id": 0}).to_list(500)
    logger.info(f"        {len(episodic)} entries")
    evidence["episodic_memory"] = episodic

    # 8. Existing graph nodes (snapshot for comparison)
    logger.info("  [8/8] Snapshotting current graph nodes...")
    existing = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)
    logger.info(f"        {len(existing)} existing nodes")
    evidence["existing_nodes"] = existing

    return evidence


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — LLM IDENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

_TRANSCRIPT_EXTRACTION_PROMPT = """Analyze this conversation between a User ({user_name}) and his AI Avatar.
Extract ONLY information about the USER — identity, personality, interests, values, experiences, connections, preferences.
Do NOT extract anything about the avatar's behavior or responses.

Conversation (session: {session_id}, date: {date}):
---
{text}
---

Return a JSON object with these arrays (each item must have a "label" and "evidence" quote):
{{
  "interests": [{{"label": "short label", "evidence": "exact quote or paraphrase", "intensity": "core|strong|casual"}}],
  "traits": [{{"label": "trait name", "evidence": "supporting quote", "confidence": 0.8}}],
  "values": [{{"label": "value name", "evidence": "supporting quote", "confidence": 0.8}}],
  "experiences": [{{"label": "experience", "details": "context", "evidence": "quote"}}],
  "preferences": [{{"label": "preference", "details": "specifics", "evidence": "quote"}}],
  "connections": [{{"name": "person name", "relationship": "type", "details": "context", "evidence": "quote"}}],
  "demographics": [{{"category": "category", "value": "value", "evidence": "quote"}}]
}}

Be thorough — extract everything the user reveals about themselves.
Only include items with clear evidence. Return ONLY valid JSON."""

_POST_EXTRACTION_PROMPT = """Analyze these social media posts written by {user_name}.
Extract identity information about the AUTHOR — interests, traits, values, experiences, connections, preferences.

Posts:
---
{text}
---

Return a JSON object:
{{
  "interests": [{{"label": "short label", "evidence": "which post", "intensity": "core|strong|casual"}}],
  "traits": [{{"label": "trait", "evidence": "which post", "confidence": 0.8}}],
  "values": [{{"label": "value", "evidence": "which post", "confidence": 0.8}}],
  "experiences": [{{"label": "experience", "details": "context", "evidence": "which post"}}],
  "preferences": [{{"label": "preference", "details": "specifics", "evidence": "which post"}}],
  "connections": [{{"name": "person name", "relationship": "type", "details": "context", "evidence": "which post"}}]
}}

Return ONLY valid JSON."""


def _merge_identity_facts(all_facts: List[Dict]) -> Dict[str, Dict[str, Dict]]:
    """Deduplicate & score identity facts across all sources."""
    merged: Dict[str, Dict[str, Dict]] = {
        "interests": {},
        "traits": {},
        "values": {},
        "experiences": {},
        "preferences": {},
        "connections": {},
        "demographics": {},
    }

    for facts in all_facts:
        for category in merged:
            items = facts.get(category, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if category == "connections":
                    raw_label = item.get("name", "").strip()
                elif category == "demographics":
                    raw_label = f"{item.get('category', '')}:{item.get('value', '')}".strip()
                else:
                    raw_label = item.get("label", "").strip()

                norm = normalize_label(raw_label)
                if not norm or len(norm) < 2:
                    continue

                if norm not in merged[category]:
                    merged[category][norm] = {
                        "label": norm,
                        "display_label": raw_label.strip(),
                        "evidence_sources": [],
                        "evidence_quotes": [],
                        "mention_count": 0,
                        "first_mentioned": "",
                        "last_mentioned": "",
                        "details": "",
                        "intensity": "casual",
                        "max_confidence": 0.5,
                        "relationship": "",
                    }

                entry = merged[category][norm]
                entry["mention_count"] += 1

                src = f"{item.get('source_type', 'unknown')}:{item.get('source_id', '')}"
                if src not in entry["evidence_sources"]:
                    entry["evidence_sources"].append(src)

                ev = item.get("evidence", "")
                if ev and len(entry["evidence_quotes"]) < 10:
                    entry["evidence_quotes"].append(ev[:200])

                date = item.get("source_date", "")
                if date:
                    if not entry["first_mentioned"] or date < entry["first_mentioned"]:
                        entry["first_mentioned"] = date
                    if not entry["last_mentioned"] or date > entry["last_mentioned"]:
                        entry["last_mentioned"] = date

                if item.get("details") and len(item["details"]) > len(entry["details"]):
                    entry["details"] = item["details"]
                if category == "connections" and item.get("relationship") and item["relationship"] != "mentioned":
                    entry["relationship"] = item["relationship"]

                intensity_rank = {"core": 3, "strong": 2, "casual": 1}
                if intensity_rank.get(item.get("intensity", ""), 0) > intensity_rank.get(entry["intensity"], 0):
                    entry["intensity"] = item["intensity"]
                if item.get("confidence", 0) > entry["max_confidence"]:
                    entry["max_confidence"] = item["confidence"]

    # Calculate evidence-based strength
    for category in merged:
        for norm, entry in merged[category].items():
            from_profile = any("profile" in s for s in entry["evidence_sources"])
            entry["strength"] = calculate_strength(
                entry["mention_count"], len(entry["evidence_sources"]), from_profile
            )

    return merged


async def phase2_extract_identity(openai_client, evidence: Dict) -> Dict:
    logger.info("=" * 70)
    logger.info("  PHASE 2: LLM-powered identity extraction")
    logger.info("=" * 70)

    all_facts: List[Dict] = []

    # ── 2a. Process voice transcripts ─────────────────────────────────────
    transcripts = evidence.get("transcripts", [])
    logger.info(f"  [2a] Processing {len(transcripts)} voice transcripts...")

    for i, t in enumerate(transcripts):
        text = t["text"]
        if len(text) > 15000:
            text = text[:15000] + "\n...[truncated]..."

        prompt = _TRANSCRIPT_EXTRACTION_PROMPT.format(
            user_name=USER_NAME,
            session_id=t["session_id"][:20],
            date=t["created_at"][:10],
            text=text,
        )
        try:
            raw = await call_llm(openai_client, prompt, max_tokens=4096)
            facts = parse_json_response(raw)
            for cat in facts:
                if isinstance(facts[cat], list):
                    for item in facts[cat]:
                        item["source_type"] = "transcript"
                        item["source_id"] = t["session_id"]
                        item["source_date"] = t["created_at"][:10] if t.get("created_at") else ""
            all_facts.append(facts)
            logger.info(f"       [{i+1}/{len(transcripts)}] extracted from {t['session_id'][:20]}")
        except Exception as exc:
            logger.error(f"       [{i+1}/{len(transcripts)}] FAILED: {exc}")
        await asyncio.sleep(0.3)

    # ── 2b. Process real posts ────────────────────────────────────────────
    posts = evidence.get("posts", [])
    if posts:
        logger.info(f"  [2b] Processing {len(posts)} real posts (in batches of 10)...")
        post_texts = []
        for p in posts[:50]:
            text = p.get("text", p.get("content", ""))
            ts = p.get("created_at", p.get("timestamp", ""))
            if text:
                post_texts.append(f"[{str(ts)[:10]}] {text}")

        for chunk_start in range(0, len(post_texts), 10):
            chunk = post_texts[chunk_start : chunk_start + 10]
            prompt = _POST_EXTRACTION_PROMPT.format(
                user_name=USER_NAME, text="\n\n---\n\n".join(chunk)
            )
            try:
                raw = await call_llm(openai_client, prompt, max_tokens=3000)
                facts = parse_json_response(raw)
                for cat in facts:
                    if isinstance(facts[cat], list):
                        for item in facts[cat]:
                            item["source_type"] = "post"
                            item["source_id"] = f"posts_batch_{chunk_start}"
                all_facts.append(facts)
                logger.info(f"       Extracted from posts batch [{chunk_start}:{chunk_start+len(chunk)}]")
            except Exception as exc:
                logger.error(f"       Post batch error: {exc}")
            await asyncio.sleep(0.3)

    # ── 2c. Profile-sourced facts (no LLM needed) ────────────────────────
    profile = evidence.get("user_profile", {})
    if profile:
        logger.info("  [2c] Processing user profile (explicit data)...")
        pf: Dict[str, list] = {k: [] for k in ("interests", "traits", "values", "experiences", "preferences", "connections", "demographics")}

        for interest in profile.get("interests", []):
            pf["interests"].append({"label": interest, "evidence": "profile: explicit interests", "intensity": "core", "source_type": "profile", "source_id": "user_profile"})

        if profile.get("bio"):
            pf["demographics"].append({"category": "bio", "value": profile["bio"], "evidence": "profile bio", "source_type": "profile", "source_id": "user_profile"})
        for field, cat in [("age", "age"), ("gender", "gender"), ("location", "location")]:
            if profile.get(field):
                pf["demographics"].append({"category": cat, "value": str(profile[field]), "evidence": "user profile", "source_type": "profile", "source_id": "user_profile"})
        if profile.get("job_title"):
            pf["experiences"].append({"label": profile["job_title"], "details": f"Current role: {profile['job_title']}", "evidence": "user profile", "source_type": "profile", "source_id": "user_profile"})

        for conn in profile.get("connections", []):
            pf["connections"].append({
                "name": conn.get("name", ""),
                "relationship": conn.get("relationship", ""),
                "details": conn.get("details", ""),
                "evidence": "profile connections",
                "source_type": "profile",
                "source_id": "user_profile",
            })
        all_facts.append(pf)

    # ── 2d. Conversation index topics & people (lightweight, no LLM) ─────
    conv_index = evidence.get("conversation_index", [])
    if conv_index:
        logger.info(f"  [2d] Processing {len(conv_index)} conversation-index entries...")
        for ci in conv_index:
            ci_facts: Dict[str, list] = {"interests": [], "connections": []}
            date_str = str(ci.get("timestamp", ""))[:10]
            for topic in ci.get("topics", []):
                ci_facts["interests"].append({
                    "label": topic, "evidence": f"conversation topic ({date_str})", "intensity": "casual",
                    "source_type": "conversation_index", "source_id": ci.get("session_id", ""), "source_date": date_str,
                })
            for person in ci.get("people_mentioned", []):
                ci_facts["connections"].append({
                    "name": person, "relationship": "mentioned", "details": f"mentioned in conversation ({date_str})",
                    "evidence": "conversation index", "source_type": "conversation_index", "source_id": ci.get("session_id", ""), "source_date": date_str,
                })
            all_facts.append(ci_facts)

    # ── 2e. Identity memory (already extracted facts) ─────────────────────
    identity_mem = evidence.get("identity_memory", [])
    if identity_mem:
        logger.info(f"  [2e] Processing {len(identity_mem)} identity-memory entries...")
        for im in identity_mem:
            im_facts: Dict[str, list] = {"interests": [], "preferences": []}
            for interest in im.get("interests", []):
                if isinstance(interest, dict):
                    im_facts["interests"].append({
                        "label": interest.get("topic", ""), "evidence": "identity memory",
                        "intensity": "strong" if interest.get("strength", 0) > 0.7 else "casual",
                        "source_type": "identity_memory", "source_id": "identity_memory",
                    })
            for fact in im.get("facts", []):
                if isinstance(fact, dict):
                    im_facts["preferences"].append({
                        "label": fact.get("fact", ""), "details": fact.get("fact", ""),
                        "evidence": "identity memory", "source_type": "identity_memory", "source_id": "identity_memory",
                    })
            all_facts.append(im_facts)

    # ── 2f. Bond moments & reflections ────────────────────────────────────
    bond_moments = evidence.get("bond_moments", [])
    reflections = evidence.get("reflections", [])
    if bond_moments or reflections:
        logger.info(f"  [2f] Processing {len(bond_moments)} bond moments + {len(reflections)} reflections...")
        br_facts: Dict[str, list] = {"traits": [], "values": [], "preferences": []}
        for bm in bond_moments:
            desc = bm.get("description", "")
            if desc and len(desc) > 10:
                br_facts["traits"].append({
                    "label": bm.get("moment_type", "connection"),
                    "evidence": desc[:200],
                    "confidence": bm.get("significance", 0.5),
                    "source_type": "bond_moment", "source_id": bm.get("id", ""),
                })
        for rl in reflections:
            content = rl.get("content", "")
            if content and len(content) > 10:
                cat = "values" if rl.get("reflection_type") in ("insight", "pattern", "learning") else "preferences"
                br_facts[cat].append({
                    "label": rl.get("title", content[:50]),
                    "evidence": content[:200],
                    "confidence": rl.get("confidence", 0.5),
                    "source_type": "reflection", "source_id": rl.get("id", ""),
                })
        all_facts.append(br_facts)

    # ── Merge all facts ──────────────────────────────────────────────────
    logger.info("  Synthesizing unified identity model...")
    unified = _merge_identity_facts(all_facts)

    total_items = sum(len(v) for v in unified.values())
    logger.info(f"  Identity model: {total_items} total items")
    for category, items in unified.items():
        if items:
            logger.info(f"    {category}: {len(items)}")

    # Save identity model for inspection
    model_path = os.path.join(BACKUP_DIR, f"identity_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(model_path, "w") as f:
        json.dump(unified, f, indent=2, default=str)
    logger.info(f"  Identity model saved -> {model_path}")

    return unified


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — NODE CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

async def phase3_cleanup_nodes(db, evidence: Dict, identity_model: Dict) -> Dict:
    logger.info("=" * 70)
    logger.info("  PHASE 3: Cleaning up existing nodes")
    logger.info("=" * 70)

    existing_nodes = evidence["existing_nodes"]
    nodes_to_delete: List[Dict] = []
    nodes_to_update: List[Dict] = []
    merge_groups: Dict[str, List[Dict]] = defaultdict(list)

    for node in existing_nodes:
        nid = node.get("id", "")
        label = node.get("label", "")
        node_type = node.get("node_type", "interest")
        normalized = normalize_label(label)

        if is_garbage_node(normalized, node_type):
            nodes_to_delete.append({"id": nid, "label": label, "reason": f"garbage ('{normalized}')"})
            continue

        key = f"{node_type}:{normalized}"
        merge_groups[key].append(node)

    # For each group, keep the best node and mark extras for deletion
    canonical_nodes: Dict[str, Dict] = {}
    for key, group in merge_groups.items():
        group.sort(
            key=lambda n: (
                n.get("properties", {}).get("strength", n.get("strength", 0)),
                n.get("mention_count", 0),
            ),
            reverse=True,
        )
        canonical = group[0]
        canonical_nodes[key] = canonical

        # Merge metadata from duplicates into canonical
        total_mentions = sum(n.get("mention_count", 0) for n in group)
        all_sources: Set[str] = set()
        for n in group:
            src = n.get("properties", {}).get("source", "")
            if src:
                all_sources.add(src)

        normalized = normalize_label(canonical.get("label", ""))
        original_label = canonical.get("label", "")
        needs_update = (
            len(group) > 1
            or normalized != original_label
        )

        if needs_update:
            nodes_to_update.append({
                "id": canonical["id"],
                "updates": {
                    "label": normalized,
                    "display_label": normalized.title(),
                    "mention_count": max(total_mentions, 1),
                    "strength": canonical.get("properties", {}).get("strength", canonical.get("strength", 0.5)),
                    "properties.all_sources": list(all_sources),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            })

        # Mark extras for deletion
        for dup in group[1:]:
            nodes_to_delete.append({
                "id": dup.get("id", ""),
                "label": dup.get("label", ""),
                "reason": f"duplicate of '{normalized}'",
            })

    logger.info(f"  Nodes to DELETE: {len(nodes_to_delete)}")
    for d in nodes_to_delete[:25]:
        logger.info(f"    x  '{d['label']}' — {d['reason']}")
    if len(nodes_to_delete) > 25:
        logger.info(f"    ... and {len(nodes_to_delete) - 25} more")

    logger.info(f"  Nodes to UPDATE (fix label / merge): {len(nodes_to_update)}")
    logger.info(f"  Canonical nodes after cleanup: {len(canonical_nodes)}")

    if not DRY_RUN:
        deleted_count = 0
        for d in nodes_to_delete:
            if d["id"]:
                r = await db.graph_nodes.delete_one({"id": d["id"], "user_id": USER_ID})
                deleted_count += r.deleted_count

        updated_count = 0
        for u in nodes_to_update:
            if u["id"]:
                r = await db.graph_nodes.update_one(
                    {"id": u["id"], "user_id": USER_ID},
                    {"$set": u["updates"]},
                )
                updated_count += r.modified_count

        logger.info(f"  Applied: {deleted_count} deletions, {updated_count} updates")
    else:
        logger.info("  [DRY RUN] No changes applied")

    return {
        "deleted": nodes_to_delete,
        "updated": nodes_to_update,
        "canonical_nodes": canonical_nodes,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — NODE AUGMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

_CATEGORY_TO_NODE_TYPE = {
    "interests": "interest",
    "traits": "trait",
    "values": "value",
    "experiences": "experience",
    "preferences": "preference",
    "connections": "connection",
    "demographics": "demographic",
}


async def phase4_augment_nodes(
    db, evidence: Dict, identity_model: Dict, cleanup_result: Dict
) -> Dict[str, Dict]:
    logger.info("=" * 70)
    logger.info("  PHASE 4: Augmenting nodes with evidence")
    logger.info("=" * 70)

    # Build lookup of surviving nodes
    if DRY_RUN:
        deleted_ids = {d["id"] for d in cleanup_result["deleted"]}
        current_nodes = [n for n in evidence["existing_nodes"] if n.get("id", "") not in deleted_ids]
    else:
        current_nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)

    current_lookup: Dict[str, Dict] = {}
    for n in current_nodes:
        key = f"{n.get('node_type', '')}:{normalize_label(n.get('label', ''))}"
        current_lookup[key] = n

    nodes_enriched = 0
    nodes_created = 0

    for category, items in identity_model.items():
        node_type = _CATEGORY_TO_NODE_TYPE.get(category, "interest")

        for norm_label, item in items.items():
            if is_garbage_node(norm_label, node_type):
                continue

            key = f"{node_type}:{norm_label}"
            existing = current_lookup.get(key)

            now_iso = datetime.now(timezone.utc).isoformat()

            if existing:
                # Enrich with evidence metadata
                updates = {
                    "strength": item["strength"],
                    "properties.strength": item["strength"],
                    "properties.confidence": item["strength"],
                    "properties.evidence_count": len(item["evidence_sources"]),
                    "properties.evidence_sources": item["evidence_sources"][:20],
                    "mention_count": max(item["mention_count"], existing.get("mention_count", 0)),
                    "updated_at": now_iso,
                }
                if item.get("first_mentioned"):
                    updates["properties.first_mentioned_at"] = item["first_mentioned"]
                if item.get("last_mentioned"):
                    updates["properties.last_mentioned_at"] = item["last_mentioned"]

                if not DRY_RUN:
                    await db.graph_nodes.update_one(
                        {"id": existing["id"], "user_id": USER_ID}, {"$set": updates}
                    )
                nodes_enriched += 1

            else:
                # Create new node
                display = item.get("display_label", norm_label).strip() or norm_label
                if category == "connections":
                    display = display.title()
                elif category != "demographics":
                    display = display.title()

                new_node = {
                    "id": make_node_id(node_type, norm_label),
                    "user_id": USER_ID,
                    "node_type": node_type,
                    "label": norm_label,
                    "display_label": display,
                    "strength": item["strength"],
                    "mention_count": item["mention_count"],
                    "properties": {
                        "source": "graph_cleanup_augmentation",
                        "strength": item["strength"],
                        "confidence": item["strength"],
                        "evidence_count": len(item["evidence_sources"]),
                        "evidence_sources": item["evidence_sources"][:20],
                    },
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
                if item.get("first_mentioned"):
                    new_node["properties"]["first_mentioned_at"] = item["first_mentioned"]
                if item.get("last_mentioned"):
                    new_node["properties"]["last_mentioned_at"] = item["last_mentioned"]
                if category == "connections":
                    new_node["properties"]["relationship"] = item.get("relationship", "")
                    new_node["properties"]["details"] = item.get("details", "")
                if category in ("experiences", "preferences"):
                    new_node["full_text"] = item.get("details", "")
                    new_node["properties"]["details"] = item.get("details", "")
                if category == "demographics":
                    parts = norm_label.split(":", 1)
                    if len(parts) == 2:
                        new_node["properties"]["category"] = parts[0]
                        new_node["properties"]["value"] = parts[1]

                if not DRY_RUN:
                    exists = await db.graph_nodes.find_one(
                        {"user_id": USER_ID, "node_type": node_type, "label": norm_label}
                    )
                    if not exists:
                        await db.graph_nodes.insert_one(new_node)
                        nodes_created += 1
                    else:
                        nodes_enriched += 1
                else:
                    nodes_created += 1

                current_lookup[key] = new_node

    logger.info(f"  Nodes enriched with evidence: {nodes_enriched}")
    logger.info(f"  New nodes created: {nodes_created}")
    if DRY_RUN:
        logger.info("  [DRY RUN] No changes applied")

    return current_lookup


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — EDGE REBUILDING
# ═══════════════════════════════════════════════════════════════════════════════

_EDGE_INFERENCE_PROMPT = """You are analyzing the identity graph of a person named {user_name}.
Given the nodes below, create meaningful RELATIONSHIP edges between them.
Use ONLY the EXACT labels listed below (copy-paste from the lists).

NODES:
{node_summary}

RELATIONSHIP TYPES (use these exactly):
- expressed_through: an interest/value expressed through a trait (e.g. "photography" expressed_through "creative")
- motivates: a value/experience that drives an interest (e.g. "family" motivates "parenting")
- shaped_by: a trait shaped by an experience (e.g. "resilient" shaped_by "entrepreneurship")
- inspires: a connection that inspires an interest (e.g. "daughter" inspires "parenting")
- reflects: an interest that reflects a value (e.g. "volunteering" reflects "giving back")
- subsumes: one concept is a sub-category of another (e.g. "technology" subsumes "machine learning")
- related_to: general semantic relatedness (e.g. "cooking" related_to "food culture")
- complements: traits/values that reinforce each other (e.g. "curious" complements "lifelong learning")

RULES:
- Focus on CROSS-TYPE connections (interest↔trait, value↔interest, experience↔trait, connection↔interest).
- IMPORTANT: Use EXACT labels and types from the node lists above. Do NOT invent labels.
- Weight: 0.3-1.0 based on how strong/direct the relationship is.
- Create {target_count} edges. Be thorough — connect as many nodes as possible.
- DO NOT create self-loops (from_label must differ from to_label).
- Every edge must connect two DIFFERENT nodes from the lists above.

Return a JSON array:
[
  {{"from_label": "exact label from list", "from_type": "node type", "to_label": "exact label from list", "to_type": "node type", "relationship_type": "type from list above", "weight": 0.8, "reasoning": "brief why"}}
]

Return ONLY a valid JSON array."""


def _resolve_label_to_id(
    label: str, ntype: str, type_label_to_id: Dict[str, str], label_to_id: Dict[str, str]
) -> Optional[str]:
    """Resolve a label + type to a node ID, with fallbacks."""
    norm = normalize_label(label)
    # Exact type:label match
    key = f"{ntype}:{norm}"
    if key in type_label_to_id:
        return type_label_to_id[key]
    # Label-only match (any type)
    if norm in label_to_id:
        return label_to_id[norm]
    # Partial match — check if any known label contains or is contained by this one
    for known_label, nid in label_to_id.items():
        if len(norm) > 3 and (norm in known_label or known_label in norm):
            return nid
    return None


async def phase5_rebuild_edges(
    db, openai_client, node_lookup: Dict[str, Dict], identity_model: Dict
) -> int:
    logger.info("=" * 70)
    logger.info("  PHASE 5: Rebuilding edges with meaningful relationships")
    logger.info("=" * 70)

    # Collect all valid node IDs and build lookups
    valid_node_ids: Dict[str, Dict] = {}
    type_label_to_id: Dict[str, str] = {}
    label_to_id: Dict[str, str] = {}

    for key, node in node_lookup.items():
        nid = node.get("id", "")
        if not nid:
            continue
        valid_node_ids[nid] = node
        label = normalize_label(node.get("label", ""))
        ntype = node.get("node_type", "interest")
        if label:
            type_label_to_id[f"{ntype}:{label}"] = nid
            label_to_id[label] = nid

    # Delete old edges
    old_node_ids = list(valid_node_ids.keys())
    if not DRY_RUN:
        result = await db.graph_edges.delete_many(
            {"$or": [
                {"user_id": USER_ID},
                {"from_node_id": {"$in": old_node_ids}},
                {"to_node_id": {"$in": old_node_ids}},
            ]}
        )
        logger.info(f"  Deleted {result.deleted_count} old edges")
    else:
        old_count = await db.graph_edges.count_documents(
            {"$or": [
                {"user_id": USER_ID},
                {"from_node_id": {"$in": old_node_ids}},
                {"to_node_id": {"$in": old_node_ids}},
            ]}
        )
        logger.info(f"  Would delete {old_count} old edges")

    # Build node summary for LLM — labels only, grouped by type
    nodes_by_type: Dict[str, List[Dict]] = defaultdict(list)
    for key, node in node_lookup.items():
        nid = node.get("id", "")
        label = normalize_label(node.get("label", ""))
        ntype = node.get("node_type", "interest")
        strength = node.get("strength", node.get("properties", {}).get("strength", 0.5))
        if nid and label and len(label) >= 2:
            nodes_by_type[ntype].append({"id": nid, "label": label, "type": ntype, "strength": strength})

    limits_per_type = {"interest": 40, "trait": 15, "value": 15, "experience": 15, "preference": 15, "connection": 20, "demographic": 8}

    summary_parts = []
    included_count = 0
    for ntype in sorted(nodes_by_type.keys()):
        items = sorted(nodes_by_type[ntype], key=lambda x: x["strength"], reverse=True)
        limit = limits_per_type.get(ntype, 15)
        items = items[:limit]
        included_count += len(items)
        lines = [f"  - {it['label']}" for it in items]
        summary_parts.append(f"\n{ntype.upper()} ({len(items)} nodes):\n" + "\n".join(lines))

    node_summary = "\n".join(summary_parts)

    # Make multiple LLM calls for better coverage
    target_per_call = 50
    num_calls = 2
    all_edges_data: List[Dict] = []

    for call_idx in range(num_calls):
        temp = 0.3 + (call_idx * 0.15)
        target = target_per_call

        prompt = _EDGE_INFERENCE_PROMPT.format(
            user_name=USER_NAME, node_summary=node_summary, target_count=target
        )
        if call_idx > 0:
            existing_pairs = set()
            for e in all_edges_data:
                pair = (normalize_label(e.get("from_label", "")), normalize_label(e.get("to_label", "")))
                existing_pairs.add(pair)
            if existing_pairs:
                prompt += f"\n\nAVOID these already-created edges (create DIFFERENT ones):\n"
                for fl, tl in list(existing_pairs)[:30]:
                    prompt += f"  - {fl} → {tl}\n"

        try:
            raw = await call_llm(openai_client, prompt, max_tokens=8000, temperature=temp)
            batch = parse_json_response(raw)
            all_edges_data.extend(batch)
            logger.info(f"  LLM call {call_idx+1}/{num_calls}: got {len(batch)} edges (temp={temp:.2f})")
        except Exception as exc:
            logger.error(f"  LLM call {call_idx+1} failed: {exc}")
        await asyncio.sleep(1)

    # Deduplicate and resolve edges
    seen_pairs: Set[Tuple[str, str]] = set()
    edges_created = 0
    edges_skipped = 0

    for ed in all_edges_data:
        from_label = ed.get("from_label", "")
        from_type = ed.get("from_type", "")
        to_label = ed.get("to_label", "")
        to_type = ed.get("to_type", "")

        from_id = _resolve_label_to_id(from_label, from_type, type_label_to_id, label_to_id)
        to_id = _resolve_label_to_id(to_label, to_type, type_label_to_id, label_to_id)

        if not from_id or not to_id or from_id == to_id:
            edges_skipped += 1
            continue

        pair = tuple(sorted([from_id, to_id]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        edge = {
            "id": str(uuid_mod.uuid4()),
            "user_id": USER_ID,
            "from_node_id": from_id,
            "to_node_id": to_id,
            "relationship_type": ed.get("relationship_type", "related_to"),
            "weight": min(1.0, max(0.0, ed.get("weight", 0.5))),
            "properties": {
                "source": "graph_cleanup_llm_inference",
                "reasoning": ed.get("reasoning", "")[:300],
                "confidence": min(1.0, max(0.0, ed.get("weight", 0.5))),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if not DRY_RUN:
            await db.graph_edges.insert_one(edge)
        edges_created += 1

    logger.info(f"  Created {edges_created} meaningful edges ({edges_skipped} skipped/unresolved, {len(all_edges_data)} total proposed)")

    if DRY_RUN:
        logger.info("  [DRY RUN] Sample edges:")
        for e in all_edges_data[:20]:
            logger.info(
                f"    {e.get('from_label','?')} [{e.get('from_type','')}] "
                f"--[{e.get('relationship_type','?')}]--> "
                f"{e.get('to_label','?')} [{e.get('to_type','')}]  (w={e.get('weight',0):.1f})"
            )

    return edges_created


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — VALIDATION & CACHE INVALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

async def phase6_validate(db) -> bool:
    logger.info("=" * 70)
    logger.info("  PHASE 6: Validation & cache invalidation")
    logger.info("=" * 70)

    nodes = await db.graph_nodes.find({"user_id": USER_ID}, {"_id": 0}).to_list(10000)

    issues: List[str] = []
    type_counter: Counter = Counter()
    strength_values: List[float] = []
    valid_types = {"interest", "trait", "value", "experience", "preference", "demographic", "connection"}

    for n in nodes:
        nid = n.get("id", "")
        label = n.get("label", "")
        ntype = n.get("node_type", "")
        strength = n.get("properties", {}).get("strength", n.get("strength", 0))

        if not nid:
            issues.append(f"Missing 'id': label={label}")
        if not label:
            issues.append(f"Missing 'label': id={nid}")
        if ntype not in valid_types:
            issues.append(f"Unknown node_type '{ntype}': {label}")
        type_counter[ntype] += 1
        strength_values.append(strength)

    # Check edges
    node_ids = {n.get("id", "") for n in nodes}
    edges = await db.graph_edges.find(
        {"$or": [
            {"user_id": USER_ID},
            {"from_node_id": {"$in": list(node_ids)}},
            {"to_node_id": {"$in": list(node_ids)}},
        ]},
        {"_id": 0},
    ).to_list(10000)

    orphan_edges = 0
    edge_type_counter: Counter = Counter()
    cross_type = 0
    same_type = 0
    for e in edges:
        fr = e.get("from_node_id", "")
        to = e.get("to_node_id", "")
        if fr not in node_ids or to not in node_ids:
            orphan_edges += 1
        edge_type_counter[e.get("relationship_type", "unknown")] += 1

        fr_type = next((n.get("node_type") for n in nodes if n.get("id") == fr), None)
        to_type = next((n.get("node_type") for n in nodes if n.get("id") == to), None)
        if fr_type and to_type:
            if fr_type == to_type:
                same_type += 1
            else:
                cross_type += 1

    # Report
    logger.info(f"  NODES: {len(nodes)}")
    for t, c in type_counter.most_common():
        logger.info(f"    {t}: {c}")

    logger.info(f"  EDGES: {len(edges)}")
    for t, c in edge_type_counter.most_common():
        logger.info(f"    {t}: {c}")
    logger.info(f"    Cross-type: {cross_type}, Same-type: {same_type}")

    if strength_values:
        avg_s = sum(strength_values) / len(strength_values)
        logger.info(f"  Avg strength: {avg_s:.3f}")

    ratio = len(edges) / len(nodes) if nodes else 0
    logger.info(f"  Edge/node ratio: {ratio:.2f}")

    if issues:
        logger.warning(f"  ISSUES: {len(issues)}")
        for iss in issues[:15]:
            logger.warning(f"    ! {iss}")
    else:
        logger.info(f"  No schema issues")

    if orphan_edges:
        logger.warning(f"  Orphan edges: {orphan_edges}")
    else:
        logger.info(f"  No orphan edges")

    # Invalidate personality prompt cache so next request regenerates with new graph
    if not DRY_RUN:
        r = await db.avatar_personality_prompts.delete_one({"user_id": USER_ID})
        if r.deleted_count:
            logger.info(f"  Invalidated cached personality prompt (will regenerate on next use)")

    passed = len(issues) == 0 and orphan_edges == 0
    if passed:
        logger.info("  VALIDATION PASSED")
    else:
        logger.warning("  VALIDATION HAS WARNINGS — review above")
    return passed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    import boto3
    from motor.motor_asyncio import AsyncIOMotorClient
    from openai import AsyncOpenAI

    print()
    print("=" * 70)
    print(f"  GRAPH CLEANUP & AUGMENTATION: {AVATAR_NAME} ({USER_NAME})")
    print(f"  Mode: {'DRY RUN (preview only)' if DRY_RUN else 'LIVE — CHANGES WILL BE APPLIED'}")
    print(f"  LLM Model: {LLM_MODEL}")
    print("=" * 70)
    print()

    # ── Connect ──────────────────────────────────────────────────────────
    logger.info("Connecting to AWS, MongoDB, OpenAI...")
    mongo_uri = get_mongo_uri()
    openai_key = get_openai_key()

    if not mongo_uri:
        logger.error("FATAL: Could not fetch MongoDB URI from Secrets Manager")
        return
    if not openai_key:
        logger.error("FATAL: Could not fetch OpenAI API key from Secrets Manager")
        return

    mongo_client = AsyncIOMotorClient(mongo_uri)
    db = mongo_client[DB_NAME]
    openai_client = AsyncOpenAI(api_key=openai_key)
    s3_client = boto3.client("s3", region_name=S3_REGION)

    logger.info(f"Connected: MongoDB ({DB_NAME}), OpenAI ({LLM_MODEL}), S3 ({S3_BUCKET})")
    print()

    t_start = datetime.now()

    try:
        # Phase 0
        backup_nodes, backup_edges = await phase0_backup(db)
        print()

        # Phase 1
        evidence = await phase1_collect_evidence(db, s3_client)
        print()

        # Phase 2
        identity_model = await phase2_extract_identity(openai_client, evidence)
        print()

        # Phase 3
        cleanup_result = await phase3_cleanup_nodes(db, evidence, identity_model)
        print()

        # Phase 4
        node_lookup = await phase4_augment_nodes(db, evidence, identity_model, cleanup_result)
        print()

        # Phase 5
        edges_created = await phase5_rebuild_edges(db, openai_client, node_lookup, identity_model)
        print()

        # Phase 6
        if not DRY_RUN:
            valid = await phase6_validate(db)
        else:
            logger.info("  Skipping live validation in DRY RUN mode")
            valid = True
        print()

    except Exception as exc:
        logger.error(f"FATAL ERROR: {exc}")
        traceback.print_exc()
        mongo_client.close()
        return

    elapsed = (datetime.now() - t_start).total_seconds()

    # ── Final summary ────────────────────────────────────────────────────
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Mode:            {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Elapsed:         {elapsed:.1f}s")
    print(f"  Backup:          {len(backup_nodes)} nodes, {len(backup_edges)} edges")
    print(f"  Evidence:")
    print(f"    Transcripts:     {len(evidence.get('transcripts', []))}")
    print(f"    Conv index:      {len(evidence.get('conversation_index', []))}")
    print(f"    Real posts:      {len(evidence.get('posts', []))}")
    print(f"    Identity mem:    {len(evidence.get('identity_memory', []))}")
    print(f"    Bond moments:    {len(evidence.get('bond_moments', []))}")
    print(f"    Reflections:     {len(evidence.get('reflections', []))}")
    print(f"  Identity model:")
    for category, items in identity_model.items():
        if items:
            print(f"    {category:15s}: {len(items)}")
    print(f"  Cleanup:")
    print(f"    Deleted:         {len(cleanup_result['deleted'])}")
    print(f"    Updated:         {len(cleanup_result['updated'])}")
    print(f"  New edges:         {edges_created}")
    if not DRY_RUN:
        print(f"  Validation:        {'PASSED' if valid else 'WARNINGS'}")
    print("=" * 70)

    if DRY_RUN:
        print()
        print("  This was a DRY RUN. To apply changes, run with --live:")
        print(f"    python {os.path.basename(__file__)} --live")
        print()

    mongo_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Graph cleanup & augmentation for {AVATAR_NAME} ({USER_NAME})"
    )
    parser.add_argument("--live", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--model", default="gpt-4o", help="LLM model (default: gpt-4o)")
    args = parser.parse_args()

    DRY_RUN = not args.live
    LLM_MODEL = args.model

    asyncio.run(main())
