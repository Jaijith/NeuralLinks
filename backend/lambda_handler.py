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

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    
    async def run_autonomous_cycle():
        """Run autonomous cycle for all enabled avatars"""
        from motor.motor_asyncio import AsyncIOMotorClient
        from domain.avatar.state_aware_agent import StateAwareAgent
        from domain.avatar.intelligent import IntelligentAvatar
        from domain.graph.rag import GraphRAG
        from openai import AsyncOpenAI
        
        # Create fresh database connection for this invocation
        mongodb_uri = os.environ.get('MONGODB_URI')
        if not mongodb_uri:
            logger.error("❌ MONGODB_URI not set")
            return {"processed": 0, "errors": 0, "error": "MONGODB_URI not set"}
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.neurallinks_local
        
        # Create fresh OpenAI client
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        openai_model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
        
        openai_client = None
        if openai_api_key:
            openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Create intelligent avatar for this invocation
        graph_rag = GraphRAG(db)
        local_intelligent_avatar = None
        if openai_client:
            local_intelligent_avatar = IntelligentAvatar(db, openai_client, openai_model, graph_rag)
        
        try:
            # Find all users with autonomy enabled
            query = {
                "avatar_autonomous": True,
                "avatar_name": {"$exists": True, "$ne": None},
                "avatar_picture": {"$exists": True, "$ne": None},
                "is_bot": {"$ne": True}
            }
            
            users = await db.users.find(query, {"_id": 0}).to_list(100)
            
            if not users:
                logger.info("ℹ️ No users with autonomy enabled")
                return {"processed": 0, "errors": 0}
            
            logger.info(f"📊 Found {len(users)} user(s) with autonomy enabled")
            
            processed = 0
            errors = 0
            skipped = 0
            
            for user in users:
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
        
        logger.info(f"🤖 EventBridge trigger received: {event.get('detail-type', 'Unknown')}")
        
        try:
            # For Lambda, we need to handle the event loop carefully
            # Try to get existing loop, if closed or doesn't exist, create new one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the autonomous cycle
            result = loop.run_until_complete(run_autonomous_cycle())
            
            logger.info(f"✅ Autonomous cycle complete: {result}")
            return {
                'statusCode': 200,
                'body': f'{{"success": true, "processed": {result["processed"]}, "errors": {result["errors"]}}}'
            }
        except Exception as e:
            logger.error(f"❌ Autonomous cycle failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'statusCode': 500,
                'body': f'{{"success": false, "error": "{str(e)}"}}'
            }
    
    def combined_handler(event, context):
        """Route to appropriate handler based on event type"""
        # Check if this is an EventBridge event
        if event.get('source') == 'aws.events' or event.get('detail-type') == 'Autonomous Avatar Cycle':
            return eventbridge_handler(event, context)
        
        # Check if this is an EventBridge scheduled event (different format)
        if 'detail' in event and event.get('detail', {}).get('action') == 'run_autonomous_cycle':
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
