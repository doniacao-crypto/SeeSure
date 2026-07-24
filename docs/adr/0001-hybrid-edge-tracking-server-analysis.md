# ADR 0001 — Hybrid architecture: edge tracking, server analysis

- Status: Accepted
- Date: 2026-07-23
- Deciders: Huilin

## Context

EyeExam today is a single-user local PyQt6 desktop app. The stated end-state is a
website plus native iOS/Android/macOS/Windows apps, with all customer data on a hosting
server (see SCOPE.md).

The codebase splits cleanly along a boundary that the file layout hides:

- **~7,000 lines of domain logic carry zero PyQt6 references.** The UI (`main_app.py` +
  `widgets/`, ~2,100 lines) is the only Qt-coupled layer.
- The domain layer itself splits along a **latency line**:
  - `eye_tracker.py`, `gaze_estimator.py`, `filters.py` (~1,900 lines; MediaPipe +
    scikit-learn) consume 30–60fps video and must run next to the camera. A saccade
    completes in 30–80ms, so round-tripping frames to a server cannot measure saccade
    latency — regardless of bandwidth.
  - `metrics.py`, `smooth_pursuit_test.py`, `saccade_test.py`, `validation.py`,
    `normative_data.py`, `pdf_report.py`, `patient_manager.py`, `progress_tracking.py`
    (~3,700 lines) operate on already-extracted gaze samples and port to a server
    essentially unchanged.

The pipeline entry point is already clean: `EyeTracker.process_frame(frame) -> EyeData`.

## Decision

Adopt a **hybrid split**:

1. **Client — one implementation** (TypeScript + MediaPipe Tasks Web): camera,
   tracking, calibration, filtering, stimulus rendering. Ships as a website; the same
   bundle wraps to the four native OS targets via a web-wrapper (Capacitor/Tauri class).
   One tracking codebase, five delivery targets.
2. **Server — Python, reusing today's modules**: receives **gaze sample streams, not
   video**, and runs metrics, normative comparison, patient records, reports, and
   longitudinal tracking. ~3,700 lines carry over.
3. **The pilot runs on the existing PyQt6 desktop app, unchanged.** It is already built
   and clinician-supervised, matching the pilot setting. No rewrite happens before gaze
   accuracy is validated (see forthcoming accuracy ADR) — porting first would port a bug.

## Alternatives considered

- **Thin client + server-side video processing.** Rejected: frame round-trip latency
  makes saccade timing unmeasurable. This is a hard physical constraint, not a tuning
  problem.
- **Four independent native tracking implementations.** Rejected: four MediaPipe
  integrations of the most accuracy-sensitive code means four places for gaze accuracy
  to diverge. Maximises the exact risk the project is trying to close.
- **Rewrite the desktop app now for the new architecture.** Rejected: accuracy is not
  yet validated; rewriting first ports unproven code.

## Consequences

- `gaze_estimator.py` gets a **TypeScript twin**. The Ridge / polynomial calibration is
  portable, but the two implementations must stay numerically in agreement — a real
  maintenance cost and a real drift risk. This is the price of avoiding three more twins.
- Wire contract becomes **gaze samples**, not frames — cheap bandwidth, and it keeps PHI
  (raw video of a patient's face) off the network by default.
- Server modules are already Qt-free and mostly transport-agnostic; server port is
  low-risk relative to the client.
- Open option: if patient-facing **training** tolerates lower precision than clinician
  **diagnosis**, a lower-fidelity web client can serve patients while the desktop app
  remains the clinician instrument. This splits along the two-user model in SCOPE.md and
  is cheaper than full parity. Not decided here.
