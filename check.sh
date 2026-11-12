#!/bin/bash
set -e

# Terminal color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running Project Verification Pipeline  ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. Ruff Format Check
echo -e "\n${BLUE}[1/4] Checking code formatting (Ruff)...${NC}"
if python3 -m ruff format --check .; then
    echo -e "${GREEN}✓ Code format is clean.${NC}"
else
    echo -e "${RED}✗ Formatting issues found. Run 'make format' or 'python3 -m ruff format .' to fix.${NC}"
    exit 1
fi

# 2. Ruff Linter Check
echo -e "\n${BLUE}[2/4] Checking code lint & rules (Ruff)...${NC}"
if python3 -m ruff check .; then
    echo -e "${GREEN}✓ Lint checks passed.${NC}"
else
    echo -e "${RED}✗ Lint errors detected.${NC}"
    exit 1
fi

# 3. Pylance / Pyright Type Check
echo -e "\n${BLUE}[3/4] Checking static types & Pylance resolution (Pyright)...${NC}"
if python3 -m pyright .; then
    echo -e "${GREEN}✓ Type checks passed (0 Pylance errors).${NC}"
else
    echo -e "${RED}✗ Type errors detected.${NC}"
    exit 1
fi

# 4. Pytest Suite
echo -e "\n${BLUE}[4/4] Running test suite (Pytest)...${NC}"
if python3 -m pytest -v; then
    echo -e "${GREEN}✓ All test cases passed.${NC}"
else
    echo -e "${RED}✗ Tests failed.${NC}"
    exit 1
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  All verification checks passed!       ${NC}"
echo -e "${GREEN}========================================${NC}"
