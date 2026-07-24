# CONTEXT — EyeExam domain language

The vocabulary of this project. Terms here mean exactly what this file says they mean,
in code, in specs, and in conversation. If a term drifts, fix it here first.

_Seeded 2026-07-21 (via `/setup` Phase 0). Expand as decisions sharpen — see `/grill-with-docs`._

## Actors

**Clinician** — optometrist or neuro-optometrist. Administers assessments, interprets
results, prescribes training. Owns interpretation; the software owns measurement.

**Patient** — also "client". Receives a prescription from a clinician and performs
prescribed training sessions, potentially unsupervised at home.

## Eye movement domain

**Smooth pursuit** — continuous eye movement tracking a slowly moving target.

**Pursuit gain** — ratio of eye velocity to target velocity. ~1.0 is healthy tracking;
lower means the eye lags and must catch up with corrective saccades.

**Phase lag** — temporal delay between target motion and eye motion during pursuit.

**Saccade** — rapid ballistic eye movement between fixation points.

**Pro-saccade** — look *toward* the stimulus. **Anti-saccade** — look *away* from it;
requires inhibitory control, so error rate is clinically informative.

**Fixation** — holding gaze steady on a stationary target.

**BCEA** (Bivariate Contour Ellipse Area) — area containing a given proportion of gaze
points during fixation. Smaller = more stable fixation.

**Microsaccade** — small involuntary movement during nominal fixation.

**Visual angle** — angular measure of gaze error, in degrees. The unit that matters
clinically; pixels are an implementation detail and must not appear in clinical output.

## System concepts

**Calibration** — mapping raw gaze estimates to screen coordinates, currently via a
9-point procedure. Calibration quality bounds every downstream metric.

**Validation** — measuring residual gaze error *after* calibration against known targets.
Distinct from calibration: calibration fits, validation checks.

**Session** — one sitting: calibration plus one or more tests, producing metrics and
optionally a report.

**Normative comparison** — placing a patient's metrics against age-matched reference
ranges. Only as trustworthy as the reference data (see DEPENDENCIES.md).

**Assessment vs training** — the same protocols serve two purposes: assessment measures
and diagnoses; training exercises and rehabilitates. The distinction drives UI, framing,
and what counts as a good outcome.

**PHI** — Protected Health Information. Patient-identifying data. Currently encrypted
at rest with Fernet keyed from the OS keychain; obligations change once data is hosted.
