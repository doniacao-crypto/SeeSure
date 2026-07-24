# SCOPE — EyeExam

_Last updated: 2026-07-21 (via `/setup` Phase 0)_

## Problem & Users

EyeExam performs eye-movement assessment (smooth pursuit, saccades, fixation) using
standard webcam hardware, replacing equipment that normally costs orders of magnitude
more. It is both a **diagnostic** and a **training** product.

Two distinct users:

| User | Role | Needs |
|------|------|-------|
| Optometrist / neuro-optometrist | Administers assessment, interprets results, writes the prescription | Clinical accuracy, reports, patient records, normative comparison |
| Patient / client | Performs prescribed training at home, follows up | Simple guided sessions, progress feedback, low setup friction |

The clinician prescribes; the patient trains. Both halves must exist for the product
to be useful — a clinician-only tool is a measuring instrument, not a product.

## Definition of Done

The product is usable by the end user (clinician **and** patient) with the gaze
accuracy problem resolved — i.e. every clinical metric derives from tracking a
clinician would defend, at a stated, measured tolerance rather than an assumed one.

> Accuracy tolerance is not yet quantified. See CONCERNS.md — this is the top open item.

## IN scope

- Assessment protocols: smooth pursuit, saccade (pro/anti), fixation
- Calibration with quality feedback
- Clinical metrics: pursuit gain, phase lag, saccade latency/velocity, BCEA, microsaccades
- Patient records, session history, longitudinal progress tracking
- Clinical PDF reports, normative comparison, pass/fail screening
- Patient-facing prescribed training sessions
- PHI protection appropriate to real patient data

## OUT of scope (parked, not deleted)

- Enterprise tier as currently written (`src/enterprise.py`): practice branding,
  multi-clinician, HL7 FHIR/EHR integration, multi-language. Parked until accuracy
  is validated and the platform target is settled. Building EHR integration on top of
  unvalidated gaze data is roofing before foundation.
- Regulatory submission (FDA SaMD / CE marking). Not in scope for the pilot; becomes
  in-scope the moment the product moves beyond pilot to real patient care.

## UNCERTAIN — needs a decision, owner, and date

| Item | Question | Owner | By |
|------|----------|-------|-----|
| ~~Platform target~~ | **RESOLVED 2026-07-23 — ADR 0001.** Hybrid: one TS+MediaPipe web tracking client wrapped to all targets; Python server reuses today's analysis modules over gaze-sample streams (not video). Pilot runs on the existing desktop app. | Huilin | ✓ |
| Pilot definition | Who runs the pilot, how many patients, what result makes it a pass? | Huilin + Clinical Lead | TBD (A-10) |
| ~~Regulatory (data)~~ | **RESOLVED — ADR 0005.** All jurisdictions → design to HIPAA+GDPR+PIPL superset. Pilot stays local. | Huilin | ✓ |
| Regulatory (device) | FDA SaMD / CE / NMPA classification for real patient care beyond pilot. | Huilin | TBD (A-18) |
| ~~Accuracy tolerance~~ | **PROVISIONAL — ADR 0004.** ≤1.5° mean / ≤2.5° worst at 60cm. Clinical Lead confirms (A-3). | Huilin + Clinical Lead | ◐ |
| ~~Normative data provenance~~ | **RESOLVED — ADR 0002.** Unverified; illustrative-only until literature pass (A-1) + register (A-6). | Huilin + Clinical Lead | ✓ |

## Trajectory

The current desktop app is best understood as a **validation vehicle and pilot
instrument**, not the shipping product. Its job is to prove webcam gaze tracking can
hit clinical tolerance. The shipping product is a hosted, multi-platform system.

Backend starts small and is expected to be replaced with something more robust once
the shape is known — this is an explicit, accepted decision, not an oversight.
