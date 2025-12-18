# AI-SDLC Quick Reference Card

_For cc-ssd-enh + Claude Max + Antigravity Workflow_

---

## ⚡ Setup

```bash
./setup.sh      # macOS/Linux
.\setup.ps1     # Windows
```

> **Smart Detection**: Scripts auto-detect `gh` auth, API keys, and Claude app - only shows what you need to configure.

---

## 🚀 Daily Commands

### Start New Feature

```bash
claude "/kiro:spec-init <feature description>"
claude "/kiro:spec-requirements <feature-name>"
claude "/kiro:spec-design <feature-name> -y"
claude "/kiro:spec-tasks <feature-name> -y"
claude "/kiro:spec-impl <feature-name> 1.1,1.2"
```

### Enhance Existing Product

```bash
claude "/kiro:steering"                         # First, capture existing context
claude "/kiro:spec-init <enhancement>"
claude "/kiro:validate-gap <feature-name>"      # Analyze vs existing
claude "/kiro:spec-design <feature-name>"
claude "/kiro:validate-design <feature-name>"   # Check compatibility
claude "/kiro:spec-tasks <feature-name> -y"
claude "/kiro:spec-impl <feature-name> 1.1"
```

---

## 🛠️ Tool Selection

| Task Type          | Use This Tool            |
| ------------------ | ------------------------ |
| Chat/Brainstorm    | Claude.ai                |
| Single file edit   | Claude Code in VS Code   |
| Multi-file feature | Claude Code + cc-ssd-enh |
| Complex/Parallel   | Google Antigravity       |
| iOS/macOS          | Xcode + Claude Code      |
| Code Review        | @claude in GitHub PR     |

---

## 📦 Testing Commands

```bash
npm run test:unit          # Unit tests
npm run test:integration   # Integration tests
npm run test:e2e           # End-to-end
npm run test:perf          # Performance
npm run test:security      # Security scan
npm run test:all           # Everything
```

---

## 🔄 GitHub Integration

### In PR/Issue Comments:

```
@claude review             # Full code review
@claude fix                # Auto-fix issues
@claude test               # Generate missing tests
@claude security           # Security review
```

---

## ✅ Quality Gates Checklist

### Before Design:

- [ ] Requirements in EARS format
- [ ] Test scenarios for each requirement
- [ ] Human approval on requirements.md

### Before Implementation:

- [ ] Design approved
- [ ] API contracts defined
- [ ] For existing products: validate-gap + validate-design done

### Before Merge:

- [ ] All tests pass
- [ ] Coverage ≥80%
- [ ] Claude review passed
- [ ] Human review approved

---

## 💰 Cost Tracking

| Tool            | Monthly Budget |
| --------------- | -------------- |
| Claude Max × 2  | $200           |
| Everything else | $0             |
| **Total**       | **$200**       |

---

_v1.0 | December 2025_
