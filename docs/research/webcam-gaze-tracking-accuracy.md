---
title: Single-Webcam Gaze Tracking — Accuracy Limits, Geometry, and Clinical Viability
date: 2026-07-14
status: research finding
scope: EyeExam gaze pipeline (MediaPipe + PyQt, one RGB webcam)
method: 46-agent parallel deep research; every claim adversarially fact-checked (36 verified, 1 refuted and dropped)
---

> **How to read this.** This answers why EyeExam's accuracy plateaued despite many algorithm
> changes, where the real ceiling is, and what to build the product on. Claims carry sources.
> Where the literature is thin, vendor-authored, or contradictory, the report says so.
>
> **Empirically confirmed against this codebase** (see `Verification` at the end) — the headline
> root cause was reproduced with a test harness, not just asserted.

# EyeExam: Why the Eye‑Tracking Plateau Is Real, Where the Ceiling Actually Is, and How to Break Through

**Audience:** EyeExam engineering team
**Scope:** single RGB webcam (Mac Studio external / MacBook built‑in) + MediaPipe + PyQt, for child attention assessment
**Status of evidence:** every number below is from a fact‑checked source pack; where the literature is thin, vendor‑authored, or contradictory, I say so explicitly.

---

## 1. Verdict

### Is the goal achievable?

**Yes — but not at the accuracy you are implicitly assuming, and not with the current feature vector.** The goal has to be re‑scoped from "measure eyeball kinematics" to "measure where the child is looking, coarsely, and count inhibition failures."

### The realistic accuracy ceiling

| Regime | Angular error | On‑screen @ 60 cm | Evidence |
|---|---|---|---|
| Your current architecture (geometric iris features + polynomial ridge) | **3–5°** | 3.1–5.2 cm | WebGazer, the direct architectural cousin, is measured at **4.17°** mean / ~15–18 % of screen offset (Papoutsaki IJCAI‑16; Semmelmann & Weigelt, *BRM* 2018) |
| Pretrained CNN + gaze normalization + ~9–20 point personal calibration, free head | **2.5–4°** | 2.6–4.2 cm | FAZE 3.14–3.42° on MPIIGaze at k=3–9 (Park, ICCV 2019); within‑dataset SOTA 3.7–4.9° (Cheng, TPAMI 2024) |
| Best published webcam number, lab conditions | **1.4° / 1.1° precision** | 1.5 cm | Kaduk et al., *BRM* 2023 — **but**: vendor‑authored (3/4 authors work for Labvanced), glasses‑wearers excluded, fixed 600 mm, external 1080p cam, ~5‑min / ~84‑target / 7‑head‑pose calibration, and an enforced **virtual chin rest** that halts the trial on head movement |
| Cross‑dataset / new person, new room, zero calibration | **6.4–8.6°** (lab‑to‑lab), **11–20°** in the wild | 6.8–9.1 cm / 12–21 cm | EIF 2024; Gaze4HRI 2026 |
| Dedicated IR tracker (what you're avoiding) | 0.5–0.9° | 0.5–1.5 cm | Tobii 5: 0.9°/15 mm (Falch & Lohan, *Front. Robot. AI* 2024) |

**Plan for 3° (≈3.1 cm at 60 cm) as your engineering target, and design every clinical measure to survive 4° (4.2 cm).** Anything you have seen claiming ≤1.5° on a webcam came with a chin rest, a 5‑minute calibration, or a phone at 30 cm.

### Hardware limit vs. engineering failure — the honest split

**True hardware/physics limits (unfixable, budget around them):**

1. **Spatial sensitivity.** At your assumed 62° hFOV, 1080p, 60 cm: `f_px = (1920/2)/tan(31°) = 1598 px`. Eye rotation moves the apparent iris centre by only `R_eff ≈ 0.19 mm/deg`, so image displacement is `0.19 × 1598/600 = 0.51 px/deg`. **1 px of iris‑centre error ≈ 2.0° of gaze.** At 720p it is **2.9°/px**. The whole ±25° usable gaze range lives in ±13 px — about ⅓ of an iris width (the iris is only ~31 px across at 1080p, ~21 px at 720p). This is a Jacobian, not a hard floor (ellipse fitting over ~60–100 limbus pixels can reach 0.1–0.3 px), but it means every bias term is multiplied by ~2°/px.
2. **Temporal.** 30 fps → 33.3 ms/sample. A 10° saccade lasts 40–58 ms → **1–2 samples inside the movement**. Peak velocity at 30 Hz is underestimated by >50 % for a 10° saccade, and **no amplitude up to 60° recovers 95 % of true peak velocity at 30 or 50 Hz** — even after spline upsampling, 30 Hz only reaches A_min = 55°, 60 Hz reaches 20°, and only 120 Hz brings it to 2.5° (Mack, Belfanti & Schwarz, *Behav Res Methods* 2017, Table 1). Saccade peak velocity, the main sequence, and microsaccades are **permanently off the table** at 30–60 fps. This is Nyquist, not a bug.
3. **Angle kappa.** The visual axis differs from the optical axis by ~5°, SD ±1.4° (adults) and ±2.5° (children 6–8). No image processing recovers this from a monocular iris centroid without a known gaze target. Per‑user calibration is mandatory forever.

**Engineering failures (all fixable, and they are where your plateau lives):**

4. Your feature vector contains **no depth, no eye 3‑D position, no head translation**. The `solvePnP` translation vector is computed and thrown away (`eye_tracker.py:349–370` keeps only Euler angles).
5. Your head‑pose features are almost certainly **numerically detonating at test time** (§3, defect A). This is my primary hypothesis for "many algorithm changes produced no improvement at all."
6. Your camera intrinsics are **assumed** (62° hFOV hard‑coded, `eye_tracker.py:190–192`), and your 3‑D face model uses **deformable landmarks** (chin, mouth corners) in **non‑metric units**.
7. Only **9 distinct design points** constrain 15 polynomial columns.
8. Head **roll** is not removed; iris offsets are taken in raw image axes.

### Why algorithm changes produced *zero* improvement

Because you have been changing the **function class** (polynomial degree, ridge alpha, filter type) while the **input information** and the **input scaling** are broken. Three independent reasons, in order of confidence:

- **The head‑pose columns are scaled by their calibration‑time standard deviation.** If the child sits still for the 9 dots (which is what you ask them to do), `std(yaw)` during calibration is a fraction of a degree — mostly landmark noise. `StandardScaler` then divides by that. At test time a real 12° head turn becomes a **20–50 σ input**, and the degree‑2 expansion squares it. The prediction saturates and gets clipped to the screen edge. Any change to the regressor is invisible against this.
- **The information required to place a gaze ray on a screen is absent from the features** (no ray origin, no depth). No regressor can invert a function of variables it cannot see.
- **9 distinct targets is not enough data to identify 15 coefficients**, so the model is doing very little beyond memorising the 9 dots.

**The binding constraint is the input representation, not the model.**

---

## 2. Q1–Q6, answered concretely

### Q1. How do you get eye–camera distance from one webcam?

Via the iris as a metric ruler. Pinhole: a segment of metric length `L` perpendicular to the optical axis at depth `Z` projects to `l = f_px · L / Z`, so:

```
Z = f_px · IRIS_mm / iris_px          f_px = (W_px/2) / tan(hFOV/2)
```

Constants: horizontal visible iris diameter (HVID) ≈ **11.7 ± 0.5 mm** (Google's MediaPipe Iris constant); white‑to‑white corneal diameter 11.80 mm, SD ≈ 0.45 mm, n = 4787 (Hashemi, *J Curr Ophthalmol*); 11.71 ± 0.42 mm (Rüfer, *Cornea* 2005). It is **lighting‑invariant** — the limbus is the cornea/sclera junction and does not move when the pupil dilates. That's why the iris beats the pupil and beats IPD as a ruler.

Worked, with your settings (62° hFOV, 1080p): `f_px = 1598`. At Z = 600 mm the iris spans `1598 × 11.7 / 600 = 31 px`. At 720p, `f_px = 1065`, iris = 21 px.

**Error budget — and this is where the honesty is required.** The three terms add:

```
|dZ/Z| ≤ |df/f| + |dL/L| + |dl/l|
```

- **FOV prior dominates.** Consumer webcam hFOV runs 55–90°. Assuming 62° when the truth is 78° gives `f_px` 1598 vs 1186 → **~35–40 % depth error (≈240 mm at 600 mm)**. Google's MediaPipe Iris achieved 4.3 % ± 2.4 % depth error *because it read `f_px` from the camera API/EXIF*. **That is exactly the step you skip**, so the 4.3 % figure does not transfer to you. (It is also a Google blog number, not peer‑reviewed; arXiv:2006.11341 contains no depth evaluation.)
- **HVID prior:** ±0.5 mm ≈ 4.3 % per subject, and it is ethnicity‑dependent (≈11.75 mm white, ≈11.26 mm Chinese, ≈11.10 mm Japanese) — a **systematic, non‑averaging** bias.
- **Pixel term:** ±1 px on a 21‑px iris (720p) = 4.6 % (28 mm). 1080p halves it.

**Two conflicting claims in my source pack, resolved:** one line of evidence (Sethu, ruler‑based, n=1234 South Indian children: HVID 10.45–10.73 mm) suggests children's irises are much smaller. This is a **measurement artefact of the 1‑mm‑step ruler** — the Shandong Children Eye Study (n=5970, ages 4–18, laser interferometry) gives **12.02 ± 0.38 mm**, and photographic measurement in children agrees with calipers. **Do not use 10.5 mm as a paediatric norm.** School‑age irises are essentially adult‑sized.

**Implementation:**
1. **Calibrate `f_px` once per device.** OpenCV chessboard/ArUco, 15 shots, `cv2.calibrateCamera`. Store per camera in `config.json`. This is a 30‑minute job and it removes the single largest error term in the whole system.
2. Fit an **ellipse** to landmarks 469–472 / 474–477 (the outer iris circle) and take its **major axis** as `iris_px` — the major axis is pose‑stable; the horizontal chord foreshortens with yaw and eccentric gaze, biasing Z upward exactly in the regime an eye‑movement exam operates in.
3. Optionally solve for a **per‑child lumped scale** `(f_px / IRIS_mm)_eff` by recording `iris_px` at a ruler‑verified 60 cm during calibration. Treat it as a camera+anatomy scale factor, not an anatomical diameter.
4. Sanity‑check against the inter‑ocular pixel distance, but **do not use IPD as the primary ruler**: adult IPD 63.4 ± 3.8 mm (CV 6 %), it *grows through childhood* (~51 mm at age 5 → 63 mm at 20; MacLachlan & Howland 2002), and `IPD_px` foreshortens as `cos(yaw)` — a 20° yaw shrinks it 6 % → +6 % depth error.

**Expected result:** with calibrated intrinsics and 1080p, **5–8 % depth error (30–50 mm at 600 mm)**. Without intrinsic calibration, be honest and label it an uncalibrated estimate with a 20–40 % tail.

---

### Q2. Head movement vs. true eyeball rotation

**Why your current feature cannot do this.** Under weak perspective with a spherical eye, your eye‑corner‑normalized offset is approximately

```
o_x ≈ (R_eff/W) · sin(θ + β)/cos β  +  (m_x/W) − (m_z/W)·tan β
```

where θ is eye rotation **in the head frame** (what you want) and

```
β = head_yaw  +  atan(x_eye / z_eye)      ← the eye's LATERAL POSITION
```

Two consequences:

- Head orientation enters **inside the sine** and as a multiplicative `1/cos β`. A degree‑2 polynomial in `(o_x, o_y, pitch, yaw)` captures the leading linear term (it does contain `o_x·yaw`), so it is *mediocre*, not useless — but the first missing monomial is `o·β²` (degree 3), so it degrades progressively and breaks down beyond β ≈ 30–40°.
- **`β` contains the head's lateral position, which is not in your feature vector at all.** At Z = 60 cm, a 15 cm lateral head shift changes β by `atan(15/60) = 14.0°`. That produces an apparent iris displacement of `12·sin(14°) = 2.90 mm` — while a genuine 15° eye rotation produces `12·sin(15°) = 3.11 mm`. **Within 6.5 % of each other.** A sideways head shift is nearly indistinguishable from a 14° gaze shift. Even a 3 cm drift gives β = 2.9° → ~3° of gaze bias, already above your target.

Good news: this is a **feature‑selection bug, not a rank deficiency**. `atan(x_eye/z_eye)` is trivially recoverable from the image as `atan((u_eye − c_x)/f_x)` — the eye's own pixel coordinate, with `f_x` already in `eye_tracker.py:188–193`.

**The fix, in two escalating tiers:**

**Tier 1 (cheap):** append `[u_eye_norm, v_eye_norm, interocular_px, iris_px]` to the feature vector, so the model can observe eye position and depth.

**Tier 2 (correct): Sugano/Zhang gaze normalization + a 3‑D eye model.** Per eye:

1. `R_head, t_head` from `solvePnP` on **rigid** landmarks only (nose bridge, outer eye corners — **drop chin and mouth corners**, they deform with expression; drop ear tragions, they are occluding‑contour landmarks and view‑dependent).
2. Eyeball rotation centre in the head frame: `e_head = midpoint(eye_corners) + d`, `d` a per‑person offset (~10 mm posterior along −z_head). Map to camera: `e_cam = R_head·e_head + t_head`. **This is the key step: `e` is rigid in the head, so head rotation and translation are absorbed exactly by `(R_head, t_head)`.**
3. Back‑project the 2‑D iris centre: `dir = normalize(K⁻¹[u,v,1]ᵀ)`, intersect the sphere `‖x − e_cam‖ = R_eff`:
   `s = (dir·e_cam) − sqrt((dir·e_cam)² − ‖e_cam‖² + R_eff²)`, `p_cam = s·dir`. Guard the discriminant.
4. Optical axis: `g_cam = normalize(p_cam − e_cam)`.
5. Eye‑in‑head signal: **`g_head = R_headᵀ · g_cam`** — its two angles (θ, φ) *are* the eyeball's rotation in the skull. **This is the quantity your app claims to measure and currently does not compute anywhere.**
6. Visual axis: apply the per‑person kappa rotation `R_κ(α, β_v)`, then intersect the screen (Q3).

**Constants:** eyeball rotation centre to corneal apex = **13.1 mm** = 5.3 mm (rotation centre → corneal curvature centre) + 7.8 mm (corneal radius) — Guestrin & Eizenman 2006 state this verbatim in Appendix A. But *measured* CORs are **15.3 ± 1.5 mm horizontal / 12.5 ± 1.3 mm vertical** (Ohlendorf, *OPO* 2022, n=59) — highly variable and **anisotropic**. For the sphere intersection use `R_eff ≈ 10.5–11.5 mm` horizontal, **not** 12 mm: the true pupil sits 5.3 + 4.2 = 9.5 mm from the rotation centre, and corneal refraction puts the entrance pupil ~0.5 mm anterior. `R_eff` is a **gain parameter** — a wrong value produces a multiplicative gaze error that per‑person calibration absorbs. It is **not** the cause of your plateau. GeoGaze explicitly tried learning it per‑sample and found "no significant difference"; **do not spend time here.**

**Ten‑minute falsification test of the whole pipeline:** have a subject fixate one dot, then **turn their head (yaw/pitch)**. `g_head` must *change* (compensatory VOR) while `g_cam` stays locked on the target. Then have them hold the head still and saccade: `g_head` and `g_cam` must change identically. If that doesn't hold, the geometry is wrong and nothing downstream matters.

**Honest caveat:** head pose does not "factor out algebraically." You replace learned head compensation with a hard dependence on `solvePnP`'s `R_head` and `t_head`, whose errors propagate into the ray origin. GeoGaze deliberately works entirely in the camera frame for this reason. Realistic accuracy for this class of method is **3.5–5° within‑dataset with per‑person calibration**, ~6.7° cross‑dataset. It is best used as a **relative** eye‑in‑head signal (saccade/nystagmus detection), where precision beats accuracy.

---

### Q3. Which part of the screen is being looked at?

The gaze **ray** must be intersected with the **screen plane**. You need three things you currently have none of: a metric ray origin, camera intrinsics, and camera→screen extrinsics.

**Screen frame (right‑handed):** origin at the top‑left of the *active pixel area*, x right, y **down**, z = x̂ × ŷ pointing **into** the screen. Extrinsics `(R_s, t_s)`: `X_cam = R_s·X_scr + t_s`.

```
n   = R_s · [0,0,1]ᵀ                 (third column of R_s)
p0  = t_s                            (top-left corner, in camera coords)
λ*  = n·(p0 − o) / (n·d)             reject if |n·d| < ε or λ* ≤ 0
X_hit = o + λ*·d
[u_mm, v_mm, 0]ᵀ = R_sᵀ·(X_hit − t_s)
px = u_mm · W_px/W_mm ,  py = v_mm · H_px/H_mm
reject if u_mm ∉ [0, W_mm] or v_mm ∉ [0, H_mm]
```

Do it **per eye** and average the two 2‑D screen points (not the 3‑D midpoint of the two rays — that is a vergence estimate and generally isn't on the screen). This cancels the mirror‑symmetric **horizontal** kappa component only; vertical kappa is same‑signed in both eyes and does **not** cancel.

**Pixels per mm:** 27″ 2560×1440 → 108.8 ppi = **4.28 px/mm**. Apple Studio Display 5120×2880 over 596.6 × 335.6 mm → **8.58 px/mm** native (4.29 pt/mm in 2× HiDPI). MacBook Pro 14.2″ 3024×1964 over 302.4 × 196.4 mm → **10.00 px/mm**. **Do not trust EDID / `CGDisplayScreenSize`** — it is cm‑quantised and sometimes wrong. Measure with a ruler once per model.

**Extrinsics are not available from any macOS API.** AVFoundation exposes *intrinsics* (`AVCameraCalibrationData.intrinsicMatrix`); `extrinsicMatrix` is camera‑to‑*reference‑camera* on multi‑cam devices, not camera‑to‑display. CoreGraphics gives bounds and physical size, no pose. You must recover `(R_s, t_s)` yourself (mirror‑based screen‑pose calibration, Rodrigues et al. 2010) or measure it.

- **MacBook built‑in and Apple Studio Display:** camera is rigidly coupled to the panel, so `(R_s, t_s)` is a **per‑model constant that survives lid rotation**. Exploit this. Caution: on notched MacBooks (14″/16″ 2021+, Air M2+) the lens sits *inside* the notch, roughly **level with** the top of the active pixel area — not 8–15 mm above it (that's pre‑notch). And be explicit about which frame you mean: `CGDisplayBounds` (full panel) vs `NSScreen.safeAreaInsets` differ by ~7–8 mm, and a sign error of one notch height is the obvious failure mode.
- **Third‑party clip‑on webcam on an arbitrary monitor:** position and tilt are user‑set. Correcting a claim you may have seen: **tilt is *not* the dominant term.** Because the camera sits essentially *in* the screen plane, a rotation error acts about a point in that plane and the eye‑position and ray‑direction errors largely cancel: error ≈ `g·m·θ`, where `g` is the gaze point's in‑plane distance from the camera axis and `m` the ray obliquity. For g = 200 mm, m = 0.1–0.3, a 5° tilt error costs **~2.5–6 mm**, not 52 mm. **Position error, by contrast, maps ~1:1** — 1 mm of webcam misplacement = 1 mm of screen error. So: physically constrain and *measure* the webcam's position; tolerate a few degrees of tilt.

The `52 mm at 5°` figure is the conversion for **gaze‑ray** angular error (`D·tan θ`), and *that* is your dominant term: a 3–5° estimator on a 60 cm baseline is 3–5 cm.

**Reference implementation:** `pperle/gaze-tracking-pipeline` (MIT) has correct `ray_plane_intersection` / `get_point_on_screen`. Note that as shipped it does **not** load a calibrated screen pose (`plane_equation(np.eye(3), [[0],[0],[0]])` + a `# TODO load calibrated screen position`, a hard‑coded 20 mm offset, and an explicit x‑flip). MPIIGaze/MPIIFaceGaze is the correct citation for actual camera↔monitor pose calibration (`screenSize` + `monitorPose` per participant).

---

### Q4. Speed and direction of the eyeball

**Direction:** from `g_head` (Q2). The angular velocity is `ω = dθ/dt` per frame, but see below.

**Speed: be extremely careful. Most velocity metrics are simply not measurable on your hardware.**

Main sequence (Inchingolo & Spanio 1985, as used by Mack et al. 2017):
```
v_max(a) = 1000·a / (18 + 1.2·a)  deg/s        d(a) = 38 + 2·a  ms
```
→ 2°: 98 °/s, 42 ms · 5°: 208 °/s, 48 ms · 10°: 333 °/s, 58 ms · 20°: 476 °/s, 78 ms. Real (skewed) saccades are shorter: 10° ≈ 40–50 ms.

At 30 fps (33.3 ms/frame) a 10° saccade has **~1.4 in‑movement samples**. At 60 fps, ~2.7.

| Metric | 30 fps | 60 fps | 120 fps |
|---|---|---|---|
| Saccade **peak velocity** | ❌ Not recoverable at any amplitude ≤60° | ❌ only ≥55° (≥20° with upsampling) | ⚠️ ≥19° raw, **≥2.5° with spline upsampling** |
| **Main sequence** | ❌ bent, non‑linearly — no constant factor fixes it | ❌ | ⚠️ defensible |
| Saccade **duration** | ❌ quantised 0/33/67 ms against a true 30–80 ms | ⚠️ biased short ~5 ms | ✓ |
| Saccade **latency**, per trial | ⚠️ ±16.7 ms quantisation (SD ≈ 9.6 ms) | ⚠️ ±8.3 ms | ✓ |
| Saccade latency, **trial‑averaged (≥30–65 trials)** | ✓ | ✓ | ✓ |
| Saccade **amplitude** | ✓ — it's a *spatial* measure, limited by your 3–4° gaze accuracy, **not** by frame rate | ✓ | ✓ |
| Saccade **direction (left/right)** | ✓ | ✓ | ✓ |
| **Microsaccades** (<1°, 20–25 ms) | ❌ | ❌ | ❌ — needs 240–500 Hz *and* sub‑degree precision |

(Mack, Belfanti & Schwarz, *Behav Res Methods* 49:2146–2162, 2017, Table 1. Their figures are a *best case*: noise‑free simulation with the true velocity peak forced onto a sample.)

Two important nuances that soften the pessimism:
- **Saccade detection degrades gracefully, it doesn't fail.** An empirical head‑mounted comparison against a 1000 Hz EyeLink found 60 Hz detected 56.1 ± 12.4 % of *reading* saccades vs 68.4 ± 13.9 % at 120 Hz, with duration biased short by −10.8 ms vs −4.9 ms (Leube, Rifai & Wahl, *JEMR* 10(3):3, 2017 — note this confounds rate with two different SMI devices). Reading saccades are 2–4°, i.e. the *worst case*. Your 10–20° stimulus‑driven prosaccades will be detected far more reliably.
- **Sub‑frame onset fitting works.** MIT's iPhone/iPad saccade‑latency work (Lai et al., ICIP 2018 / TBME 2022) fits a parametric saccade waveform and matches high‑speed‑camera latency distributions from a consumer front camera; a 2025 npj Parkinson's iPad study fits at 60 fps and upsamples to 1 kHz. Latency is degraded, not destroyed.

**Actionable:** run the webcam at **60 fps** if you can (many Mac webcams do 60 fps at 720p; MediaPipe keeps up). But **measure the actual inter‑frame timestamps** rather than trusting the requested frame rate — 60 fps is silently negotiated down all the time. And fix stimulus‑render→frame‑timestamp synchronisation at the same time; on this class of pipeline that jitter often exceeds the sampling quantisation.

---

### Q5. "Is the child looking at *this* spot?" — with what confidence?

Treat this as a **hypothesis test on a fixation, never on a frame.**

**Never emit a per‑frame gaze point as a clinical screen coordinate.** Per‑frame angular noise is `σ_θ ≈ σ_px / k` with `k = 0.45–0.70 px/deg`:

| σ_px (landmark jitter) | σ_θ per frame |
|---|---|
| 0.5 px | 0.7–1.1° |
| 1.0 px (realistic CNN jitter) | 1.5–2.2° |
| 2.0 px (compression, motion blur, bad light) | 3.0–4.4° |

**Procedure:**
1. Segment fixations with **I‑DT (dispersion), not I‑VT.** At 1.9° per‑frame noise and 30 fps, sample‑to‑sample velocity noise is ~80 °/s — far above standard I‑VT thresholds of 20–35 °/s, so vanilla I‑VT fires on noise continuously. Salvucci & Goldberg (ETRA 2000) themselves recommend I‑DT for noisy, low‑rate data.
2. Report the **fixation centroid** with an uncertainty. Averaging buys `√N` only on zero‑mean, temporally *independent* noise — and webcam landmark jitter is strongly autocorrelated (same pose, same lighting, codec‑stabilised blocks). A 300 ms fixation at 30 fps nominally gives 9 samples, but boundary frames are saccade‑contaminated, so usable N ≈ 5–7 and the realistic gain is **1.5–2×, not 3×**.
3. **Averaging does nothing for systematic error** — kappa, depth‑scale error, head‑pose bias, camera–screen extrinsics. Since published webcam error is bias‑dominated, cutting a 1.9° random term to ~1.0° moves a 3°‑bias system from ~3.6° to ~3.2° total: a **10–15 % gain, not a factor of 2–3.** The dominant lever is calibration/bias removal.
4. **The decision.** Model the fixation centroid as Gaussian with covariance `Σ = σ_sys² I + (σ_frame²/N_eff) I`, where `σ_sys` is measured from a held‑out validation grid *per session*. Then:
   ```
   d² = (p_fix − p_target)ᵀ Σ⁻¹ (p_fix − p_target)      # Mahalanobis
   "looking at it" if d² < χ²₂(0.95) = 5.99
   ```
   With σ_total = 3.5° at 60 cm (= 3.7 cm), a 95 % acceptance radius is **≈ 2.45σ = 9 cm**. **That is your real tolerance.** Design your stimuli around it.

**Design consequence:** targets must be **≥10–15° apart** (≥10–16 cm at 60 cm). A 3×3 region grid on a 27″ monitor (59.8 cm wide) is about the finest spatial resolution you can defend. Do **not** build any task that requires distinguishing adjacent 5 cm objects.

---

### Q6. Hardware limit or engineering failure? Where exactly is the ceiling?

**Engineering failure, with a hard hardware floor underneath it that you are nowhere near.**

The decisive evidence: **WebGazer.js — grayscale/geometric eye features → ridge regression on calibration points, architecturally the same family as your PolynomialFeatures→RidgeCV on iris offsets — measures at 4.17° / 169–187 px on a 1920×1200 display** (Papoutsaki, IJCAI 2016; independently ~15 % of screen in Semmelmann & Weigelt 2018). You are sitting on WebGazer's known ceiling. Meanwhile CNN‑based systems on the *same* sensor class sit 2–4× better (Labvanced 1.4°, Google 0.6–1.0° on a phone). **There is documented 2–4× headroom above where you are.**

But be precise about how that headroom was bought. It was **not** bought by the model alone. It was bought by a *combination* of:
- learned appearance models instead of hand‑crafted geometric features,
- far denser, **multi‑head‑pose** calibration (Labvanced: ~84 targets × 7 head poses, 5 minutes),
- enforced head‑pose stability (virtual chin rest),
- known camera intrinsics and camera–screen extrinsics,
- better cameras (1080p external, not 720p built‑in).

Anyone telling you "just swap in a CNN and you'll get 1.4°" is wrong.

**The hardware floor** — where you genuinely cannot go, ever, with one RGB webcam:
- **Spatial:** ~2–2.5° for a well‑engineered free‑head system without a chin rest; ~1.4° with a chin rest and heavy calibration. Sub‑1° needs IR + corneal reflections.
- **Temporal:** saccade peak velocity, the main sequence, and microsaccades are gone at 30–60 fps. Permanently.
- **Even IR isn't magic:** Guestrin & Eizenman prove that 1 camera + 1 glint works only with a near‑stationary head; 1 camera + ≥2 glints allows free head motion but requires a *multi‑point* per‑user calibration; only ≥2 cameras + ≥2 glints collapse calibration to a single point. **No hardware configuration removes the need for per‑user calibration** (kappa is unidentifiable from one eye without a known target). Your 9‑dot calibration is right *in principle*. The sample handling and the feature vector are what's wrong.

---

## 3. Diagnosis of *this* codebase, ranked by expected accuracy impact

I read the code at HEAD (`ca47269`). **One item in the brief is stale**, and I found one that isn't in the brief and that I believe is the actual root cause.

### 🔴 A. `StandardScaler` on near-zero-variance head-pose columns → degree-2 blow-up at test time
**`gaze_estimator.py:539–556`** — `StandardScaler().fit_transform(features_raw)` is applied to `[iris_x, iris_y, pitch, yaw]` *before* the degree‑2 polynomial expansion. If the child holds still during the 9‑dot calibration (which the protocol asks them to do), `std(yaw)` and `std(pitch)` are a few tenths of a degree — **mostly `solvePnP` landmark noise**. The scaler divides by that.

At inference, `_build_features` (line 426–441) applies the *same* `scaler.transform`. A real 12° head turn becomes a **~20–50 σ** input, and the degree‑2 expansion squares it (400–2500). The Ridge coefficients on those columns were fitted against noise over a ±2 σ range. The prediction diverges and gets clipped by `np.clip(gaze_x, 0, screen_width−1)`.

**Symptom this produces:** gaze pinned to a screen edge or wildly wrong the instant the head moves; accuracy that looks "randomly bad"; and — critically — **complete insensitivity to changes in the regressor, the polynomial degree, or the filter**, because the failure happens in the scaling, upstream of all of them.

**This is my primary hypothesis for "many algorithm changes produced no improvement at all."**

**Five-line diagnostic — run this first, before anything else:**
```python
# after finish_calibration()
print("scaler.scale_ =", est._scaler.scale_)   # [iris_x, iris_y, pitch, yaw]
print("scaler.mean_  =", est._scaler.mean_)
# then at test time, with the child's head turned ~12 deg:
z = est._scaler.transform([[ix, iy, pitch, yaw]])
print("z-scores:", z)          # if |z[0][3]| > ~4, this defect is live
```
If `scale_[2]` or `scale_[3]` is below ~1.0 (degrees), this defect is live.

**Fixes (any one works):** (a) scale head pose by a **fixed physical constant** (e.g. `/15.0` deg) rather than by the sample std; (b) clip z‑scores to ±3 at inference; (c) best — vary head pose deliberately during calibration (see D) so the std is real.
**Cost:** 1 hour. **Expected gain:** potentially the difference between "unusable when the head moves" and "works." Unquantifiable until measured, which is exactly why you should measure it first.

### 🔴 B. No depth, no eye 3-D position, no head translation — `tvec` is computed and discarded
**`eye_tracker.py:349–370`** — `solvePnP` returns `translation_vec`, which is used only to build `pose_mat` for `decomposeProjectionMatrix`, and then thrown away. `EyeData` carries no depth, no eye pixel position, no inter‑ocular width.

This is the structural defect from §Q2/Q3: the model is asked to invert a function of variables it cannot observe. **No regressor fixes this.**

Also, `MODEL_POINTS` (lines 83–89) are the classic OpenCV values (chin at `(0, −330, −65)`), which are **not metric** — a 330 mm chin‑to‑nose distance is absurd. So even if you kept `tvec`, its **scale is meaningless**. You must replace `MODEL_POINTS` with a real metric face model (MediaPipe ships `canonical_face_model.obj`, in cm) before `tvec` means anything.
**Cost:** 1–2 days. **Expected gain:** 1–2°, and it is a *precondition* for the ray‑plane chain in Q3.

### 🟠 C. `solvePnP` on assumed intrinsics + deformable landmarks
**`eye_tracker.py:190–192`:** `hfov_rad = np.radians(62)` — hard‑coded. If the real FOV is 78°, `f_px` is off by 35 %, and every `solvePnP` angle and depth inherits that.
**`eye_tracker.py:78`:** `POSE_LANDMARKS = [1, 152, 33, 263, 61, 291]` — nose tip, **chin**, eye corners, **mouth corners ×2**. Half of these deform with expression. A child smiling or talking changes your "head pose."
**Fix:** (a) one‑time OpenCV chessboard intrinsic calibration per camera, stored in `config.json`; (b) restrict `POSE_LANDMARKS` to rigid points — nose bridge (168), nose tip (1), outer canthi (33, 263), and optionally the nasion. Drop chin and mouth entirely.
**Cost:** half a day. **Expected gain:** 0.5–1.5°, plus a large reduction in frame‑to‑frame head‑pose jitter (which is currently *also* what's poisoning defect A's scaler).

### 🟠 D. Only 9 distinct design points; head pose never varies; grouped CV leak
The brief says "the 10 samples/dot are collapsed to 1." **That is stale.** Commit `ca47269` fixed it: `finish_calibration` (lines 494–530) now trains on every raw sample (`point.samples`), builds `_cv_groups` for leave‑one‑point‑out CV, and the code comment states the rationale. Formal rank deficiency is gone (rank 9 → 15).

But **90 rows is not 10× the information**: the 81 extra rows are within‑dot repeats whose feature variation is measurement noise. `y` still has only **9 distinct values**. Effective sample size is still 9 gaze conditions. And RidgeCV responds to the extra rows by dropping alpha (10 → 0.1) and inflating train R², which is partly noise‑fitting.

Two live sub‑defects:
- **`RidgeCV(alphas=[...])` is called with `cv=None`** (lines 565–569), which sklearn implements as per‑*sample* LOO/GCV. Samples within a dot are ~33 ms apart with the same target — so **alpha selection leaks dot identity** and is scored on interpolation‑within‑a‑fixation. Fix: `cv=list(LeaveOneGroupOut().split(X, y, groups=self._cv_groups))`.
- **Head pose is near‑constant during calibration**, so the `pitch`/`yaw` coefficients and all their cross‑terms (`iris_x·yaw`, `iris_y·pitch` — your *only* head‑compensation mechanism in the calibrated path) are unidentifiable, determined entirely by ridge's shrinkage prior. **Fix the protocol:** run the 9 (or 13) dots at **3 head poses** — straight, ~±15° yaw, ~±10° pitch, child still fixating the same dot — giving 27–39 dot×pose cells. This both fills the design and makes the yaw/pitch coefficients real. It also fixes defect A for free.
**Cost:** 1 day (protocol + UI). **Expected gain:** 0.5–1.5°, plus it makes every subsequent change *measurable*, which is the real prize.

Caveat on the Cerrolaza citation you may have seen: their >400,000‑model polynomial search found high‑order (3rd–5th) expressions "little better or even worse" than the conventional **2nd‑order** baseline — that argues against degree ≥3, **not** against degree 2, and it certainly does not license dropping your `iris × head_pose` cross terms. Their subjects were also on a **chin rest**, and their "head movement" was ±5 cm of *depth translation only* — no rotation ever. Their actual lesson: head‑movement tolerance came from **normalizing the input features**, not from richer polynomials. Which is exactly recommendation B.

### 🟡 E. Head roll is never removed
`_calculate_iris_position_in_eye` (`eye_tracker.py:250–268`) computes `iris_offset_x/y` in **raw image axes** while dividing by the corner‑to‑corner Euclidean `eye_width`. Head roll rotates the eye‑corner axis in the image, so roll leaks directly into *both* x and y offsets. Zhang/Sugano/Bulling (ETRA 2018) call out roll removal as a design choice that matters.
**Fix:** project the iris offset onto the eye‑corner axis frame (unit vector along inner→outer canthus and its perpendicular) before normalizing. **~20 lines.**
**Cost:** 2 hours. **Expected gain:** 0.2–0.5°, more if the child tilts their head (children tilt their heads).

### 🟡 F. You are tracking the PUPIL centre, not the IRIS centre
`_get_iris_center` (`eye_tracker.py:200–215`) returns `landmarks[iris_indices[0]]` = **landmark 468 / 473**. Google's own paper (Ablavatski et al. 2020) states the network predicts "pupil center, 4 points of outer iris circle, and 16 points of eye contour." **468 is the pupil centre.** Only 469–472 / 474–477 are the limbus.

The pupil centre migrates **temporally by 0.13 ± 0.07 mm** as the pupil dilates (mesopic 6.37 mm → photopic 4.06 mm; Yang, Thompson & Burns, *IOVS* 2002, n=130 eyes). At a ~10.5 mm lever arm that's **~0.7° of systematic gaze bias**, with a per‑subject tail to 1.5–3° (15 % of eyes exceeded 0.25 mm; one reached ~0.6 mm), and empirical pupil‑size artefact on real video trackers reaches **2.5°** (occasionally ~5°). If room brightness differs between calibration and task — which it will, because your stimuli change the screen luminance — you get this bias for free.
**Fix:** fit a circle/ellipse to landmarks 469–472 / 474–477 and use *its* centre. Also note the `z` coordinates of 468–477 are **synthetic** (set to the mean z of the eye corners) and carry **no depth information** — do not use them.
**Cost:** 1 hour. **Expected gain:** 0.5–1°, and it removes a lighting‑dependent bias that will otherwise contaminate every session comparison.

### 🟢 G. `_pitch_factor` / `_yaw_factor` are dead code in the calibrated path
Confirmed: `_learn_head_compensation` (lines 443–478) fits them and stores them in the profile, but `estimate_gaze` (lines 584–646) never uses them — they are applied **only** in `_estimate_gaze_uncalibrated` (lines 716–717).

**This is not a bug you should "fix" by applying them.** The polynomial already contains the `iris × yaw` cross terms, and `_learn_head_compensation` fits its factors on the *residuals of that model* — applying them in the calibrated path would **double‑count**. Furthermore, the `std > 0.1°` gate means that with a still head they're fitted to landmark noise, and otherwise fall back to the hard‑coded 15.0 / 20.0 px/deg.

**Recommendation: delete `_learn_head_compensation` and the two factors entirely** once you adopt the geometric/normalized pipeline. Right now they are confusing dead weight that makes the code look like it does head compensation when it doesn't.
**Cost:** 30 minutes. **Expected gain:** 0° accuracy, meaningful clarity.

### Ranked fix order

| # | Defect | Cost | Expected gain |
|---|---|---|---|
| 1 | **A** — StandardScaler / head-pose blow-up | 1 h | Possibly the whole plateau. **Diagnose first.** |
| 2 | **D** — pose-varied calibration + grouped CV for alpha | 1 d | 0.5–1.5° + makes everything else measurable |
| 3 | **C** — real intrinsics + rigid-only `POSE_LANDMARKS` | 0.5 d | 0.5–1.5° |
| 4 | **B** — metric face model, keep `tvec`, add depth/eye-position features | 1–2 d | 1–2°, unlocks Q1/Q3 |
| 5 | **F** — iris circle, not landmark 468 | 1 h | 0.5–1° |
| 6 | **E** — roll removal | 2 h | 0.2–0.5° |
| 7 | **G** — delete dead head-compensation | 0.5 h | clarity |

---

## 4. Recommended architecture

**Do not throw away the app. Replace the *gaze mapping layer*, keep everything else.**

```
Webcam (1080p, 60 fps if available)
  │
  ├─► [ONE-TIME] OpenCV chessboard → K (fx, fy, cx, cy), dist_coeffs   ← per device, config.json
  ├─► [ONE-TIME] Screen pose (R_s, t_s) → constant for MacBook/Studio Display;
  │              measured/mirror-calibrated for clip-on webcams
  │
  ├─► MediaPipe FaceLandmarker (Apache-2.0)  ← KEEP. 478 landmarks, GPU delegate on macOS.
  │      ├─ rigid landmarks → solvePnP(metric canonical_face_model) → R_head, t_head
  │      └─ iris ellipse (469-472 / 474-477) → iris_px, iris centre
  │
  ├─► Sugano/Zhang NORMALIZATION → virtual camera on the eye→camera axis,
  │      fixed distance, roll removed → normalized eye/face crop + R_norm
  │
  ├─► Appearance CNN → gaze vector in normalized space
  │      └─ de-normalize: d_cam = R_norm⁻¹ · d_norm
  │
  ├─► PER-USER CALIBRATION (9–13 dots × 3 head poses)
  │      └─ small correction in GAZE-ANGLE space: 2-param kappa offset + 2-param gain
  │         (NOT a 15-term polynomial in screen space)
  │
  ├─► Ray-plane intersection (o = eye centre in camera coords, metric) → screen mm → px
  │
  └─► I-DT fixation segmentation → fixation centroids + covariance
         (NEVER emit a per-frame screen coordinate)
```

### Model choices, with licenses — and the licensing problem is real

| Option | License | Accuracy | Apple Silicon | Verdict |
|---|---|---|---|---|
| **MediaPipe FaceLandmarker** | Apache‑2.0 | n/a (landmarks) | ✅ GPU delegate, real‑time | **Keep.** Best-in-class free face/iris landmarker. |
| **ETH‑XGaze ResNet‑50** (`xucong-zhang/ETH-XGaze`) | Code permissive; **dataset & weights are research‑only** | 4.50° within‑dataset; best cross‑dataset generalizer (Gaze4HRI: ETH‑trained models generalize far better than Gaze360‑trained) | ✅ PyTorch MPS; ResNet‑50 @224² runs 30–60 fps on M‑series | **Best technical choice. ⚠️ Non‑commercial weights — blocking issue for a clinical product.** |
| **L2CS‑Net** | Code **MIT**; Gaze360 weights non‑commercial | 3.92° MPIIFaceGaze; **degrades badly cross‑domain** (17.6–19.6° in Gaze4HRI) | ✅ | Code is clean, weights are the problem, generalization is poor. |
| **pperle/gaze-tracking-pipeline** | **MIT** | — | ✅ | **Use as the reference implementation** for normalization + ray‑plane. Note: ships with a `# TODO load calibrated screen position`, a hard‑coded 20 mm offset, and an x‑flip. |
| **OpenFace 2.0** | Non‑commercial; commercial license reportedly **$10k–$18k/yr** (secondary source, may be stale) | 9.1° cross‑dataset; arm64 build broken (issue #1003, gfortran/OpenBLAS) | ❌ | **Reject.** License, platform, and accuracy all fail. |
| **OpenFace 3.0** (CMU, arXiv 2506.02891, 2025) | PyTorch rewrite, active | 2.56° MPIIGaze *within‑dataset* | ✅ MPS | Worth evaluating; check its license before committing. |
| **Purely geometric 3‑D eye model** (§Q2) | Yours | 3.5–5° with per‑person calibration | ✅ trivially | **The pragmatic answer.** No license risk. |

**The licensing recommendation, stated plainly:** every high‑accuracy pretrained gaze model in the literature is trained on a research‑only dataset (ETH‑XGaze, Gaze360, MPIIGaze, GazeCapture). **If EyeExam is going to be a commercial clinical product, you cannot ship those weights.** Your options are (a) train your own on data you own or license, (b) negotiate a commercial license with ETH Zürich, or (c) **build the geometric 3‑D eye‑model pipeline (§Q2), which has no license encumbrance and lands at 3.5–5°** — right where I told you to target in §1. **I recommend (c) for v1, with (a) as the medium‑term play** — and note that if you're going to collect child data anyway for a normative database, you are collecting the training set at the same time.

### Why this design on macOS

- MediaPipe Tasks runs the GPU delegate natively; Apple Silicon handles 1080p @ 60 fps landmarking comfortably.
- The CNN (if you use one) at 224×224 runs on **MPS** in PyTorch, or convert to **CoreML** via `coremltools` for the ANE — a ResNet‑50 on the ANE is single‑digit milliseconds.
- The geometric path is pure NumPy/OpenCV and costs nothing.
- The 30–60 fps budget is not the constraint. **Accuracy is.**

### The calibration protocol you should ship

Not 9 dots × 10 samples in one head pose. Ship:
- **13 dots** (9 grid + 4 mid‑edge) × **3 head poses** (straight, ±15° yaw, ±10° pitch) × 20–30 frames each.
- A **virtual chin rest**: pause and give feedback when the head leaves the acceptable range (this is Labvanced's key trick, and it's free).
- **Accept/reject gate**: recompute leave‑one‑*dot*‑out error; refuse to proceed if held‑out error exceeds ~7 % of screen width (Labvanced's threshold).
- **Re‑validate every 6–7 trials** with a 5‑point check (~15 s) — head drift is real, and children drift.
- FAZE's curve is nearly flat after ~9–20 calibration *points*, so don't gold‑plate beyond that — but the **head‑pose spread is not optional**.

Expect the calibration to take **2–4 minutes**. With children, budget for the fact that a meaningful fraction won't complete it — see §6.

---

## 5. Reframe the product: what you can and cannot measure

### The single most important reframing

**The largest oculomotor effects in ADHD are event‑COUNT and CATEGORICAL measures, not gaze‑position‑accuracy measures.** From the definitive meta‑analysis (Chamorro, Betz, Philipsen, Kambeitz & Ettinger, *Biol Psychiatry CNNI* 2022 — 31 studies, N = 1,567):

| Measure | Hedges *g* (ADHD vs control) | Webcam‑compatible at 3–4°? |
|---|---|---|
| Prolonged‑fixation **intrusive saccades** | **1.11** (large) | ❌ **No** — an intrusion is a 1–2° deviation from a central point. 3–4° error + 30 Hz cannot separate it from tracker noise. |
| Memory‑guided **anticipatory saccades** | **0.86** (large) | ❌ **No** — it's a *timing* measure (onset relative to a go signal). Needs the temporal resolution you don't have. |
| **Antisaccade DIRECTION errors** | **0.57** (moderate) | ✅ **Yes** — a categorical left/right judgment. Tolerates 3–4° if targets are ≥10–15° from a central fixation. **Independently validated on consumer webcams.** |
| Visually‑guided saccade **variability** | 0.53 | ⚠️ Spatial; marginal |
| Antisaccade **reaction time** | 0.34 (small) | ⚠️ Trial‑averaged only |

Maron et al. (*Neurosci Biobehav Rev* 2021) independently found more intrusive saccades and impaired antisaccades in ADHD, but **no group difference on reflexive prosaccades** and no pursuit deficit.

**Be blunt about the implication:** the two *biggest* effects are the two you cannot measure. **Your strongest webcam‑compatible marker is the antisaccade direction‑error rate at g ≈ 0.57 — moderate, not large.** Any product plan built on the g = 1.11 number is building on sand. Those effect sizes were all obtained on 250–1000 Hz research trackers under chin rests, and measurement noise *attenuates* effect sizes. **No meta‑analytic webcam effect sizes exist for any of these measures.**

### Build the product on these ✅

1. **Antisaccade task** — targets at the screen's left/right edges (≥15° eccentricity), fixation cross at centre. Outcome: **direction‑error rate**. This is your flagship measure.
2. **AOI dwell proportions** — "% of task time looking at the task region vs. elsewhere." A 3×3 region grid is your resolution limit. Google replicated reading comprehension this way: 62.3 % relevant‑passage dwell on correct trials vs 42.0 % on incorrect (Valliappan, *Nat Commun* 2020).
3. **Gaze‑away count / off‑task episodes** — count fixations landing outside the task AOI, with a generous (≥10°) threshold. This is the cleanest "distractibility" proxy your hardware supports.
4. **Fixation counts** (not durations) — relatively robust at low sampling rates.
5. **Trial‑averaged prosaccade latency** over ≥30–65 trials with a stated CI. Google matched the literature (210 ms mean) this way at 30 Hz. **Never report a per‑trial latency as a clinical value.**
6. **Smooth pursuit tracking error** (coarse) — Google got 0.39 cm pursuit error at 30 Hz on a phone. Directionally usable; don't over‑claim.
7. **Object‑level gaze heatmaps / scanpaths** — Google reported r = 0.90 object‑level correlation with a desktop tracker (r = 0.74 pixel‑level). **Report at the object level, not the pixel level.**

### Do NOT build the product on these ❌

- **Microsaccades.** Needs 240–500 Hz *and* sub‑degree precision. Not happening.
- **Saccade peak velocity / the main sequence.** Not recoverable at 30 or 50 Hz at *any* amplitude ≤60°; at 60 Hz only ≥55°. Even spline upsampling only helps from 120 Hz. **If any current EyeExam screen shows a peak velocity in °/s, delete it — it is a fabricated number.**
- **Per‑trial saccade latency or duration in milliseconds.** Quantised to 0/33/67 ms.
- **Absolute fixation durations** as clinical values (±17 ms on a 200–300 ms fixation, plus systematic short bias). Group/condition *comparisons* are fine; absolute values are not.
- **Intrusive saccades during prolonged fixation** — the g = 1.11 measure — **as classically defined.** You would need to redesign it as a fixation‑with‑peripheral‑distractor variant, and then it is a *different* measure with an *unknown* effect size.
- **Nystagmus / fine oculomotor pathology.** Different product.

### The realistic screening ceiling

Yoo et al. (2024, *Front. Psychiatry* 15:1337595) — the closest existing thing to what you're building — used a **tablet RGB front camera, no IR, no chin rest** (VisualCamp SeeSo SDK, vendor‑claimed ~1.7°) on 135 children (56 ADHD / 79 TD, mean age ~8.4). Eye‑tracking features alone: **AUC 0.724, accuracy 76.3 %, sensitivity 0.725**. Adding ATA + Stroop raised AUC to 0.838.

**Read the fine print, because it is the most important operational number in this entire report:**
- Those are **cross‑validated** figures with feature selection and **no held‑out test set** → likely optimistic. Majority‑class baseline was 58.5 %.
- **250 children were recruited; 115 were dropped — 99 of them for outright eye‑tracking failure.** **Roughly 40 % of children could not produce usable RGB gaze data.**
- The ADHD group was ~80 % male vs ~42 % in TD — a possible confound.
- The claimed "eye tracking alone ≈ eye tracking + ATA + Stroop" equivalence rests on a **Wilcoxon rank‑sum test on CV AUCs across different subsamples** (n = 135 vs n = 73), not a DeLong test. That null result is underpowered and proves nothing.

**AUC 0.72 is screening, not diagnosis.** At a ~7 % population base rate it produces a lot of false positives. And **the ~40 % data‑failure rate in children is the number that will kill the product**, not the accuracy. Design the UX around it: real‑time face/iris quality feedback, a gamified re‑engagement loop, and an explicit "could not assess" outcome that is not a failure state for the child.

---

## 6. Honest risk section

### Does oculomotor training actually improve attention?

**I have to be blunt: the evidence pack contains *zero* verified evidence that eye‑movement training improves attention or concentration in children.** Every finding above concerns *measurement*, not *intervention*. That is not an accident of the search — it reflects a genuinely thin and contested literature. The broader clinical consensus (AAP/AAO/AAPOS joint statements on vision therapy) has been consistently skeptical of vision‑training claims for learning and attention disorders.

**Recommendation:** do not ship therapeutic claims. Position the training exercises as **engagement/gamification that keeps the child performing the assessment tasks**, or run your own pre/post study before claiming anything. If a stakeholder asks "does the training work?", the honest answer today is **"we don't know, and neither does anyone else."** Saying so now is far cheaper than saying it to a regulator later.

### The regulatory line around "help diagnose"

**"Help diagnose ADHD" is a medical‑device claim.** In the US that is FDA territory (an ADHD diagnostic aid would be a Class II device requiring 510(k) or De Novo — there is precedent: EndeavorRx, NEBA). In the EU it is MDR, likely Class IIa. In China it is NMPA. The moment your marketing, your UI, or your PDF report says "diagnose," "ADHD indicator," "clinical assessment," or shows a red/green pass‑fail against a normative database, **you are a regulated medical device.**

Note that your repo already contains `normative_data.py`, `pdf_report.py`, and pass/fail screening — **you have already built the regulated surface.** That is a decision that was made without being made.

**Safe positioning for v1:**
- **"Research instrument"** / **"attention training game"** / **"gaze‑based engagement measure."**
- No diagnostic labels. No "ADHD risk score." No pass/fail against a clinical threshold.
- If you produce a report, it goes **to a clinician as an input**, framed as raw behavioural data, not as an assessment.
- Get regulatory counsel **before** the first clinical pilot, not after.

**Also, PHI:** you already encrypt patient data at rest (commit `50c6612`). Good. But if you are recording **children's faces**, you are in COPPA / GDPR‑Article‑9 (biometric) territory. Confirm you never persist raw video, only derived landmarks — and if you *do* need video for model training, that is an explicit, separately‑consented data collection, not a side effect of the app.

---

## 7. Prioritized action plan

Each step has an expected gain. **Measure after every step** — you have been flying blind, and the first four items exist mostly to make measurement possible.

### Phase 0 — Instrumentation (do this before touching any algorithm). 1–2 days.

| Step | Action | Gain |
|---|---|---|
| 0.1 | **Print `scaler.scale_` after calibration.** If `scale_[2]` or `scale_[3]` < ~1.0, defect A is live and is your root cause. | Diagnosis |
| 0.2 | Build a **held‑out validation grid** (13 fresh targets, never used in calibration) and report error in **degrees**, per target, per session. Right now you cannot tell whether any change helped. | Diagnosis |
| 0.3 | Run the three **falsification tests**: (a) fixate a dot, slide head 5 cm laterally — measure the drift; (b) fixate a dot, turn head ±15° — measure the drift; (c) depth sweep, calibrate at 60 cm, validate at 45/60/75 cm. | Quantifies B and A |

### Phase 1 — Free wins. 2–3 days.

| Step | Action | Expected gain |
|---|---|---|
| 1.1 | **Fix defect A**: scale head pose by a fixed constant (÷15°), not by sample std. Clip z‑scores to ±3. | **Potentially the entire plateau.** |
| 1.2 | **Pose‑varied calibration**: 13 dots × 3 head poses, with a virtual chin rest and a leave‑one‑*dot*‑out accept gate at 7 % of screen width. | 0.5–1.5° |
| 1.3 | Pass `cv=LeaveOneGroupOut(groups=_cv_groups)` to `RidgeCV`. Stops alpha selection from leaking dot identity. | Honest metrics |
| 1.4 | **Iris circle from 469–472 / 474–477**, not landmark 468 (which is the *pupil* centre). | 0.5–1° |
| 1.5 | **Roll removal**: compute iris offset in the eye‑corner axis frame. | 0.2–0.5° |
| 1.6 | Delete `_learn_head_compensation`, `_pitch_factor`, `_yaw_factor`. | Clarity |
| 1.7 | **Delete every peak‑velocity / main‑sequence readout in the UI.** They are not measurable. | Integrity |

**Expected state after Phase 1: ~3–5°, and — crucially — a working measurement harness.**

### Phase 2 — Fix the geometry. 1 week.

| Step | Action | Expected gain |
|---|---|---|
| 2.1 | **OpenCV chessboard intrinsic calibration** per device → real `K`. Removes the single largest error term in depth and head pose. | 0.5–1.5° |
| 2.2 | Replace `MODEL_POINTS` with MediaPipe's **metric** `canonical_face_model`; restrict `POSE_LANDMARKS` to **rigid** points (nose bridge, nose tip, outer canthi). Drop chin and mouth. | 0.5–1° + big jitter reduction |
| 2.3 | **Keep `tvec`.** Add `[eye_u, eye_v, iris_px, interocular_px, Z_est]` to `EyeData`. Depth from `Z = f_px · 11.7 / iris_px`. | 1–2° |
| 2.4 | **3‑D eye model + gaze normalization** (§Q2), producing `g_head` and `g_cam`. Run the VOR falsification test. | Structural |
| 2.5 | **Camera→screen extrinsics** — constant for MacBook / Studio Display, measured for clip‑ons. Ray‑plane intersection (§Q3). | Structural |
| 2.6 | Replace the 15‑term screen‑space polynomial with a **4‑parameter correction in gaze‑angle space** (2‑param kappa offset + 2‑param gain). It is what the physics says you need, and it is identifiable from 9 points. | Robustness |

**Expected state after Phase 2: ~3–4°, ≈3.1–4.2 cm at 60 cm, with graceful degradation under head movement rather than catastrophic failure.**

### Phase 3 — Output layer & product. 1 week.

| Step | Action | Expected gain |
|---|---|---|
| 3.1 | **I‑DT fixation segmentation** (not I‑VT — at 30 fps your velocity noise is ~80 °/s, far above any sane I‑VT threshold). Emit fixation centroids with a covariance. **Never emit a per‑frame screen coordinate.** | 10–15 % + honest uncertainty |
| 3.2 | **Mahalanobis "is the child looking at target X?"** test with a per‑session σ from the validation grid. | Confidence |
| 3.3 | **Re‑scope the task battery**: antisaccade (direction errors, targets ≥15° eccentric) as the flagship; AOI dwell; gaze‑away counts; trial‑averaged prosaccade latency over ≥30 trials. | Product validity |
| 3.4 | **Try 60 fps** — but *measure the actual inter‑frame timestamps*, don't trust the constraint. Fix stimulus‑render→frame‑timestamp sync at the same time. | Latency: ±17 ms → ±8 ms |
| 3.5 | **Data‑quality UX**: real‑time face/iris quality feedback + an explicit "could not assess" outcome. **~40 % of children failed to yield usable RGB gaze data in the closest published study — this is the biggest product risk, not accuracy.** | Ship‑or‑die |

### Phase 4 — Optional, only if Phase 2 lands short of 3°.

| Step | Action | Expected gain |
|---|---|---|
| 4.1 | Swap the geometric gaze estimator for an **ETH‑XGaze‑normalized CNN** (PyTorch MPS / CoreML), keeping the same normalization and calibration layers. | 0.5–1° |
| 4.2 | **Resolve the license.** ETH‑XGaze / Gaze360 / MPIIGaze / GazeCapture weights are all research‑only. Either license commercially, or train on your own child data — which you will be collecting anyway for the normative database. | Legal |

---

## Closing: the one‑sentence answer

**Your webcam is not the problem — a well‑engineered single‑RGB pipeline reaches 2.5–4° (2.6–4.2 cm at 60 cm), and you are stuck at WebGazer's 4–5° ceiling because your head‑pose features are being z‑scored against calibration noise and then squared, and because the feature vector physically does not contain the depth and eye‑position information a screen‑gaze projection requires — but even after you fix all of it, saccade velocity, the main sequence, and microsaccades stay permanently out of reach at 30–60 fps, so build the product on antisaccade direction errors, AOI dwell, and off‑task gaze counts, and call it a screening/training tool rather than a diagnostic.**

---

## Verification against this codebase (2026-07-14)

The report's primary root-cause claim (defect A) was tested directly against `src/gaze_estimator.py`,
not taken on faith. Findings:

**Confirmed.** With the current head-still calibration protocol, `StandardScaler` fits the head-pose
columns against calibration-time noise: measured `scaler.scale_[yaw] = 0.28 degrees`. The yaw
coefficient is therefore unidentifiable, and the model learns no head compensation at all.

Measured gaze error while the subject fixates screen centre and turns their head (synthetic forward
model, 9-dot calibration):

| head yaw | still-head calibration (today) | pose-varied calibration (fix) |
|---|---|---|
| 0 deg  | 0.4 deg  | 0.2 deg |
| 5 deg  | **22.4 deg** | 0.2 deg |
| 12 deg | 31.5 deg (pinned to screen edge) | 0.3 deg |
| 20 deg | 31.5 deg (pinned to screen edge) | 0.6 deg |

A 5-degree head turn destroys the estimate. A child cannot hold their head to 5 degrees.

**One correction to the report.** It predicted a *numerical* blow-up (39-sigma inputs squared by the
degree-2 expansion). The z-scores do explode exactly as described, but RidgeCV shrinks those
coefficients to near-zero, so nothing diverges numerically. The model instead silently performs *no*
head compensation and saturates against the screen-edge clamp. Same fix, different mechanism: the
cure is varying head pose during calibration so the coefficient becomes identifiable.

**Also confirmed:** `saccade_test.py:488` emits `Mean Peak Velocity: X deg/s` into a clinical report.
Per section 2/Q4 this quantity is not recoverable at 30-60 fps and should be removed.
