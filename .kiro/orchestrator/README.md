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
