"""
Avatar Cycle Manager - Manages per-avatar EventBridge rules

Each avatar with autonomy enabled gets its own EventBridge rule
that triggers at intervals based on their activity level.
"""
import os
import logging
import boto3
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AvatarCycleManager:
    """
    Manages EventBridge rules for individual avatar cycles.
    
    Each avatar gets its own scheduled rule that triggers Lambda
    to process that specific avatar's autonomous cycle.
    """
    
    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-west-2')
        self.events_client = boto3.client('events', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        
        # Get Lambda function name from environment or use default pattern
        self.lambda_function_name = os.environ.get('LAMBDA_FUNCTION_NAME')
        if not self.lambda_function_name:
            # Try to infer from stack name
            stack_name = os.environ.get('STACK_NAME', 'BackendStack')
            # This will be set by CDK
            self.lambda_function_name = f"{stack_name}-BackendFunction*"
    
    def _get_rule_name(self, user_id: str) -> str:
        """Generate EventBridge rule name for a user"""
        # Use first 8 chars of user_id to keep name short (max 64 chars)
        user_id_short = user_id.replace('-', '')[:8]
        return f"avatar-cycle-{user_id_short}"
    
    def _get_schedule_expression(self, activity_level: str) -> str:
        """
        Get EventBridge schedule expression based on activity level.
        
        Returns rate expression like 'rate(7 minutes)' or 'rate(60 minutes)'
        """
        # Map activity levels to intervals (in minutes)
        activity_intervals = {
            "hypo": 2,              # Testing: every 2 minutes
            "user_active": 7,       # User: every 7 minutes
            "bot_hourly": 60,       # Bot: every hour
            "low": 720,             # Low: every 12 hours
            "medium": 144,          # Medium: ~2.4 hours
            "high": 72,             # High: ~1.2 hours
        }
        
        interval_minutes = activity_intervals.get(activity_level, 144)  # Default to medium
        
        # EventBridge rate expression
        if interval_minutes < 60:
            return f"rate({interval_minutes} minutes)"
        elif interval_minutes == 60:
            return "rate(1 hour)"
        else:
            hours = interval_minutes / 60
            return f"rate({hours} hours)"
    
    def _get_lambda_function_arn(self) -> Optional[str]:
        """
        Get the Lambda function ARN.
        First tries environment variable, then tries to find by context.
        """
        try:
            # Try to get from environment first (set by CDK)
            function_arn = os.environ.get('LAMBDA_FUNCTION_ARN')
            if function_arn:
                return function_arn
            
            # Try to get from Lambda context (if running in Lambda)
            # This requires the context to be passed, but we can't do that here
            # So we'll try to find it by listing functions as fallback
            try:
                paginator = self.lambda_client.get_paginator('list_functions')
                for page in paginator.paginate():
                    for func in page.get('Functions', []):
                        func_name = func['FunctionName']
                        # Match BackendStack-BackendFunction pattern
                        if 'BackendFunction' in func_name:
                            return func['FunctionArn']
            except Exception as list_error:
                logger.warning(f"Could not list Lambda functions: {list_error}")
            
            logger.warning("Could not find Lambda function ARN - LAMBDA_FUNCTION_ARN env var not set")
            return None
        except Exception as e:
            logger.error(f"Error getting Lambda function ARN: {e}")
            return None
    
    async def create_rule(self, user_id: str, activity_level: str = "medium") -> bool:
        """
        Create EventBridge rule for an avatar.
        
        Args:
            user_id: The user's ID
            activity_level: Activity level (determines schedule interval)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule_name = self._get_rule_name(user_id)
            schedule_expression = self._get_schedule_expression(activity_level)
            lambda_arn = self._get_lambda_function_arn()
            
            if not lambda_arn:
                logger.error(f"Could not get Lambda ARN for user {user_id}")
                return False
            
            # Create the rule
            self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                State='ENABLED',
                Description=f"Autonomous cycle for avatar {user_id}",
                Tags=[
                    {'Key': 'AvatarId', 'Value': user_id},
                    {'Key': 'ActivityLevel', 'Value': activity_level},
                    {'Key': 'ManagedBy', 'Value': 'AvatarCycleManager'}
                ]
            )
            
            # Add Lambda as target
            self.events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': '1',
                        'Arn': lambda_arn,
                        'Input': f'{{"source":"avatar.cycle","avatar_id":"{user_id}","action":"run_single_avatar_cycle","activity_level":"{activity_level}"}}'
                    }
                ]
            )
            
            # Grant EventBridge permission to invoke Lambda
            try:
                # Extract function name from ARN (last part after colon)
                function_name = lambda_arn.split(':')[-1]
                # Extract account ID from ARN (5th part)
                account_id = lambda_arn.split(':')[4]
                
                self.lambda_client.add_permission(
                    FunctionName=function_name,
                    StatementId=f'avatar-cycle-{user_id.replace("-", "")[:16]}',  # Max 64 chars, remove dashes
                    Action='lambda:InvokeFunction',
                    Principal='events.amazonaws.com',
                    SourceArn=f'arn:aws:events:{self.region}:{account_id}:rule/{rule_name}'
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceConflictException':
                    # Permission already exists, that's fine
                    logger.debug(f"Lambda permission already exists for {user_id}")
                else:
                    logger.warning(f"Could not add Lambda permission for {user_id}: {e}")
                    # Continue anyway - rule will still work if permission exists
            
            logger.info(f"✅ Created EventBridge rule '{rule_name}' for user {user_id} (schedule: {schedule_expression})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating EventBridge rule for user {user_id}: {e}", exc_info=True)
            return False
    
    async def update_rule(self, user_id: str, activity_level: str) -> bool:
        """
        Update EventBridge rule schedule for an avatar.
        
        Args:
            user_id: The user's ID
            activity_level: New activity level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule_name = self._get_rule_name(user_id)
            schedule_expression = self._get_schedule_expression(activity_level)
            
            # Update the rule
            self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                State='ENABLED',
                Description=f"Autonomous cycle for avatar {user_id}",
            )
            
            # Update target input to include new activity level
            lambda_arn = self._get_lambda_function_arn()
            if lambda_arn:
                self.events_client.put_targets(
                    Rule=rule_name,
                    Targets=[
                        {
                            'Id': '1',
                            'Arn': lambda_arn,
                            'Input': f'{{"source":"avatar.cycle","avatar_id":"{user_id}","action":"run_single_avatar_cycle","activity_level":"{activity_level}"}}'
                        }
                    ]
                )
            
            logger.info(f"✅ Updated EventBridge rule '{rule_name}' for user {user_id} (new schedule: {schedule_expression})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating EventBridge rule for user {user_id}: {e}", exc_info=True)
            return False
    
    async def delete_rule(self, user_id: str) -> bool:
        """
        Delete EventBridge rule for an avatar.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule_name = self._get_rule_name(user_id)
            
            # Remove targets first
            try:
                targets = self.events_client.list_targets_by_rule(Rule=rule_name)
                if targets.get('Targets'):
                    target_ids = [t['Id'] for t in targets['Targets']]
                    self.events_client.remove_targets(Rule=rule_name, Ids=target_ids)
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    logger.warning(f"Error removing targets: {e}")
            
            # Delete the rule
            self.events_client.delete_rule(Name=rule_name)
            
            logger.info(f"✅ Deleted EventBridge rule '{rule_name}' for user {user_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Rule doesn't exist, that's fine
                logger.info(f"Rule for user {user_id} doesn't exist, skipping deletion")
                return True
            logger.error(f"❌ Error deleting EventBridge rule for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error deleting EventBridge rule for user {user_id}: {e}", exc_info=True)
            return False
    
    async def rule_exists(self, user_id: str) -> bool:
        """Check if EventBridge rule exists for a user"""
        try:
            rule_name = self._get_rule_name(user_id)
            self.events_client.describe_rule(Name=rule_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise

