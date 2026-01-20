#!/bin/bash

# Script to set up Gmail SMTP credentials in AWS Secrets Manager for 2N1
# This enables the backend to send admin notification emails

echo "================================================"
echo "2N1 Gmail SMTP Setup"
echo "================================================"
echo ""
echo "This script will configure Gmail SMTP for sending admin notifications."
echo ""
echo "PREREQUISITES:"
echo "1. You must have a Gmail account"
echo "2. You must enable 2-Factor Authentication on your Gmail"
echo "3. You must generate an App Password for SMTP access"
echo ""
echo "To generate a Gmail App Password:"
echo "1. Go to: https://myaccount.google.com/security"
echo "2. Enable 2-Factor Authentication if not already enabled"
echo "3. Go to: https://myaccount.google.com/apppasswords"
echo "4. Create a new app password for 'Mail'"
echo "5. Copy the 16-character password (e.g., 'abcd efgh ijkl mnop')"
echo ""
read -p "Press Enter when you're ready to continue..."

# Get user inputs
echo ""
read -p "Enter your Gmail address (this will receive signup notifications): " ADMIN_EMAIL
read -p "Enter the same Gmail address for SMTP username: " SMTP_USERNAME
echo ""
echo "Enter your Gmail App Password (16 characters, spaces optional):"
echo "Note: This will not be displayed as you type"
read -s SMTP_PASSWORD
echo ""

# Remove spaces from password
SMTP_PASSWORD=$(echo "$SMTP_PASSWORD" | tr -d ' ')

# Validate inputs
if [ -z "$ADMIN_EMAIL" ] || [ -z "$SMTP_USERNAME" ] || [ -z "$SMTP_PASSWORD" ]; then
    echo "❌ Error: All fields are required"
    exit 1
fi

# Create JSON secret
SECRET_JSON=$(cat <<EOF
{
  "username": "$SMTP_USERNAME",
  "password": "$SMTP_PASSWORD",
  "admin_email": "$ADMIN_EMAIL"
}
EOF
)

echo ""
echo "Creating/updating secret in AWS Secrets Manager..."
echo "Secret name: 2n1/smtp/credentials"
echo "Region: us-west-2"
echo ""

# Check if secret exists
if aws secretsmanager describe-secret --secret-id "2n1/smtp/credentials" --region us-west-2 &>/dev/null; then
    echo "Secret already exists. Updating..."
    aws secretsmanager update-secret \
        --secret-id "2n1/smtp/credentials" \
        --secret-string "$SECRET_JSON" \
        --region us-west-2
else
    echo "Creating new secret..."
    aws secretsmanager create-secret \
        --name "2n1/smtp/credentials" \
        --description "Gmail SMTP credentials for 2N1 admin notifications" \
        --secret-string "$SECRET_JSON" \
        --region us-west-2
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! SMTP credentials stored in AWS Secrets Manager"
    echo ""
    echo "Next steps:"
    echo "1. Deploy the updated infrastructure: cd infrastructure && npm run deploy"
    echo "2. Test by requesting early access at https://2ness.com"
    echo "3. You should receive an email at: $ADMIN_EMAIL"
    echo ""
else
    echo ""
    echo "❌ ERROR: Failed to create/update secret"
    echo "Please check your AWS credentials and try again"
    exit 1
fi
