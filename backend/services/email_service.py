"""
Email service for sending approval notifications
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
        self.admin_email = os.getenv("ADMIN_EMAIL", "s.jaijith@gmail.com")
        self.enabled = bool(self.smtp_username and self.smtp_password)
        
        if not self.enabled:
            logger.warning("Email service not configured. SMTP credentials missing.")
    
    def send_approval_request(self, email: str, name: str, request_id: str, approval_url: str) -> bool:
        """Send approval request email to admin"""
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send approval request for {email}")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.admin_email
            msg['Subject'] = f"New User Signup Request - {name}"
            
            body = f"""
A new user has requested to join the platform.

User Details:
- Name: {name}
- Email: {email}
- Request ID: {request_id}

To approve this request, click the link below:
{approval_url}

Or visit the admin panel to approve/reject requests.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Approval request email sent to {self.admin_email} for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")
            return False
    
    def send_approval_notification(self, email: str, name: str, approved: bool) -> bool:
        """Send approval/rejection notification to user"""
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send approval notification to {email}")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = f"Your Signup Request - {'Approved' if approved else 'Pending Review'}"
            
            if approved:
                body = f"""
Hello {name},

Great news! Your signup request has been approved.

You can now log in to the platform using your Google account.

Welcome to Maya!

Best regards,
The Geneses Team
"""
            else:
                body = f"""
Hello {name},

Thank you for your interest in joining our platform.

Your signup request is currently being reviewed. We'll notify you once a decision has been made.

Best regards,
The Geneses Team
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Approval notification email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send approval notification email: {e}")
            return False

