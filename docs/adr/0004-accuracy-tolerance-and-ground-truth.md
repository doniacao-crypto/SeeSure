# ADR 0004 — Accuracy tolerance & ground-truth strategy

- Status: Accepted (target provisional, pending Clinical Lead confirmation)
- Date: 2026-07-23
- Deciders: Huilin (accuracy target to be confirmed by Clinical Lead)

## Context

"Accuracy fixed" is the Definition of Done (SCOPE.md), but no numeric target existed and
no external reference to measure against. `src/validation.py` reports mean/worst accuracy
in degrees — but only against the app's **own on-screen targets**. That is
**self-consistency, not ground truth**: a biased calibration inherits the same bias in
validation, so the app can report good accuracy while being systematically wrong.

Available reference: the **Clinical Lead owns a separate (commercial) eye-tracking device,
currently broken.** Repairing it is the cheapest path to a gold-standard reference.

For orientation: research-grade webcam gaze ≈ 2–4° visual angle; commercial/lab trackers
≈ 0.5–1°. The existing PDF report already uses a ≤2° "normal limits" line.

## Decision

**Accuracy target (provisional):**
- **≤ 1.5° mean gaze error at ~60 cm viewing distance**
- **≤ 2.5° worst-point error**
- Clinical Lead to confirm whether the diagnostic protocols (saccade / fixation / pursuit)
  need tighter or looser bounds — they may differ per protocol. Until confirmed, this is
  the written commitment the accuracy work targets.

**Ground-truth strategy (tiered, cheapest → strongest):**
1. **Now — fixed-head grid test.** Chin rest / forehead braced, dots at known screen
   angles. Cheap, catches gross error. Still shares calibration bias; a floor, not proof.
2. **Before the pilot — repair the Clinical Lead's device** and run subjects on EyeExam
   and the reference tracker **simultaneously**. This is the defensible, bias-catching
   measurement and the gate for any accuracy claim to a clinician or regulator.

## Alternatives considered

- **Keep using self-validation only.** Rejected: cannot detect systematic bias; makes the
  Definition of Done unfalsifiable.
- **Buy a new commercial tracker.** Deferred: the Clinical Lead already owns one; repair is
  cheaper than purchase.
- **No numeric target until the pilot.** Rejected: leaves accuracy work aiming at nothing;
  a provisional written number is better than none.

## Consequences

- A-3 (target) is satisfied provisionally; A-4 (ground truth) reduces to "repair the
  device"; A-5 (run validation) can start immediately with the grid test.
- Accuracy claims stay marked provisional until the simultaneous-tracker comparison runs.
- The grid test is a small, buildable harness; worth adding to the desktop app.
