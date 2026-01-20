"""
Initialize Bonding Collections
Creates necessary indexes for bonding workflow collections
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database


async def init_bonding_collections():
    """Create bonding collections and indexes"""
    db = get_database()
    
    print("🔧 Initializing bonding collections and indexes...")
    
    # ========================================================================
    # BONDING STATES
    # ========================================================================
    print("\n📊 Creating bonding_states collection...")
    
    # Main lookup index
    await db.bonding_states.create_index([("user_id", 1), ("avatar_id", 1)], unique=True)
    print("   ✓ Created index: user_id + avatar_id (unique)")
    
    # Query indexes
    await db.bonding_states.create_index([("user_id", 1)])
    print("   ✓ Created index: user_id")
    
    await db.bonding_states.create_index([("avatar_id", 1)])
    print("   ✓ Created index: avatar_id")
    
    await db.bonding_states.create_index([("updated_at", -1)])
    print("   ✓ Created index: updated_at (desc)")
    
    await db.bonding_states.create_index([("metrics.bond_strength", -1)])
    print("   ✓ Created index: metrics.bond_strength (desc)")
    
    # ========================================================================
    # BONDING SESSIONS
    # ========================================================================
    print("\n📝 Creating bonding_sessions collection...")
    
    # Main lookup index
    await db.bonding_sessions.create_index([("user_id", 1), ("start_time", -1)])
    print("   ✓ Created index: user_id + start_time (desc)")
    
    # Query indexes
    await db.bonding_sessions.create_index([("avatar_id", 1), ("start_time", -1)])
    print("   ✓ Created index: avatar_id + start_time (desc)")
    
    await db.bonding_sessions.create_index([("id", 1)], unique=True)
    print("   ✓ Created index: id (unique)")
    
    await db.bonding_sessions.create_index([("detected_intent", 1)])
    print("   ✓ Created index: detected_intent")
    
    await db.bonding_sessions.create_index([("delight_score", -1)])
    print("   ✓ Created index: delight_score (desc)")
    
    # ========================================================================
    # IDENTITY MEMORY
    # ========================================================================
    print("\n🧠 Creating identity_memory collection...")
    
    # Main lookup index
    await db.identity_memory.create_index([("user_id", 1), ("preference_type", 1)])
    print("   ✓ Created index: user_id + preference_type")
    
    # Query indexes
    await db.identity_memory.create_index([("user_id", 1), ("is_active", 1)])
    print("   ✓ Created index: user_id + is_active")
    
    await db.identity_memory.create_index([("id", 1)], unique=True)
    print("   ✓ Created index: id (unique)")
    
    await db.identity_memory.create_index([("confidence", -1)])
    print("   ✓ Created index: confidence (desc)")
    
    await db.identity_memory.create_index([("importance", -1)])
    print("   ✓ Created index: importance (desc)")
    
    # ========================================================================
    # NARRATIVE MEMORY
    # ========================================================================
    print("\n📖 Creating narrative_memory collection...")
    
    # Main lookup index
    await db.narrative_memory.create_index([("user_id", 1), ("arc_type", 1)])
    print("   ✓ Created index: user_id + arc_type")
    
    # Query indexes
    await db.narrative_memory.create_index([("user_id", 1), ("is_active", 1)])
    print("   ✓ Created index: user_id + is_active")
    
    await db.narrative_memory.create_index([("id", 1)], unique=True)
    print("   ✓ Created index: id (unique)")
    
    await db.narrative_memory.create_index([("started_at", -1)])
    print("   ✓ Created index: started_at (desc)")
    
    await db.narrative_memory.create_index([("significance", -1)])
    print("   ✓ Created index: significance (desc)")
    
    # ========================================================================
    # BOND MOMENTS
    # ========================================================================
    print("\n✨ Creating bond_moments collection...")
    
    # Main lookup index
    await db.bond_moments.create_index([("user_id", 1), ("timestamp", -1)])
    print("   ✓ Created index: user_id + timestamp (desc)")
    
    # Query indexes
    await db.bond_moments.create_index([("avatar_id", 1), ("timestamp", -1)])
    print("   ✓ Created index: avatar_id + timestamp (desc)")
    
    await db.bond_moments.create_index([("id", 1)], unique=True)
    print("   ✓ Created index: id (unique)")
    
    await db.bond_moments.create_index([("moment_type", 1)])
    print("   ✓ Created index: moment_type")
    
    await db.bond_moments.create_index([("significance", -1)])
    print("   ✓ Created index: significance (desc)")
    
    await db.bond_moments.create_index([("bond_impact", -1)])
    print("   ✓ Created index: bond_impact (desc)")
    
    # ========================================================================
    # REFLECTION LOGS
    # ========================================================================
    print("\n💭 Creating reflection_logs collection...")
    
    # Main lookup index
    await db.reflection_logs.create_index([("avatar_id", 1), ("created_at", -1)])
    print("   ✓ Created index: avatar_id + created_at (desc)")
    
    # Query indexes
    await db.reflection_logs.create_index([("user_id", 1), ("reflection_type", 1)])
    print("   ✓ Created index: user_id + reflection_type")
    
    await db.reflection_logs.create_index([("id", 1)], unique=True)
    print("   ✓ Created index: id (unique)")
    
    await db.reflection_logs.create_index([("confidence", -1)])
    print("   ✓ Created index: confidence (desc)")
    
    await db.reflection_logs.create_index([("usefulness", -1)])
    print("   ✓ Created index: usefulness (desc)")
    
    await db.reflection_logs.create_index([("times_applied", -1)])
    print("   ✓ Created index: times_applied (desc)")
    
    print("\n" + "="*70)
    print("✅ Bonding collections initialized successfully!")
    print("="*70)
    
    print("\n📋 Collections created:")
    print("   • bonding_states (relationship health metrics)")
    print("   • bonding_sessions (session tracking)")
    print("   • identity_memory (user preferences & boundaries)")
    print("   • narrative_memory (relationship journey)")
    print("   • bond_moments (special closeness events)")
    print("   • reflection_logs (avatar learnings)")
    
    print("\n💾 Total indexes created: 38")
    print("\n🚀 Ready for bonding workflow!")


if __name__ == "__main__":
    asyncio.run(init_bonding_collections())
