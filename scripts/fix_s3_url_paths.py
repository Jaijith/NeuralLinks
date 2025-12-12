#!/usr/bin/env python3
"""
Fix S3 URLs in MongoDB to remove /uploads/ prefix from paths
"""

import os
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "neurallinks_local")

# S3 Configuration
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', '2n1-uploads-019396192218')

def fix_url(url: str) -> str:
    """Remove /uploads/ prefix from S3 URL path"""
    if not url:
        return url
    
    # Pattern: https://bucket.s3.region.amazonaws.com/uploads/images/file.jpg
    # Should be: https://bucket.s3.region.amazonaws.com/images/file.jpg
    if f".s3." in url and "/uploads/" in url:
        # Find the part after .amazonaws.com/
        parts = url.split(".amazonaws.com/")
        if len(parts) == 2:
            path = parts[1]
            if path.startswith("uploads/"):
                new_path = path[8:]  # Remove "uploads/" prefix
                new_url = f"{parts[0]}.amazonaws.com/{new_path}"
                return new_url
    
    return url

def main():
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    logger.info(f"Connected to MongoDB: {MONGO_URI}, Database: {MONGO_DB_NAME}")

    # Fix posts collection
    posts_updated = 0
    for post in db.posts.find({"image_url": {"$regex": "/uploads/"}}):
        old_url = post.get("image_url")
        if old_url and "/uploads/" in old_url:
            new_url = fix_url(old_url)
            if new_url != old_url:
                db.posts.update_one({"_id": post["_id"]}, {"$set": {"image_url": new_url}})
                posts_updated += 1
                logger.info(f"Updated post {post['_id']}: {old_url} -> {new_url}")
    
    logger.info(f"✅ Updated {posts_updated} posts")

    # Fix users collection (picture, cover_photo, avatar_picture, avatar_cover_photo)
    users_updated = 0
    for user in db.users.find({
        "$or": [
            {"picture": {"$regex": "/uploads/"}},
            {"cover_photo": {"$regex": "/uploads/"}},
            {"avatar_picture": {"$regex": "/uploads/"}},
            {"avatar_cover_photo": {"$regex": "/uploads/"}},
        ]
    }):
        update_fields = {}
        for field in ["picture", "cover_photo", "avatar_picture", "avatar_cover_photo"]:
            old_url = user.get(field)
            if old_url and "/uploads/" in old_url:
                new_url = fix_url(old_url)
                if new_url != old_url:
                    update_fields[field] = new_url
        
        if update_fields:
            db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
            users_updated += 1
            logger.info(f"Updated user {user['_id']}: {update_fields}")
    
    logger.info(f"✅ Updated {users_updated} users")
    logger.info("🎉 All S3 URL paths fixed!")

if __name__ == "__main__":
    main()

