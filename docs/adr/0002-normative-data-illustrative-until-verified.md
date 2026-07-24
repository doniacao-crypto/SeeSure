# ADR 0002 — Normative data is illustrative-only until verified

- Status: Accepted
- Date: 2026-07-23
- Deciders: Huilin

## Context

`src/normative_data.py` provides age-matched reference ranges (pursuit gain, saccade
latency, antisaccade error, fixation BCEA) used to produce pass/fail/borderline
screening verdicts.

Each row carries a citation (Ross et al. 2000, Munoz et al. 1998, Leigh & Zee 2015,
Crossland et al. 2004, etc.). These are real names in the oculomotor literature, so the
table does not look fabricated. However, **Huilin confirmed the citations were generated
alongside the numbers and none has been verified against its source paper.** The numbers
are plausible but unsourced; the citations are decorative until checked.

Two compounding problems:

1. **Provenance unverified.** No row is confirmed to match the paper attached to it.
   A clinician spot-checking one value against one paper, finding a mismatch, will
   distrust the entire table.
2. **Instrument mismatch.** The cited norms are derived from **laboratory eye trackers**
   (high sampling rate, sub-degree accuracy). EyeExam metrics are **webcam-derived**.
   Lower sampling rate and higher noise systematically bias latency and velocity, so even
   correctly-transcribed lab norms may flag healthy patients as abnormal purely from
   instrument difference. Also: BCEA has only 3 age groups where others have 5.

## Decision

Treat normative comparison as **illustrative-only** until the data is validated. Concretely:

1. **No unqualified pass/fail verdict is presented as clinical.** Screening output must
   carry an explicit caveat: norms are lab-derived, unverified against source, and not
   validated against webcam-derived metrics.
2. **Verification is a tracked, separate task** — a literature pass that confirms each row
   against its cited paper (or replaces/removes it), plus an explicit note on lab-vs-webcam
   applicability. Recorded in DEPENDENCIES.md.
3. **Longer term**, the trustworthy source of norms is a **webcam-derived cohort collected
   during the pilot** on the same instrument patients will use — not borrowed lab norms.

## Alternatives considered

- **Ship the table as-is with citations.** Rejected: presents unverified numbers as
  authoritative; trivially falsifiable by a clinician; the highest-credibility-risk item
  in the repo.
- **Delete normative comparison entirely.** Rejected: the mechanism (percentile, status,
  age grouping) is sound and worth keeping; only the reference values are untrusted. Gate,
  don't remove.

## Consequences

- Screening UI/reports need a visible "illustrative / not clinically validated" caveat
  wherever normative comparison appears.
- A verification/replacement pass is owed before any claim of clinical screening.
- The pilot gains a second purpose: collect webcam-native norms, not just prove accuracy.
