# Project Notes — EyeExam

## Quick Context

- **What:** Clinical-grade eye movement assessment using standard webcam
- **Status:** Active - All auto-claude specs complete ✅
- **Last worked on:** 2026-02-05
- **Telegram Group:** -1003865868299
- **GitHub:** https://github.com/ibetterai/EyeExam

## Decisions

- 2026-02-05: Using branch naming `x.yy.zzz` (version.category.issue)
- 2026-02-05: M4 Max coordinates with auto-claude, tracks via COORDINATION.md
- 2026-02-05: Security issues first, then build, performance, refactor, testing

## Completed Work (2026-02-05)

All 7 auto-claude specs implemented and merged:

| Issue | Title                                | Category    |
| ----- | ------------------------------------ | ----------- |
| #3    | ML model integrity verification      | Security    |
| #5    | CI security audit enforcement        | Security    |
| #4    | Pin dependency versions              | Build       |
| #6    | MediaPipe VIDEO mode (20-40% faster) | Performance |
| #7    | Split main_app.py (880→462 lines)    | Refactor    |
| #9    | Refactor MainWindow God Object       | Refactor    |
| #8    | Add unit tests (40→91 tests)         | Testing     |

## Current State

- All foundational specs complete
- Test coverage: 91 tests (127% increase)
- Code split into modular widgets
- Security hardened (hash verification, CI audit)
- Performance optimized (VIDEO mode)

## Roadmap (4 phases)

1. **Core Clinical Testing** — saccade tests, fixation tests, <2° accuracy
2. **Clinical Workflow** — PDF reports, patient profiles
3. **Longitudinal Tracking** — progress over time, research mode
4. **Enterprise** — multi-clinic, EHR integration

## Next Steps

- Review auto-claude ideation backlog for next priorities
- Consider Issue #2 (test window dots clipped)
- Begin Phase 1 features from roadmap
