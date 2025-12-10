#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default paths
PATHS="${*:-dify_assistant tests}"

# Track failures
FAILED=0

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

run_check() {
    local name="$1"
    shift
    print_step "$name"
    if "$@"; then
        print_success "$name passed"
        return 0
    else
        print_error "$name failed"
        FAILED=1
        return 1
    fi
}

echo -e "${YELLOW}🔍 Running lint checks on: ${PATHS}${NC}"

# Run checks (continue on failure to show all issues)
run_check "isort (import sorting)" uv run isort ${PATHS} || true
run_check "black (code formatting)" uv run black ${PATHS} || true
run_check "ruff (linting)" uv run ruff check dify_assistant --fix || true
run_check "mypy (type checking)" uv run mypy dify_assistant || true

# Summary
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed${NC}"
    exit 1
fi
