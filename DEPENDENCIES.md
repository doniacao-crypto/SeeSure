# DEPENDENCIES — EyeExam

External contracts this project depends on but does not control.
One row per contract. Status is honest, not aspirational.

_Last updated: 2026-07-21 (via `/setup` Phase 0)_

| Dependency | What we need | Provider | Status | Risk if unmet |
|---|---|---|---|---|
| Clinical domain expertise | Line-by-line validation of thresholds, norms, and interpretation text; prescribed-training logic | **Clinical Lead** — practising optometrist, clinic owner, product originator (ADR 0003) | **Identified & engaged at concept level; validation pending** via sign-off register | Concept is grounded, but concrete clinical assertions remain un-validated until the register is completed. Gated by ADR 0003. |
| Normative reference data | Age-matched normal ranges backing `src/normative_data.py` | Published literature (verify) → pilot-collected webcam cohort (replace) | **Unverified — citations generated with the numbers, none checked against source (ADR 0002).** Gated to illustrative-only. | Every pass/fail screening verdict is unfounded until each row is verified against its paper, or replaced with webcam-native norms. Highest credibility risk in the repo. |
| Accuracy ground truth | A reference eye tracker to measure our gaze error against | **Clinical Lead owns a commercial device — currently broken** | **Sourced but blocked on repair (ADR 0004)** | Until repaired, only self-validation + fixed-head grid test are available; neither catches systematic bias. Repair unlocks the whole P0 accuracy band. |
| Pilot site | A clinic willing to run the pilot with real patients | TBD | **Not identified** | Pilot gate in SCOPE.md has no execution path. |
| Hosting / backend platform | Server for customer data in the multi-platform product | TBD | **Not selected** | Blocks the stated end-state architecture. Accepted as deferred — start small, replace later. |
| MediaPipe face landmarker | `src/face_landmarker.task` model, gaze-relevant landmark stability across faces, lighting, glasses | Google / MediaPipe | **In use, pinned** | Upstream model behaviour changes silently shift all downstream metrics. Model integrity is SHA256-verified; behavioural drift is not. |
| PHI regulatory obligations | Compliance with the **union** of HIPAA + GDPR + PIPL (patients in all jurisdictions) once hosted | Determined by scope — global patient base | **Determined: multi-jurisdiction superset (ADR 0005)** | Forces region-partitioned hosting, per-region consent/residency, audit, BAAs. Large weight on the backend design. Pilot stays local to avoid it entirely. |
| Consumer hardware floor | Minimum webcam resolution, frame rate, lighting, viewing distance | Pilot setup fixed by us; product floor **measured from pilot data** | **Pilot floor set; product floor deferred to pilot data** | Product floor guessed from a spec sheet would be wrong; deriving it from pilot observations + a client that refuses to measure below it is the plan (A-13). |
