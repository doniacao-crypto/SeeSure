#!/bin/bash

#######################################
# AI-SDLC Template Setup Script
# For macOS and Linux
#######################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Header
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║          AI-SDLC Workflow Template Setup                  ║"
echo "║   Spec-Driven Development with Claude Code & Gemini CLI   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

#######################################
# Check Prerequisites
#######################################

print_status "Checking prerequisites..."

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        print_success "Node.js $(node -v) found"
    else
        print_warning "Node.js version is below 18. Please upgrade."
        echo "  Install: https://nodejs.org/"
        exit 1
    fi
else
    print_error "Node.js not found"
    echo "  Install from: https://nodejs.org/"
    echo "  Or via brew: brew install node"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    print_success "npm $(npm -v) found"
else
    print_error "npm not found"
    exit 1
fi

# Check Git
if command -v git &> /dev/null; then
    print_success "Git $(git --version | cut -d' ' -f3) found"
else
    print_error "Git not found"
    echo "  Install from: https://git-scm.com/"
    exit 1
fi

# Check GitHub CLI (optional but recommended)
if command -v gh &> /dev/null; then
    print_success "GitHub CLI found"
else
    print_warning "GitHub CLI not found (optional but recommended)"
    echo "  Install: brew install gh"
fi

echo ""

#######################################
# Install Dependencies
#######################################

print_status "Installing npm dependencies..."

# Install project dependencies
npm install --save-dev \
    jest \
    @types/jest \
    ts-jest \
    typescript \
    @playwright/test \
    eslint \
    prettier \
    husky \
    lint-staged \
    > /dev/null 2>&1

print_success "npm dependencies installed"

#######################################
# Install Claude Code
#######################################

print_status "Checking Claude Code..."

CLAUDE_INSTALLED=false
if command -v claude &> /dev/null; then
    print_success "Claude Code already installed"
    CLAUDE_INSTALLED=true
else
    print_status "Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code > /dev/null 2>&1 && {
        print_success "Claude Code installed"
        CLAUDE_INSTALLED=true
    } || {
        print_warning "Claude Code installation failed (optional)"
    }
fi

#######################################
# Install Gemini CLI
#######################################

print_status "Checking Gemini CLI..."

GEMINI_INSTALLED=false
if command -v gemini &> /dev/null; then
    print_success "Gemini CLI already installed"
    GEMINI_INSTALLED=true
else
    print_status "Installing Gemini CLI..."
    npm install -g @anthropic-ai/gemini-cli > /dev/null 2>&1 || \
    npm install -g @anthropic-ai/claude-code > /dev/null 2>&1 || true

    # Try alternative installation methods
    if command -v gemini &> /dev/null; then
        print_success "Gemini CLI installed"
        GEMINI_INSTALLED=true
    else
        print_warning "Gemini CLI not installed (install manually: npm install -g @google/gemini-cli)"
    fi
fi

#######################################
# Install cc-ssd-enh Framework
#######################################

print_status "Installing cc-ssd-enh (Spec-Driven Development framework)..."

# Run cc-ssd-enh setup
npx cc-ssd-enh@latest --yes > /dev/null 2>&1 || {
    print_warning "cc-ssd-enh auto-install failed, trying manual setup..."
    npx cc-ssd-enh@latest
}

print_success "cc-ssd-enh framework installed"

#######################################
# Sync Kiro Commands to Gemini CLI
#######################################

if [ "$GEMINI_INSTALLED" = true ] || [ -f "GEMINI.md" ]; then
    print_status "Syncing Kiro commands to Gemini CLI..."
    if [ -f "scripts/sync-kiro-commands.sh" ]; then
        chmod +x scripts/sync-kiro-commands.sh
        ./scripts/sync-kiro-commands.sh > /dev/null 2>&1
        print_success "Kiro commands synced to .gemini/customPrompts/"
    else
        print_warning "sync-kiro-commands.sh not found, skipping Gemini sync"
    fi
fi

#######################################
# Setup Git Hooks
#######################################

print_status "Setting up Git hooks..."

# Initialize husky
npx husky init > /dev/null 2>&1 || true

# Create pre-commit hook
mkdir -p .husky
cat > .husky/pre-commit << 'EOF'
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
npm run test:unit -- --onlyChanged --passWithNoTests
EOF

chmod +x .husky/pre-commit

print_success "Git hooks configured"

#######################################
# Setup Environment File
#######################################

print_status "Setting up environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
    print_success "Created .env file (please add your API keys)"
else
    print_success ".env file already exists"
fi

#######################################
# Check Current Authentication Status
#######################################

GH_AUTHENTICATED=false
ANTHROPIC_SECRET_SET=false
GEMINI_SECRET_SET=false
CLAUDE_APP_INSTALLED=false

# Check if gh is authenticated
if command -v gh &> /dev/null; then
    if gh auth status &> /dev/null; then
        GH_AUTHENTICATED=true
        print_success "GitHub CLI is authenticated"

        # Check if ANTHROPIC_API_KEY secret is already set
        if gh secret list 2>/dev/null | grep -q "ANTHROPIC_API_KEY"; then
            ANTHROPIC_SECRET_SET=true
            print_success "ANTHROPIC_API_KEY secret is already configured"
        fi

        # Check if GEMINI_API_KEY secret is already set
        if gh secret list 2>/dev/null | grep -q "GEMINI_API_KEY"; then
            GEMINI_SECRET_SET=true
            print_success "GEMINI_API_KEY secret is already configured"
        fi
    fi
fi

# Check if Claude GitHub App is installed (check for .claude directory or config)
if [ -d ".claude" ] || gh api /user/installations 2>/dev/null | grep -q "claude"; then
    CLAUDE_APP_INSTALLED=true
    print_success "Claude GitHub App appears to be installed"
fi

# Check for Gemini configuration
if [ -d ".gemini" ] || [ -f "GEMINI.md" ]; then
    print_success "Gemini CLI configuration detected"
fi

#######################################
# Final Instructions
#######################################

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

print_success "All components installed successfully!"

echo ""
echo "📋 Next Steps:"
echo ""

STEP_NUM=1

# Show installed AI tools
echo "🤖 AI Tools Status:"
if [ "$CLAUDE_INSTALLED" = true ]; then
    echo "   ✅ Claude Code installed"
else
    echo "   ⚠️  Claude Code not installed"
fi
if [ "$GEMINI_INSTALLED" = true ]; then
    echo "   ✅ Gemini CLI installed"
else
    echo "   ⚠️  Gemini CLI not installed"
fi
echo ""

# Only show API key instructions if not already configured
if [ "$ANTHROPIC_SECRET_SET" = false ] && [ "$CLAUDE_INSTALLED" = true ]; then
    echo "  $STEP_NUM. Add your Anthropic API key (for Claude Code):"
    echo "     Edit .env and add ANTHROPIC_API_KEY"
    if [ "$GH_AUTHENTICATED" = true ]; then
        echo "     gh secret set ANTHROPIC_API_KEY"
    fi
    echo ""
    STEP_NUM=$((STEP_NUM + 1))
fi

if [ "$GEMINI_SECRET_SET" = false ] && [ "$GEMINI_INSTALLED" = true ]; then
    echo "  $STEP_NUM. Add your Google API key (for Gemini CLI):"
    echo "     Edit .env and add GEMINI_API_KEY"
    if [ "$GH_AUTHENTICATED" = true ]; then
        echo "     gh secret set GEMINI_API_KEY"
    fi
    echo ""
    STEP_NUM=$((STEP_NUM + 1))
fi

if [ "$GH_AUTHENTICATED" = false ]; then
    echo "  $STEP_NUM. Authenticate GitHub CLI:"
    echo "     gh auth login"
    echo ""
    STEP_NUM=$((STEP_NUM + 1))
fi

# Only show Claude GitHub App instructions if not installed
if [ "$CLAUDE_APP_INSTALLED" = false ] && [ "$CLAUDE_INSTALLED" = true ]; then
    echo "  $STEP_NUM. Install Claude GitHub App:"
    echo "     claude \"/install-github-app\""
    echo ""
    STEP_NUM=$((STEP_NUM + 1))
fi

echo "  $STEP_NUM. Customize project context:"
echo "     code steering/project-context.md"
echo "     code CLAUDE.md"
if [ "$GEMINI_INSTALLED" = true ]; then
    echo "     code GEMINI.md (optional - for Gemini CLI)"
fi
echo ""
STEP_NUM=$((STEP_NUM + 1))

echo "  $STEP_NUM. Start your first feature:"
if [ "$CLAUDE_INSTALLED" = true ]; then
    echo "     claude \"/kiro:spec-init Your feature description\""
fi
if [ "$GEMINI_INSTALLED" = true ]; then
    echo "     gemini \"/kiro:spec-init Your feature description\""
fi
echo ""

echo "📚 Documentation: ./docs/workflow-guide.md"
echo "🆘 Quick Reference: ./docs/quick-reference.md"
echo ""
print_success "Happy coding with AI-SDLC! 🚀"
echo ""
