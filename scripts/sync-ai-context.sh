#!/bin/bash

#######################################
# Sync AI Context Files
# Generates CLAUDE.md and GEMINI.md from PROJECT.md
#######################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SOURCE_FILE="$PROJECT_ROOT/PROJECT.md"
CLAUDE_FILE="$PROJECT_ROOT/CLAUDE.md"
GEMINI_FILE="$PROJECT_ROOT/GEMINI.md"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${YELLOW}[WARNING]${NC} PROJECT.md not found. Skipping sync."
    exit 0
fi

# Get the content without the first header block (we'll replace it with AI-specific headers)
CONTENT=$(cat "$SOURCE_FILE")

# Generate CLAUDE.md
cat > "$CLAUDE_FILE" << 'EOF'
# Project Context for Claude Code

> **Auto-generated from PROJECT.md** - Do not edit directly. Run `./scripts/sync-ai-context.sh` to update.

EOF
# Append content starting from "## Project Overview"
echo "$CONTENT" | sed -n '/^## Project Overview/,$p' >> "$CLAUDE_FILE"

echo -e "${GREEN}[SYNCED]${NC} CLAUDE.md"

# Generate GEMINI.md
cat > "$GEMINI_FILE" << 'EOF'
# Project Context for Gemini/Antigravity

> **Auto-generated from PROJECT.md** - Do not edit directly. Run `./scripts/sync-ai-context.sh` to update.

EOF
# Append content starting from "## Project Overview"
echo "$CONTENT" | sed -n '/^## Project Overview/,$p' >> "$GEMINI_FILE"

echo -e "${GREEN}[SYNCED]${NC} GEMINI.md"

echo ""
echo "AI context files synchronized from PROJECT.md"
