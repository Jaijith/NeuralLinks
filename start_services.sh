#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
START_AGENTS=false
if [[ "$1" == "--auto" ]] || [[ "$1" == "-a" ]]; then
    START_AGENTS=true
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║     🚀 Geneses - Starting Services                          ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to check if a process is running
check_process() {
    local process_name=$1
    if pgrep -f "$process_name" > /dev/null; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

# ============ MongoDB ============
echo -e "${BLUE}📦 Checking MongoDB...${NC}"
if check_process "mongod"; then
    echo -e "${GREEN}✅ MongoDB is already running${NC}"
else
    echo -e "${YELLOW}⚠️  MongoDB is not running. Starting...${NC}"
    
    if command -v brew &> /dev/null; then
        brew services start mongodb-community@8.0 2>/dev/null || brew services start mongodb-community 2>/dev/null
        sleep 3
        
        if check_process "mongod"; then
            echo -e "${GREEN}✅ MongoDB started successfully${NC}"
        else
            echo -e "${RED}❌ Failed to start MongoDB. Please start it manually:${NC}"
            echo -e "   ${YELLOW}brew services start mongodb-community@8.0${NC}"
            echo -e "   ${YELLOW}or: mongod --dbpath ~/data/db${NC}"
        fi
    else
        echo -e "${RED}❌ Homebrew not found. Please start MongoDB manually:${NC}"
        echo -e "   ${YELLOW}mongod --dbpath ~/data/db${NC}"
    fi
fi
echo ""

# ============ Backend ============
echo -e "${BLUE}🔧 Checking Backend (port 8001)...${NC}"
if check_port 8001; then
    echo -e "${GREEN}✅ Backend is already running on port 8001${NC}"
else
    echo -e "${YELLOW}⚠️  Backend is not running. Starting...${NC}"
    
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        echo -e "${RED}❌ Virtual environment not found. Please run setup first:${NC}"
        echo -e "   ${YELLOW}cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
        exit 1
    fi
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠️  Warning: .env file not found in backend directory${NC}"
    fi
    
    # Start backend in background (using modularized app.main)
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 > backend.log 2>&1 &
    BACKEND_PID=$!
    
    sleep 3
    
    if check_port 8001; then
        echo -e "${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"
        echo -e "   ${BLUE}📝 Logs: $BACKEND_DIR/backend.log${NC}"
    else
        echo -e "${RED}❌ Failed to start backend. Check logs: $BACKEND_DIR/backend.log${NC}"
    fi
fi
echo ""

# ============ Frontend ============
echo -e "${BLUE}🎨 Checking Frontend (port 3000)...${NC}"
if check_port 3000; then
    echo -e "${GREEN}✅ Frontend is already running on port 3000${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend is not running. Starting...${NC}"
    
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
        cd "$FRONTEND_DIR"
        npm install
    fi
    
    cd "$FRONTEND_DIR"
    
    # Start frontend in background
    nohup npm start > frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    sleep 5
    
    if check_port 3000; then
        echo -e "${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
        echo -e "   ${BLUE}📝 Logs: $FRONTEND_DIR/frontend.log${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend is starting (may take a moment)...${NC}"
        echo -e "   ${BLUE}📝 Logs: $FRONTEND_DIR/frontend.log${NC}"
    fi
fi
echo ""

# ============ Summary ============
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Service Status Summary                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if check_process "mongod"; then
    echo -e "${GREEN}✅ MongoDB: Running${NC}"
else
    echo -e "${RED}❌ MongoDB: Not Running${NC}"
fi

if check_port 8001; then
    echo -e "${GREEN}✅ Backend: Running on http://localhost:8001${NC}"
    echo -e "   ${BLUE}📚 API Docs: http://localhost:8001/docs${NC}"
else
    echo -e "${RED}❌ Backend: Not Running${NC}"
fi

if check_port 3000; then
    echo -e "${GREEN}✅ Frontend: Running on http://localhost:3000${NC}"
else
    echo -e "${RED}❌ Frontend: Not Running${NC}"
fi

# ============ Autonomous Agents ============
if [ "$START_AGENTS" = true ]; then
    echo ""
    echo -e "${BLUE}🤖 Checking Autonomous Agents...${NC}"
    
    # Check if agents are already running
    if pgrep -f "run_autonomous_agents.py" > /dev/null; then
        AGENT_PID=$(pgrep -f "run_autonomous_agents.py" | head -1)
        echo -e "${GREEN}✅ Autonomous Agents: Already running (PID: $AGENT_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Autonomous Agents: Not running. Starting...${NC}"
        
        if [ ! -d "$BACKEND_DIR/venv" ]; then
            echo -e "${RED}❌ Virtual environment not found. Cannot start agents.${NC}"
        else
            cd "$BACKEND_DIR"
            source venv/bin/activate
            
            # Start agents in background
            nohup python scripts/run_autonomous_agents.py > agents.log 2>&1 &
            AGENT_PID=$!
            
            sleep 3
            
            # Check if started successfully
            if pgrep -f "run_autonomous_agents.py" > /dev/null; then
                echo -e "${GREEN}✅ Autonomous Agents: Started successfully (PID: $AGENT_PID)${NC}"
                echo -e "   ${BLUE}📝 Logs: $BACKEND_DIR/agents.log${NC}"
            else
                echo -e "${YELLOW}⚠️  Autonomous Agents: Starting (may take a moment)...${NC}"
                echo -e "   ${BLUE}📝 Logs: $BACKEND_DIR/agents.log${NC}"
            fi
            
            cd "$SCRIPT_DIR"
        fi
    fi
else
    echo ""
    echo -e "${BLUE}🤖 Autonomous Agents:${NC}"
    if pgrep -f "run_autonomous_agents.py" > /dev/null; then
        AGENT_PID=$(pgrep -f "run_autonomous_agents.py" | head -1)
        echo -e "${GREEN}✅ Running (PID: $AGENT_PID)${NC}"
    else
        echo -e "${YELLOW}⏸️  Not running${NC}"
        echo -e "   ${BLUE}💡 Start with: ${YELLOW}./start_services.sh --auto${NC}"
    fi
fi

echo ""
echo -e "${BLUE}💡 Tips:${NC}"
echo -e "   • View backend logs: ${YELLOW}tail -f $BACKEND_DIR/backend.log${NC}"
echo -e "   • View frontend logs: ${YELLOW}tail -f $FRONTEND_DIR/frontend.log${NC}"
if [ "$START_AGENTS" = true ]; then
    echo -e "   • View agent logs: ${YELLOW}tail -f $BACKEND_DIR/agents.log${NC}"
fi
echo -e "   • Stop all services: ${YELLOW}./stop_services.sh${NC} (if available)"
echo ""

