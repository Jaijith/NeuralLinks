#!/usr/bin/env python3
"""
Fix S3 URLs in MongoDB to use correct region (us-west-2 instead of us-east-1)
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
OLD_REGION = 'us-east-1'
NEW_REGION = 'us-west-2'

def fix_url(url: str) -> str:
    """Replace old region with new region in S3 URL"""
    if not url:
        return url
    
    # Replace us-east-1 with us-west-2
    if f".s3.{OLD_REGION}.amazonaws.com" in url:
        return url.replace(f".s3.{OLD_REGION}.amazonaws.com", f".s3.{NEW_REGION}.amazonaws.com")
    
    return url

def main():
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    logger.info(f"Connected to MongoDB: {MONGO_URI}, Database: {MONGO_DB_NAME}")

    # Fix posts collection
    posts_updated = 0
    for post in db.posts.find({"image_url": {"$regex": f".s3.{OLD_REGION}.amazonaws.com"}}):
        old_url = post.get("image_url")
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
            {"picture": {"$regex": f".s3.{OLD_REGION}.amazonaws.com"}},
            {"cover_photo": {"$regex": f".s3.{OLD_REGION}.amazonaws.com"}},
            {"avatar_picture": {"$regex": f".s3.{OLD_REGION}.amazonaws.com"}},
            {"avatar_cover_photo": {"$regex": f".s3.{OLD_REGION}.amazonaws.com"}},
        ]
    }):
        update_fields = {}
        for field in ["picture", "cover_photo", "avatar_picture", "avatar_cover_photo"]:
            old_url = user.get(field)
            if old_url and f".s3.{OLD_REGION}.amazonaws.com" in old_url:
                new_url = fix_url(old_url)
                if new_url != old_url:
                    update_fields[field] = new_url
        
        if update_fields:
            db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
            users_updated += 1
            logger.info(f"Updated user {user['_id']}: {update_fields}")
    
    logger.info(f"✅ Updated {users_updated} users")
    logger.info("🎉 All S3 URLs fixed!")

if __name__ == "__main__":
    main()

