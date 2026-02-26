#!/usr/bin/env python3
"""
Simulate the voice prompt generation for DigitalHunter and _bLikker.
Shows exactly what the avatar "knows" about the user during a voice session.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import boto3
from motor.motor_asyncio import AsyncIOMotorClient

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


async def main():
    print("=" * 80)
    print("  Voice Prompt Simulation")
    print("=" * 80)

    uri = get_mongo_uri()
    client = AsyncIOMotorClient(
        uri, serverSelectionTimeoutMS=30000, connectTimeoutMS=30000, socketTimeoutMS=60000,
    )
    db = client[DB_NAME]
    await client.admin.command("ismaster")

    from domain.voice.prompt_generator import VoicePromptGenerator
    gen = VoicePromptGenerator(db)

    for name, user_id in USERS.items():
        print(f"\n{'#' * 80}")
        print(f"#  {name}")
        print(f"{'#' * 80}")

        prompt = await gen.generate_prompt(
            user_id=user_id,
            avatar_id=user_id,
        )

        prompt_tokens = len(prompt) // 4
        print(f"\n  Total prompt length: {len(prompt)} chars (~{prompt_tokens} tokens)")

        # Break down what sections are present
        sections_found = []
        sections_missing = []

        checks = [
            ("Who You Are", "Who You Are"),
            ("Who {name} Really Is (personality prompt)", "Really Is"),
            ("Identity from knowledge graph", "Identity (from knowledge graph)"),
            ("People in their life (voice memory)", "People in"),
            ("What they told you (voice memory)", "told you"),
            ("What Matters", "What Matters"),
            ("Social context", "Social Life"),
            ("Knowledge gap question", "Curious About"),
            ("Post insight threads", "Threads From Their Heart"),
            ("Emotional Authenticity", "Emotional Authenticity"),
        ]
        for label, marker in checks:
            if marker in prompt:
                sections_found.append(label)
            else:
                sections_missing.append(label)

        print(f"\n  Sections present ({len(sections_found)}):")
        for s in sections_found:
            print(f"    ✅ {s}")
        if sections_missing:
            print(f"\n  Sections absent ({len(sections_missing)}):")
            for s in sections_missing:
                print(f"    ⬜ {s}")

        # Check if identity narrative is present with real content
        if "Identity (from knowledge graph)" in prompt:
            idx = prompt.index("Identity (from knowledge graph)")
            snippet = prompt[idx:idx+500]
            print(f"\n  Identity narrative snippet:")
            for line in snippet.split("\n")[:8]:
                print(f"    │ {line[:100]}")

        # Check if personality prompt has graph data
        if "Really Is" in prompt:
            idx = prompt.index("Really Is")
            snippet = prompt[idx:idx+400]
            # Check for key identity markers
            has_interests = "interest" in snippet.lower() or "passion" in snippet.lower()
            has_traits = "trait" in snippet.lower() or "personality" in snippet.lower()
            has_connections = "family" in snippet.lower() or "people" in snippet.lower() or "daughter" in snippet.lower() or "wife" in snippet.lower() or "mother" in snippet.lower()
            print(f"\n  Personality prompt content:")
            print(f"    Has interests: {'✅' if has_interests else '❌'}")
            print(f"    Has traits: {'✅' if has_traits else '❌'}")
            print(f"    Has connections: {'✅' if has_connections else '❌'}")

        # Show what the avatar would know about specific things
        print(f"\n  Key identity markers in full prompt:")
        identity_checks = {
            "Jaijith": ["Subhadra", "Manju", "Kerala", "data scientist", "AI", "tea", "kathakali"],
            "Sreejith": ["Taran", "Narmada", "architect", "Vili", "Kozhikode", "nadumuttam", "badminton"],
        }
        for person, markers in identity_checks.items():
            if person.lower() in name.lower():
                for marker in markers:
                    found = marker.lower() in prompt.lower()
                    print(f"    {'✅' if found else '❌'} Knows about: {marker}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
