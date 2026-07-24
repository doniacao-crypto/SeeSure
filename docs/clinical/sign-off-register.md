# Clinical Sign-off Register — EyeExam

Every clinical assertion the software currently makes. Nothing user-facing and clinical
ships without a verdict from the **Clinical Lead** (see ADR 0003).

**How to use:** Clinical Lead fills the **Verdict** column for each row:
`approve` · `change to ___` · `remove` · `unknown (need data)`.
Extracted from code 2026-07-23. Line references are where the value lives.

> ⚠️ Known inconsistency to resolve first: pursuit-gain "reduced" threshold is defined
> **twice and differently** — `normative_data.py` uses per-age norms (young-adult lower
> bound ≈ 0.85), while `pdf_report.py` hardcodes a flat 0.80 / 0.70. Pick one source of
> truth. (Register rows R1 and R7.)

## A. Normative reference ranges (`src/normative_data.py`)

Each is `mean, std, 5th pct, 95th pct` per age group. Citations were generated with the
numbers and are **unverified** (ADR 0002).

| # | Metric | Age group | Range (mean / low–high) | Cited source | Verdict |
|---|--------|-----------|--------------------------|--------------|---------|
| R1 | Pursuit gain | Child 6–12 | 0.85 / 0.70–1.00 | Ross 2000 | |
| R2 | Pursuit gain | Adolescent 13–17 | 0.90 / 0.75–1.00 | Munoz 1998 | |
| R3 | Pursuit gain | Young adult 18–39 | 0.95 / 0.85–1.00 | Leigh & Zee 2015 | |
| R4 | Pursuit gain | Middle 40–59 | 0.92 / 0.80–1.00 | Leigh & Zee 2015 | |
| R5 | Pursuit gain | Older 60+ | 0.85 / 0.70–0.98 | Sharpe & Zackon 1987 | |
| R6 | Saccade latency | Child | 250 / 170–350 ms | Munoz 1998 | |
| R7 | Saccade latency | Adolescent | 220 / 150–300 ms | Munoz 1998 | |
| R8 | Saccade latency | Young adult | 200 / 150–260 ms | Leigh & Zee 2015 | |
| R9 | Saccade latency | Middle | 210 / 150–280 ms | Leigh & Zee 2015 | |
| R10 | Saccade latency | Older | 240 / 170–330 ms | Abel 1983 | |
| R11 | Antisaccade error | Child | 30 / 10–55 % | Munoz 1998 | |
| R12 | Antisaccade error | Adolescent | 20 / 5–40 % | Munoz 1998 | |
| R13 | Antisaccade error | Young adult | 12 / 2–25 % | Evdokimidis 2002 | |
| R14 | Antisaccade error | Middle | 15 / 3–30 % | Evdokimidis 2002 | |
| R15 | Antisaccade error | Older | 25 / 8–45 % | Olincy 1997 | |
| R16 | Fixation BCEA | Young adult | 0.5 / 0.1–1.2 deg² | Crossland 2004 | |
| R17 | Fixation BCEA | Middle | 0.6 / 0.15–1.4 deg² | Crossland 2004 | |
| R18 | Fixation BCEA | Older | 0.8 / 0.2–1.8 deg² | Crossland 2004 | |
| — | Fixation BCEA | Child / Adolescent | **MISSING** — no norms defined | — | |

## B. Interpretation text (`src/normative_data.py`, `_get_*_interpretation`)

| # | Trigger | Text shown to user | Verdict |
|---|---------|--------------------|---------|
| T1 | Gain borderline | "Pursuit gain slightly reduced - monitor" | |
| T2 | Gain fail | "Pursuit gain significantly reduced - recommend evaluation" | |
| T3 | Latency < 100ms | "Anticipatory saccades noted" | |
| T4 | Latency fail | "Saccade latency prolonged - recommend evaluation" | |
| T5 | Antisaccade borderline | "Mild difficulty with inhibitory control" | |
| T6 | Antisaccade fail | "Significant inhibitory control difficulties - may indicate executive dysfunction" | |

## C. Overall screening verdicts (`get_overall_screening`)

| # | Rule | Output | Verdict |
|---|------|--------|---------|
| S1 | ≥1 metric fails | "REFER — recommend specialist referral" | |
| S2 | >1 borderline | "MONITOR — recommend follow-up" | |
| S3 | exactly 1 borderline | "PASS* — continue routine monitoring" | |
| S4 | all normal | "PASS — all metrics within normal limits" | |

## D. PDF report thresholds (`src/pdf_report.py`)

| # | Threshold | Text | Verdict |
|---|-----------|------|---------|
| P1 | gain ≥ 0.8 | "within normal limits (≥0.8)" — **conflicts with R3** | |
| P2 | gain 0.7–0.8 | "borderline - recommend monitoring" | |
| P3 | gain < 0.7 | "reduced (<0.7) - recommend further evaluation" | |
| P4 | accuracy ≤ 2.0° | "within normal limits (≤2°)" | |
| P5 | smooth_score ≥ 70 | "smooth with minimal saccadic intrusions" | |
| P6 | smooth_score 50–70 | "some saccadic intrusions noted" | |
| P7 | smooth_score < 50 | "may indicate pursuit dysfunction" | |

## E. Caveat: instrument mismatch (applies to ALL of the above)

All ranges above are **lab-eye-tracker-derived**. EyeExam metrics are **webcam-derived**
at lower sampling rate and higher noise. Even a correctly-transcribed norm may misclassify
a healthy patient on a webcam. Clinical Lead to note, per metric, whether the lab range is
usable as-is on webcam, needs an offset, or must be replaced by pilot-collected norms.
