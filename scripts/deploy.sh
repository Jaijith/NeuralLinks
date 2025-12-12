#!/bin/bash

# Manual Deployment Script for 2N1
# Use this for manual deployments or troubleshooting

set -e

echo "🚀 Deploying 2N1 to AWS..."

# Check if we're in the right directory
if [ ! -d "infrastructure" ]; then
    echo "❌ Please run this script from the project root"
    exit 1
fi

# Deploy infrastructure
echo ""
echo "📦 Deploying infrastructure..."
cd infrastructure
npm install
npm run build
cdk deploy --all --require-approval never

# Deploy backend
echo ""
echo "🔧 Deploying backend..."
cd ../backend
pip install -r requirements.txt -t .
zip -r ../lambda-deployment.zip . -x "*.pyc" "__pycache__/*" "*.git*" "venv/*" "*.env"

FUNCTION_NAME=$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'BackendStack-BackendFunction')].FunctionName" --output text)
aws lambda update-function-code --function-name $FUNCTION_NAME --zip-file fileb://../lambda-deployment.zip
aws lambda wait function-updated --function-name $FUNCTION_NAME

# Deploy frontend
echo ""
echo "🎨 Deploying frontend..."
cd ../frontend
npm install
API_URL=$(aws cloudformation describe-stacks --stack-name BackendStack --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
REACT_APP_API_URL=$API_URL npm run build

BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name FrontendStack --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text)
aws s3 sync build/ s3://$BUCKET_NAME/ --delete

DIST_ID=$(aws cloudformation describe-stacks --stack-name FrontendStack --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" --output text)
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"

echo ""
echo "✅ Deployment complete!"
echo "🌐 Frontend: https://2ness.com"
echo "🔌 API: $API_URL"

