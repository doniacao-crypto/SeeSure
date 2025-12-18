# Project: [YOUR PROJECT NAME]

> **AI Context File**: This file defines the shared context for all AI coding assistants (Claude Code, Gemini/Antigravity, etc.). Both CLAUDE.md and GEMINI.md are generated from this file.

## Project Overview

[Describe your project in 2-3 sentences. What problem does it solve? Who is it for?]

## Tech Stack

### Frontend

- Framework: [React/Vue/Angular/Next.js]
- Styling: [Tailwind/CSS Modules/Styled Components]
- State: [Redux/Zustand/Context]

### Backend

- Runtime: [Node.js/Python/Go]
- Framework: [Express/FastAPI/Gin]
- Database: [PostgreSQL/MongoDB/MySQL]

### Infrastructure

- Cloud: [AWS/GCP/Azure]
- CI/CD: GitHub Actions
- Deployment: [Vercel/Railway/K8s]

## AI Workflow Distribution

This project uses multiple AI tools for different phases:

| Phase                   | Tool                 | Purpose                                      |
| ----------------------- | -------------------- | -------------------------------------------- |
| Ideation & Requirements | Claude Code          | `/kiro:spec-init`, `/kiro:spec-requirements` |
| Design                  | Claude Code          | `/kiro:spec-design`, `/kiro:validate-*`      |
| Task Breakdown          | Claude Code          | `/kiro:spec-tasks`                           |
| Implementation          | Antigravity (Gemini) | Parallel coding from task specs              |
| Testing                 | Antigravity (Gemini) | Unit, integration, E2E tests                 |
| Deployment              | Either               | CI/CD automation                             |

**Important**: All AI tools MUST follow the cc-ssd-enh framework discipline.

## Development Standards

### Spec-Driven Development (cc-ssd-enh)

- **Framework**: cc-ssd-enh (AI-DLC)
- **Workflow**: Requirements → Design → Tasks → Implementation
- All features MUST start with `/kiro:spec-init`
- Specs location: `specs/features/<feature-name>/`

### Test-Driven Development

- Write tests BEFORE implementation
- All requirements MUST have test scenarios
- Coverage target: ≥80%

### Code Quality

- TypeScript strict mode enabled
- ESLint + Prettier enforced via pre-commit hooks
- All PRs require AI review + human approval

## Commands Reference

### Spec Workflow (Claude Code)

```bash
/kiro:steering              # Generate/update project context
/kiro:spec-init <desc>      # Start new feature specification
/kiro:spec-requirements <n> # Generate requirements (EARS format)
/kiro:spec-design <n>       # Create technical design
/kiro:spec-tasks <n>        # Break into implementation tasks
/kiro:spec-impl <n> [tasks] # Implement with TDD
```

### Brownfield (Existing Code)

```bash
/kiro:validate-gap <n>      # Analyze existing vs required
/kiro:validate-design <n>   # Check design compatibility
```

### Implementation (Antigravity/Gemini)

When implementing tasks, always:

1. Read the task spec from `specs/features/<feature-name>/tasks.md`
2. Follow the design in `specs/features/<feature-name>/design.md`
3. Write tests first (TDD)
4. Reference requirements from `specs/features/<feature-name>/requirements.md`

## Quality Gates

### Before Design

- [ ] Requirements in EARS format
- [ ] Test scenarios defined for each requirement
- [ ] Human approval on requirements.md

### Before Implementation

- [ ] Design approved
- [ ] API contracts defined
- [ ] For brownfield: validate-gap + validate-design done

### Before Merge

- [ ] All tests pass
- [ ] Coverage ≥80%
- [ ] AI review passed
- [ ] Human review approved

## Spec File Locations

```
specs/features/<feature-name>/
├── requirements.md    # EARS format requirements + test scenarios
├── design.md          # Technical design + API contracts
└── tasks.md           # Implementation tasks with acceptance criteria
```

**All AI tools must read these specs before implementation.**

---

_Last updated: [DATE]_
