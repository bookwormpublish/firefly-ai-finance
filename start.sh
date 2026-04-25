#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
# firefly-ai-finance  •  start.sh
# Usage: ./start.sh [--reset] [--logs]
#   --reset   wipe volumes and start fresh
#   --logs    tail all service logs after start
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

RESET=false
SHOW_LOGS=false

for arg in "$@"; do
  case $arg in
    --reset) RESET=true ;;
    --logs)  SHOW_LOGS=true ;;
  esac
done

echo -e "${CYAN}"
echo '  ███████╗██╗██████╗ ███████╗███████╗██╗  ██╗    █████╗ ██╗'
echo '  ██╔════╝██║██╔══██╗██╔════╝██╔════╝██║  ╚██╗ ██╔══██╗██║'
echo '  █████╗  ██║██████╔╝█████╗  █████╗  ██║   ╚████╔╝ ███████║██║'
echo '  ██╔══╝  ██║██╔══██╗██╔══╝  ██╔══╝  ██║    ╚██╔╝  ██╔══██║██║'
echo '  ██║     ██║██║  ██║███████╗██║     ███████╗██║   ██║  ██║██║'
echo '  ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝'
echo -e "  AI-Powered Personal Finance Tracker${NC}"
echo ''

# ── 1. Check dependencies ───────────────────
echo -e "${YELLOW}[1/5] Checking dependencies...${NC}"

if ! command -v docker &>/dev/null; then
  echo -e "${RED}✗ Docker not found. Install from https://docs.docker.com/get-docker/${NC}"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo -e "${RED}✗ Docker Compose v2 not found. Update Docker Desktop or install the plugin.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Docker $(docker --version | awk '{print $3}' | tr -d ',')${NC}"
echo -e "${GREEN}✓ Docker Compose $(docker compose version --short)${NC}"

# ── 2. Check / create .env ──────────────────
echo -e "${YELLOW}[2/5] Checking environment config...${NC}"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠  Created .env from .env.example${NC}"
    echo -e "${YELLOW}   Edit .env and add your API keys, then re-run this script.${NC}"
    echo ''
    echo -e "   Required variables:"
    echo -e "   ${CYAN}ANTHROPIC_API_KEY${NC}  or  ${CYAN}OPENAI_API_KEY${NC}"
    echo -e "   ${CYAN}APP_KEY${NC}            (run: openssl rand -base64 32)"
    echo ''
    exit 0
  else
    echo -e "${RED}✗ No .env or .env.example found. Cannot continue.${NC}"
    exit 1
  fi
fi

# Warn if key API vars are still placeholders
source .env 2>/dev/null || true
if [[ "${ANTHROPIC_API_KEY:-}" == "your_anthropic_key_here" ]] || \
   [[ -z "${ANTHROPIC_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo -e "${YELLOW}⚠  Warning: No AI API key set in .env. AI categorization will not work.${NC}"
fi
echo -e "${GREEN}✓ .env loaded${NC}"

# ── 3. Optional reset ───────────────────────
if [ "$RESET" = true ]; then
  echo -e "${YELLOW}[3/5] Resetting volumes and containers...${NC}"
  docker compose down -v --remove-orphans
  echo -e "${GREEN}✓ Volumes cleared${NC}"
else
  echo -e "${YELLOW}[3/5] Skipping reset (pass --reset to wipe data)${NC}"
fi

# ── 4. Pull images & build ──────────────────
echo -e "${YELLOW}[4/5] Pulling images and building services...${NC}"
docker compose pull --quiet
docker compose build --quiet
echo -e "${GREEN}✓ Images ready${NC}"

# ── 5. Start stack ──────────────────────────
echo -e "${YELLOW}[5/5] Starting all services...${NC}"
docker compose up -d

# ── Wait for Firefly III to be healthy ──────
echo ''
echo -e "${CYAN}Waiting for Firefly III to become healthy...${NC}"
SECONDS_WAITED=0
MAX_WAIT=120
until curl -sf http://localhost:8080/health &>/dev/null || [ $SECONDS_WAITED -ge $MAX_WAIT ]; do
  printf '.'
  sleep 3
  SECONDS_WAITED=$((SECONDS_WAITED + 3))
done
echo ''

if [ $SECONDS_WAITED -ge $MAX_WAIT ]; then
  echo -e "${YELLOW}⚠  Firefly III is taking longer than usual. Check logs: docker compose logs firefly${NC}"
else
  echo -e "${GREEN}✓ Firefly III is up${NC}"
fi

# ── Summary ─────────────────────────────────
echo ''
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ''
echo -e "  ${CYAN}Firefly III${NC}     →  http://localhost:8080"
echo -e "  ${CYAN}AI Service${NC}      →  http://localhost:8000"
echo -e "  ${CYAN}AI Docs${NC}         →  http://localhost:8000/docs"
echo -e "  ${CYAN}Dashboard${NC}       →  http://localhost:3000"
echo ''
echo -e "  ${YELLOW}First run?${NC} Visit http://localhost:8080 to create your account,"
echo -e "  then add your Firefly Personal Access Token to .env as FIREFLY_TOKEN"
echo -e "  and run: ${CYAN}docker compose restart ai-service${NC}"
echo ''

if [ "$SHOW_LOGS" = true ]; then
  echo -e "${CYAN}Tailing logs (Ctrl+C to stop)...${NC}"
  docker compose logs -f
fi
