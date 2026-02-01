"""
Lambda Handler for FastAPI Application
Wraps FastAPI app with Mangum for AWS Lambda compatibility

CRITICAL: Handler MUST be a function at module level - DO NOT REDEFINE IT
"""

# CRITICAL: Define handler as a function FIRST before any imports
# Lambda runtime looks for 'handler' function in this module
# We'll use a closure pattern so the function is never redefined

# Use a mutable container to hold the actual handler
_handler_impl = [None]

def handler(event, context):
    """Lambda handler function - delegates to actual implementation"""
    if _handler_impl[0] is not None:
        return _handler_impl[0](event, context)
    else:
        # Fallback if handler not initialized
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"error": "Handler not initialized"}'
        }

import os
import logging
import sys

# Configure logging for Lambda - must use root logger and set format
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove default handlers and add our own
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

handler_stdout = logging.StreamHandler(sys.stdout)
handler_stdout.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
handler_stdout.setFormatter(formatter)
root_logger.addHandler(handler_stdout)

logger = logging.getLogger(__name__)

def get_secret(secret_name: str) -> str:
    """Get secret from AWS Secrets Manager"""
    try:
        import boto3
        import json
        
        client = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
        response = client.get_secret_value(SecretId=secret_name)
        secret = response['SecretString']
        # If secret is JSON, parse it
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret
    except Exception as e:
        logger.error(f"Error fetching secret {secret_name}: {e}")
        return ""

# Set environment variables from secrets (only if secret names are provided)
try:
    mongodb_secret_name = os.environ.get('MONGODB_SECRET_NAME')
    if mongodb_secret_name:
        secret_value = get_secret(mongodb_secret_name)
        if secret_value:
            os.environ['MONGODB_URI'] = secret_value
            logger.info("MongoDB URI set from Secrets Manager")
        else:
            logger.warning("MongoDB secret not found or empty")

    google_client_id_secret_name = os.environ.get('GOOGLE_CLIENT_ID_SECRET_NAME')
    if google_client_id_secret_name:
        secret_value = get_secret(google_client_id_secret_name)
        if secret_value:
            os.environ['GOOGLE_CLIENT_ID'] = secret_value
            logger.info("Google Client ID set from Secrets Manager")
        else:
            logger.warning("Google Client ID secret not found or empty")

    google_client_secret_secret_name = os.environ.get('GOOGLE_CLIENT_SECRET_SECRET_NAME')
    if google_client_secret_secret_name:
        secret_value = get_secret(google_client_secret_secret_name)
        if secret_value:
            os.environ['GOOGLE_CLIENT_SECRET'] = secret_value
            logger.info("Google Client Secret set from Secrets Manager")
        else:
            logger.warning("Google Client Secret not found or empty")

    # OpenAI API Key
    openai_secret_name = os.environ.get('OPENAI_SECRET_NAME')
    if openai_secret_name:
        secret_value = get_secret(openai_secret_name)
        if secret_value:
            os.environ['OPENAI_API_KEY'] = secret_value
            logger.info("OpenAI API Key set from Secrets Manager")
        else:
            logger.warning("OpenAI API Key secret not found or empty")
except Exception as e:
    logger.error(f"Error setting up secrets: {e}")
    # Continue anyway - app might work without secrets in some cases

# Import FastAPI app after secrets are set
# Initialize the actual handler implementation
try:
    from mangum import Mangum
    from app.main import app
    
    # Wrap FastAPI app with Mangum
    # lifespan="off" disables FastAPI lifespan events (startup/shutdown)
    # This is recommended for Lambda to avoid issues with connection pooling
    mangum_adapter = Mangum(app, lifespan="off")
    
    async def run_single_avatar_cycle(avatar_id: str, force_action: str = None):
        """Run autonomous cycle for a single avatar
        
        Args:
            avatar_id: The avatar's user ID
            force_action: Optional action to force (bypasses cooldown), e.g., 'create_post'
        """
        print(f"📍 run_single_avatar_cycle() started for avatar: {avatar_id}, force_action: {force_action}")
        from motor.motor_asyncio import AsyncIOMotorClient
        from domain.avatar.state_aware_agent import StateAwareAgent
        from domain.avatar.intelligent import IntelligentAvatar
        from domain.graph.rag import GraphRAG
        from openai import AsyncOpenAI
        
        # Create fresh database connection for this invocation
        mongodb_uri = os.environ.get('MONGODB_URI')
        print(f"📍 MongoDB URI present: {bool(mongodb_uri)}")
        if not mongodb_uri:
            logger.error("❌ MONGODB_URI not set")
            return {"processed": 0, "errors": 1, "error": "MONGODB_URI not set"}
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.neurallinks_local
        
        # Create fresh OpenAI client using config
        from core.config import get_openai_client, OPENAI_MODEL
        
        openai_client = get_openai_client()
        openai_model = OPENAI_MODEL
        
        # Create intelligent avatar for this invocation
        graph_rag = GraphRAG(db)
        local_intelligent_avatar = None
        if openai_client:
            local_intelligent_avatar = IntelligentAvatar(db, openai_client, openai_model, graph_rag)
        
        try:
            # Find the specific user
            user = await db.users.find_one(
                {"id": avatar_id},
                {"_id": 0}
            )
            
            if not user:
                logger.error(f"❌ User {avatar_id} not found")
                return {"processed": 0, "errors": 1, "error": "User not found"}
            
            # Verify autonomy is still enabled
            if not user.get('avatar_autonomous', False):
                logger.info(f"ℹ️ Autonomy disabled for {avatar_id}, skipping")
                return {"processed": 0, "errors": 0, "skipped": True}
            
            avatar_name = user.get('avatar_name', 'Unknown')
            activity_level = user.get('avatar_activity_level', 'medium')
            
            agent = StateAwareAgent(
                bot=user,
                db=db,
                intelligent_avatar=local_intelligent_avatar
            )
            await agent.initialize()
            
            # Log activity level info
            logger.info(
                f"🎯 {avatar_name}: Activity={activity_level}, "
                f"Max={agent.max_actions_per_day}/day, "
                f"Interval={agent.min_action_interval.total_seconds()/60:.0f}min"
            )
            
            # Run cycle with optional forced action
            await agent._run_single_cycle(force_action=force_action)
            logger.info(f"✅ Processed {avatar_name}")
            return {"processed": 1, "errors": 0, "avatar_name": avatar_name}
            
        except Exception as e:
            logger.error(f"❌ Error processing avatar {avatar_id}: {e}", exc_info=True)
            return {"processed": 0, "errors": 1, "error": str(e)}
        finally:
            # Close the database connection
            client.close()
    
    async def run_autonomous_cycle():
        """Run autonomous cycle for all enabled avatars (legacy - for backward compatibility)"""
        import time
        start_time = time.time()
        MAX_EXECUTION_TIME = 90  # Stop processing after 90 seconds to avoid timeout
        MAX_AVATARS_PER_CYCLE = 5  # Process max 5 avatars per cycle to reduce costs
        
        print("📍 run_autonomous_cycle() started (legacy batch mode)")
        from motor.motor_asyncio import AsyncIOMotorClient
        from domain.avatar.state_aware_agent import StateAwareAgent
        from domain.avatar.intelligent import IntelligentAvatar
        from domain.graph.rag import GraphRAG
        from openai import AsyncOpenAI
        
        # Create fresh database connection for this invocation
        mongodb_uri = os.environ.get('MONGODB_URI')
        print(f"📍 MongoDB URI present: {bool(mongodb_uri)}")
        if not mongodb_uri:
            logger.error("❌ MONGODB_URI not set")
            return {"processed": 0, "errors": 0, "error": "MONGODB_URI not set"}
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.neurallinks_local
        
        # Create fresh OpenAI client using config
        from core.config import get_openai_client, OPENAI_MODEL
        
        openai_client = get_openai_client()
        openai_model = OPENAI_MODEL
        
        # Create intelligent avatar for this invocation
        graph_rag = GraphRAG(db)
        local_intelligent_avatar = None
        if openai_client:
            local_intelligent_avatar = IntelligentAvatar(db, openai_client, openai_model, graph_rag)
        
        try:
            # Find all users with autonomy enabled (including bots for testing)
            query = {
                "avatar_autonomous": True,
                "avatar_name": {"$exists": True, "$ne": None},
                "avatar_picture": {"$exists": True, "$ne": None}
                # Note: Removed is_bot filter to include bot avatars
            }
            
            users = await db.users.find(query, {"_id": 0}).to_list(100)
            
            if not users:
                logger.info("ℹ️ No users with autonomy enabled")
                return {"processed": 0, "errors": 0}
            
            logger.info(f"📊 Found {len(users)} user(s) with autonomy enabled")
            
            # ROTATION: Calculate offset based on current time to rotate through avatars
            # Each cycle will start from a different position in the list
            from datetime import datetime, timezone
            import random
            
            # Get or create a cycle counter from the database
            cycle_doc = await db.system_config.find_one({"key": "avatar_cycle_offset"})
            current_offset = cycle_doc.get("value", 0) if cycle_doc else 0
            
            # Rotate the list: start from the offset position
            total_users = len(users)
            rotated_users = users[current_offset:] + users[:current_offset]
            
            # Update the offset for next cycle (wrap around)
            next_offset = (current_offset + MAX_AVATARS_PER_CYCLE) % total_users
            await db.system_config.update_one(
                {"key": "avatar_cycle_offset"},
                {"$set": {"value": next_offset, "updated_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            
            logger.info(f"🔄 Rotation: offset={current_offset}, next_offset={next_offset}, processing from index {current_offset}")
            
            processed = 0
            errors = 0
            skipped = 0
            
            for user in rotated_users:
                # Check time limit to avoid Lambda timeout
                elapsed = time.time() - start_time
                if elapsed > MAX_EXECUTION_TIME:
                    logger.warning(f"⏱️ Time limit reached ({elapsed:.1f}s), stopping cycle")
                    break
                
                # Limit avatars per cycle to reduce costs
                if processed >= MAX_AVATARS_PER_CYCLE:
                    logger.info(f"📊 Avatar limit reached ({MAX_AVATARS_PER_CYCLE}), stopping cycle")
                    break
                user_id = user.get('id')
                avatar_name = user.get('avatar_name', 'Unknown')
                activity_level = user.get('avatar_activity_level', 'medium')
                
                try:
                    agent = StateAwareAgent(
                        bot=user,
                        db=db,
                        intelligent_avatar=local_intelligent_avatar
                    )
                    await agent.initialize()
                    
                    # Log activity level info
                    logger.info(
                        f"🎯 {avatar_name}: Activity={activity_level}, "
                        f"Max={agent.max_actions_per_day}/day, "
                        f"Interval={agent.min_action_interval.total_seconds()/60:.0f}min"
                    )
                    
                    await agent._run_single_cycle()
                    processed += 1
                    logger.info(f"✅ Processed {avatar_name}")
                except Exception as e:
                    logger.error(f"❌ Error processing {avatar_name}: {e}")
                    errors += 1
            
            logger.info(f"📈 Cycle complete: processed={processed}, errors={errors}")
            return {"processed": processed, "errors": errors}
        finally:
            # Close the database connection
            client.close()
    
    def eventbridge_handler(event, context):
        """Handle EventBridge scheduled events for autonomous cycles"""
        import asyncio
        import json
        
        print(f"🤖 EventBridge handler invoked!")
        print(f"🤖 Event keys: {list(event.keys())}")
        print(f"🤖 Full event: {json.dumps(event, default=str)[:500]}")
        
        # Check if this is a single avatar cycle or batch cycle
        detail = event.get('detail', {})
        source = event.get('source', '')
        
        # EventBridge scheduled rules put custom Input JSON in the detail field
        # The detail might be a string (JSON) or already a dict
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
                print(f"🤖 Parsed detail from string: {detail}")
            except json.JSONDecodeError:
                detail = {}
                print(f"🤖 Failed to parse detail as JSON")
        
        # Check if detail contains avatar cycle info
        detail_source = detail.get('source', '')
        detail_action = detail.get('action', '')
        
        print(f"🤖 Event source: {source}, detail source: {detail_source}, detail action: {detail_action}")
        
        # New format: single avatar cycle (check both event source and detail source)
        # EventBridge may put avatar_id at top level or in detail
        avatar_id = event.get('avatar_id') or detail.get('avatar_id')
        print(f"🤖 Avatar ID from event: {event.get('avatar_id')}, from detail: {detail.get('avatar_id')}, final: {avatar_id}")
        
        # Check for force_action parameter
        force_action = event.get('force_action') or detail.get('force_action')
        
        if (source == 'avatar.cycle' or detail_source == 'avatar.cycle' or 
            detail_action == 'run_single_avatar_cycle' or detail_action == 'run_single_avatar' or avatar_id):
            if avatar_id:
                print(f"🎯 Detected single avatar cycle for: {avatar_id}, force_action: {force_action}")
                logger.info(f"🎯 Processing single avatar cycle for: {avatar_id}")
                try:
                    # For Lambda, we need to handle the event loop carefully
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run single avatar cycle with optional force_action
                    result = loop.run_until_complete(run_single_avatar_cycle(avatar_id, force_action=force_action))
                    
                    logger.info(f"✅ Single avatar cycle complete: {result}")
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'success': True,
                            'processed': result.get('processed', 0),
                            'errors': result.get('errors', 0),
                            'avatar_id': avatar_id
                        })
                    }
                except Exception as e:
                    logger.error(f"❌ Single avatar cycle failed for {avatar_id}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {
                        'statusCode': 500,
                        'body': json.dumps({'success': False, 'error': str(e), 'avatar_id': avatar_id})
                    }
        
        # Legacy format: batch cycle (all avatars)
        logger.info(f"🤖 EventBridge trigger received: {event.get('detail-type', 'Unknown')} (batch mode)")
        try:
            # For Lambda, we need to handle the event loop carefully
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the autonomous cycle (legacy batch mode)
            result = loop.run_until_complete(run_autonomous_cycle())
            
            logger.info(f"✅ Autonomous cycle complete: {result}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'processed': result.get('processed', 0),
                    'errors': result.get('errors', 0)
                })
            }
        except Exception as e:
            logger.error(f"❌ Autonomous cycle failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'body': json.dumps({'success': False, 'error': str(e)})
            }
    
    async def process_voice_memory(session_id: str = None):
        """Process voice transcript and extract memories
        
        Args:
            session_id: Specific session to process, or None to process all unprocessed
        """
        from motor.motor_asyncio import AsyncIOMotorClient
        from domain.voice.voice_memory import VoiceMemoryService
        from openai import AsyncOpenAI
        
        print(f"🧠 Voice memory processing started: session_id={session_id}")
        
        mongodb_uri = os.environ.get('MONGODB_URI')
        if not mongodb_uri:
            logger.error("❌ MONGODB_URI not set")
            return {"processed": 0, "errors": 1, "error": "MONGODB_URI not set"}
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.neurallinks_local
        
        try:
            # Get OpenAI client
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                logger.error("❌ OPENAI_API_KEY not set")
                return {"processed": 0, "errors": 1, "error": "OPENAI_API_KEY not set"}
            
            openai_client = AsyncOpenAI(api_key=openai_api_key)
            memory_service = VoiceMemoryService(db)
            
            processed = 0
            errors = 0
            
            if session_id:
                # Process specific session
                result = await memory_service.extract_and_store_memories(session_id, openai_client)
                if result.get("success"):
                    processed = 1
                else:
                    errors = 1
                    logger.error(f"❌ Memory extraction failed: {result.get('error')}")
            else:
                # Process all unprocessed transcripts (daily backup)
                # Get all unprocessed transcripts
                cursor = db.voice_transcripts.find({"processed": False}).limit(50)
                transcripts = await cursor.to_list(length=50)
                
                logger.info(f"📊 Found {len(transcripts)} unprocessed transcripts")
                
                for transcript in transcripts:
                    try:
                        result = await memory_service.extract_and_store_memories(
                            transcript.get("session_id"),
                            openai_client
                        )
                        if result.get("success"):
                            processed += 1
                        else:
                            errors += 1
                    except Exception as e:
                        logger.error(f"❌ Error processing {transcript.get('session_id')}: {e}")
                        errors += 1
            
            logger.info(f"✅ Voice memory processing complete: processed={processed}, errors={errors}")
            return {"processed": processed, "errors": errors}
            
        except Exception as e:
            logger.error(f"❌ Voice memory processing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"processed": 0, "errors": 1, "error": str(e)}
        finally:
            client.close()
    
    def voice_memory_handler(event, context):
        """Handle voice memory extraction events"""
        import asyncio
        import json
        
        print(f"🧠 Voice memory handler invoked!")
        print(f"🧠 Event: {json.dumps(event, default=str)[:500]}")
        
        # Get session_id if processing specific session
        session_id = event.get('session_id')
        detail = event.get('detail', {})
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except json.JSONDecodeError:
                detail = {}
        
        # Check for session_id in detail as well
        if not session_id:
            session_id = detail.get('session_id')
        
        try:
            # Handle event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(process_voice_memory(session_id))
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'processed': result.get('processed', 0),
                    'errors': result.get('errors', 0)
                })
            }
        except Exception as e:
            logger.error(f"❌ Voice memory handler failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'body': json.dumps({'success': False, 'error': str(e)})
            }
    
    def combined_handler(event, context):
        """Route to appropriate handler based on event type"""
        import json
        
        # Debug: print event type for troubleshooting
        print(f"[DEBUG] Lambda invoked. Event keys: {list(event.keys())}")
        print(f"[DEBUG] source={event.get('source')}, detail-type={event.get('detail-type')}")
        
        # Check if this is a per-avatar cycle event (new format)
        # EventBridge puts custom Input in detail field (might be string or dict)
        # OR puts fields directly in event (top level)
        detail = event.get('detail', {})
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except json.JSONDecodeError:
                detail = {}
        
        # Check for voice memory extraction (async invocation or EventBridge)
        if (event.get('action') == 'extract_memories' or 
            detail.get('action') == 'extract_memories' or
            detail.get('action') == 'process_unprocessed_transcripts' or
            event.get('detail-type') == 'Voice Memory Processing'):
            print("[DEBUG] Routing to voice memory handler")
            return voice_memory_handler(event, context)
        
        # Check for avatar_id at top level or in detail
        avatar_id = event.get('avatar_id') or detail.get('avatar_id')
        
        if (detail.get('source') == 'avatar.cycle' or 
            detail.get('action') == 'run_single_avatar_cycle' or
            event.get('source') == 'avatar.cycle' or
            avatar_id):
            print(f"[DEBUG] Routing to EventBridge handler (per-avatar cycle) - avatar_id: {avatar_id}")
            return eventbridge_handler(event, context)
        
        # Check if this is an EventBridge event (legacy batch mode)
        if event.get('source') == 'aws.events' or event.get('detail-type') == 'Autonomous Avatar Cycle':
            print("[DEBUG] Routing to EventBridge handler (batch mode)")
            return eventbridge_handler(event, context)
        
        # Check if this is an EventBridge scheduled event (different format)
        if 'detail' in event and event.get('detail', {}).get('action') == 'run_autonomous_cycle':
            print("[DEBUG] Routing to EventBridge handler (alternate format)")
            return eventbridge_handler(event, context)
        
        # Otherwise, treat as HTTP request via API Gateway
        return mangum_adapter(event, context)
    
    # Store the combined handler
    _handler_impl[0] = combined_handler
    logger.info("Lambda handler initialized successfully (with EventBridge support)")
except Exception as e:
    logger.error(f"Error initializing FastAPI app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Create error handler
    def error_handler(event, context):
        error_msg = "FastAPI app initialization failed. Check Lambda logs."
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "{error_msg}", "detail": "Please check Lambda logs"}}'
        }
    _handler_impl[0] = error_handler
    logger.warning("Using error handler - FastAPI app not initialized")

# Final verification
logger.info(f"Handler ready: {type(handler)}, callable: {callable(handler)}, impl: {type(_handler_impl[0])}")
