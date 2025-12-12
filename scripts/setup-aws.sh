#!/bin/bash

# Setup AWS Account for 2N1 Deployment
# This script helps set up initial AWS resources

set -e

echo "🚀 Setting up AWS for 2N1 deployment..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI is configured"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_REGION:-us-west-2}

echo "📋 AWS Account ID: $ACCOUNT_ID"
echo "🌍 Region: $REGION"

# Create secrets in AWS Secrets Manager
echo ""
echo "🔐 Setting up secrets in AWS Secrets Manager..."

# MongoDB URI
read -p "Enter MongoDB Atlas connection string: " MONGODB_URI
aws secretsmanager create-secret \
  --name 2n1/mongodb/uri \
  --secret-string "$MONGODB_URI" \
  --region us-west-2 \
  --description "MongoDB Atlas connection string" 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id 2n1/mongodb/uri \
  --secret-string "$MONGODB_URI" \
  --region us-west-1

# Google OAuth Client ID
read -p "Enter Google OAuth Client ID: " GOOGLE_CLIENT_ID
aws secretsmanager create-secret \
  --name 2n1/google/client-id \
  --secret-string "$GOOGLE_CLIENT_ID" \
  --region us-west-2 \
  --description "Google OAuth Client ID" 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id 2n1/google/client-id \
  --secret-string "$GOOGLE_CLIENT_ID" \
  --region us-west-1

# Google OAuth Client Secret
read -p "Enter Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
aws secretsmanager create-secret \
  --name 2n1/google/client-secret \
  --secret-string "$GOOGLE_CLIENT_SECRET" \
  --region us-west-2 \
  --description "Google OAuth Client Secret" 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id 2n1/google/client-secret \
  --secret-string "$GOOGLE_CLIENT_SECRET" \
  --region us-west-1

# Azure OpenAI Key (optional)
read -p "Enter Azure OpenAI API Key (or press Enter to skip): " AZURE_OPENAI_KEY
if [ ! -z "$AZURE_OPENAI_KEY" ]; then
  aws secretsmanager create-secret \
    --name 2n1/azure/openai-key \
    --secret-string "$AZURE_OPENAI_KEY" \
    --region $REGION \
    --description "Azure OpenAI API Key" 2>/dev/null || \
  aws secretsmanager update-secret \
    --secret-id 2n1/azure/openai-key \
    --secret-string "$AZURE_OPENAI_KEY" \
    --region $REGION
fi

echo ""
echo "✅ Secrets configured successfully!"

# Bootstrap CDK
echo ""
echo "📦 Bootstrapping AWS CDK..."
cdk bootstrap aws://$ACCOUNT_ID/$REGION

echo ""
echo "✅ AWS setup complete!"
echo ""
echo "Next steps:"
echo "1. Update GoDaddy nameservers (after deploying infrastructure)"
echo "2. Run: cd infrastructure && npm install"
echo "3. Run: cdk deploy --all"
echo "4. Configure GitHub Actions secrets (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"

