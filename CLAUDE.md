# Claude Code Enhanced Spec-Driven Development

Enhanced Kiro-style Spec Driven Development with WebSearch integration, knowledge management, and error documentation.

## Project Scaffold

| Field | Value |
|-------|-------|
| Tier | Moderate |
| Setup date | 2026-07-23 |
| Last check-in | 2026-07-23 |

## Documentation Map

| Concept | Path | Status |
|---------|------|--------|
| Scope (in/out/uncertain) | SCOPE.md | Active |
| Domain glossary | CONTEXT.md | Active |
| External dependencies | DEPENDENCIES.md | Active |
| Architecture decisions | docs/adr/ | Active (0001–0005) |
| **Tracking backlog (work list)** | docs/BACKLOG.md | Active |
| Clinical sign-off register | docs/clinical/sign-off-register.md | Awaiting Clinical Lead |
| Working concerns (local) | docs/local/CONCERNS.md | Active, gitignored |

**Start each session at `docs/BACKLOG.md`** — it is the single ordered work list
(P0 trust the measurement → P1 clinical trust → P2 pilot → P3 platform).

## Project Context

### Paths

- Steering: `.kiro/steering/`
- Specs: `.kiro/specs/`
- Commands: `.claude/commands/`
- **Knowledge Base**: `.kiro/knowledge/` (Enhanced)

### Enhanced Capabilities

- **WebSearch Integration**: Automatic research for requirements and design
- **Knowledge Management**: Structured documentation of research findings
- **Error Documentation**: Comprehensive error tracking with web-searched solutions
- **Knife Surgery Coding**: Context-aware code changes with minimal impact

### Directory Structure

**Steering** (`.kiro/steering/`) - Guide AI with project-wide rules and context
**Specs** (`.kiro/specs/`) - Formalize development process for individual features
**Knowledge** (`.kiro/knowledge/`) - Research documentation and error solutions

### Knowledge Organization

- `.kiro/knowledge/research-{topic}-{number}.md` - Research findings
- `.kiro/knowledge/docs-{technology}-{number}.md` - Fetched documentation
- `.kiro/knowledge/bestpractices-{type}-{number}.md` - Best practices research
- `.kiro/knowledge/errors/{errorname}.md` - Error documentation with solutions
- `.kiro/knowledge/architecture-{pattern}-{number}.md` - Architecture analysis
- `.kiro/knowledge/comparison-{technologies}-{number}.md` - Technology comparisons

### Active Specifications

- **eye-movement-assessment**: Clinical-grade eye tracking assessment system (Phase: initialized, POC: completed)
  - Status: `/kiro:spec-status eye-movement-assessment`
  - Next: `/kiro:spec-requirements eye-movement-assessment`

- Check `.kiro/specs/` for active specifications
- Use `/kiro:spec-status [feature-name]` to check progress
- Review `.kiro/knowledge/` for relevant research before starting new specs

## Development Guidelines

- Think in English, generate responses in English

## Enhanced Workflow

### Phase 0: Steering & Knowledge Review (Recommended)

`/kiro:steering` - Create/update steering documents
`/kiro:steering-custom` - Create custom steering for specialized contexts
**Enhanced**: Review existing knowledge base in `.kiro/knowledge/` for relevant research

### Phase 1: Research-Enhanced Specification Creation

1. `/kiro:spec-init [detailed description]` - Initialize spec with detailed project description
2. `/kiro:spec-requirements [feature]` - **Enhanced**: Automatic web research + requirements generation
3. `/kiro:spec-design [feature]` - **Enhanced**: Research-informed design with documentation
4. `/kiro:spec-tasks [feature]` - Interactive: Confirms both requirements and design review

### Phase 2: Knowledge-Driven Implementation

`/kiro:spec-impl [feature] [tasks]` - **Enhanced**: Knife surgery coding with error documentation

### Phase 3: Progress & Knowledge Tracking

`/kiro:spec-status [feature]` - Check current progress and phases
**Enhanced**: Review accumulated knowledge and error solutions

## Enhanced Features

### Automatic Research Integration

- **Requirements Phase**: Web search for latest versions, best practices, examples
- **Design Phase**: Technology analysis, architecture patterns, dependency research
- **All phases**: Structured documentation in knowledge base

### Error Handling & Documentation

- **No Assumptions**: Always use WebSearch for unknown errors
- **Comprehensive Documentation**: All errors documented with research and solutions
- **Knowledge Reuse**: Check existing error solutions before researching

### Knife Surgery Coding

- **Context Understanding**: Always read target files before changes
- **Minimal Impact**: Surgical changes preserving existing functionality
- **Self-Review & Mistake Detection**: Mandatory re-reading of all modified files to check for mistakes
- **Self-Correction Loop**: Automatic mistake detection and fixing before testing
- **Backward Compatibility**: Verify compatibility after changes

## Development Rules

1. **Consider steering**: Run `/kiro:steering` before major development (optional for new features)
2. **Follow 3-phase approval workflow**: Requirements → Design → Tasks → Implementation
3. **Approval required**: Each phase requires human review (interactive prompt or manual)
4. **No skipping phases**: Design requires approved requirements; Tasks require approved design
5. **Update task status**: Mark tasks as completed when working on them
6. **Keep steering current**: Run `/kiro:steering` after significant changes
7. **Check spec compliance**: Use `/kiro:spec-status` to verify alignment

## Steering Configuration

### Current Steering Files

Managed by `/kiro:steering` command. Updates here reflect command changes.

### Active Steering Files

- `product.md`: Always included - Product context and business objectives
- `tech.md`: Always included - Technology stack and architectural decisions
- `structure.md`: Always included - File organization and code patterns

### Custom Steering Files

<!-- Added by /kiro:steering-custom command -->
<!-- Format:
- `filename.md`: Mode - Pattern(s) - Description
  Mode: Always|Conditional|Manual
  Pattern: File patterns for Conditional mode
-->

### Inclusion Modes

- **Always**: Loaded in every interaction (default)
- **Conditional**: Loaded for specific file patterns (e.g., "\*.test.js")
- **Manual**: Reference with `@filename.md` syntax
