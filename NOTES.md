# Project Notes — EyeExam

## Quick Context

- **What:** Clinical eye movement assessment application (PyQt6 + MediaPipe)
- **Status:** Features built; **now foundation-first** — the desktop app is a validation
  vehicle for a pilot, not the shipping product. See SCOPE.md + docs/adr/.
- **Last worked on:** 2026-07-23 (setup + grill session)

---

## ▶ NEXT SESSION START HERE (2026-07-23)

**Read first:** `docs/BACKLOG.md` (the ordered work list) → `CLAUDE.md` Documentation Map.

**What happened this session:** ran `/setup` Phase 0 + `/grill-with-docs`. Reframed the
project and recorded 5 ADRs. Key reframes:
- **Product ≠ current app.** End-state = website + iOS/Android/macOS/Windows, all data
  server-hosted. Current PyQt6 app = pilot instrument only. Architecture = **hybrid**
  (ADR 0001): one TS+MediaPipe web tracking client wrapped to all targets; Python server
  reuses today's analysis modules (metrics/protocols/reports/norms) over gaze-sample
  streams (NOT video — saccade latency forbids frame round-trips).
- **Two users:** clinician (prescribes/diagnoses) + patient (trains). Clinician = an
  optometrist, clinic owner, product originator, now the **Clinical Lead / sign-off
  authority** (ADR 0003).
- **Nothing clinical is validated yet.** Norms in `normative_data.py` have citations that
  were generated with the numbers — none verified (ADR 0002). Interpretation strings are
  dev-authored. All gated to illustrative-only until the sign-off register is completed.
- **Accuracy** target provisional ≤1.5°/≤2.5° at 60cm (ADR 0004). Clinical Lead owns a
  commercial reference tracker — **broken**; repairing it (A-4a) is the top P0 unlock.
- **PHI** must satisfy HIPAA+GDPR+PIPL superset when hosted (ADR 0005). Pilot stays local.

**Critical path:** repair her tracker (A-4a) → validate accuracy (A-5) → Clinical Lead
signs the register (A-6) → run pilot (P2) → build platform (P3).

**Owed but not done:** A-2 (add "not clinically validated" caveat in UI/PDF — quick),
A-1 (literature-verify the norms — research task). Both queued in BACKLOG P1.

**Bugs found:** A-19 PHI delete uses `.json` not `.phi` (may leave PHI on disk);
A-7 two conflicting pursuit-gain thresholds; A-8 missing BCEA norms for child/adolescent.

**Note:** current git branch is `fix/gaze-calibration-sample-usage`; these docs are
setup/planning, not part of that fix. Nothing committed — commit at your discretion.

## Decisions

- Branch naming: `x.yy.zzz` (version.category.issue) — e.g., `0.10.043`
- Squash-merge all PRs with conventional commits
- 1 pre-existing test failure allowed: `test_smooth_pursuit_test.py::TestTestConfig::test_default_config`
- Stack widget indices: 0=home, 1=calibration, 2=test, 3=saccade, 4=validation, 5=results, 6=history

## Current State

### Completed Features (30 PRs merged)

**Auto-Claude Specs (7):**

- ML model SHA256 integrity verification
- CI security audit hardening
- Pin Python dependencies
- MediaPipe VIDEO mode
- Split main_app.py into widgets/
- Refactor MainWindow helpers
- Unit tests expansion 40→91

**Ideation Backlog (14):**

- CSV export, Phase lag, Microsaccade detection
- Speed slider, Fixation test, Constants extraction
- README docs, Tooltips, Kalman filter
- Session history, Visual icons, Camera loading
- Enhanced results display

**Roadmap Phase 1 — Core Clinical:**

- Saccade Testing Suite (`saccade_test.py`, `saccade_widget.py`)
- Trajectory Visualization (`visualization.py`)
- Gaze Accuracy Validation (`validation.py`, `validation_widget.py`)

**Roadmap Phase 2 — Clinical Workflow:**

- PDF Clinical Reports (`pdf_report.py`)
- Patient Profile Management (`patient_manager.py`)
- Gaze Heatmap Visualization
- Normative Data Comparison (`normative_data.py`)
- Pass/Fail Screening Indicators

**Roadmap Phase 3 — Research:**

- Longitudinal Progress Tracking (`progress_tracking.py`)
- Multi-Session Comparison (`session_comparison.py`)
- Research Mode (`research_mode.py`)

**Roadmap Phase 4 — Enterprise:**

- Practice Branding
- Multi-Clinician Support
- EHR Integration (HL7 FHIR)
- Tablet/Touch Mode
- Multi-Language (EN/ES/ZH/FR/DE)
- All in `enterprise.py`

## Architecture

### Source Modules

```
src/
├── main_app.py          # Main window
├── widgets/             # UI widgets (home, calibration, test, saccade, validation)
├── eye_tracker.py       # Face mesh tracking
├── gaze_estimator.py    # Gaze estimation
├── filters.py           # Kalman filter
├── metrics.py           # Clinical metrics
├── smooth_pursuit_test.py
├── saccade_test.py      # Pro/anti-saccade protocols
├── validation.py        # Accuracy validation
├── visualization.py     # Trajectories + heatmaps
├── pdf_report.py        # Clinical PDF reports
├── patient_manager.py   # Patient CRUD
├── session_history.py   # Session management
├── normative_data.py    # Age-matched norms
├── progress_tracking.py # Longitudinal tracking
├── session_comparison.py
├── research_mode.py     # Extended protocols
└── enterprise.py        # Branding, clinicians, EHR, i18n
```

## Next Steps

- User may want tags/branches recreated for version history
- Integration testing for new modules
- UI polish for enterprise features
- Documentation updates

## Links

- GitHub: https://github.com/ibetterai/EyeExam
- Telegram: -1003865868299
