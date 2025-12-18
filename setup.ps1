#######################################
# AI-SDLC Template Setup Script
# For Windows (PowerShell)
#######################################

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Status { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Header
Write-Host ""
Write-Host "+==========================================================+" -ForegroundColor Cyan
Write-Host "|          AI-SDLC Workflow Template Setup                 |" -ForegroundColor Cyan
Write-Host "|  Spec-Driven Development with Claude Code & Gemini CLI   |" -ForegroundColor Cyan
Write-Host "+==========================================================+" -ForegroundColor Cyan
Write-Host ""

#######################################
# Check Prerequisites
#######################################

Write-Status "Checking prerequisites..."

# Check Node.js
try {
    $nodeVersion = (node -v) -replace 'v', '' -split '\.' | Select-Object -First 1
    if ([int]$nodeVersion -ge 18) {
        Write-Success "Node.js $(node -v) found"
    } else {
        Write-Warn "Node.js version is below 18. Please upgrade."
        Write-Host "  Install: https://nodejs.org/"
        exit 1
    }
} catch {
    Write-Err "Node.js not found"
    Write-Host "  Install from: https://nodejs.org/"
    exit 1
}

# Check npm
try {
    $npmVersion = npm -v
    Write-Success "npm $npmVersion found"
} catch {
    Write-Err "npm not found"
    exit 1
}

# Check Git
try {
    $gitVersion = (git --version) -replace 'git version ', ''
    Write-Success "Git $gitVersion found"
} catch {
    Write-Err "Git not found"
    Write-Host "  Install from: https://git-scm.com/"
    exit 1
}

# Check GitHub CLI (optional but recommended)
$ghInstalled = $false
try {
    gh --version | Out-Null
    Write-Success "GitHub CLI found"
    $ghInstalled = $true
} catch {
    Write-Warn "GitHub CLI not found (optional but recommended)"
    Write-Host "  Install: winget install GitHub.cli"
}

Write-Host ""

#######################################
# Install Dependencies
#######################################

Write-Status "Installing npm dependencies..."

npm install --save-dev `
    jest `
    "@types/jest" `
    ts-jest `
    typescript `
    "@playwright/test" `
    eslint `
    prettier `
    husky `
    lint-staged 2>&1 | Out-Null

Write-Success "npm dependencies installed"

#######################################
# Install Claude Code
#######################################

Write-Status "Checking Claude Code..."

$claudeInstalled = $false
try {
    claude --version | Out-Null
    Write-Success "Claude Code already installed"
    $claudeInstalled = $true
} catch {
    Write-Status "Installing Claude Code..."
    try {
        npm install -g @anthropic-ai/claude-code 2>&1 | Out-Null
        Write-Success "Claude Code installed"
        $claudeInstalled = $true
    } catch {
        Write-Warn "Claude Code installation failed (optional)"
    }
}

#######################################
# Install Gemini CLI
#######################################

Write-Status "Checking Gemini CLI..."

$geminiInstalled = $false
try {
    gemini --version | Out-Null
    Write-Success "Gemini CLI already installed"
    $geminiInstalled = $true
} catch {
    Write-Status "Installing Gemini CLI..."
    try {
        npm install -g @google/gemini-cli 2>&1 | Out-Null
        $geminiInstalled = $true
        Write-Success "Gemini CLI installed"
    } catch {
        Write-Warn "Gemini CLI not installed (install manually: npm install -g @google/gemini-cli)"
    }
}

#######################################
# Install cc-ssd-enh Framework
#######################################

Write-Status "Installing cc-ssd-enh (Spec-Driven Development framework)..."

try {
    npx cc-ssd-enh@latest --yes 2>&1 | Out-Null
    Write-Success "cc-ssd-enh framework installed"
} catch {
    Write-Warn "cc-ssd-enh auto-install failed, trying manual setup..."
    npx cc-ssd-enh@latest
}

#######################################
# Sync Kiro Commands to Gemini CLI
#######################################

if ($geminiInstalled -or (Test-Path "GEMINI.md")) {
    Write-Status "Syncing Kiro commands to Gemini CLI..."

    $claudeCommands = ".claude/commands/kiro"
    $geminiPrompts = ".gemini/customPrompts"

    if (Test-Path $claudeCommands) {
        New-Item -ItemType Directory -Force -Path $geminiPrompts | Out-Null

        Get-ChildItem "$claudeCommands/*.md" | ForEach-Object {
            $filename = $_.Name
            $geminiFilename = "kiro-$filename"
            $content = @"
<!-- Synced from .claude/commands/kiro/$filename -->
<!-- Use: /kiro-$($filename -replace '\.md$','') in Gemini CLI -->

$(Get-Content $_.FullName -Raw)
"@
            Set-Content -Path "$geminiPrompts/$geminiFilename" -Value $content
        }

        # Create settings.json if not exists
        $settingsFile = ".gemini/settings.json"
        if (-not (Test-Path $settingsFile)) {
            $settings = @'
{
  "customPromptsPath": ".gemini/customPrompts",
  "contextFiles": ["GEMINI.md", "PROJECT.md"],
  "syncWithClaude": true
}
'@
            Set-Content -Path $settingsFile -Value $settings
        }

        Write-Success "Kiro commands synced to .gemini/customPrompts/"
    } else {
        Write-Warn "Claude commands not found, skipping Gemini sync"
    }
}

#######################################
# Setup Git Hooks
#######################################

Write-Status "Setting up Git hooks..."

try {
    npx husky init 2>&1 | Out-Null
} catch {
    # Ignore if already initialized
}

# Create .husky directory and pre-commit hook
New-Item -ItemType Directory -Force -Path ".husky" | Out-Null

$preCommitContent = @'
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
npm run test:unit -- --onlyChanged --passWithNoTests
'@

Set-Content -Path ".husky/pre-commit" -Value $preCommitContent -NoNewline

Write-Success "Git hooks configured"

#######################################
# Setup Environment File
#######################################

Write-Status "Setting up environment..."

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    }
    Write-Success "Created .env file (please add your API keys)"
} else {
    Write-Success ".env file already exists"
}

#######################################
# Check Current Authentication Status
#######################################

$ghAuthenticated = $false
$anthropicSecretSet = $false
$geminiSecretSet = $false
$claudeAppInstalled = $false

# Check if gh is authenticated
if ($ghInstalled) {
    try {
        gh auth status 2>&1 | Out-Null
        $ghAuthenticated = $true
        Write-Success "GitHub CLI is authenticated"

        # Check if ANTHROPIC_API_KEY secret is already set
        $secrets = gh secret list 2>&1
        if ($secrets -match "ANTHROPIC_API_KEY") {
            $anthropicSecretSet = $true
            Write-Success "ANTHROPIC_API_KEY secret is already configured"
        }

        # Check if GEMINI_API_KEY secret is already set
        if ($secrets -match "GEMINI_API_KEY") {
            $geminiSecretSet = $true
            Write-Success "GEMINI_API_KEY secret is already configured"
        }
    } catch {
        # Not authenticated
    }
}

# Check if Claude GitHub App is installed
if (Test-Path ".claude") {
    $claudeAppInstalled = $true
    Write-Success "Claude GitHub App appears to be installed"
} elseif ($ghAuthenticated) {
    try {
        $installations = gh api /user/installations 2>&1
        if ($installations -match "claude") {
            $claudeAppInstalled = $true
            Write-Success "Claude GitHub App appears to be installed"
        }
    } catch {
        # Ignore API errors
    }
}

# Check for Gemini configuration
if ((Test-Path ".gemini") -or (Test-Path "GEMINI.md")) {
    Write-Success "Gemini CLI configuration detected"
}

#######################################
# Final Instructions
#######################################

Write-Host ""
Write-Host "+==========================================================+" -ForegroundColor Cyan
Write-Host "|                    Setup Complete!                       |" -ForegroundColor Cyan
Write-Host "+==========================================================+" -ForegroundColor Cyan
Write-Host ""

Write-Success "All components installed successfully!"

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host ""

$stepNum = 1

# Show installed AI tools
Write-Host "AI Tools Status:" -ForegroundColor White
if ($claudeInstalled) {
    Write-Host "   [OK] Claude Code installed" -ForegroundColor Green
} else {
    Write-Host "   [--] Claude Code not installed" -ForegroundColor Yellow
}
if ($geminiInstalled) {
    Write-Host "   [OK] Gemini CLI installed" -ForegroundColor Green
} else {
    Write-Host "   [--] Gemini CLI not installed" -ForegroundColor Yellow
}
Write-Host ""

# Only show API key instructions if not already configured
if ((-not $anthropicSecretSet) -and $claudeInstalled) {
    Write-Host "  $stepNum. Add your Anthropic API key (for Claude Code):" -ForegroundColor White
    Write-Host "     Edit .env and add ANTHROPIC_API_KEY" -ForegroundColor Gray
    if ($ghAuthenticated) {
        Write-Host "     gh secret set ANTHROPIC_API_KEY" -ForegroundColor Gray
    }
    Write-Host ""
    $stepNum++
}

if ((-not $geminiSecretSet) -and $geminiInstalled) {
    Write-Host "  $stepNum. Add your Google API key (for Gemini CLI):" -ForegroundColor White
    Write-Host "     Edit .env and add GEMINI_API_KEY" -ForegroundColor Gray
    if ($ghAuthenticated) {
        Write-Host "     gh secret set GEMINI_API_KEY" -ForegroundColor Gray
    }
    Write-Host ""
    $stepNum++
}

if (-not $ghAuthenticated) {
    Write-Host "  $stepNum. Authenticate GitHub CLI:" -ForegroundColor White
    Write-Host "     gh auth login" -ForegroundColor Gray
    Write-Host ""
    $stepNum++
}

# Only show Claude GitHub App instructions if not installed
if ((-not $claudeAppInstalled) -and $claudeInstalled) {
    Write-Host "  $stepNum. Install Claude GitHub App:" -ForegroundColor White
    Write-Host "     claude `"/install-github-app`"" -ForegroundColor Gray
    Write-Host ""
    $stepNum++
}

Write-Host "  $stepNum. Customize project context:" -ForegroundColor White
Write-Host "     code steering/project-context.md" -ForegroundColor Gray
Write-Host "     code CLAUDE.md" -ForegroundColor Gray
if ($geminiInstalled) {
    Write-Host "     code GEMINI.md (optional - for Gemini CLI)" -ForegroundColor Gray
}
Write-Host ""
$stepNum++

Write-Host "  $stepNum. Start your first feature:" -ForegroundColor White
if ($claudeInstalled) {
    Write-Host "     claude `"/kiro:spec-init Your feature description`"" -ForegroundColor Gray
}
if ($geminiInstalled) {
    Write-Host "     gemini `"/kiro:spec-init Your feature description`"" -ForegroundColor Gray
}
Write-Host ""

Write-Host "Documentation: ./docs/workflow-guide.md" -ForegroundColor Cyan
Write-Host "Quick Reference: ./docs/quick-reference.md" -ForegroundColor Cyan
Write-Host ""
Write-Success "Happy coding with AI-SDLC!"
Write-Host ""
