#!/bin/bash

# NeuralLinks Local Setup Script
# This script automates the local development setup

set -e  # Exit on error

echo "🚀 NeuralLinks - Local Development Setup"
echo "========================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."
echo "------------------------"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status "Node.js: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check MongoDB
if command -v mongod &> /dev/null; then
    print_status "MongoDB: Found"
    MONGODB_INSTALLED=true
else
    print_warning "MongoDB not found in PATH"
    MONGODB_INSTALLED=false
fi

echo ""

# Install MongoDB if needed
if [ "$MONGODB_INSTALLED" = false ]; then
    echo "Installing MongoDB..."
    echo "-------------------"
    
    if command -v brew &> /dev/null; then
        echo "Using Homebrew to install MongoDB..."
        
        # Fix Homebrew permissions if needed
        if [ ! -w /opt/homebrew/Cellar ]; then
            echo "Fixing Homebrew permissions (requires password)..."
            sudo chown -R $(whoami) /opt/homebrew/Cellar
        fi
        
        brew tap mongodb/brew
        brew install mongodb-community@8.0
        
        print_status "MongoDB installed"
    else
        print_error "Homebrew not found. Please install MongoDB manually:"
        echo "  https://www.mongodb.com/try/download/community"
        exit 1
    fi
    echo ""
fi

# Start MongoDB
echo "Starting MongoDB..."
echo "------------------"

# Check if MongoDB is already running
if pgrep -x "mongod" > /dev/null; then
    print_status "MongoDB is already running"
else
    if command -v brew &> /dev/null; then
        brew services start mongodb-community@8.0
        sleep 2  # Wait for MongoDB to start
        
        if pgrep -x "mongod" > /dev/null; then
            print_status "MongoDB started successfully"
        else
            print_warning "MongoDB service started but process not detected"
        fi
    else
        print_warning "Please start MongoDB manually: mongod --dbpath ~/data/db"
    fi
fi

echo ""

# Setup Backend
echo "Setting up Backend..."
echo "-------------------"

cd "$BACKEND_DIR"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt
print_status "Python dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating backend .env file..."
    cat > .env << 'EOF'
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=neurallinks_local

# CORS - Allow frontend
CORS_ORIGINS=http://localhost:3000

# Azure OpenAI Configuration
# ⚠️ IMPORTANT: Add your Azure OpenAI credentials below!
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-10-21
EOF
    print_warning "Backend .env created - PLEASE UPDATE WITH YOUR AZURE OPENAI CREDENTIALS!"
else
    print_status "Backend .env already exists"
fi

echo ""

# Setup Frontend
echo "Setting up Frontend..."
echo "--------------------"

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    
    if command -v yarn &> /dev/null; then
        yarn install
    else
        npm install --legacy-peer-deps
    fi
    
    print_status "Node.js dependencies installed"
else
    print_status "Node.js dependencies already installed"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating frontend .env file..."
    cat > .env << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
EOF
    print_status "Frontend .env created"
else
    print_status "Frontend .env already exists"
fi

echo ""
echo "========================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "-----------"
echo ""
echo -e "1. ${YELLOW}Update Azure OpenAI credentials:${NC}"
echo "   Edit: $BACKEND_DIR/.env"
echo ""
echo "2. Start the backend server (Terminal 1):"
echo "   ${BLUE}cd $BACKEND_DIR${NC}"
echo "   ${BLUE}source venv/bin/activate${NC}"
echo "   ${BLUE}uvicorn server:app --reload --host 0.0.0.0 --port 8001${NC}"
echo ""
echo "3. Start the frontend server (Terminal 2):"
echo "   ${BLUE}cd $FRONTEND_DIR${NC}"
echo "   ${BLUE}npm start${NC}"
echo ""
echo "4. Open your browser:"
echo "   ${BLUE}http://localhost:3000${NC}"
echo ""
echo "For detailed instructions, see: LOCAL_SETUP.md"
echo ""


