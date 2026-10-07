# drift-eval: simulated evaluation of Evoki's drift detector

> **Read first:** every number in this repository comes from **simulated users** and depends on the
> simulator's assumptions. It is **not clinical validation** and uses **no real user data**.
> See [`NOTE.md`](NOTE.md).

- App commit evaluated: `f389fc6383ae6416a84afea227639b4faa6f8dbb`
- No app code was modified, and no app source files are included in this repository.

## What was tested

The negative domain alerts (MEDIUM or HIGH) of `DriftDetection.detect`
(`DriftDetection.swift`), ported to Python, on synthetic check-in histories with
known ground truth. Positive alerts are not scored.

Four detector variants:

| Variant | Windows | Gating | Status |
|---|---|---|---|
| `count_gated` | last 7 check-ins vs previous 7 | on | **current app behaviour** |
| `count_ungated` | same | `hasEnoughDataForAlert` always true | evaluation only |
| `calendar_gated` | last 7 calendar days vs previous 7 | on | evaluation only |
| `calendar_ungated` | same | off | evaluation only |

**Calendar-window definition (evaluation only, not app behaviour):** on day *T*, `recent` = check-ins
dated *T-6 … T*, `previous` = check-ins dated *T-13 … T-7*. Everything else is unchanged: the same
±0.25 thresholds, `recent.count >= 4`, a non-empty `previous`, the same confidence rule
`min(recent, previous)` (≥ 6 strong, ≥ 4 moderate), and the same severity rule.

**Gating** only changes anything when `previous` has 1-3 check-ins. Under count windows, that is
only when there are **8-10 check-ins in total**.

## Files

| File | Purpose |
|---|---|
| `detector.py` | Line-by-line port of the Swift detector, with Swift line references |
| `test_detector.py` | 15 hand-checked cases (input -> expected alert) |
| `simulate.py` | Synthetic users; sample plot |
| `metrics.py` | Episodes, windows, metrics, confidence intervals, noise x check-in-rate grid |
| `test_metrics.py` | Checks for episode/window logic and simulator basics |
| `personalised.py` | Variability-scaled threshold and tuned global control: tuning and held-out evaluation |
| `run_all.py` | Reproduces every table and figure |
| `results/summary.md` | All result tables (generated); the source for the numbers below |
| `results/*.csv` | Same results, machine-readable (`*_primary` and `*_full_change` = previous definition) |
| `figures/*.png` | All figures (generated); `detection_by_magnitude_previous_definition.png` is the sensitivity analysis; `personalised_threshold.png` compares current, tuned global and variability-scaled |
| `DESIGN_DECISIONS.md` | Detector specification, evaluation decisions and definitions |
| `LICENSE` | MIT licence |

## How to run

Tested with Python 3.9.6. `requirements.txt` pins exact versions (numpy 2.0.2, matplotlib 3.9.4,
pytest 8.4.2); with these pins, use Python 3.9-3.12.

```sh
cd evoki-drift-eval
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q        # 28 tests
python run_all.py          # about 100 s; writes results/ and figures/
```

All randomness uses fixed seeds (`simulate.SEED = 20261006`, a separate stream per user), so re-runs
give identical output.

## Port fidelity

- `detector.py` follows the Swift code line by line. Sums use a plain loop to match Swift's
  `reduce(0, +)`; Python 3.12+ `sum()` uses compensated summation and could flip cases exactly on
  ±0.25. The adherence rate is computed in 32-bit float, as in Swift's `Float`.
- Cases 1, 3, 4, 6, 7 (gated) and 8 were run against the **real Swift code**, and all 7 results
  matched. The Xcode test target did not build on this branch, so the original Swift files were
  compiled unmodified with `swiftc` together with a temporary driver, which was then deleted.
  The ungated and calendar variants have no Swift counterpart.
- Input scales were verified in the UI code: sleep 1-5 (`EvokiComponents.swift:195`),
  mood 1-5 (`CheckInView.swift:286`), social 0-2 (`CheckInView.swift:333`).

## Simulator (assumptions)

The groups are **behaviour types, not demographics**. They describe how regularly and how
consistently someone answers. They do not represent age, sex, diagnosis or any population.

| Group | Check-in rate | Noise SD (1-5 scale) | Baseline (1-5 scale) |
|---|---|---|---|
| stable | 0.9 | 0.5 | N(3.5, 0.5) |
| high_variability | 0.9 | 1.0 | N(3.5, 0.5) |
| sparse | 0.4 | 0.5 | N(3.5, 0.5) |
| low_baseline (floor effect) | 0.9 | 0.5 | N(1.8, 0.3) |

- 500 users per group, 90 days each.
- Each domain is generated as a continuous latent score: baseline + AR(1) noise (φ = 0.3) − change.
  It is then rounded half-up and clamped to the real scale (sleep and mood 1-5, social 0-2).
- Social's baseline, noise and change are multiplied by 0.5, so the latent normalised effect equals
  sleep and mood (1 point on 1-5 = 0.5 point on 0-2 = 0.25 normalised). After rounding, social has
  only 3 levels, so results are also reported per domain.
- 50% of users have one true decline in one random domain; the other domains stay stable.
  - Onset: a random day from 40 to 60.
  - Shape: step, or gradual (a linear ramp reaching full size on day onset + 13).
  - Size: 0.5, 1, 1.5 or 2 points on the 1-5 scale.
- Each day independently has a check-in or not.
- The detector runs once per day, right after that day's check-in, through the same fetch as the
  app (latest edit per date, last 14, at least 3).

## Metric definitions

- **Episode:** consecutive firing runs. A day without a check-in does not split an episode.
  Alarm-days are also reported.
- **False alarms per user-month:** no-change users; episodes starting on day ≥ 14; divided by
  76/30 user-months. The first 14 days (warm-up) are excluded from both numerator and denominator.
- **Full-change day:** step → onset; gradual → onset + 13, when the ramp reaches full size.
- **TP window (primary):** from **onset** to **full-change day + 13**, i.e. 14 days after the
  change is complete. For step changes this is the same 14-day window as before; for gradual
  changes it also covers the 13-day ramp (27 days in total). Sensitivity at W = 7 and 21 uses
  onset to full-change day + W − 1. Windows are cut off at day 89 for the latest gradual onsets.
- **TP window (previous definition, now a sensitivity analysis):** from the full-change day to
  full-change day + 13.
- **Detected:** an any-domain episode *starts* in the window; episodes already running when the
  window opens do not count. **Domain-correct:** the changed domain's own episode starts in the
  window. **Delay:** episode start minus onset.
- **Chance:** each no-change user gets a pseudo onset and shape, drawn the same way as real
  changes, and the **same window rule** is applied: same definition and same W, so the same
  window length (W days for a pseudo step, W + 13 days for a pseudo gradual change). It is the
  detection rate that false alarms alone would produce.
- **Precision by confidence:** among all episodes starting on day ≥ 14, the share that start in a
  changed user's TP window, grouped by the confidence label of the episode's first alert. Every
  other episode (in a no-change user, or outside the window) is incorrect. Confidence is a
  **three-level label based on data quantity only**. It is not a probability, so no calibration
  analysis was done. Precision depends on the 50% prevalence of changed users in the simulation.
- **95% intervals:** Wilson for proportions; user-level percentile bootstrap (2000 resamples) for
  rates and median delay. Wilson intervals for precision ignore clustering within users, so they
  are somewhat too narrow.

### Change to the true-positive definition (made after seeing results)

**The primary TP window was changed after the first results were seen.** The first definition
started the window on the full-change day. That counted alarms starting *during* a gradual ramp
as misses, even though the change was real and already under way. As a result, larger changes
scored *lower* than smaller ones; for example, in the stable group, 21 of 23 gradual 2-point
changes started an alarm during the ramp. The window now starts at onset. The previous definition
is kept as a sensitivity analysis: the tables below and in `results/summary.md` show both, and
`figures/detection_by_magnitude_previous_definition.png` shows it as a figure. Because the
definition was chosen after seeing data, treat the comparison between the two as exploratory.
The "from onset" diagnostic in the earlier draft is the same as the new primary definition, so
it is no longer a separate column.

## Results (current app: `count_gated`)

From `results/summary.md`; that file has all variants and intervals. Simulated data only.

False-alarm rates do not depend on the TP window:

| Group | False-alarm episodes / user-month | Alarm-days / user-month |
|---|---|---|
| stable | 0.46 [0.40, 0.52] | 0.88 [0.76, 1.00] |
| high_variability | 1.95 [1.87, 2.04] | 5.29 [5.06, 5.52] |
| sparse | 0.11 [0.08, 0.14] | 0.19 [0.14, 0.25] |
| low_baseline | 0.60 [0.53, 0.66] | 1.24 [1.09, 1.39] |

Detection, **primary definition** (window from onset to full-change day + 13):

| Group | Detected | Chance | Domain-correct | Median delay from onset (days) |
|---|---|---|---|---|
| stable | 70.6% [64.7, 75.8] | 26.9% [21.8, 32.8] | 64.3% [58.3, 69.9] | 6 (IQR 4-9) |
| high_variability | 90.2% [85.8, 93.3] | 81.2% [75.9, 85.5] | 81.2% [75.9, 85.6] | 6 (IQR 3-9) |
| sparse | 56.4% [50.3, 62.3] | 9.5% [6.4, 13.9] | 54.1% [48.0, 60.0] | 12 (IQR 8-16) |
| low_baseline | 45.7% [39.8, 51.7] | 30.2% [24.7, 36.4] | 32.1% [26.7, 37.9] | 6 (IQR 4-9) |

Detection, **previous definition** (sensitivity analysis; window from full-change day to + 13):

| Group | Detected | Chance | Domain-correct | Median delay from onset (days) |
|---|---|---|---|---|
| stable | 55.3% [49.2, 61.3] | 19.2% [14.7, 24.6] | 50.2% [44.1, 56.3] | 6 (IQR 4-14) |
| high_variability | 72.7% [66.8, 77.9] | 69.0% [63.1, 74.4] | 57.1% [50.9, 63.2] | 11 (IQR 4-17) |
| sparse | 47.5% [41.5, 53.6] | 4.6% [2.6, 8.0] | 45.9% [40.0, 52.0] | 13 (IQR 8-18) |
| low_baseline | 29.4% [24.3, 35.2] | 20.4% [15.8, 26.0] | 18.5% [14.3, 23.6] | 6 (IQR 4-13) |

Worst group (primary): highest false alarms is **high_variability** (1.95 per user-month); lowest
detection is **low_baseline** (45.7%).

What these simulations show (under the assumptions above, primary definition unless stated):

1. **High-variability users:** detection (90.2%) is only slightly above chance (81.2%). In this
   group, most "detections" can be explained by false alarms (about 2 episodes per user-month).
2. **Floor effect:** in `low_baseline`, scores already sit near the bottom of the scale and cannot
   fall much further. Detection is 45.7% against 30.2% chance, domain-correct detection is 32.1%,
   and detection does not rise with change size (0.5 pt 39.1%, 2 pt 42.1%).
3. **Detection by magnitude (stable):**
   - primary: 0.5 pt 30.9%, 1 pt 65.1%, 1.5 pt 93.4%, 2 pt 97.9%;
   - previous definition: 23.5%, 57.1%, 76.3%, 64.6%. The dip at 2 pt was caused by alarms starting
     during the ramp (see the definition change above).
4. **Step vs gradual (stable):** 71.9% vs 69.2% (primary); under the previous definition gradual
   was 36.7%.
5. **Gating:** after the 14-day warm-up, gated and ungated count windows give identical detection
   in all groups, and identical false alarms for stable, high_variability and low_baseline. For
   daily users, 8-10 check-ins only happen in the first days. In sparse users, gating lowered false
   alarms (0.11 vs 0.19 per user-month) with the same detection (56.4%).
6. **Calendar windows (evaluation only):**
   - Sparse users: detection drops from 56.4% to 16.2% (gated), because few 7-day windows contain
     4 or more check-ins.
   - Daily users: false alarms rise (stable 0.46 → 0.64 per user-month) with similar detection
     (70.6% → 71.4%).
7. **Precision by confidence (`count_gated`, primary):** `strong` 21.6% [20.3, 22.8] (4268
   episodes; previous definition 14.5%). For `moderate`, 0 of 49 episodes were correct; that is
   **too few episodes (n=49) to conclude**. Precision depends on the 50% prevalence of changed
   users in the simulation and on the definitions above.
8. **Per domain:** for stable and low_baseline users, social produces more false-alarm episodes
   than sleep or mood (stable 0.30 vs 0.09 and 0.08). A likely reason, not tested separately:
   social has only 3 levels, so a one-level change on a few days moves its normalised mean a lot.
9. **Noise × check-in-rate grid** (`figures/grid_heatmap.png`): with count windows, false alarms
   rise with both noise and check-in rate, from 0.06 to 2.55 per user-month. Chance detection rises
   with them, so high detection in noisy cells mostly reflects false alarms. With calendar windows,
   detection is 0.06 or lower at a check-in rate of 0.3, and 0.26 or lower at 0.4.

## Variability-scaled threshold, with a tuned global control (evaluation only, not app behaviour)

(In the code, file names and figure labels this rule is called `personalised`.)

The high-variability result points to one specific problem: the same fixed ±0.25 threshold is
used for every user. This section tests a threshold scaled by each user's own variability. It
compares that against a **control**: a single global threshold tuned the same way. Without the
control, any gain could just come from a lower threshold overall.

**Rules compared** (all keep count windows, gating and the same minimum rules):

| Rule | Threshold for each domain | History needed |
|---|---|---|
| current | 0.25 | 14 check-ins (what the app fetches) |
| tuned global (control) | one constant T for every user and domain | 14 check-ins |
| variability-scaled | `max(FLOOR, K × sd)`; sd = SD of the user's own normalised scores over up to **28 check-ins** before the recent window (0.25 if fewer than 4) | up to **35 check-ins**, more than the app currently fetches |

**Tuning and held-out evaluation.**
- Both rules were tuned on the same **tuning users** (seed 1, 150 per group).
- They used the same goal, fixed before tuning: the mean over the four groups of
  (detection − chance), primary definition, W = 14.
- Grids:
  - Global: T from 0.10 to 0.40 in steps of 0.0125 (25 values).
  - Variability-scaled: K ∈ {0.5 … 3} × FLOOR ∈ {0.125, 0.1875, 0.25} (24 combinations).
- All three rules were then run on the same **held-out users** (seed 2, 500 per group), never
  used for tuning.
- Chosen: **T = 0.2375** (tied with 0.225; ties go to the larger T), and **K = 1.25,
  FLOOR = 0.1875**.
- Tests check that T = 0.25, and K = 0 with FLOOR = 0.25, both reproduce the current detector
  exactly.

**Goal score** (mean over groups of detection − chance):

| Rule | Tuning users | Held-out users |
|---|---|---|
| current (0.25) | 0.375 | 0.338 |
| tuned global (0.2375) | 0.379 | 0.343 |
| variability-scaled | 0.400 | 0.393 |

Paired differences on held-out users (same users, 95% paired bootstrap):
- tuned global − current: **+0.005 [−0.002, +0.013]**
- variability-scaled − current: **+0.056 [+0.022, +0.090]**
- variability-scaled − tuned global: **+0.050 [+0.017, +0.085]**

**Held-out results by group** (simulated data; full intervals in `results/summary.md`; figure
`figures/personalised_threshold.png`):

| Group | Rule | False alarms / user-month | Detected | Chance | Detected − chance | Domain-correct | Median delay |
|---|---|---|---|---|---|---|---|
| stable | current | 0.42 [0.37, 0.47] | 71.9% | 27.5% | 44.4 pts | 67.1% | 6 d |
| stable | tuned global | 0.43 [0.38, 0.48] | 73.5% | 27.9% | 45.6 pts | 68.7% | 6 d |
| stable | variability-scaled | 0.49 [0.44, 0.54] | 80.3% | 30.3% | 50.0 pts | 75.5% | 6 d |
| high_variability | current | 1.86 [1.78, 1.93] | 94.4% | 79.5% | 14.9 pts | 83.6% | 5 d |
| high_variability | tuned global | 1.88 [1.81, 1.96] | 94.4% | 80.6% | 13.8 pts | 83.2% | 5 d |
| high_variability | variability-scaled | 1.10 [1.04, 1.17] | 78.0% | 54.5% | 23.5 pts | 63.4% | 6 d |
| sparse | current | 0.13 [0.10, 0.16] | 57.3% | 5.8% | 51.5 pts | 54.8% | 11 d |
| sparse | tuned global | 0.14 [0.11, 0.16] | 59.3% | 5.8% | 53.5 pts | 56.4% | 11 d |
| sparse | variability-scaled | 0.17 [0.14, 0.20] | 65.6% | 8.5% | 57.1 pts | 62.7% | 11 d |
| low_baseline | current | 0.55 [0.49, 0.61] | 50.6% | 26.4% | 24.2 pts | 30.7% | 6 d |
| low_baseline | tuned global | 0.56 [0.50, 0.62] | 50.6% | 26.4% | 24.2 pts | 30.7% | 6 d |
| low_baseline | variability-scaled | 0.54 [0.48, 0.59] | 55.9% | 29.3% | 26.6 pts | 39.8% | 6 d |

Numbers in the held-out comparison differ slightly from the main tables because they use different
simulated users (seed 2).

**What the comparison shows:**
1. **Retuning one global threshold does almost nothing.** The best constant (0.2375) is close
   to 0.25, and its gain over the current detector is +0.005, with an interval that includes zero.
2. **The variability-scaled rule's gain is not explained by a lower global threshold.** It beats the
   tuned global control by +0.050 [+0.017, +0.085] on held-out users. A global threshold as low as
   the variability-scaled FLOOR (0.1875) scored much worse on tuning users (0.292 vs 0.379): it lowers
   the threshold for high-variability users too, and their false alarms rise.
3. **What variability scaling does here:** it sets different levels for different users.
   - Steady users get a lower threshold (stable and sparse: more detection *and* more false
     alarms).
   - Noisy users get a higher threshold (high_variability: about 40% fewer false alarms, but
     detection 94% → 78% and domain-correct 84% → 63%).
   - In every group, detection − chance is higher than under both fixed rules. It is a trade-off
     per user type, not an improvement on every measure.
4. **Delays are about the same** for all three rules.

**What it does not show:**
- In this simulator every user in a group has the same noise SD, so "variability-scaled" cannot be told
  apart from "a threshold per noise level". Variation in noise between users of the same group was
  not simulated.
- Both rules were tuned and tested on the same simulator family: different seeds, but the same
  group settings and the same stationary Gaussian noise. That is exactly the case where scaling by
  a user's SD should work.
- Only one goal and small grids were tried.
- None of this says the rule would help real users. The variability-scaled rule also needs up to
  35 past check-ins, while the app currently fetches 14.

## Findings from the code (no simulation needed)

1. **The adherence alert can never fire** (`DriftDetection.swift:35-43`): it needs `count >= 4` and
   `count/7 < 0.43` (count ≤ 3) at the same time.
2. **No de-duplication:** every run creates alerts with new UUIDs and saves them all
   (`InMemoryRepositories.swift:490-492`). The detector runs on every home-screen load and after
   each check-in (`HomeViewModel.swift:55, 127, 196`), so the same alert is saved again each time.
   This was **not** simulated; episodes approximate one alert per sustained signal.
3. **Windows are counted in check-ins, not days.** A sparse user's "recent week" can cover several
   calendar weeks.
4. **Confidence is a data-quantity label** (`ClinicalScoreSupport.swift:20-25`). It never looks at
   the scores, and gating only matters for 8-10 total check-ins.
5. **The first 7 check-ins can never produce a domain alert** (empty `previous`, `DriftDetection.swift:62`).
6. The combined positive alert uses a different threshold (> 0.18, strict) from the domain alerts
   (±0.25, inclusive).

## Limitations

- **All results depend on assumed parameters** (noise SD, baselines, check-in rates, AR(1) φ,
  change sizes and shapes, 50% prevalence). None were estimated from real data.
- Domains are independent; real sleep, mood and social answers are probably correlated.
- Missing check-ins are random and independent of scores. In reality, people may check in less
  often when they feel worse; this was not modelled.
- Baselines are stationary: no seasonality, no slow trends, and at most one change per user.
- Answers come from rounding a Gaussian latent score. Real response styles (always picking the
  middle, anchoring on yesterday) are not modelled.
- The detector runs once per day after a check-in. The app also runs it on every home-screen load,
  and it saves duplicate alerts (finding 2). Neither is simulated.
- "Detected" counts an alarm in any domain, so it can include coincidental alarms. Domain-correct
  detection and the chance baseline are reported for that reason.
- The variability-scaled threshold and its tuned global control were tuned and evaluated on the same
  simulator family (different seeds only), with one goal and small grids. Within-group
  differences in noise between users were not simulated.
- The primary TP window was chosen after seeing the first results (see "Change to the
  true-positive definition"). Both definitions are reported; the comparison is exploratory.
- Precision depends on the 50% prevalence of changed users. Its Wilson intervals ignore
  clustering within users.
- Only 7 Swift results were cross-checked, using `swiftc` rather than XCTest.
- The AI narrative, the UI, notifications and HealthKit fields are out of scope; they do not affect
  firing.

## Use of AI tools

Code in this repository was written with an AI coding assistant (Claude Code) under my direction.
The research question, definitions, design decisions (including the change to the true-positive
definition) and the interpretation of results are mine.
