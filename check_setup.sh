#!/bin/bash

# NeuralLinks - Setup Verification Script
# Checks if all requirements are met for local development

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🔍 NeuralLinks - Setup Verification"
echo "===================================="
echo ""

ISSUES=0

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} $VERSION"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

# Check Node.js
echo -n "Checking Node.js... "
if command -v node &> /dev/null; then
    VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} $VERSION"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

# Check MongoDB
echo -n "Checking MongoDB... "
if command -v mongod &> /dev/null; then
    echo -e "${GREEN}✓${NC} Installed"
    
    # Check if running
    echo -n "  MongoDB service... "
    if pgrep -x "mongod" > /dev/null; then
        echo -e "${GREEN}✓${NC} Running"
    else
        echo -e "${YELLOW}⚠${NC} Not running"
        echo "    Run: brew services start mongodb-community@8.0"
        ((ISSUES++))
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    echo "    Install: brew install mongodb-community@8.0"
    ((ISSUES++))
fi

echo ""

# Check Backend Setup
echo "Backend Setup:"
echo "-------------"

# Virtual environment
echo -n "  Virtual environment... "
if [ -d "backend/venv" ]; then
    echo -e "${GREEN}✓${NC} Found"
else
    echo -e "${YELLOW}⚠${NC} Not found"
    echo "    Run: cd backend && python3 -m venv venv"
    ((ISSUES++))
fi

# Backend dependencies
echo -n "  Dependencies... "
if [ -d "backend/venv/lib/python"*/site-packages/fastapi ]; then
    echo -e "${GREEN}✓${NC} Installed"
else
    echo -e "${YELLOW}⚠${NC} Not installed"
    echo "    Run: cd backend && source venv/bin/activate && pip install -r requirements.txt"
    ((ISSUES++))
fi

# Backend .env
echo -n "  Configuration (.env)... "
if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓${NC} Found"
    
    # Check if Azure OpenAI is configured
    if grep -q "your_api_key_here" backend/.env 2>/dev/null; then
        echo -e "    ${YELLOW}⚠${NC} Azure OpenAI credentials need updating"
        echo "    Edit: backend/.env"
        ((ISSUES++))
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    echo "    Create from: backend/.env.example"
    ((ISSUES++))
fi

echo ""

# Check Frontend Setup
echo "Frontend Setup:"
echo "--------------"

# Node modules
echo -n "  Dependencies (node_modules)... "
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓${NC} Installed"
else
    echo -e "${YELLOW}⚠${NC} Not installed"
    echo "    Run: cd frontend && npm install"
    ((ISSUES++))
fi

# Frontend .env
echo -n "  Configuration (.env)... "
if [ -f "frontend/.env" ]; then
    echo -e "${GREEN}✓${NC} Found"
else
    echo -e "${YELLOW}⚠${NC} Not found"
    echo "    Create from: frontend/.env.example"
    ((ISSUES++))
fi

echo ""

# Check if servers are running
echo "Running Services:"
echo "----------------"

echo -n "  Backend (port 8001)... "
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Running"
    
    # Test API
    if curl -s http://localhost:8001/api/auth/me > /dev/null 2>&1; then
        echo "    API responding: ${GREEN}✓${NC}"
    else
        echo "    API responding: ${YELLOW}⚠${NC}"
    fi
else
    echo -e "${YELLOW}○${NC} Not running"
    echo "    Start: cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8001"
fi

echo -n "  Frontend (port 3000)... "
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Running"
else
    echo -e "${YELLOW}○${NC} Not running"
    echo "    Start: cd frontend && npm start"
fi

echo ""
echo "===================================="

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start backend: cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8001"
    echo "  2. Start frontend: cd frontend && npm start"
    echo "  3. Open: http://localhost:3000"
else
    echo -e "${YELLOW}⚠ Found $ISSUES issue(s) that need attention${NC}"
    echo ""
    echo "Run the setup script to fix issues:"
    echo "  ./setup_local.sh"
fi

echo ""



