#!/bin/bash

# Automated MongoDB Atlas Setup Script
# This script automates MongoDB Atlas cluster creation using their API

set -e

echo "🚀 Setting up MongoDB Atlas cluster automatically..."

# Check if MongoDB Atlas API credentials are set
if [ -z "$MONGODB_ATLAS_PUBLIC_KEY" ] || [ -z "$MONGODB_ATLAS_PRIVATE_KEY" ]; then
    echo "❌ MongoDB Atlas API credentials not set!"
    echo ""
    echo "To use this script, you need to:"
    echo "1. Go to MongoDB Atlas → Access Manager → API Keys"
    echo "2. Create a new API key with 'Organization Owner' or 'Project Owner' permissions"
    echo "3. Set environment variables:"
    echo "   export MONGODB_ATLAS_PUBLIC_KEY='your-public-key'"
    echo "   export MONGODB_ATLAS_PRIVATE_KEY='your-private-key'"
    echo "   export MONGODB_ATLAS_PROJECT_ID='your-project-id'"
    echo ""
    echo "Or run manually (takes 2 minutes):"
    echo "1. Go to https://cloud.mongodb.com"
    echo "2. Create free M0 cluster"
    echo "3. Get connection string"
    exit 1
fi

# Check if project ID is set
if [ -z "$MONGODB_ATLAS_PROJECT_ID" ]; then
    echo "❌ MONGODB_ATLAS_PROJECT_ID not set!"
    echo "Get it from: MongoDB Atlas → Project Settings → Project ID"
    exit 1
fi

# Install jq if not available
if ! command -v jq &> /dev/null; then
    echo "Installing jq..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        sudo apt-get install -y jq
    fi
fi

# MongoDB Atlas API base URL
API_BASE="https://cloud.mongodb.com/api/atlas/v1.0"

# Function to make authenticated API calls
atlas_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -u "$MONGODB_ATLAS_PUBLIC_KEY:$MONGODB_ATLAS_PRIVATE_KEY" \
            -H "Content-Type: application/json" \
            "$API_BASE$endpoint"
    else
        curl -s -X "$method" \
            -u "$MONGODB_ATLAS_PUBLIC_KEY:$MONGODB_ATLAS_PRIVATE_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE$endpoint"
    fi
}

echo "📋 Checking existing clusters..."

# Check if cluster already exists
CLUSTERS=$(atlas_api GET "/groups/$MONGODB_ATLAS_PROJECT_ID/clusters")
CLUSTER_NAME="2n1-cluster"

if echo "$CLUSTERS" | jq -e ".results[] | select(.name == \"$CLUSTER_NAME\")" > /dev/null; then
    echo "✅ Cluster '$CLUSTER_NAME' already exists!"
    CLUSTER_EXISTS=true
else
    echo "📦 Creating MongoDB Atlas M0 cluster..."
    
    # Create cluster configuration
    CLUSTER_CONFIG=$(cat <<EOF
{
  "name": "$CLUSTER_NAME",
  "clusterType": "REPLICASET",
  "mongoDBMajorVersion": "7.0",
  "providerSettings": {
    "providerName": "AWS",
    "regionName": "US_EAST_1",
    "instanceSizeName": "M0",
    "diskIOPS": 0
  },
  "backupEnabled": false,
  "providerBackupEnabled": false
}
EOF
)
    
    # Create cluster
    RESPONSE=$(atlas_api POST "/groups/$MONGODB_ATLAS_PROJECT_ID/clusters" "$CLUSTER_CONFIG")
    
    if echo "$RESPONSE" | jq -e ".error" > /dev/null; then
        echo "❌ Error creating cluster:"
        echo "$RESPONSE" | jq -r ".error"
        exit 1
    fi
    
    echo "✅ Cluster creation initiated!"
    echo "⏳ Waiting for cluster to be ready (this may take 5-10 minutes)..."
    
    # Wait for cluster to be ready
    while true; do
        STATUS=$(atlas_api GET "/groups/$MONGODB_ATLAS_PROJECT_ID/clusters/$CLUSTER_NAME" | jq -r ".stateName")
        echo "   Current status: $STATUS"
        
        if [ "$STATUS" == "IDLE" ]; then
            echo "✅ Cluster is ready!"
            break
        elif [ "$STATUS" == "CREATING" ] || [ "$STATUS" == "UPDATING" ]; then
            sleep 30
        else
            echo "❌ Cluster creation failed with status: $STATUS"
            exit 1
        fi
    done
fi

# Create database user
echo ""
echo "👤 Creating database user..."

read -p "Enter database username (default: 2n1user): " DB_USERNAME
DB_USERNAME=${DB_USERNAME:-2n1user}

read -sp "Enter database password: " DB_PASSWORD
echo ""

# Create user
USER_CONFIG=$(cat <<EOF
{
  "username": "$DB_USERNAME",
  "password": "$DB_PASSWORD",
  "databaseName": "admin",
  "roles": [
    {
      "roleName": "readWriteAnyDatabase",
      "databaseName": "admin"
    }
  ]
}
EOF
)

USER_RESPONSE=$(atlas_api POST "/groups/$MONGODB_ATLAS_PROJECT_ID/databaseUsers" "$USER_CONFIG")

if echo "$USER_RESPONSE" | jq -e ".error" > /dev/null; then
    if echo "$USER_RESPONSE" | jq -e '.errorCode == "USER_ALREADY_EXISTS"' > /dev/null; then
        echo "ℹ️  User already exists, skipping..."
    else
        echo "❌ Error creating user:"
        echo "$USER_RESPONSE" | jq -r ".error"
        exit 1
    fi
else
    echo "✅ Database user created!"
fi

# Configure network access (allow from anywhere for Lambda)
echo ""
echo "🌐 Configuring network access..."

NETWORK_CONFIG='{"cidrBlock":"0.0.0.0/0","comment":"Allow Lambda access"}'
NETWORK_RESPONSE=$(atlas_api POST "/groups/$MONGODB_ATLAS_PROJECT_ID/accessList" "$NETWORK_CONFIG")

if echo "$NETWORK_RESPONSE" | jq -e ".error" > /dev/null; then
    if echo "$NETWORK_RESPONSE" | jq -e '.errorCode == "DUPLICATE_IP_ACCESS_LIST_ENTRY"' > /dev/null; then
        echo "ℹ️  Network access already configured, skipping..."
    else
        echo "❌ Error configuring network access:"
        echo "$NETWORK_RESPONSE" | jq -r ".error"
    fi
else
    echo "✅ Network access configured!"
fi

# Get connection string
echo ""
echo "🔗 Getting connection string..."

CLUSTER_INFO=$(atlas_api GET "/groups/$MONGODB_ATLAS_PROJECT_ID/clusters/$CLUSTER_NAME")
CONNECTION_STRING=$(echo "$CLUSTER_INFO" | jq -r ".connectionStrings.standardSrv")

# Replace <password> with actual password
CONNECTION_STRING="${CONNECTION_STRING/<password>/$DB_PASSWORD}"
CONNECTION_STRING="${CONNECTION_STRING/<username>/$DB_USERNAME}"

echo "✅ Connection string:"
echo "$CONNECTION_STRING"

# Store in AWS Secrets Manager
echo ""
echo "💾 Storing connection string in AWS Secrets Manager..."

aws secretsmanager create-secret \
  --name 2n1/mongodb/uri \
  --secret-string "$CONNECTION_STRING" \
  --region us-west-2 \
  --description "MongoDB Atlas connection string" 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id 2n1/mongodb/uri \
  --secret-string "$CONNECTION_STRING" \
  --region us-west-1

echo "✅ Connection string stored in AWS Secrets Manager!"

echo ""
echo "🎉 MongoDB Atlas setup complete!"
echo ""
echo "Next steps:"
echo "1. Continue with infrastructure deployment"
echo "2. The connection string is already stored in AWS Secrets Manager"

