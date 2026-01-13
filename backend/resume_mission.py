"""
Resume a stuck mission directly
"""
import asyncio
import os
import sys

# Environment variables should be set externally
# MONGODB_URI, DB_NAME, OPENAI_API_KEY

from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from domain.workflow.engines.engine_registry import WorkflowEngineRegistry
from domain.workflow.mcp.tools import WorkflowMCPServer
from domain.avatar.intelligent_avatar import IntelligentAvatar

async def resume_mission(mission_id: str):
    """Resume a stuck mission"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.environ['MONGODB_URI'])
    db = client[os.environ['DB_NAME']]
    
    # Initialize OpenAI
    openai_client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'])
    
    # Initialize MCP server
    mcp_server = WorkflowMCPServer(db, openai_client)
    
    # Initialize IntelligentAvatar
    intelligent_avatar = IntelligentAvatar(openai_client)
    
    # Get mission
    mission_doc = await db.missions.find_one({"id": mission_id})
    if not mission_doc:
        print(f"❌ Mission {mission_id} not found")
        return
    
    mission_type = mission_doc.get("type", "matchmaking")
    avatar_id = mission_doc.get("avatar_id")
    
    print(f"🚀 Resuming mission: {mission_id} (type: {mission_type})")
    print(f"   Current status: {mission_doc.get('status')}, phase: {mission_doc.get('phase')}")
    
    # Get workflow engine
    engine = WorkflowEngineRegistry.get_engine(
        mission_type=mission_type,
        db=db,
        mcp_server=mcp_server,
        openai_client=openai_client,
        intelligent_avatar=intelligent_avatar
    )
    
    if not engine:
        print(f"❌ No engine found for mission type: {mission_type}")
        return
    
    print(f"🔧 Using {engine.engine_name} workflow engine")
    
    # Execute mission
    try:
        result = await asyncio.wait_for(
            engine.execute(mission_id, avatar_id),
            timeout=240.0
        )
        print(f"✅ Mission completed!")
        print(f"   Result: {result}")
    except asyncio.TimeoutError:
        print(f"⏱️  Mission timed out after 4 minutes - progress saved")
    except Exception as e:
        print(f"❌ Mission failed: {e}")
        import traceback
        traceback.print_exc()
    
    client.close()

if __name__ == "__main__":
    mission_id = sys.argv[1] if len(sys.argv) > 1 else "5d487969-97c3-4f62-8935-35c4cc3e7dc5"
    asyncio.run(resume_mission(mission_id))
