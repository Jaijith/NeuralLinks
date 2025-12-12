"""
Email service for sending approval notifications
Supports both SMTP and AWS SES
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.admin_email = os.getenv("ADMIN_EMAIL", "2nesss1@gmail.com")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username or self.admin_email)
        self.smtp_enabled = bool(self.smtp_username and self.smtp_password)
        
        # Check for AWS SES
        self.ses_enabled = bool(os.getenv("AWS_REGION") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        
        if not self.smtp_enabled and not self.ses_enabled:
            logger.warning("Email service not fully configured. Emails may not be sent.")
    
    def _send_via_ses(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via AWS SES"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            region = os.getenv("AWS_REGION", "us-west-2")
            ses_client = boto3.client('ses', region_name=region)
            
            response = ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}
                }
            )
            logger.info(f"SES email sent to {to_email}, MessageId: {response['MessageId']}")
            return True
        except ClientError as e:
            logger.error(f"SES error: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Failed to send via SES: {e}")
            return False
    
    def _send_via_smtp(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"SMTP email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send via SMTP: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email using available method"""
        # Try SMTP first if configured
        if self.smtp_enabled:
            if self._send_via_smtp(to_email, subject, body):
                return True
        
        # Fall back to SES if in AWS
        if self.ses_enabled:
            if self._send_via_ses(to_email, subject, body):
                return True
        
        logger.warning(f"Could not send email to {to_email} - no email service available")
        return False
    
    def send_approval_request(self, email: str, name: str, request_id: str, approval_url: str) -> bool:
        """Send approval request email to admin"""
        subject = f"🔔 New 2N1 Signup Request - {name}"
        
        body = f"""
New User Signup Request for 2N1
================================

A new user has requested to join 2N1.

User Details:
- Name: {name}
- Email: {email}
- Request ID: {request_id}

To approve this request, use this link:
{approval_url}

Or call the API directly:
POST /api/signup/approve/{request_id}

To reject:
POST /api/signup/reject/{request_id}

---
2N1 | Two Worlds, One You
"""
        
        result = self._send_email(self.admin_email, subject, body)
        if not result:
            logger.warning(f"Could not send approval request email to admin for {email}")
        return result
    
    def send_approval_notification(self, email: str, name: str, approved: bool) -> bool:
        """Send approval/rejection notification to user"""
        if approved:
            subject = "✅ Welcome to 2N1 - Your Request is Approved!"
            body = f"""
Hello {name},

Great news! Your signup request has been approved! 🎉

You can now log in to 2N1 using your Google account:
https://2ness.com

Start your journey:
• Create your digital twin avatar
• Connect with others in two worlds
• Let your avatar build meaningful connections

Welcome to 2N1 - Two Worlds, One You!

Best regards,
The 2N1 Team
"""
        else:
            subject = "2N1 Signup Request - Update"
            body = f"""
Hello {name},

Thank you for your interest in joining 2N1.

Unfortunately, we're unable to approve your signup request at this time.

If you believe this is an error, please contact us at support@2ness.com.

Best regards,
The 2N1 Team
"""
        
        result = self._send_email(email, subject, body)
        if not result:
            logger.warning(f"Could not send approval notification to {email}")
        return result
