# ADR 0003 — Clinical Lead is the sign-off authority for clinical output

- Status: Accepted
- Date: 2026-07-23
- Deciders: Huilin

## Context

EyeExam is both diagnostic and training software. The product concept and features
originate from a practising optometrist who runs a clinic (the "Clinical Lead"). However,
the concrete clinical assertions in the code — normative ranges, pass/fail thresholds,
interpretation text like "may indicate executive dysfunction" — were written by the
implementers to match her general direction and have **not** been reviewed by her
line-by-line. The software therefore emits clinical-sounding judgments wearing her
authority without her explicit sign-off (see ADR 0002 for the normative-data instance).

She is deeply involved at the concept level but not yet at the validation level. Her time
is scarce (she runs a clinic), so involvement must be structured as small, self-contained
review artifacts — not code reading or long meetings.

## Decision

1. **Define the role.** The optometrist is the **Clinical Lead** and the **sign-off
   authority**: nothing user-facing and clinical ships without her verdict.
2. **Sign-off register is the mechanism** (`docs/clinical/sign-off-register.md`): every
   clinical assertion the software makes, extracted and pre-filled, with a verdict column
   (`approve / change to ___ / remove / unknown`). She completes it in one sitting; this
   converts "involve her more" into a finite checklist and exposes what is currently
   unfounded before patients see it.
3. **Sequencing:** register is completed **before** the pilot; the pilot then **collects
   her real interpretations and webcam-native norms** to replace guesses (see ADR 0002).
4. **Pilot posture:** software presents **measurements only**; the Clinical Lead supplies
   all interpretation per patient. Auto-interpretation text is suppressed or explicitly
   caveated during the pilot.
5. **Standing cadence:** short, artifact-driven, async-friendly reviews (a batch of
   register rows, sample reports, real result screens) — never open-ended meetings.

## Alternatives considered

- **Trust that her involvement covers the details.** Rejected: source-of-ideas is not
  line-by-line validation; the seam between the two is exactly where unfounded clinical
  claims hide.
- **Have implementers pick clinically reasonable values.** Rejected: that is the current
  state and the root cause of ADR 0002.

## Consequences

- A gate now exists: clinical output is "not clinically validated" until its register row
  is approved. UI/reports must reflect that state until then.
- The pilot gains a second purpose beyond accuracy: harvesting her expertise (norms +
  interpretations) into the product.
- Small recurring demand on the Clinical Lead's time, deliberately structured to be light.
