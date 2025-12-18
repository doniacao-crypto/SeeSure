#!/bin/bash

#######################################
# Sync Kiro Commands to Gemini CLI
# Copies .claude/commands/kiro/ to .gemini/customPrompts/
#######################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

CLAUDE_COMMANDS=".claude/commands/kiro"
GEMINI_PROMPTS=".gemini/customPrompts"

# Check if Claude commands exist
if [ ! -d "$CLAUDE_COMMANDS" ]; then
    echo "No Claude commands found at $CLAUDE_COMMANDS"
    exit 1
fi

# Create Gemini directory structure
mkdir -p "$GEMINI_PROMPTS"

print_status "Syncing Kiro commands to Gemini CLI..."

# Copy and transform commands
for cmd_file in "$CLAUDE_COMMANDS"/*.md; do
    if [ -f "$cmd_file" ]; then
        filename=$(basename "$cmd_file")
        # Transform filename: spec-init.md -> kiro-spec-init.md
        gemini_filename="kiro-${filename}"

        # Copy with header modification for Gemini
        {
            echo "<!-- Synced from .claude/commands/kiro/${filename} -->"
            echo "<!-- Use: /kiro-${filename%.md} in Gemini CLI -->"
            echo ""
            cat "$cmd_file"
        } > "$GEMINI_PROMPTS/$gemini_filename"

        print_status "  Synced: $filename -> $gemini_filename"
    fi
done

# Create Gemini settings if not exists
GEMINI_SETTINGS=".gemini/settings.json"
if [ ! -f "$GEMINI_SETTINGS" ]; then
    cat > "$GEMINI_SETTINGS" << 'EOF'
{
  "customPromptsPath": ".gemini/customPrompts",
  "contextFiles": ["GEMINI.md", "PROJECT.md"],
  "syncWithClaude": true
}
EOF
    print_success "Created $GEMINI_SETTINGS"
fi

print_success "Synced $(ls -1 "$GEMINI_PROMPTS" | wc -l | tr -d ' ') commands to Gemini CLI"
echo ""
echo "Gemini commands available at: $GEMINI_PROMPTS"
echo "Use /kiro-spec-init, /kiro-spec-requirements, etc. in Gemini CLI"
