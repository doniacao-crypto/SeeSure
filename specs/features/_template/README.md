# Feature Specification Template

Copy this folder when starting a new feature with `/kiro:spec-init`.

## Files Generated

1. **init.md** - Feature overview and scope
2. **requirements.md** - EARS format requirements with test scenarios
3. **design.md** - Technical design and architecture
4. **tasks.md** - Implementation tasks with dependencies
5. **test-spec.md** - Detailed test specifications

## EARS Format Examples

**Ubiquitous**: THE SYSTEM SHALL [action]
**Event-Driven**: WHEN [trigger] THE SYSTEM SHALL [action]
**State-Driven**: WHILE [state] THE SYSTEM SHALL [action]
**Optional**: WHERE [condition] THE SYSTEM SHALL [action]

## Workflow

```
/kiro:spec-init → requirements.md → design.md → tasks.md → implementation
```
