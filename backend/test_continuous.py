#!/usr/bin/env python3
"""Quick test of continuous mode"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from dotenv import load_dotenv
from domain.avatar.manager import SimpleAgentManager
from core.config import get_openai_client, OPENAI_MODEL

load_dotenv('.env')

async def main():
    client = AsyncIOMotorClient(os.getenv("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.getenv("DB_NAME", "neurallinks_local")]
    
    llm_client = get_openai_client()
    if not llm_client:
        print("❌ OpenAI not configured. Set OPENAI_API_KEY environment variable.")
        return
    
    manager = SimpleAgentManager(db=db, llm_client=llm_client, deployment=OPENAI_MODEL)
    await manager.initialize_agents()
    
    print(f"\n✅ Starting continuous mode with {len(manager.agents)} agents")
    print("   Agents will run continuously (press Ctrl+C after 30 seconds to stop)\n")
    
    # Run for 30 seconds to test
    try:
        await asyncio.wait_for(manager.run_continuously(), timeout=30.0)
    except asyncio.TimeoutError:
        print("\n✅ Test complete - agents were running continuously!")
        manager.stop()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
