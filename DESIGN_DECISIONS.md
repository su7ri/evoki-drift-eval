# Design decisions and definitions

All results produced with these definitions are from simulated data. See `NOTE.md`.

## 1. Detector specification (from the Swift code)

File references are file name and line number at app commit
`f389fc6383ae6416a84afea227639b4faa6f8dbb`.

**Inputs**
- The caller fetches the last 14 check-ins. There is one check-in per date (the latest edit wins),
  sorted by date string. Nothing runs with fewer than 3 (`HomeViewModel.swift:258-259`,
  `InMemoryRepositories.swift:36-43, 67-70`).
- Signals and normalisation (`ClinicalScoreSupport.swift:4-31`):

| Signal | Scale in the UI | Normalised |
|---|---|---|
| sleep | 1-5 (`EvokiComponents.swift:195-197`) | (x − 1) / 4 |
| mood | 1-5 (`CheckInView.swift:286`) | (x − 1) / 4 |
| social | 0-2 (`CheckInView.swift:333`) | x / 2 |

  Out-of-range values are clamped. Energy, forgetting and HealthKit fields are not used.

**Windows** (`DriftDetection.swift:6-8`): `recent` = last 7 check-ins; `previous` = up to 7
check-ins before them. Windows are counted in check-ins, not calendar days.

**Threshold** (`DriftDetection.swift:66-86`): per domain, `delta = mean(recent) − mean(previous)`
on normalised scores.
- `delta <= −0.25` → negative alert. Severity is HIGH if `delta <= −0.38` and confidence is
  `strong`; otherwise MEDIUM.
- `delta >= 0.25` → positive alert, severity LOW.

**Minimum data**
- `recent.count >= 4` (`DriftDetection.swift:10`).
- No domain alert if `previous` is empty (`DriftDetection.swift:62`).

**Confidence and gating** (`ClinicalScoreSupport.swift:20-25, 39-41`; `DriftDetection.swift:63-64`)
- `c = min(recent.count, previous.count)`: c ≥ 6 → `strong`; c ≥ 4 → `moderate`; else `low`.
- `low` blocks domain alerts. This only matters when `previous` has 1-3 check-ins (8-10 in total).
- Confidence is a three-level label based on data quantity only; it is not a probability.

**Other alerts**
- Adherence alert (`DriftDetection.swift:35-43`): unreachable. It needs `count >= 4` and `count ≤ 3`.
- Combined positive alert (`DriftDetection.swift:45-54, 90-107`): fires when at least 2 domains
  improve by more than 0.18.

**Runtime behaviour**
- The detector runs on every home-screen load and after each check-in
  (`HomeViewModel.swift:55, 127, 196`).
- Each run saves new alerts with new IDs; there is no de-duplication
  (`InMemoryRepositories.swift:490-492`).
- The AI narrative replaces only the text.

## 2. Port

- `detector.py` mirrors the Swift code line by line.
  - Sums use a plain left-to-right loop, like Swift's `reduce`.
  - The adherence rate uses 32-bit float, like Swift's `Float`.
- 15 hand-checked cases (`test_detector.py`).
- 7 results (cases 1, 3, 4, 6, 7 gated, 8) were checked against the original Swift files compiled
  with `swiftc`; all matched.

## 3. What is scored

- Only negative domain alerts (MEDIUM or HIGH). Positive and combined positive alerts are ignored.
- The adherence alert is ported exactly; it never fires.
- The no-de-duplication behaviour is not simulated; it is reported as a code finding.

## 4. Detector variants

| Variant | Definition |
|---|---|
| `count_gated` | current app behaviour |
| `count_ungated` | `hasEnoughDataForAlert` always true; nothing else changed |
| `calendar_gated` | on day T: recent = check-ins dated T−6…T, previous = T−13…T−7; all thresholds, minimum rules, confidence and severity rules unchanged |
| `calendar_ungated` | calendar windows, no gating |

The calendar variants are for evaluation only and are not app behaviour.

## 5. Simulator

- Groups are behaviour types, not demographics: stable, high_variability, sparse (about 60% of
  days missing), low_baseline (floor effect). 500 users each, 90 days.
- Latent score = baseline + AR(1) noise (φ = 0.3) − change. Rounded half-up and clamped to the
  real scales.
- Social's baseline, noise and change are scaled by 0.5, so the latent normalised effect equals
  sleep and mood. Results are also reported per domain.
- Domains are independent. Each day independently has a check-in or not.
- 50% of users have one decline in one random domain.
  - Onset: day 40-60.
  - Shape: step, or gradual (linear ramp, full size on day onset + 13).
  - Size: 0.5, 1, 1.5 or 2 points (1-5 scale).
- Fixed seeds: master seed 20261006, one random stream per user. The grid uses seed 20261007.
- The detector runs once per day, right after that day's check-in; there is no run on days
  without one.

## 6. Metric definitions

- **Episode:** consecutive firing runs (any domain, or per domain). A day without a check-in does
  not split an episode. Primary unit for alarms; alarm-days are also reported.
- **False alarms per user-month:** no-change users, episodes starting on day ≥ 14, over 76/30
  user-months. Days 0-13 are excluded from both numerator and denominator.
- **Full-change day:** step → onset; gradual → onset + 13.
- **TP window, primary:** [onset, full-change day + W − 1], with W = 14. Sensitivity at W = 7 and 21.
- **TP window, previous definition (sensitivity analysis):** [full-change day,
  full-change day + W − 1]. This was the first primary definition. It was replaced after the first
  results showed that alarms during a gradual ramp were counted as misses. For step changes, the
  two definitions are identical.
- **Detected:** an any-domain episode starts in the window. **Domain-correct:** an episode of the
  changed domain starts in the window. **Delay:** episode start minus onset.
- **Chance:** no-change users get a pseudo onset and shape, drawn like real changes (seeded from
  the user id). The same window rule is applied, with the same definition and W, so the window has
  the same length.
- **Precision by confidence:** among episodes starting on day ≥ 14 in all users, correct = starts
  in a changed user's 14-day TP window; all others are incorrect. Grouped by the confidence label
  of the episode's first alert. Depends on the 50% prevalence of changed users. Rows with fewer
  than 100 episodes are marked as too few to conclude. Not a calibration analysis.
- **Worst group:** the group with the highest false-alarm rate and the group with the lowest
  detection rate, per variant.

## 7. Intervals

- 95% Wilson intervals for proportions.
- 95% percentile bootstrap over users (2000 resamples, seed 7) for false-alarm rates and median
  delay.
- Wilson intervals for precision ignore clustering within users.

## 8. Noise × check-in-rate grid

- Noise SD 0.3-1.2 (7 levels) × check-in rate 0.3-1.0 (8 levels). 200 users per cell, baseline
  N(3.5, 0.5).
- The same per-user random streams are used in every cell.
- Variants: `count_gated` and `calendar_gated`. Reported: false alarms, detection and chance
  (primary definition).

## 9. Variability-scaled threshold and tuned global control (evaluation only)

- **Variability-scaled:** same as `count_gated` except the domain threshold: `max(FLOOR, K × sd)`, where
  sd is the sample SD (ddof = 1) of the user's normalised scores over up to 28 check-ins before the
  recent window. The fixed 0.25 is used if there are fewer than 4. Needs up to 35 past check-ins;
  the app fetches 14.
- **Tuned global (control):** same as `count_gated` with one constant threshold T for every user
  and domain. Needs no extra history.
- **Grids:**
  - Variability-scaled: K ∈ {0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3} × FLOOR ∈ {0.125, 0.1875, 0.25}.
  - Global: T = 0.10 to 0.40 in steps of 0.0125.
- **Users:** tuning users seed 1, 150 per group; held-out users seed 2, 500 per group, never used
  for tuning. Both are separate from the main seed 20261006. All three rules (current, tuned
  global, variability-scaled) are evaluated on the same held-out users.
- **Objective** (same for both, fixed before tuning): mean over the four groups of
  (detection − chance), primary definition, W = 14.
  - Ties, variability-scaled: the smaller K, then the larger FLOOR.
  - Ties, global: the larger T.
- **Chosen:** K = 1.25, FLOOR = 0.1875; T = 0.2375.
- **Comparison:** paired differences in the held-out objective, with a 95% paired bootstrap
  (users resampled within each group, separately for changed and no-change users, identically
  for both rules; 2000 resamples, seed 7).
