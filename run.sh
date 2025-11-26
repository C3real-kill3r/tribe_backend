#!/bin/bash
# Robust shell script wrapper for running Tribe Backend

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Print header
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║           Tribe Backend - Development Server                 ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
if ! python3 --version | grep -qE "Python 3\.(1[1-9]|[2-9][0-9])"; then
    echo -e "${RED}✗ Python 3.11+ required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"

# Setup virtual environment
echo -e "${BLUE}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ requirements.txt not found${NC}"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠ .env file not found, creating from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠ Please update .env with your configuration!${NC}"
    else
        echo -e "${RED}✗ .env file not found and .env.example doesn't exist${NC}"
        exit 1
    fi
fi

# Run migrations (optional)
if command -v alembic &> /dev/null; then
    echo -e "${BLUE}Running database migrations...${NC}"
    alembic upgrade head || echo -e "${YELLOW}⚠ Migration check failed, continuing...${NC}"
fi

# Start server
echo -e "${GREEN}Starting development server...${NC}"
echo -e "${CYAN}API will be available at: http://localhost:8000${NC}"
echo -e "${CYAN}API Documentation: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

