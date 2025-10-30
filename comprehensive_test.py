#!/usr/bin/env python3
"""
Comprehensive test to verify all Graph RAG functionality
"""

import asyncio
import httpx
import json

BACKEND_URL = "https://sense-maya.preview.emergentagent.com/api"
SESSION_TOKEN = "test_session_1761825596222"

async def test_comprehensive_graph_rag():
    """Test comprehensive Graph RAG functionality"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}
        
        print("🧪 Comprehensive Graph RAG Test Suite")
        print("=" * 50)
        
        # 1. Test Avatar Chat Response
        print("\n1. Testing Avatar Chat Response...")
        chat_data = {
            "other_user_id": "test_other_user",
            "conversation_history": [
                {"sender_id": "test_other_user", "content": "Hi! I love hiking too!"},
                {"sender_id": "test-graphrag-user-1761825596222", "content": "That's awesome! Where do you like to hike?"}
            ],
            "last_message": "I usually hike in the Bay Area. Do you have any favorite trails?"
        }
        
        response = await client.post(
            f"{BACKEND_URL}/avatar/chat-response",
            json=chat_data,
            headers=headers
        )
        
        if response.status_code == 200:
            chat_response = response.json()
            content = chat_response.get("content", "")
            print(f"✅ Chat Response Generated: {len(content)} characters")
            print(f"   Sample: {content[:100]}...")
        else:
            print(f"❌ Chat Response Failed: {response.status_code}")
        
        # 2. Test Match Explanation
        print("\n2. Testing Match Explanation...")
        response = await client.get(
            f"{BACKEND_URL}/avatar/match-explanation/test_match_user",
            headers=headers
        )
        
        if response.status_code == 200:
            explanation = response.json().get("explanation", "")
            print(f"✅ Match Explanation: {explanation}")
        else:
            print(f"❌ Match Explanation Failed: {response.status_code}")
        
        # 3. Test Graph Compatibility
        print("\n3. Testing Graph Compatibility...")
        response = await client.get(
            f"{BACKEND_URL}/graph/compatibility/test_other_user",
            headers=headers
        )
        
        if response.status_code == 200:
            compatibility = response.json()
            score = compatibility.get("compatibility_score", 0)
            shared = compatibility.get("shared_interests", [])
            print(f"✅ Compatibility Score: {score}%")
            print(f"   Shared Interests: {shared}")
        else:
            print(f"❌ Compatibility Test Failed: {response.status_code}")
        
        # 4. Test Graph Interaction Enrichment
        print("\n4. Testing Graph Interaction Enrichment...")
        interaction_data = {
            "target_user_id": "test_target_user",
            "interaction_type": "match"
        }
        
        response = await client.post(
            f"{BACKEND_URL}/graph/enrich-from-interaction",
            json=interaction_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Graph Interaction Enrichment: Success")
        else:
            print(f"❌ Graph Interaction Enrichment Failed: {response.status_code}")
        
        # 5. Test Multiple Platform Integrations
        print("\n5. Testing Multiple Platform Integrations...")
        platforms = ["youtube", "instagram", "goodreads"]
        
        for platform in platforms:
            # Connect
            connect_response = await client.post(
                f"{BACKEND_URL}/integrations/connect",
                json={"platform_name": platform},
                headers=headers
            )
            
            if connect_response.status_code == 200:
                print(f"✅ Connected to {platform}")
                
                # Sync
                sync_response = await client.post(
                    f"{BACKEND_URL}/integrations/sync",
                    json={"platform_name": platform},
                    headers=headers
                )
                
                if sync_response.status_code == 200:
                    sync_data = sync_response.json()
                    nodes_added = sync_data.get("nodes_added", 0)
                    print(f"   Synced {platform}: {nodes_added} nodes added")
                else:
                    print(f"   ❌ Sync failed for {platform}")
            else:
                print(f"❌ Connection failed for {platform}")
        
        # 6. Test Final Graph State
        print("\n6. Testing Final Graph State...")
        response = await client.get(
            f"{BACKEND_URL}/graph/context",
            headers=headers
        )
        
        if response.status_code == 200:
            context = response.json()
            total_nodes = sum(len(context.get(key, [])) for key in context.keys())
            print(f"✅ Final Graph State: {total_nodes} total nodes")
            
            for category, items in context.items():
                if items:
                    print(f"   {category}: {len(items)} items")
                    # Show top 3 items
                    for item in items[:3]:
                        label = item.get("label", "")
                        strength = item.get("strength", 0)
                        print(f"     - {label} (strength: {strength})")
        else:
            print(f"❌ Final Graph State Failed: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("🎉 Comprehensive Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_graph_rag())