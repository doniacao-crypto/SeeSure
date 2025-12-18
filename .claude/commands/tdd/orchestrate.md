---
description: Run the complete SDLC workflow with TDD for a feature
arguments:
  - name: feature
    description: Feature description (will be converted to slug for directory name)
    required: true
  - name: mode
    description: 'interactive (default), auto, or resume'
    required: false
---

# SDLC Orchestrator: $ARGUMENTS.feature

## Mode: {{ default $ARGUMENTS.mode "interactive" }}

You are orchestrating the complete spec-driven development workflow for:
**$ARGUMENTS.feature**

{{#if (eq $ARGUMENTS.mode "auto")}}
⚠️ AUTO MODE: Running all phases without stopping for approval.
Only errors will pause the workflow.
{{else if (eq $ARGUMENTS.mode "resume")}}
🔄 RESUME MODE: Continuing from last checkpoint.
Read .kiro/specs/<feature>/.workflow-state.json to determine current state.
{{else}}
🔄 INTERACTIVE MODE: Will pause after each phase for your approval.
{{/if}}

## Execution Instructions

### 1. Invoke the SDLC Orchestrator Agent

Use the `sdlc-orchestrator` agent to manage the complete workflow.

### 2. Follow This Sequence

```
Phase 0: /kiro:steering (if not done)
Phase 1: /kiro:spec-init "$ARGUMENTS.feature"
Phase 2: /kiro:spec-requirements <feature-slug>
Phase 3: /kiro:validate-gap <feature-slug> (if existing codebase)
Phase 4: /kiro:spec-design <feature-slug>
Phase 5: /kiro:validate-design <feature-slug>
Phase 6: /kiro:spec-tasks <feature-slug>
Phase 7: TDD Implementation Loop (use tdd-implementer agent)
Phase 8: /kiro:validate-impl <feature-slug>
```

### 3. TDD Implementation (Phase 7)

For each task:

1. **Write failing test first** (RED)
2. **Implement minimum code** (GREEN)
3. **Refactor while green** (REFACTOR)
4. **Validate against design**
5. **Move to next task**

### 4. State Tracking

Save progress to `.kiro/specs/<feature>/.workflow-state.json` after each phase.

### 5. Completion

Generate final report with:

- All spec file locations
- Test results summary
- Coverage report
- Files changed

## BEGIN ORCHESTRATION NOW

Start by determining the feature slug from "$ARGUMENTS.feature" and checking project steering status.
