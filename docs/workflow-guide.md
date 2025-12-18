# AI-SDLC Workflow Guide

Complete end-to-end software development lifecycle using AI tools.

## Overview

This workflow combines:

- **cc-ssd-enh**: Spec-driven development framework (11 slash commands)
- **Claude Code**: AI coding assistant (Claude Max subscription)
- **Google Antigravity**: Multi-agent IDE for parallel work (free preview)
- **GitHub Actions**: CI/CD automation with Claude Code Action

## Initial Setup

Run the setup script for your platform:

```bash
# macOS/Linux
./setup.sh

# Windows (PowerShell)
.\setup.ps1
```

The setup scripts automatically detect your environment and only show relevant configuration steps:

- ✅ Skips GitHub authentication instructions if `gh` is already authenticated
- ✅ Skips API key setup if `ANTHROPIC_API_KEY` secret is already configured
- ✅ Skips Claude GitHub App installation if already installed

## Workflow Phases

### Phase 1: Ideation & Requirements

```bash
claude "/kiro:spec-init Build user authentication with OAuth"
claude "/kiro:spec-requirements auth-oauth"
```

**Output**: `specs/features/auth-oauth/requirements.md` with EARS format requirements

### Phase 2: Architecture & Design

```bash
claude "/kiro:spec-design auth-oauth"
```

For existing codebases:

```bash
claude "/kiro:validate-gap auth-oauth"
claude "/kiro:validate-design auth-oauth"
```

**Output**: `specs/features/auth-oauth/design.md` with architecture

### Phase 3: Task Breakdown

```bash
claude "/kiro:spec-tasks auth-oauth -y"
```

**Output**: `specs/features/auth-oauth/tasks.md` with implementation tasks

### Phase 4: Implementation (TDD)

```bash
claude "/kiro:spec-impl auth-oauth 1.1,1.2,1.3"
```

Tests are written BEFORE implementation code.

### Phase 5: Review & Merge

- Push to feature branch
- Create PR
- Claude automatically reviews
- Human approves
- Merge

### Phase 6: Deployment

- Staging deploys automatically on merge to main
- Production requires manual approval

## Multi-Person Parallel Work

```
Feature: auth-oauth
├── Person A: Tasks 1.1, 1.2 (config, service)
├── Person B: Tasks 2.1, 2.2 (callback, UI)
└── Person C: E2E tests + integration tests
```

Use separate branches:

```bash
git checkout -b feature/auth-oauth/config  # Person A
git checkout -b feature/auth-oauth/ui      # Person B
```

## Tool Selection

| Scenario              | Tool                     |
| --------------------- | ------------------------ |
| Simple edits          | Claude Code              |
| Multi-file features   | Claude Code + cc-ssd-enh |
| Complex parallel work | Google Antigravity       |
| Code review           | @claude in GitHub        |

## Multi-AI Workflow

This project supports using Claude Code and Antigravity (Gemini) together:

| Phase          | Tool        | Commands/Actions                                        |
| -------------- | ----------- | ------------------------------------------------------- |
| Ideation       | Claude Code | `/kiro:spec-init`                                       |
| Requirements   | Claude Code | `/kiro:spec-requirements`                               |
| Design         | Claude Code | `/kiro:spec-design`, `/kiro:validate-*`                 |
| Task Breakdown | Claude Code | `/kiro:spec-tasks`                                      |
| Implementation | Antigravity | Read `specs/features/<name>/tasks.md`, code in parallel |
| Testing        | Antigravity | Write tests per requirements, achieve ≥80% coverage     |
| Deployment     | Either      | CI/CD pipelines                                         |

### AI Context Sync

Both tools share the same project context via `PROJECT.md`:

```bash
# Edit shared context
code PROJECT.md

# Generate CLAUDE.md and GEMINI.md
./scripts/sync-ai-context.sh
```

**Important**: Always edit `PROJECT.md`, never edit `CLAUDE.md` or `GEMINI.md` directly.

## Cost Summary

| Tool           | Cost           |
| -------------- | -------------- |
| Claude Max × 2 | $200/month     |
| GitHub Free    | $0             |
| Antigravity    | $0 (preview)   |
| **Total**      | **$200/month** |

---

For daily commands, see [Quick Reference](./quick-reference.md)
