#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║     🛑 Geneses - Stopping Services                          ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to kill process on a port
kill_port() {
    local port=$1
    local process_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        local pid=$(lsof -ti :$port)
        if [ ! -z "$pid" ]; then
            kill $pid 2>/dev/null
            sleep 1
            if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
                echo -e "${GREEN}✅ Stopped $process_name on port $port${NC}"
            else
                kill -9 $pid 2>/dev/null
                echo -e "${YELLOW}⚠️  Force stopped $process_name on port $port${NC}"
            fi
        fi
    else
        echo -e "${BLUE}ℹ️  $process_name is not running on port $port${NC}"
    fi
}

# Stop Frontend (port 3000)
echo -e "${BLUE}🎨 Stopping Frontend...${NC}"
kill_port 3000 "Frontend"
echo ""

# Stop Backend (port 8001)
echo -e "${BLUE}🔧 Stopping Backend...${NC}"
kill_port 8001 "Backend"
echo ""

# Stop MongoDB (optional - commented out by default)
echo -e "${BLUE}📦 MongoDB Status...${NC}"
if pgrep -x "mongod" > /dev/null; then
    echo -e "${YELLOW}⚠️  MongoDB is still running${NC}"
    echo -e "${BLUE}   To stop MongoDB, run:${NC}"
    echo -e "   ${YELLOW}brew services stop mongodb-community@8.0${NC}"
    echo -e "   ${YELLOW}or: pkill mongod${NC}"
else
    echo -e "${BLUE}ℹ️  MongoDB is not running${NC}"
fi
echo ""

echo -e "${GREEN}✅ Service stop complete${NC}"
echo ""

