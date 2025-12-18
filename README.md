# AI-SDLC Workflow Template

> **Spec-Driven Development with AI-DLC for Teams**
>
> Clone this template → Run setup → Start building with AI-powered workflows

[![Setup](https://img.shields.io/badge/setup-automated-green)](./setup.sh)
[![Framework](https://img.shields.io/badge/framework-cc--ssd--enh-blue)](https://www.npmjs.com/package/cc-ssd-enh)
[![License](https://img.shields.io/badge/license-MIT-yellow)](./LICENSE)

---

## 🚀 Quick Start (5 minutes)

### Option 1: Use as GitHub Template (Recommended)

1. Click **"Use this template"** → **"Create a new repository"**
2. Clone your new repository
3. Run setup:

```bash
# macOS/Linux
./setup.sh

# Windows (PowerShell as Admin)
.\setup.ps1
```

### Option 2: Clone and Reinitialize

```bash
# Clone template
git clone https://github.com/ibetterai/sdlc.git my-project
cd my-project

# Remove template git history and start fresh
rm -rf .git
git init

# Run setup
./setup.sh

# Create your repository and push
git remote add origin https://github.com/YOUR_ORG/my-project.git
git push -u origin main
```

---

## 📦 What's Included

```
sdlc/
├── .claude/                    # Claude Code slash commands
│   └── commands/               # /kiro:* commands (auto-installed)
├── .github/
│   ├── workflows/
│   │   ├── claude.yml          # Claude Code PR reviews
│   │   ├── ci.yml              # Full test pipeline
│   │   └── deploy.yml          # Deployment workflow
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── specs/
│   ├── features/               # Feature specifications
│   │   └── _template/          # Template for new features
│   └── templates/              # Reusable spec templates
├── steering/
│   ├── project-context.md      # Project memory (customize)
│   ├── architecture.md         # Tech decisions
│   └── conventions.md          # Team standards
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── performance/
├── src/                        # Your source code
├── docs/
│   ├── workflow-guide.md       # Complete workflow documentation
│   ├── diagrams.md             # Visual workflow diagrams
│   └── quick-reference.md      # Daily commands cheat sheet
├── CLAUDE.md                   # Claude Code project context
├── package.json                # Dependencies & scripts
├── setup.sh                    # Unix/macOS setup script
├── setup.ps1                   # Windows setup script
├── Makefile                    # Common commands
└── .env.example                # Environment variables template
```

---

## 🛠️ Prerequisites

The setup script will check and install these automatically:

| Tool        | Purpose            | Auto-Install |
| ----------- | ------------------ | ------------ |
| Node.js 18+ | Runtime            | ✅ Prompted  |
| Git 2.23+   | Version control    | ✅ Prompted  |
| Claude Code | AI assistant       | ✅ Via npm   |
| cc-ssd-enh  | Spec framework     | ✅ Via npm   |
| GitHub CLI  | GitHub integration | ✅ Prompted  |

---

## 🔧 Post-Setup Configuration

The setup scripts (`setup.sh` / `setup.ps1`) are **smart** - they automatically detect what's already configured and only show relevant next steps:

| Check                          | If Already Configured              |
| ------------------------------ | ---------------------------------- |
| GitHub CLI authenticated       | Skips `gh auth login` instructions |
| `ANTHROPIC_API_KEY` secret set | Skips API key setup steps          |
| Claude GitHub App installed    | Skips app installation step        |

### Manual Configuration (if needed)

#### Add GitHub Secrets

If not already configured, go to your repo → Settings → Secrets and variables → Actions:

| Secret Name         | Description                               | Required |
| ------------------- | ----------------------------------------- | -------- |
| `ANTHROPIC_API_KEY` | Claude API key from console.anthropic.com | ✅ Yes   |
| `DEPLOY_KEY`        | Deployment credentials (if deploying)     | Optional |

Or via CLI (if `gh` is authenticated):

```bash
gh secret set ANTHROPIC_API_KEY
```

#### Customize Project Context

Edit these files for your project:

```bash
# Update project memory
code steering/project-context.md

# Set your tech stack and architecture
code steering/architecture.md

# Define team conventions
code steering/conventions.md

# Update Claude Code context
code CLAUDE.md
```

#### Install GitHub App (for @claude mentions)

If not already installed:

```bash
claude "/install-github-app"
```

---

## 📋 Workflow Commands

### Starting a New Feature

```bash
# 1. Initialize feature spec
claude "/kiro:spec-init Build user authentication with OAuth"

# 2. Generate requirements (EARS format with test scenarios)
claude "/kiro:spec-requirements auth-oauth"

# 3. Create technical design
claude "/kiro:spec-design auth-oauth"

# 4. Break into tasks
claude "/kiro:spec-tasks auth-oauth"

# 5. Implement with TDD
claude "/kiro:spec-impl auth-oauth 1.1,1.2,1.3"
```

### Enhancing Existing Code

```bash
# 1. Update project context
claude "/kiro:steering"

# 2. Initialize enhancement
claude "/kiro:spec-init Add password reset to auth"

# 3. Analyze gap with existing code
claude "/kiro:validate-gap password-reset"

# 4. Design with integration focus
claude "/kiro:spec-design password-reset"

# 5. Validate design compatibility
claude "/kiro:validate-design password-reset"

# 6. Continue with tasks and implementation...
```

### Testing

```bash
make test          # Run all tests
make test-unit     # Unit tests only
make test-e2e      # End-to-end tests
make test-perf     # Performance tests
make test-security # Security scan
```

### GitHub Integration

In any PR or Issue comment:

```
@claude review          # Request code review
@claude fix             # Auto-fix issues
@claude test            # Generate missing tests
@claude security        # Security review
```

---

## 👥 Multi-Person Collaboration

### Parallel Work Pattern

```
┌─────────────────────────────────────────────────────────┐
│                 FEATURE: User Auth                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Person A              Person B              Person C    │
│  ───────────           ───────────           ─────────   │
│  Task 1.1: Config      Task 2.1: Callback    E2E Tests  │
│  Task 1.2: Service     Task 2.2: UI          Int Tests  │
│                                                          │
│           └──────────────┬───────────────────┘          │
│                          ▼                               │
│                   Code Review                            │
│                          ▼                               │
│                   Merge & Deploy                         │
└─────────────────────────────────────────────────────────┘
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/auth-oauth

# Work on your tasks
claude "/kiro:spec-impl auth-oauth 1.1"

# Push and create PR
git push -u origin feature/auth-oauth
gh pr create --fill

# Claude automatically reviews when PR is opened
```

---

## 🤖 Multi-AI Workflow

This template supports using multiple AI tools across the development lifecycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Tool Distribution                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Claude Code                        Antigravity (Gemini)         │
│  ────────────                       ─────────────────────        │
│  • Ideation                         • Implementation              │
│  • Requirements (/kiro:spec-*)      • Parallel coding            │
│  • Design & Architecture            • Testing                     │
│  • Task breakdown                   • Deployment                  │
│                                                                   │
│              ↓ specs/features/* ↓                                │
│                                                                   │
│  Both AI tools share:                                            │
│  • PROJECT.md (single source of truth)                           │
│  • cc-ssd-enh discipline                                         │
│  • Quality gates & standards                                     │
└─────────────────────────────────────────────────────────────────┘
```

### AI Context Sync

All AI tools use the same project context. `PROJECT.md` is the single source of truth:

```bash
# Edit the shared context
code PROJECT.md

# Sync to CLAUDE.md and GEMINI.md
./scripts/sync-ai-context.sh

# Validate sync (useful in CI)
./scripts/validate-ai-context.sh
```

| File         | Purpose                               |
| ------------ | ------------------------------------- |
| `PROJECT.md` | Single source of truth (edit this)    |
| `CLAUDE.md`  | Auto-generated for Claude Code        |
| `GEMINI.md`  | Auto-generated for Gemini/Antigravity |

---

## 💰 Cost Optimization

### Recommended Stack (2-3 People)

| Tool           | Monthly Cost | Notes               |
| -------------- | ------------ | ------------------- |
| Claude Max × 2 | $200         | Primary AI backbone |
| GitHub Free    | $0           | 2,000 CI/CD minutes |
| VS Code        | $0           | Primary IDE         |
| Antigravity    | $0           | Free preview        |
| **Total**      | **$200**     |                     |

---

## 📚 Documentation

| Document                                     | Description                    |
| -------------------------------------------- | ------------------------------ |
| [Workflow Guide](./docs/workflow-guide.md)   | Complete end-to-end SDLC guide |
| [Diagrams](./docs/diagrams.md)               | Visual workflow diagrams       |
| [Quick Reference](./docs/quick-reference.md) | Daily commands cheat sheet     |
| [Troubleshooting](./docs/troubleshooting.md) | Common issues and fixes        |

---

## 🔄 Updating the Template

To pull updates from the template into your project:

```bash
# Add template as upstream (one time)
git remote add template https://github.com/ibetterai/sdlc.git

# Fetch and merge updates
git fetch template
git merge template/main --allow-unrelated-histories
```

---

## 📄 License

MIT License - See [LICENSE](./LICENSE)

---

_Built with ❤️ using Claude Max, cc-ssd-enh, and Google Antigravity_
