"""
Migration script to update YouTube node sources from old format to new format
Old: source: "youtube_llm_analysis" -> New: source: "youtube", service: "llm_analysis"
Old: source: "youtube_aggregated" -> New: source: "youtube", service: "watch_history"
Old: source: "youtube_liked_aggregated" -> New: source: "youtube", service: "liked_videos"
Old: source: "youtube_watch_history" -> New: source: "youtube", service: "watch_history_upload"
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def migrate_youtube_sources():
    """Migrate YouTube node sources to new format"""
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "neurallinks_local")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Mapping of old sources to new source + service
    migrations = {
        "youtube_llm_analysis": {"source": "youtube", "service": "llm_analysis"},
        "youtube_aggregated": {"source": "youtube", "service": "watch_history"},
        "youtube_liked_aggregated": {"source": "youtube", "service": "liked_videos"},
        "youtube_watch_history": {"source": "youtube", "service": "watch_history_upload"}
    }
    
    total_updated = 0
    
    for old_source, new_props in migrations.items():
        # Find all nodes with old source
        nodes = await db.graph_nodes.find({
            "properties.source": old_source
        }).to_list(10000)
        
        print(f"\nFound {len(nodes)} nodes with source '{old_source}'")
        
        for node in nodes:
            # Update the node
            await db.graph_nodes.update_one(
                {"id": node["id"]},
                {
                    "$set": {
                        "properties.source": new_props["source"],
                        "properties.service": new_props["service"]
                    }
                }
            )
            total_updated += 1
        
        print(f"Updated {len(nodes)} nodes from '{old_source}' to source='{new_props['source']}', service='{new_props['service']}'")
    
    # Also ensure subscription and playlist nodes have service field
    subscription_nodes = await db.graph_nodes.find({
        "properties.source": "youtube",
        "properties.category": "subscription",
        "properties.service": {"$exists": False}
    }).to_list(1000)
    
    if subscription_nodes:
        await db.graph_nodes.update_many(
            {
                "properties.source": "youtube",
                "properties.category": "subscription",
                "properties.service": {"$exists": False}
            },
            {
                "$set": {"properties.service": "subscriptions"}
            }
        )
        print(f"\nUpdated {len(subscription_nodes)} subscription nodes to include service='subscriptions'")
    
    playlist_nodes = await db.graph_nodes.find({
        "properties.source": "youtube",
        "properties.category": "playlist",
        "properties.service": {"$exists": False}
    }).to_list(1000)
    
    if playlist_nodes:
        await db.graph_nodes.update_many(
            {
                "properties.source": "youtube",
                "properties.category": "playlist",
                "properties.service": {"$exists": False}
            },
            {
                "$set": {"properties.service": "playlists"}
            }
        )
        print(f"\nUpdated {len(playlist_nodes)} playlist nodes to include service='playlists'")
    
    # Update any remaining YouTube nodes without service field
    # These are likely old nodes created before service field was added
    remaining_nodes = await db.graph_nodes.find({
        "properties.source": "youtube",
        "$or": [
            {"properties.service": {"$exists": False}},
            {"properties.service": "unknown"}
        ]
    }).to_list(10000)
    
    if remaining_nodes:
        print(f"\nFound {len(remaining_nodes)} YouTube nodes without service field")
        
        # Determine service based on category or label
        for node in remaining_nodes:
            props = node.get("properties", {})
            category = props.get("category", "")
            label = node.get("label", "")
            
            service = None
            if category == "subscription" or "youtube_channel" in label:
                service = "subscriptions"
            elif category == "playlist" or "youtube_playlist" in label:
                service = "playlists"
            elif "youtube_category" in label or "youtube_tag" in label:
                service = "watch_history"
            elif "youtube_liked" in label:
                service = "liked_videos"
            else:
                # Default to subscriptions for channel-based interests
                service = "subscriptions"
            
            await db.graph_nodes.update_one(
                {"id": node["id"]},
                {"$set": {"properties.service": service}}
            )
        
        print(f"Updated {len(remaining_nodes)} remaining nodes with appropriate service field")
    
    print(f"\n{'='*80}")
    print(f"Migration complete! Total nodes updated: {total_updated + len(subscription_nodes) + len(playlist_nodes) + len(remaining_nodes)}")
    print(f"{'='*80}\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_youtube_sources())

