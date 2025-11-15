"""
TURBO TEST MODE - Forces high action probability for rapid testing
Modifies SimpleReactiveAgent to have 80% post chance instead of 20%
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncAzureOpenAI
from simple_agent_manager import SimpleAgentManager
from datetime import datetime
import time

# Monkey patch the SimpleReactiveAgent run_cycle method
from simple_reactive_agent import SimpleReactiveAgent
original_run_cycle = SimpleReactiveAgent.run_cycle

async def turbo_run_cycle(self):
    """Turbo cycle with 80% post chance (instead of 20%)"""
    try:
        avatar_indicator = "✨ USER AVATAR" if self.is_user_avatar else "🤖"
        print(f"\n{'='*60}")
        print(f"🔄 {self.bot.get('avatar_name')} activity cycle {avatar_indicator}")
        print(f"{'='*60}")
        
        # Check if we're at action limit
        if self.actions_this_hour >= self.max_actions_per_hour:
            print(f"⏸️  Action limit reached for this hour")
            return
        
        # 1. React to posts (50% of time - reduced from 60%)
        if random.random() < 0.5:
            await self._react_to_posts()
        
        # 2. Create own post (80% of time - INCREASED from 20% for testing!)
        print(f"   🎲 Rolling dice for post creation (80% chance)...")
        if random.random() < 0.8:
            print(f"   🎯 ATTEMPTING POST CREATION...")
            await self._create_post()
        else:
            print(f"   ⚠️ Dice roll failed (not posting this cycle)")
        
        # 3. Check friend requests (30% of time)
        if random.random() < 0.3:
            await self._check_friend_requests()
        
        # 4. Discover new profiles (10% of time)
        if random.random() < 0.1:
            await self._discover_profiles()
        
        from datetime import datetime, timezone
        self.last_action_time = datetime.now(timezone.utc)
        
    except Exception as e:
        print(f"❌ Error in {self.bot.get('avatar_name')} cycle: {e}")
        import traceback
        traceback.print_exc()

# Apply the monkey patch
import random
SimpleReactiveAgent.run_cycle = turbo_run_cycle

# Load environment
load_dotenv()

# Configuration
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "neurallinks_local"
CYCLE_INTERVAL = 120  # 2 minutes (HYPO mode)

# Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPENAI_SERVICE")
if AZURE_OPENAI_ENDPOINT and not AZURE_OPENAI_ENDPOINT.startswith('https://'):
    AZURE_OPENAI_ENDPOINT = f"https://{AZURE_OPENAI_ENDPOINT}.openai.azure.com"

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")

async def main():
    print("\n" + "="*80)
    print("🚀 TURBO TEST MODE - 80% POST CHANCE (2-minute cycles)")
    print("="*80)
    print(f"💡 This mode increases post probability from 20% → 80%")
    print(f"⏱️  Cycles run every {CYCLE_INTERVAL} seconds")
    print(f"🎯 DigitalHunter should post within 1-2 cycles!")
    print("="*80 + "\n")
    
    # Verify Azure OpenAI configuration
    if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]):
        print("❌ ERROR: Azure OpenAI configuration incomplete!")
        print(f"   AZURE_OPENAI_ENDPOINT: {AZURE_OPENAI_ENDPOINT or 'MISSING'}")
        print(f"   AZURE_OPENAI_API_KEY: {'SET' if AZURE_OPENAI_API_KEY else 'MISSING'}")
        print(f"   AZURE_OPENAI_DEPLOYMENT: {AZURE_OPENAI_DEPLOYMENT or 'MISSING'}")
        return
    
    # Initialize connections
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    # Test database connection
    try:
        await db.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return
    
    # Initialize LLM
    llm_client = AsyncAzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_API_VERSION
    )
    print(f"✅ Azure OpenAI configured: {AZURE_OPENAI_DEPLOYMENT}")
    print()
    
    # Initialize agent manager
    manager = SimpleAgentManager(
        db=db,
        llm_client=llm_client,
        deployment=AZURE_OPENAI_DEPLOYMENT
    )
    
    await manager.initialize_agents()
    
    # Run cycles
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n{'='*80}")
            print(f"📍 TURBO CYCLE #{cycle_count}")
            print(f"{'='*80}")
            
            await manager.run_single_cycle()
            
            print(f"\n{'='*80}")
            print(f"✅ Cycle complete")
            print(f"{'='*80}")
            print(f"⏳ Sleeping for {CYCLE_INTERVAL} seconds...")
            
            next_cycle_time = datetime.now()
            next_cycle_time = next_cycle_time.replace(second=next_cycle_time.second + CYCLE_INTERVAL)
            print(f"   Next cycle at: {next_cycle_time.strftime('%H:%M:%S')}")
            print(f"{'='*80}\n")
            
            time.sleep(CYCLE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())




