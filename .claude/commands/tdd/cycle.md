---
description: Run a single TDD cycle (red-green-refactor) for a specific task
arguments:
  - name: feature
    description: Feature name (directory under .kiro/specs/)
    required: true
  - name: task
    description: Task ID (e.g., "1.1", "2.3")
    required: true
---

# TDD Cycle: $ARGUMENTS.feature / Task $ARGUMENTS.task

Execute a single TDD cycle for task **$ARGUMENTS.task** of feature **$ARGUMENTS.feature**.

## Pre-flight Checks

1. Read task details from `.kiro/specs/$ARGUMENTS.feature/tasks.md`
2. Read related requirements from `.kiro/specs/$ARGUMENTS.feature/requirements.md`
3. Read design context from `.kiro/specs/$ARGUMENTS.feature/design.md`

## TDD Cycle

### 🔴 RED Phase

1. Write a failing test for this task
2. Run the test to confirm it fails
3. If test passes without code → rewrite the test

### 🟢 GREEN Phase

1. Write the MINIMUM code to make the test pass
2. Run the test to confirm it passes
3. No extra features, no optimization

### ♻️ REFACTOR Phase

1. Clean up the code (if needed)
2. Run ALL tests to ensure nothing broke
3. Commit the changes

## Output

Update `.kiro/specs/$ARGUMENTS.feature/tasks.md` to mark task $ARGUMENTS.task as complete.

Report:

- Test file created/modified
- Implementation file created/modified
- Test results
- Coverage delta
