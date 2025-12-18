#!/bin/bash

#######################################
# Validate AI Context Files are in sync
# Returns non-zero if CLAUDE.md or GEMINI.md differ from PROJECT.md
#######################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SOURCE_FILE="$PROJECT_ROOT/PROJECT.md"
CLAUDE_FILE="$PROJECT_ROOT/CLAUDE.md"
GEMINI_FILE="$PROJECT_ROOT/GEMINI.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} PROJECT.md not found."
    exit 1
fi

# Create temp files with expected content
TEMP_DIR=$(mktemp -d)
TEMP_CLAUDE="$TEMP_DIR/CLAUDE.md"
TEMP_GEMINI="$TEMP_DIR/GEMINI.md"

CONTENT=$(cat "$SOURCE_FILE")

# Generate expected CLAUDE.md
cat > "$TEMP_CLAUDE" << 'EOF'
# Project Context for Claude Code

> **Auto-generated from PROJECT.md** - Do not edit directly. Run `./scripts/sync-ai-context.sh` to update.

EOF
echo "$CONTENT" | sed -n '/^## Project Overview/,$p' >> "$TEMP_CLAUDE"

# Generate expected GEMINI.md
cat > "$TEMP_GEMINI" << 'EOF'
# Project Context for Gemini/Antigravity

> **Auto-generated from PROJECT.md** - Do not edit directly. Run `./scripts/sync-ai-context.sh` to update.

EOF
echo "$CONTENT" | sed -n '/^## Project Overview/,$p' >> "$TEMP_GEMINI"

# Compare
SYNC_ERROR=0

if [ ! -f "$CLAUDE_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} CLAUDE.md does not exist. Run ./scripts/sync-ai-context.sh"
    SYNC_ERROR=1
elif ! diff -q "$CLAUDE_FILE" "$TEMP_CLAUDE" > /dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} CLAUDE.md is out of sync with PROJECT.md"
    SYNC_ERROR=1
else
    echo -e "${GREEN}[OK]${NC} CLAUDE.md is in sync"
fi

if [ ! -f "$GEMINI_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} GEMINI.md does not exist. Run ./scripts/sync-ai-context.sh"
    SYNC_ERROR=1
elif ! diff -q "$GEMINI_FILE" "$TEMP_GEMINI" > /dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} GEMINI.md is out of sync with PROJECT.md"
    SYNC_ERROR=1
else
    echo -e "${GREEN}[OK]${NC} GEMINI.md is in sync"
fi

# Cleanup
rm -rf "$TEMP_DIR"

if [ $SYNC_ERROR -ne 0 ]; then
    echo ""
    echo "Run './scripts/sync-ai-context.sh' to fix."
    exit 1
fi

echo ""
echo "All AI context files are in sync."
exit 0
