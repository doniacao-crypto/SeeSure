# ADR 0005 — PHI & regulatory posture (multi-jurisdiction)

- Status: Accepted
- Date: 2026-07-23
- Deciders: Huilin

## Context

The hosted product will handle identifiable patient health data (PHI). Patients are
expected in **all jurisdictions** — US, EU/UK, China, and others. Each imposes its own
regime: **HIPAA** (US), **GDPR** (EU/UK, health = special category), **PIPL** (China), plus
local laws elsewhere.

Current PHI protection (`src/crypto.py`, `src/patient_manager.py`) is a **local device**
model: Fernet-encrypted `.phi` files, key in the OS keychain, single machine, single user.
Its threat model is device theft. It does **not** address server compromise, cross-tenant
access, insider access, in-transit protection, key management at scale, audit, residency,
retention, or breach notification — all of which server hosting introduces.

## Decision

**Pilot (local desktop app):** the existing device-encryption model is adequate for a
supervised pilot **provided real patient data stays on the clinic's machine and is not
synced anywhere.** Required fixes before pilot: repair the delete bug (below) and document
key backup/restore. The pilot deliberately does not touch the multi-jurisdiction problem.

**Product (hosted):** design to the **strictest superset** of the applicable regimes
("highest common denominator"), because patients span all of them:
- Encryption **at rest and in transit**; key management **not** tied to a single OS keychain.
- **Per-user access control + full audit trail** (HIPAA), lawful basis + **explicit consent**
  and data-subject rights incl. erasure (GDPR), separate consent + local processing (PIPL).
- **Data residency by region** — EU data in the EU, China data in China → **region-partitioned
  hosting**, not one global database. This is a first-class input to the backend design (A-14).
- Defined **retention/deletion** policy and **breach-notification** procedure.
- US clinics: **Business Associate Agreement** with each covered-entity clinic.

**Hard gate:** no real patient data touches a server until the target regime's
non-negotiables are designed in. The pilot's local-only posture is what buys time to do
this properly.

## Alternatives considered

- **Pick one jurisdiction first, add others later.** Rejected by the "all" scope. Retrofitting
  residency and consent models onto a running multi-tenant PHI system is far costlier than
  designing for the superset up front.
- **Keep the OS-keychain key model on the server.** Rejected: single-key, single-host model
  does not scale to multi-user hosted data or survive key-rotation/audit requirements.

## Consequences

- The backend (A-14) is not "a server" but **region-partitioned, compliance-first hosting** —
  a materially larger effort. Reinforces starting small ≠ starting naive on data location.
- Data migration from the small first backend to a robust one must itself be
  compliance-preserving (previously flagged in CONCERNS.md).
- A concrete hosted-PHI design doc is owed before P3 server work begins (A-17).
