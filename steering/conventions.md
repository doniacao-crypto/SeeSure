# Team Conventions

## Code Style

### Naming

| Type      | Convention      | Example       |
| --------- | --------------- | ------------- |
| Variables | camelCase       | `userName`    |
| Constants | SCREAMING_SNAKE | `MAX_RETRIES` |
| Functions | camelCase       | `getUserById` |
| Classes   | PascalCase      | `UserService` |

### TypeScript

- Use explicit types for function signatures
- Avoid `any` - use `unknown` if needed
- Use interfaces for objects, types for unions

## Git Workflow

### Branch Naming

```
feature/[ticket-id]-short-description
bugfix/[ticket-id]-short-description
hotfix/[ticket-id]-short-description
```

### Commit Messages (Conventional Commits)

```
feat(auth): add Google OAuth login
fix(api): handle null response
docs(readme): update installation
```

## Testing Standards

- Unit tests: `tests/unit/**/*.test.ts`
- Integration: `tests/integration/**/*.test.ts`
- E2E: `tests/e2e/**/*.spec.ts`
- Coverage minimum: 80%

## PR Process

1. Create feature branch
2. Make changes with conventional commits
3. Push and create PR
4. Wait for Claude review
5. Address feedback
6. Get human approval
7. Squash and merge

---

_Last updated: [Date]_
