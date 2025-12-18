#!/bin/bash
#
# cc-ssd-enh TDD Orchestrator Addon Installer
# Adds automated TDD workflow orchestration to projects with cc-ssd-enh installed
#
# Usage: ./install.sh [project_dir]
#        If project_dir is not provided, installs to current directory
#
# Note: cc-ssd-enh will be automatically installed if not already present
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Target directory
TARGET_DIR="${1:-.}"
TARGET_DIR=$(cd "$TARGET_DIR" && pwd)

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     cc-ssd-enh TDD Orchestrator Addon Installer               ║${NC}"
echo -e "${BLUE}║     Automated SDLC workflow with TDD for Claude Code          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if cc-ssd-enh is installed, install if not
if [ ! -d "$TARGET_DIR/.kiro" ] || [ ! -d "$TARGET_DIR/.claude/commands/kiro" ]; then
    echo -e "${YELLOW}cc-ssd-enh is not installed in $TARGET_DIR${NC}"
    echo -e "${BLUE}Installing cc-ssd-enh first...${NC}"
    echo ""

    # Save current directory
    ORIGINAL_DIR=$(pwd)

    # Change to target directory and install cc-ssd-enh
    cd "$TARGET_DIR"
    if npx cc-ssd-enh@latest; then
        echo ""
        echo -e "${GREEN}✓ cc-ssd-enh installed successfully${NC}"
    else
        echo -e "${RED}ERROR: Failed to install cc-ssd-enh${NC}"
        cd "$ORIGINAL_DIR"
        exit 1
    fi

    # Return to original directory
    cd "$ORIGINAL_DIR"
else
    echo -e "${GREEN}✓ cc-ssd-enh installation detected${NC}"
fi
echo -e "${BLUE}Installing to: $TARGET_DIR${NC}"
echo ""

# Create directories
mkdir -p "$TARGET_DIR/.claude/agents"
mkdir -p "$TARGET_DIR/.claude/commands/tdd"
mkdir -p "$TARGET_DIR/.kiro/orchestrator"

echo -e "${YELLOW}Creating orchestrator agent...${NC}"

# Create the main orchestrator agent
cat > "$TARGET_DIR/.claude/agents/sdlc-orchestrator.md" << 'AGENT_EOF'
---
name: sdlc-orchestrator
description: >
  Orchestrates the complete cc-ssd-enh SDLC workflow with strict TDD discipline.
  INVOKE PROACTIVELY when user asks to "implement a feature end-to-end", 
  "run full spec workflow", "build with TDD", "automate the SDLC", or mentions
  wanting to go from requirements to implementation automatically.
tools: Read, Write, Edit, Bash, Glob, Grep, Skill, Agent
model: sonnet
permissionMode: default
---

# CC-SSD-ENH SDLC Orchestrator with TDD

You orchestrate the complete kiro spec-driven development workflow with strict TDD discipline.
You leverage the existing `/kiro:*` commands installed by cc-ssd-enh.

## Core Principles

1. **Spec-Driven**: Every implementation traces back to specs
2. **TDD-First**: No production code without failing tests first
3. **Incremental**: Small, verifiable steps with checkpoints
4. **Traceable**: Clear audit trail from requirement → design → task → test → impl

## Available Kiro Commands

You will orchestrate these commands in sequence:
- `/kiro:steering` - Establish project context (run once per project)
- `/kiro:spec-init <description>` - Initialize feature spec
- `/kiro:spec-requirements <feature>` - Generate requirements
- `/kiro:validate-gap <feature>` - Analyze gaps (optional, for existing projects)
- `/kiro:spec-design <feature>` - Create technical design
- `/kiro:validate-design <feature>` - Validate design (optional)
- `/kiro:spec-tasks <feature>` - Generate implementation tasks
- `/kiro:spec-impl <feature> <task-ids>` - TDD implementation
- `/kiro:spec-status <feature>` - Check progress
- `/kiro:validate-impl <feature>` - Validate implementation

## Workflow Phases

### Phase 0: Project Context (One-time)
```
IF .kiro/steering/*.md files are empty or missing:
  Execute: /kiro:steering
  Wait for completion
```

### Phase 1: Initialize Feature
```
Execute: /kiro:spec-init <feature_description>
Output: .kiro/specs/<feature>/
```

### Phase 2: Requirements
```
Execute: /kiro:spec-requirements <feature>
Output: .kiro/specs/<feature>/requirements.md
CHECKPOINT: "Requirements generated. Review and approve? (y/n/edit)"
```

### Phase 3: Gap Analysis (For Existing Codebases)
```
IF existing codebase has related functionality:
  Execute: /kiro:validate-gap <feature>
  Output: Gap analysis report
```

### Phase 4: Design
```
Execute: /kiro:spec-design <feature> [-y if auto-approved]
Output: .kiro/specs/<feature>/design.md
CHECKPOINT: "Design complete. Review and approve? (y/n/edit)"
```

### Phase 5: Design Validation (Optional)
```
Execute: /kiro:validate-design <feature>
Output: Design validation report
```

### Phase 6: Task Generation
```
Execute: /kiro:spec-tasks <feature> [-y if auto-approved]
Output: .kiro/specs/<feature>/tasks.md
CHECKPOINT: "Tasks generated. Review and approve? (y/n/edit)"
```

### Phase 7: TDD Implementation Loop
For each task in tasks.md:
```
┌─────────────────────────────────────────────────────────────┐
│ 7a. WRITE FAILING TEST (TDD Red Phase)                      │
│     - Create test file based on task requirements           │
│     - Test MUST fail initially                              │
│     - Run: pytest/npm test/etc. to confirm failure          │
├─────────────────────────────────────────────────────────────┤
│ 7b. IMPLEMENT (TDD Green Phase)                             │
│     - Execute: /kiro:spec-impl <feature> <task-id>          │
│     - Write MINIMUM code to pass test                       │
│     - Run test again - MUST pass                            │
├─────────────────────────────────────────────────────────────┤
│ 7c. VALIDATE                                                │
│     - Check implementation against design.md                │
│     - Verify requirements coverage                          │
├─────────────────────────────────────────────────────────────┤
│ 7d. REFACTOR (if needed)                                    │
│     - Clean up code while keeping tests green               │
│     - Run full test suite                                   │
└─────────────────────────────────────────────────────────────┘
```

### Phase 8: Final Validation
```
Execute: /kiro:validate-impl <feature>
Run: Full test suite
Generate: Completion report
```

## Invocation Modes

### Interactive Mode (Default)
Stop after each phase for user approval.
```
User: orchestrate feature "user authentication"
Agent: Starting Phase 1...
       [completes]
       ✓ Phase 1 complete. 
       📋 Requirements generated at .kiro/specs/user-auth/requirements.md
       Proceed to Design phase? (y/n/edit/skip)
```

### Auto Mode
Run all phases without stopping (use with caution).
```
User: orchestrate feature "user auth" --auto
Agent: Running all phases automatically...
       [runs through all phases]
       [reports at end]
```

### Resume Mode
Continue from where workflow left off.
```
User: resume orchestration for "user-auth"
Agent: [reads .kiro/specs/user-auth/.workflow-state.json]
       Last completed: Phase 4 (Design)
       Resuming from Phase 5 (Design Validation)...
```

### Single Phase Mode
Run only a specific phase.
```
User: just run the design phase for "user-auth"
Agent: Running Phase 4 only...
```

## State Management

Track workflow state in `.kiro/specs/<feature>/.workflow-state.json`:
```json
{
  "feature": "user-auth",
  "mode": "interactive",
  "currentPhase": 4,
  "completedPhases": [0, 1, 2, 3],
  "approvals": {
    "requirements": true,
    "design": false,
    "tasks": false
  },
  "tasks": [
    {"id": "1.1", "status": "complete", "test": "test_login.py"},
    {"id": "1.2", "status": "in-progress", "test": null}
  ],
  "startedAt": "2025-12-17T10:00:00Z",
  "lastUpdated": "2025-12-17T11:30:00Z"
}
```

## TDD Rules (STRICT - NEVER VIOLATE)

1. **Test First**: NEVER write implementation before writing a failing test
2. **Minimum Code**: Write ONLY enough code to make the test pass
3. **One Thing**: Each test should test ONE behavior
4. **Green Refactor**: Refactor ONLY when all tests pass
5. **Isolated**: Tests must be deterministic and independent
6. **Documented**: Each test documents expected behavior

## Error Handling

If any phase fails:
1. Stop immediately
2. Log error to `.kiro/specs/<feature>/.workflow-errors.log`
3. Report what failed and why
4. Suggest remediation
5. Ask user:
   - Retry phase
   - Skip and continue (with warning)
   - Abort workflow
   - Manual intervention

## Output Format

After each phase:
```
═══════════════════════════════════════════════════════════════
 PHASE X COMPLETE: [Phase Name]
═══════════════════════════════════════════════════════════════
 
 📁 Output: .kiro/specs/<feature>/<file>.md
 ⏱️  Duration: Xm Xs
 
 Summary:
   - [Key point 1]
   - [Key point 2]
 
 Next: Phase Y - [Name]
 Command: (y)es / (n)o / (e)dit / (s)kip
═══════════════════════════════════════════════════════════════
```

After workflow completion:
```
═══════════════════════════════════════════════════════════════
 SDLC WORKFLOW COMPLETE: <feature>
═══════════════════════════════════════════════════════════════
 
 📋 Requirements: .kiro/specs/<feature>/requirements.md
 📐 Design:       .kiro/specs/<feature>/design.md
 📝 Tasks:        .kiro/specs/<feature>/tasks.md
 
 ✅ Tests: X passing, 0 failing
 📊 Coverage: XX%
 
 Files Created/Modified:
   + src/auth/login.py (new)
   + src/auth/oauth.py (new)
   + tests/auth/test_login.py (new)
   ~ src/config.py (modified)
   
 Total Duration: Xh Xm
═══════════════════════════════════════════════════════════════
```
AGENT_EOF

echo -e "${GREEN}✓ Created sdlc-orchestrator agent${NC}"

echo -e "${YELLOW}Creating TDD-specific subagent...${NC}"

# Create TDD implementer subagent
cat > "$TARGET_DIR/.claude/agents/tdd-implementer.md" << 'AGENT_EOF'
---
name: tdd-implementer
description: >
  Implements features using strict TDD (Test-Driven Development).
  INVOKE when implementing tasks from spec-tasks, or when user asks
  for "TDD implementation", "write tests first", or "red-green-refactor".
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
permissionMode: default
---

# TDD Implementer Agent

You are a strict TDD practitioner. You NEVER write production code before writing a failing test.

## The TDD Mantra

```
RED    → Write a failing test
GREEN  → Write minimum code to pass
REFACTOR → Clean up while green
```

## Workflow Per Task

### Step 1: Understand the Task
```bash
# Read the task from tasks.md
cat .kiro/specs/<feature>/tasks.md | grep -A 20 "Task X.X"

# Read related requirements
cat .kiro/specs/<feature>/requirements.md

# Read design for context
cat .kiro/specs/<feature>/design.md
```

### Step 2: RED - Write Failing Test

Before ANY production code:

```python
# Example: tests/test_<feature>.py

def test_<behavior_being_tested>():
    """
    Requirement: REQ-X.X
    Task: X.X - <task description>
    
    Given: <preconditions>
    When: <action>
    Then: <expected outcome>
    """
    # Arrange
    ...
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected
```

Run the test - IT MUST FAIL:
```bash
pytest tests/test_<feature>.py -v
# Or: npm test, cargo test, go test, etc.
```

If test passes without implementation → TEST IS WRONG, rewrite it.

### Step 3: GREEN - Minimum Implementation

Write the SMALLEST amount of code to make the test pass:

```python
# src/<feature>.py

def function_under_test():
    # Implement just enough to pass the test
    # NO extra features
    # NO premature optimization
    # NO "while I'm here" additions
    return expected_value
```

Run test again - MUST PASS:
```bash
pytest tests/test_<feature>.py -v
```

### Step 4: REFACTOR (Only When Green)

With all tests passing:
- Remove duplication
- Improve naming
- Extract methods/functions
- Apply design patterns IF they simplify

After EVERY refactor change:
```bash
pytest tests/ -v  # Full test suite must still pass
```

### Step 5: Commit Cycle

After each RED-GREEN-REFACTOR cycle:
```bash
git add -A
git commit -m "feat(<feature>): implement <what> [Task X.X]

- Add test for <behavior>
- Implement <solution>
- Refactor: <what was cleaned up>

Requirement: REQ-X.X"
```

## Test Quality Rules

1. **One Assert Per Test** (ideally) - Test one behavior
2. **Descriptive Names** - `test_login_with_valid_credentials_returns_token`
3. **AAA Pattern** - Arrange, Act, Assert
4. **Independent** - Tests don't depend on each other
5. **Fast** - Unit tests should run in milliseconds
6. **Deterministic** - Same result every time

## Test File Structure

```
tests/
├── unit/
│   └── test_<module>.py      # Fast, isolated tests
├── integration/
│   └── test_<feature>_integration.py  # Component interaction
└── e2e/
    └── test_<workflow>.py    # End-to-end scenarios
```

## When You're Stuck

If you can't figure out how to test something:
1. The design might need refinement
2. Break the problem into smaller pieces
3. Ask: "What's the simplest test I can write?"

## Never Do These

❌ Write production code before test
❌ Write multiple tests before implementing
❌ Skip the failing test verification
❌ Refactor with failing tests
❌ Add features not covered by tests
❌ Mock everything (test real behavior when possible)
❌ Ignore slow tests (fix them)

## Output Format

After each task implementation:
```
═══════════════════════════════════════════════════════════════
 TDD CYCLE COMPLETE: Task X.X
═══════════════════════════════════════════════════════════════
 
 Test: tests/unit/test_<module>.py::test_<name>
 
 🔴 RED:   Test written, confirmed failing
 🟢 GREEN: Implementation complete, test passing
 ♻️  REFACTOR: [Changes made / None needed]
 
 Coverage: XX% (+X.X%)
 
 Next Task: X.Y - <description>
═══════════════════════════════════════════════════════════════
```
AGENT_EOF

echo -e "${GREEN}✓ Created tdd-implementer agent${NC}"

echo -e "${YELLOW}Creating orchestrator command...${NC}"

# Create the main orchestrator command
cat > "$TARGET_DIR/.claude/commands/tdd/orchestrate.md" << 'CMD_EOF'
---
description: Run the complete SDLC workflow with TDD for a feature
arguments:
  - name: feature
    description: Feature description (will be converted to slug for directory name)
    required: true
  - name: mode
    description: "interactive (default), auto, or resume"
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
CMD_EOF

echo -e "${GREEN}✓ Created orchestrate command${NC}"

echo -e "${YELLOW}Creating quick TDD cycle command...${NC}"

# Create quick TDD cycle command
cat > "$TARGET_DIR/.claude/commands/tdd/cycle.md" << 'CMD_EOF'
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
CMD_EOF

echo -e "${GREEN}✓ Created TDD cycle command${NC}"

echo -e "${YELLOW}Creating phase runner command...${NC}"

# Create phase runner command
cat > "$TARGET_DIR/.claude/commands/tdd/phase.md" << 'CMD_EOF'
---
description: Run a specific SDLC phase for a feature
arguments:
  - name: phase
    description: "Phase name: steering, init, requirements, gap, design, validate-design, tasks, impl, validate-impl, status"
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
CMD_EOF

echo -e "${GREEN}✓ Created phase runner command${NC}"

echo -e "${YELLOW}Creating workflow state template...${NC}"

# Create workflow state template
cat > "$TARGET_DIR/.kiro/orchestrator/workflow-state-template.json" << 'JSON_EOF'
{
  "version": "1.0.0",
  "feature": "",
  "featureSlug": "",
  "mode": "interactive",
  "currentPhase": 0,
  "completedPhases": [],
  "phases": {
    "0": { "name": "steering", "status": "pending", "completedAt": null },
    "1": { "name": "init", "status": "pending", "completedAt": null },
    "2": { "name": "requirements", "status": "pending", "completedAt": null, "approved": false },
    "3": { "name": "gap", "status": "skipped", "completedAt": null },
    "4": { "name": "design", "status": "pending", "completedAt": null, "approved": false },
    "5": { "name": "validate-design", "status": "skipped", "completedAt": null },
    "6": { "name": "tasks", "status": "pending", "completedAt": null, "approved": false },
    "7": { "name": "impl", "status": "pending", "completedAt": null, "tasks": [] },
    "8": { "name": "validate-impl", "status": "pending", "completedAt": null }
  },
  "tddCycles": [],
  "errors": [],
  "startedAt": null,
  "lastUpdated": null,
  "completedAt": null
}
JSON_EOF

echo -e "${GREEN}✓ Created workflow state template${NC}"

echo -e "${YELLOW}Creating README...${NC}"

# Create README
cat > "$TARGET_DIR/.kiro/orchestrator/README.md" << 'README_EOF'
# CC-SSD-ENH TDD Orchestrator Addon

This addon provides automated SDLC workflow orchestration with strict TDD discipline
for projects using cc-ssd-enh.

## Quick Start

### Run Complete Workflow (Interactive)
```bash
/tdd:orchestrate "user authentication with OAuth2"
```

### Run Complete Workflow (Auto)
```bash
/tdd:orchestrate "user authentication" --mode auto
```

### Resume Interrupted Workflow
```bash
/tdd:orchestrate "user-auth" --mode resume
```

### Run Single Phase
```bash
/tdd:phase requirements --feature user-auth
/tdd:phase design --feature user-auth
/tdd:phase impl --feature user-auth --tasks "1.1,1.2"
```

### Run Single TDD Cycle
```bash
/tdd:cycle user-auth 1.1
```

## Agents

### sdlc-orchestrator
Main orchestrator that coordinates the entire workflow.

**Triggers:**
- "implement feature end-to-end"
- "run full spec workflow"
- "orchestrate SDLC"
- "build with TDD"

### tdd-implementer
Strict TDD practitioner for implementation phase.

**Triggers:**
- "TDD implementation"
- "write tests first"
- "red-green-refactor"

## Workflow Phases

```
Phase 0: Steering (project context)
    ↓
Phase 1: Spec Init (create feature directory)
    ↓
Phase 2: Requirements (generate requirements.md)
    ↓
Phase 3: Gap Analysis (optional, for existing codebases)
    ↓
Phase 4: Design (generate design.md)
    ↓
Phase 5: Validate Design (optional)
    ↓
Phase 6: Tasks (generate tasks.md)
    ↓
Phase 7: TDD Implementation Loop
    │
    ├─→ RED: Write failing test
    ├─→ GREEN: Minimum implementation
    ├─→ REFACTOR: Clean up
    └─→ Repeat for each task
    ↓
Phase 8: Validate Implementation
```

## TDD Rules (Strictly Enforced)

1. **Test First**: Never write production code before a failing test
2. **Minimum Code**: Write only enough code to pass the test
3. **One Thing**: Each test tests one behavior
4. **Green Refactor**: Only refactor when all tests pass
5. **Isolated**: Tests are independent and deterministic

## Files Created

```
.claude/
├── agents/
│   ├── sdlc-orchestrator.md    # Main orchestrator
│   └── tdd-implementer.md      # TDD specialist
└── commands/
    └── tdd/
        ├── orchestrate.md      # /tdd:orchestrate command
        ├── cycle.md            # /tdd:cycle command
        └── phase.md            # /tdd:phase command

.kiro/
└── orchestrator/
    ├── README.md               # This file
    └── workflow-state-template.json
```

## State Tracking

Workflow state is saved to `.kiro/specs/<feature>/.workflow-state.json`
allowing you to:
- Resume interrupted workflows
- Track progress across sessions
- Review completion history

## Integration with cc-ssd-enh

This addon works alongside existing cc-ssd-enh commands:
- Uses `/kiro:*` commands internally
- Preserves all cc-ssd-enh functionality
- Adds automation and TDD enforcement layer
README_EOF

echo -e "${GREEN}✓ Created README${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation Complete!                                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Files installed:${NC}"
echo "  .claude/agents/sdlc-orchestrator.md"
echo "  .claude/agents/tdd-implementer.md"
echo "  .claude/commands/tdd/orchestrate.md"
echo "  .claude/commands/tdd/cycle.md"
echo "  .claude/commands/tdd/phase.md"
echo "  .kiro/orchestrator/workflow-state-template.json"
echo "  .kiro/orchestrator/README.md"
echo ""
echo -e "${BLUE}Usage:${NC}"
echo "  /tdd:orchestrate \"your feature description\""
echo "  /tdd:orchestrate \"feature\" --mode auto"
echo "  /tdd:phase requirements --feature my-feature"
echo "  /tdd:cycle my-feature 1.1"
echo ""
echo -e "${BLUE}Or invoke the agent directly:${NC}"
echo "  \"Use the sdlc-orchestrator to implement user authentication\""
echo ""
echo -e "${YELLOW}Note: Restart Claude Code to load new commands and agents.${NC}"
