"""
Seed Script for Siddhi Bazaar
Seeds the skill catalog and optionally installs default skills for all existing users.

Usage:
    python -m scripts.seed_siddhi_bazaar
    python -m scripts.seed_siddhi_bazaar --install-defaults
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_database
from domain.marketplace.catalog import seed_catalog
from domain.marketplace.installer import SkillInstaller


async def main(install_defaults: bool = False):
    db = get_database()

    print("🔮 Seeding Siddhi Bazaar catalog...")
    created = await seed_catalog(db)
    print(f"✅ Catalog seeded: {created} new skills created")

    total = await db.siddhi_skills.count_documents({})
    print(f"📦 Total skills in catalog: {total}")

    if install_defaults:
        print("\n📥 Installing default skills for all existing users...")
        installer = SkillInstaller(db)
        users = await db.users.find({}).to_list(None)
        print(f"Found {len(users)} users")

        for user in users:
            user_id = user.get("id")
            if not user_id:
                continue

            existing = await db.siddhi_installations.count_documents({"user_id": user_id})
            if existing > 0:
                print(f"  ⏭️  {user.get('name', 'Unknown')}: already has {existing} installations")
                continue

            count = await installer.install_defaults_for_user(user_id)
            print(f"  ✅ {user.get('name', 'Unknown')}: {count} default skills installed")

        print("✅ Default skills installed for all users")

    print("\n🔮 Siddhi Bazaar seed complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Siddhi Bazaar")
    parser.add_argument("--install-defaults", action="store_true", help="Install default skills for all users")
    args = parser.parse_args()
    asyncio.run(main(install_defaults=args.install_defaults))
