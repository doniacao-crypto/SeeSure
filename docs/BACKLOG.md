# EyeExam — Tracking Backlog

Single source of truth for open work surfaced during setup + grilling. Complete top to
bottom within each priority band. Check items off as done; link the PR/commit.

_Started 2026-07-23. Legend: ☐ open · ◐ in progress · ☑ done · ⏸ blocked/parked._

---

## P0 — Foundation: trust the measurement (blocks everything above it)

- ◐ **A-3 Accuracy tolerance — provisional set (ADR 0004):** ≤1.5° mean at 60cm, worst
  ≤2.5°. **Clinical Lead to confirm** (may differ per protocol). → done when confirmed.
- ☐ **A-4a Repair the Clinical Lead's reference eye tracker.** Highest-leverage P0 unlock —
  turns accuracy from unfalsifiable to gold-standard measurable. Owner: Huilin + Clinical
  Lead. *(ADR 0004)*
- ☐ **A-4b Build a fixed-head grid-target test** in the desktop app (dots at known angles,
  head braced) as the interim ground truth available now. *(ADR 0004 tier 1)*
- ☐ **A-5 Run accuracy validation** — grid test now; simultaneous dual-tracker comparison
  once A-4a lands. Record measured error vs the A-3 target. Gate the pilot depends on.

## P1 — Clinical trust: nothing unfounded reaches a patient

- ☐ **A-6 Clinical Lead completes the sign-off register**
  (`docs/clinical/sign-off-register.md`). Every threshold/norm/interpretation gets a
  verdict. Owner: Clinical Lead, facilitated by Huilin. *(ADR 0003)*
- ☐ **A-7 Resolve the duplicated pursuit-gain threshold.** `normative_data.py` (per-age,
  ≈0.85) vs `pdf_report.py` (flat 0.80/0.70) disagree. Pick one source of truth, delete
  the other. *(register R3 vs P1)*
- ☐ **A-2 Add "not clinically validated" caveat** everywhere normative comparison / screening
  surfaces (screening UI + PDF report), until the register approves the row. *(ADR 0002)*
- ☐ **A-1 Literature verification pass** on the normative table: confirm / correct / remove
  each row against its cited paper, and flag lab-vs-webcam applicability. Feeds A-6.
  *(ADR 0002 — research task)*
- ☐ **A-8 Fill missing BCEA norms** for Child / Adolescent, or mark BCEA age-restricted.
  *(register, section A)*
- ☐ **A-9 Suppress/caveat auto-interpretation text for the pilot** — software shows
  measurements only; Clinical Lead interprets. *(ADR 0003 item 4)*

## P2 — Pilot as expertise + data harvester

- ☐ **A-10 Define the pilot** — site, patient count, and the pass criterion that makes it a
  success. Owner: Huilin + Clinical Lead. → SCOPE.md uncertain row. *(grill — pending)*
- ☐ **A-11 Capture Clinical Lead's per-patient interpretations** during the pilot as labeled
  data to replace hardcoded rules. *(ADR 0003)*
- ☐ **A-12 Collect webcam-native normal ranges** from the pilot cohort to replace borrowed
  lab norms. *(ADR 0002 long-term fix)*
- ☐ **A-13a Pin the pilot hardware setup** — 720p+ webcam @30fps, ~60cm, even front
  lighting, no strong backlight. Removes hardware as a variable during accuracy validation.
- ☐ **A-13b Measure the product hardware floor from pilot data** (not a spec sheet), and
  make the tracking client detect + refuse conditions below it (low res/light, face
  distance, glasses glare) with a fix-it prompt. *(client requirement)*

## P3 — Platform build-out (ADR 0001 hybrid)

- ☐ **A-14 Extract the transport-agnostic server modules** (metrics, protocols, validation,
  reports, patient, progress, norms) behind a clean gaze-sample interface. *(ADR 0001)*
- ☐ **A-15 TypeScript + MediaPipe Web tracking client** — port camera/tracking/calibration/
  filtering; must stay numerically in agreement with `gaze_estimator.py`. *(ADR 0001)*
- ☐ **A-16 Define the gaze-sample wire contract** (samples, not video) between client and
  server. *(ADR 0001)*
- ☐ **A-17 Write the hosted-PHI design doc** to the ADR 0005 superset — encryption in
  transit+rest, scalable key mgmt, per-user access control + audit, region-partitioned
  residency, consent models (HIPAA/GDPR/PIPL), retention/deletion, breach procedure, BAAs.
  Gates all P3 server work. *(ADR 0005)*
- ☐ **A-18 Regulatory path decision** (FDA SaMD / CE / NMPA per region) for the move beyond
  pilot to real patient care. → SCOPE.md uncertain row.

## P1 — Bugs found during setup (fix before pilot)

- ☐ **A-19 Fix PHI delete bug.** `patient_manager.py:229` deletes `{id}.json` but patients
  are saved as `{id}.phi` — delete may leave PHI on disk. Confirm and fix; add a test.
- ☐ **A-20 Document PHI key backup/restore** (crypto.py references a README procedure —
  verify it exists and is correct). *(ADR 0005 pilot requirement)*

## Parked (revisit when unblocked)

- ⏸ **`src/enterprise.py`** — branding / multi-clinician / FHIR / i18n. OUT of scope until
  accuracy validated and platform settled. Do not treat as working functionality. *(SCOPE.md)*

---

### Decision record index
- ADR 0001 — Hybrid edge-tracking / server-analysis architecture
- ADR 0002 — Normative data illustrative-only until verified
- ADR 0003 — Clinical Lead is the sign-off authority
- (pending) ADR — accuracy tolerance & ground truth (A-3/A-4)
- (pending) ADR — hardware floor (A-13)
- (pending) ADR — PHI/regulatory posture for hosted data (A-17)
