"""
Autonomous Activity Manager
Coordinates all autonomous bot activities: posting, conversations, reactions
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from intelligent_avatar import IntelligentAvatar
from graph_rag import GraphRAG
from autonomous_config import (
    assign_archetype_to_bot,
    get_archetype_config,
    should_bot_act,
    get_conversation_length,
    get_post_delay_hours,
    get_post_prompt
)


class AutonomousActivityManager:
    """Manages autonomous bot activities"""
    
    def __init__(self, db: AsyncIOMotorDatabase, intelligent_avatar: IntelligentAvatar):
        self.db = db
        self.intelligent_avatar = intelligent_avatar
        self.activity_log = []
        self.max_activities_per_cycle = 5
        self.api_call_budget = 100  # Max API calls per hour
        self.current_api_calls = 0
    
    async def initialize_bot_archetypes(self):
        """Assign archetypes to all bots that don't have one"""
        bots = await self.db.users.find({
            "is_bot": True,
            "archetype": {"$exists": False}
        }, {"_id": 0}).to_list(1000)
        
        print(f"🎭 Assigning archetypes to {len(bots)} bots...")
        
        for bot in bots:
            archetype = assign_archetype_to_bot(bot)
            config = get_archetype_config(archetype)
            
            await self.db.users.update_one(
                {"id": bot['id']},
                {"$set": {
                    "archetype": archetype,
                    "archetype_config": config,
                    "last_activity": datetime.now(timezone.utc),
                    "next_post_time": datetime.now(timezone.utc) + timedelta(
                        hours=random.uniform(0.1, 2)  # Stagger initial posts
                    )
                }}
            )
            
            print(f"   {bot.get('avatar_name', bot.get('name'))}: {config['name']}")
    
    async def run_activity_cycle(self):
        """Main activity cycle - runs periodically"""
        print("\n" + "="*60)
        print(f"🔄 Activity Cycle Starting at {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # Check API budget
        if self.current_api_calls >= self.api_call_budget:
            print("⚠️  API budget reached for this hour. Waiting...")
            return
        
        # Get active bots
        active_bots = await self._get_active_bots()
        
        if not active_bots:
            print("No bots ready for activity")
            return
        
        # Decide activities
        activities = []
        
        # 1. Post Generation (40%)
        for bot in active_bots[:3]:  # Max 3 posts per cycle
            if should_bot_act(bot.get('archetype', 'casual_observer'), 'post'):
                activities.append(('post', bot))
        
        # 2. Conversations (30%)
        for bot in active_bots[:2]:  # Max 2 conversations per cycle
            if should_bot_act(bot.get('archetype', 'casual_observer'), 'conversation'):
                activities.append(('conversation', bot))
        
        # Execute activities
        for activity_type, bot in activities[:self.max_activities_per_cycle]:
            try:
                if activity_type == 'post':
                    await self._generate_bot_post(bot)
                elif activity_type == 'conversation':
                    await self._start_bot_conversation(bot)
                    
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error in {activity_type} for {bot.get('avatar_name')}: {str(e)}")
        
        print(f"\n✅ Cycle complete. API calls used: {self.current_api_calls}")
    
    async def _get_active_bots(self) -> List[Dict]:
        """Get bots that should be active now"""
        now = datetime.now(timezone.utc)
        
        # Get bots whose next_post_time has passed
        bots = await self.db.users.find({
            "is_bot": True,
            "archetype": {"$exists": True},
            "$or": [
                {"next_post_time": {"$lte": now}},
                {"next_post_time": {"$exists": False}}
            ]
        }, {"_id": 0}).to_list(20)
        
        # Shuffle for randomness
        random.shuffle(bots)
        
        return bots[:10]  # Return top 10
    
    async def _generate_bot_post(self, bot: Dict):
        """Generate an autonomous post for a bot"""
        archetype = bot.get('archetype', 'casual_observer')
        avatar_name = bot.get('avatar_name', bot.get('name'))
        
        print(f"\n📝 {avatar_name} ({archetype}) is posting...")
        
        # Get appropriate post prompt
        post_prompt = get_post_prompt(archetype)
        
        # Generate post using intelligent avatar
        result = await self.intelligent_avatar.generate_avatar_post(
            bot['id'],
            post_type="general"
        )
        
        if 'content' in result:
            # Save to avatar_posts (using frontend-compatible field names)
            post = {
                "text": result['content'],  # Frontend expects 'text'
                "content": result['content'],  # Keep for compatibility
                "created_at": datetime.now(timezone.utc).isoformat(),  # Frontend expects 'created_at'
                "timestamp": datetime.now(timezone.utc).isoformat(),  # Keep for compatibility
                "generated": True,
                "archetype": archetype,
                "likes": 0,
                "comments": []
            }
            
            await self.db.users.update_one(
                {"id": bot['id']},
                {
                    "$push": {"avatar_posts": post},
                    "$set": {
                        "last_activity": datetime.now(timezone.utc),
                        "next_post_time": datetime.now(timezone.utc) + timedelta(
                            hours=get_post_delay_hours(archetype)
                        )
                    }
                }
            )
            
            self.current_api_calls += 1
            
            print(f"   ✅ Posted: \"{result['content'][:60]}...\"")
            
            # Log activity
            await self._log_activity(bot['id'], 'post', {
                'content_preview': result['content'][:100],
                'archetype': archetype
            })
        else:
            print(f"   ❌ Post generation failed: {result.get('error')}")
    
    async def _start_bot_conversation(self, bot: Dict):
        """Start a conversation between two bots"""
        archetype = bot.get('archetype', 'casual_observer')
        avatar_name = bot.get('avatar_name', bot.get('name'))
        
        print(f"\n💬 {avatar_name} ({archetype}) wants to chat...")
        
        # Find a conversation partner
        partner = await self._find_conversation_partner(bot)
        
        if not partner:
            print(f"   ⚠️  No suitable conversation partner found")
            return
        
        partner_name = partner.get('avatar_name', partner.get('name'))
        print(f"   Partner: {partner_name}")
        
        # Check if they have shared interests
        bot_interests = set(bot.get('interests', []))
        partner_interests = set(partner.get('interests', []))
        shared_interests = list(bot_interests & partner_interests)
        
        if shared_interests:
            topic = random.choice(shared_interests)
            print(f"   Topic: {topic}")
        else:
            topic = "general interests"
        
        # Generate conversation starter
        conversation_starters = [
            f"Hey! I noticed you're into {topic}. What do you think about it?",
            f"Hi! I've been really interested in {topic} lately. Do you have any recommendations?",
            f"Hello! I saw your profile and we both love {topic}. How did you get into it?",
            f"Hey there! Want to chat about {topic}?",
        ]
        
        starter_message = random.choice(conversation_starters)
        
        # Create conversation record
        conversation = {
            "participants": [bot['id'], partner['id']],
            "messages": [
                {
                    "sender_id": bot['id'],
                    "sender_name": avatar_name,
                    "content": starter_message,
                    "timestamp": datetime.now(timezone.utc),
                    "generated": True
                }
            ],
            "status": "active",
            "topic": topic,
            "started_at": datetime.now(timezone.utc),
            "bot_archetypes": {
                bot['id']: archetype,
                partner['id']: partner.get('archetype', 'casual_observer')
            }
        }
        
        result = await self.db.avatar_conversations.insert_one(conversation)
        conversation_id = str(result.inserted_id)
        
        print(f"   ✅ Started: \"{starter_message[:50]}...\"")
        
        # Generate response from partner
        await self._continue_conversation(conversation_id, partner)
        
        self.current_api_calls += 2  # Initial message + response
        
        # Log activity
        await self._log_activity(bot['id'], 'conversation', {
            'partner_id': partner['id'],
            'partner_name': partner_name,
            'topic': topic
        })
    
    async def _find_conversation_partner(self, bot: Dict) -> Optional[Dict]:
        """Find a suitable conversation partner for a bot"""
        # Get bot's friends first (preferred)
        friendships = await self.db.friendships.find({
            "$or": [
                {"requester_id": bot['id'], "status": "accepted"},
                {"recipient_id": bot['id'], "status": "accepted"}
            ]
        }, {"_id": 0}).to_list(100)
        
        friend_ids = []
        for friendship in friendships:
            if friendship['requester_id'] == bot['id']:
                friend_ids.append(friendship['recipient_id'])
            else:
                friend_ids.append(friendship['requester_id'])
        
        # Get recent conversation partners to avoid repetition
        recent_conversations = await self.db.avatar_conversations.find({
            "participants": bot['id'],
            "started_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        }, {"_id": 0}).to_list(10)
        
        recent_partner_ids = set()
        for conv in recent_conversations:
            for p_id in conv['participants']:
                if p_id != bot['id']:
                    recent_partner_ids.add(p_id)
        
        # Find partners (friends first, then shared interests)
        if friend_ids:
            available_friends = [fid for fid in friend_ids if fid not in recent_partner_ids]
            if available_friends:
                partner_id = random.choice(available_friends)
                partner = await self.db.users.find_one({"id": partner_id}, {"_id": 0})
                if partner:
                    return partner
        
        # Fallback: Find bot with shared interests
        bot_interests = bot.get('interests', [])
        if bot_interests:
            partners = await self.db.users.find({
                "is_bot": True,
                "id": {"$ne": bot['id'], "$nin": list(recent_partner_ids)},
                "interests": {"$in": bot_interests}
            }, {"_id": 0}).limit(10).to_list(10)
            
            if partners:
                return random.choice(partners)
        
        return None
    
    async def _continue_conversation(self, conversation_id: str, responding_bot: Dict):
        """Generate a response in an ongoing conversation"""
        from bson import ObjectId
        
        conversation = await self.db.avatar_conversations.find_one(
            {"_id": ObjectId(conversation_id)}
        )
        
        if not conversation:
            return
        
        # Get conversation history
        messages = conversation.get('messages', [])
        last_message = messages[-1]['content'] if messages else ""
        
        # Generate response using intelligent avatar
        result = await self.intelligent_avatar.generate_chat_response(
            responding_bot['id'],
            messages[-1]['sender_id'],
            messages,
            last_message
        )
        
        if 'content' in result:
            response_message = {
                "sender_id": responding_bot['id'],
                "sender_name": responding_bot.get('avatar_name', responding_bot.get('name')),
                "content": result['content'],
                "timestamp": datetime.now(timezone.utc),
                "generated": True
            }
            
            await self.db.avatar_conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$push": {"messages": response_message}}
            )
            
            partner_name = responding_bot.get('avatar_name', responding_bot.get('name'))
            print(f"   💬 {partner_name} replied: \"{result['content'][:50]}...\"")
    
    async def _log_activity(self, bot_id: str, activity_type: str, details: Dict):
        """Log bot activity for analytics"""
        log_entry = {
            "bot_id": bot_id,
            "activity_type": activity_type,
            "timestamp": datetime.now(timezone.utc),
            "details": details,
            "success": True
        }
        
        await self.db.autonomous_activities.insert_one(log_entry)
        self.activity_log.append(log_entry)
    
    async def get_activity_stats(self) -> Dict[str, Any]:
        """Get statistics about autonomous activities"""
        stats = {
            "total_activities": len(self.activity_log),
            "api_calls_used": self.current_api_calls,
            "api_budget_remaining": self.api_call_budget - self.current_api_calls,
            "activities_by_type": {}
        }
        
        for entry in self.activity_log:
            activity_type = entry['activity_type']
            stats['activities_by_type'][activity_type] = \
                stats['activities_by_type'].get(activity_type, 0) + 1
        
        return stats
    
    def reset_api_counter(self):
        """Reset API call counter (call this hourly)"""
        self.current_api_calls = 0
        print("🔄 API call counter reset")

