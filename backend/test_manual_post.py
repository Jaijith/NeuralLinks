"""
Quick test to see if DigitalHunter can generate ONE post manually
This will help us find where the system is failing
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
import os
from dotenv import load_dotenv
from graph_rag import GraphRAG
from intelligent_avatar import IntelligentAvatar
import sys

load_dotenv()

async def test_post():
    print("\n" + "="*80)
    print("🧪 TESTING DIGITALHUNTER POST GENERATION")
    print("="*80 + "\n")
    
    # Step 1: MongoDB Connection
    print("1️⃣ Testing MongoDB connection...")
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client["neurallinks_local"]
        await db.command("ping")
        print("   ✅ MongoDB connected")
    except Exception as e:
        print(f"   ❌ MongoDB failed: {e}")
        sys.exit(1)
    
    # Step 2: Azure OpenAI Setup
    print("\n2️⃣ Setting up Azure OpenAI...")
    try:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if not all([endpoint, api_key, deployment]):
            print(f"   ❌ Missing env vars!")
            print(f"      AZURE_OPENAI_ENDPOINT: {'✓' if endpoint else '✗'}")
            print(f"      AZURE_OPENAI_API_KEY: {'✓' if api_key else '✗'}")
            print(f"      AZURE_OPENAI_DEPLOYMENT: {'✓' if deployment else '✗'}")
            sys.exit(1)
        
        llm = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-02-01-preview"
        )
        print(f"   ✅ Azure OpenAI configured")
        print(f"      Endpoint: {endpoint}")
        print(f"      Deployment: {deployment}")
    except Exception as e:
        print(f"   ❌ Azure OpenAI setup failed: {e}")
        sys.exit(1)
    
    # Step 3: Graph RAG Initialization
    print("\n3️⃣ Initializing Graph RAG...")
    try:
        graph_rag = GraphRAG(db)
        print("   ✅ Graph RAG initialized")
    except Exception as e:
        print(f"   ❌ Graph RAG failed: {e}")
        sys.exit(1)
    
    # Step 4: Get DigitalHunter's Profile from Graph
    print("\n4️⃣ Fetching DigitalHunter's personality profile...")
    try:
        user_id = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
        profile = await graph_rag.get_avatar_personality_profile(user_id)
        print("   ✅ Profile retrieved:")
        print(f"      {profile[:200]}...")
    except Exception as e:
        print(f"   ❌ Profile retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 5: Intelligent Avatar Setup
    print("\n5️⃣ Creating IntelligentAvatar...")
    try:
        avatar = IntelligentAvatar(db, llm, deployment, graph_rag)
        print("   ✅ IntelligentAvatar created")
    except Exception as e:
        print(f"   ❌ IntelligentAvatar creation failed: {e}")
        sys.exit(1)
    
    # Step 6: Generate Post
    print("\n6️⃣ Generating post for DigitalHunter...")
    print("   ⏳ This may take 5-10 seconds (calling LLM)...")
    try:
        result = await avatar.generate_avatar_post(
            user_id=user_id,
            post_type="general"
        )
        
        if 'error' in result:
            print(f"   ❌ Post generation returned error:")
            print(f"      {result['error']}")
            sys.exit(1)
        else:
            print(f"   ✅ Post generated successfully!")
            print(f"\n📝 Generated Post:")
            print(f"   \"{result.get('content', result)}\"")
            print(f"\n   Type: {result.get('type', 'unknown')}")
            print(f"   Generated at: {result.get('generated_at', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Post generation EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback
        print("\n   Full traceback:")
        traceback.print_exc()
        sys.exit(1)
    
    # Step 7: Summary
    print("\n" + "="*80)
    print("🎉 ALL TESTS PASSED!")
    print("="*80)
    print("\n✅ DigitalHunter CAN generate posts using Graph RAG!")
    print("\nThis means the issue is elsewhere in the autonomous system.")
    print("Likely causes:")
    print("  • Exception handling in SimpleReactiveAgent suppressing errors")
    print("  • Cycle logic not reaching post generation")
    print("  • Random chance preventing post creation (check probabilities)")
    
    client.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_post())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()




