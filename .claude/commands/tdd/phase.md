---
description: Run a specific SDLC phase for a feature
arguments:
  - name: phase
    description: 'Phase name: steering, init, requirements, gap, design, validate-design, tasks, impl, validate-impl, status'
    required: true
  - name: feature
    description: Feature name (required for most phases)
    required: false
  - name: tasks
    description: Task IDs for impl phase (e.g., "1.1,1.2,1.3")
    required: false
---

# Run Phase: $ARGUMENTS.phase

{{#if (eq $ARGUMENTS.phase "steering")}}

## Phase 0: Project Steering

Execute: `/kiro:steering`
This analyzes your project and creates context files in `.kiro/steering/`

{{else if (eq $ARGUMENTS.phase "init")}}

## Phase 1: Initialize Spec

Execute: `/kiro:spec-init $ARGUMENTS.feature`
This creates `.kiro/specs/<feature-slug>/` directory structure.

{{else if (eq $ARGUMENTS.phase "requirements")}}

## Phase 2: Requirements

Execute: `/kiro:spec-requirements $ARGUMENTS.feature`
This generates `requirements.md` with structured requirements.

{{else if (eq $ARGUMENTS.phase "gap")}}

## Phase 3: Gap Analysis

Execute: `/kiro:validate-gap $ARGUMENTS.feature`
This analyzes existing code vs new requirements.

{{else if (eq $ARGUMENTS.phase "design")}}

## Phase 4: Design

Execute: `/kiro:spec-design $ARGUMENTS.feature`
This generates `design.md` with technical architecture.

{{else if (eq $ARGUMENTS.phase "validate-design")}}

## Phase 5: Validate Design

Execute: `/kiro:validate-design $ARGUMENTS.feature`
This validates design against existing architecture.

{{else if (eq $ARGUMENTS.phase "tasks")}}

## Phase 6: Generate Tasks

Execute: `/kiro:spec-tasks $ARGUMENTS.feature`
This generates `tasks.md` with implementation tasks.

{{else if (eq $ARGUMENTS.phase "impl")}}

## Phase 7: Implementation

{{#if $ARGUMENTS.tasks}}
Execute: `/kiro:spec-impl $ARGUMENTS.feature $ARGUMENTS.tasks`
{{else}}
Execute: `/kiro:spec-impl $ARGUMENTS.feature` (all tasks)
{{/if}}
Use TDD: Write failing test → Implement → Refactor

{{else if (eq $ARGUMENTS.phase "validate-impl")}}

## Phase 8: Validate Implementation

Execute: `/kiro:validate-impl $ARGUMENTS.feature`
This validates implementation against design and requirements.

{{else if (eq $ARGUMENTS.phase "status")}}

## Check Status

Execute: `/kiro:spec-status $ARGUMENTS.feature`
This shows current progress of the feature.

{{else}}

## Unknown Phase

Phase "$ARGUMENTS.phase" is not recognized.
Available phases: steering, init, requirements, gap, design, validate-design, tasks, impl, validate-impl, status

{{/if}}

## After This Phase

Report what was generated and suggest the next phase in the workflow.
