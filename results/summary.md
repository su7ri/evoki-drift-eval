# Results (simulated data only)

All numbers come from simulated users and depend on the assumptions in `simulate.py`. They are not clinical validation and do not come from real users.

App commit: `f389fc6383ae6416a84afea227639b4faa6f8dbb`. Seed `20261006`. 500 users per group, 90 days. Brackets are 95% intervals (Wilson for proportions, user-level bootstrap for rates and median delay).

## Groups (behaviour types, not demographics)

| group | users | with change | mean check-in rate |
|---|---|---|---|
| stable | 500 | 255 | 0.90 |
| high_variability | 500 | 245 | 0.90 |
| sparse | 500 | 259 | 0.40 |
| low_baseline | 500 | 265 | 0.90 |

## False alarms per user-month (no-change users, days 14-89)

Episodes are the primary metric. An episode is consecutive firing runs; days without a check-in do not split it.

| group | variant | episodes / user-month | alarm-days / user-month |
|---|---|---|---|
| stable | count_gated | 0.46 [0.40, 0.52] | 0.88 [0.76, 1.00] |
| stable | count_ungated | 0.46 [0.40, 0.52] | 0.88 [0.76, 1.00] |
| stable | calendar_gated | 0.64 [0.57, 0.71] | 1.26 [1.11, 1.41] |
| stable | calendar_ungated | 0.64 [0.57, 0.71] | 1.27 [1.12, 1.42] |
| high_variability | count_gated | 1.95 [1.87, 2.04] | 5.29 [5.06, 5.52] |
| high_variability | count_ungated | 1.95 [1.86, 2.04] | 5.29 [5.06, 5.52] |
| high_variability | calendar_gated | 2.18 [2.10, 2.27] | 5.79 [5.55, 6.04] |
| high_variability | calendar_ungated | 2.19 [2.10, 2.27] | 5.82 [5.58, 6.06] |
| sparse | count_gated | 0.11 [0.08, 0.14] | 0.19 [0.14, 0.25] |
| sparse | count_ungated | 0.19 [0.16, 0.23] | 0.32 [0.26, 0.39] |
| sparse | calendar_gated | 0.11 [0.08, 0.14] | 0.15 [0.10, 0.20] |
| sparse | calendar_ungated | 0.51 [0.46, 0.57] | 0.80 [0.70, 0.90] |
| low_baseline | count_gated | 0.60 [0.53, 0.66] | 1.24 [1.09, 1.39] |
| low_baseline | count_ungated | 0.59 [0.53, 0.66] | 1.24 [1.09, 1.39] |
| low_baseline | calendar_gated | 0.80 [0.73, 0.87] | 1.75 [1.58, 1.91] |
| low_baseline | calendar_ungated | 0.81 [0.74, 0.88] | 1.76 [1.59, 1.92] |

### False-alarm episodes per user-month by alerting domain (count, gated)

| group | sleep | social | mood |
|---|---|---|---|
| stable | 0.09 [0.07, 0.11] | 0.30 [0.25, 0.35] | 0.08 [0.06, 0.10] |
| high_variability | 0.74 [0.69, 0.80] | 0.77 [0.71, 0.83] | 0.80 [0.74, 0.86] |
| sparse | 0.02 [0.01, 0.03] | 0.07 [0.05, 0.10] | 0.02 [0.01, 0.03] |
| low_baseline | 0.06 [0.04, 0.08] | 0.47 [0.41, 0.53] | 0.07 [0.05, 0.10] |

## Detection, primary definition: window [onset, full-change day + W - 1] (changed users, all sizes pooled)

Full-change day: step -> onset; gradual -> onset + 13. Detected = an any-domain episode starts inside the window. For steps the window is W days from onset; for gradual changes it also covers the 13-day ramp. Domain-correct = the changed domain's own episode starts in the 14-day window. Delay = episode start minus onset, in days.

**Read detection next to the chance column.** Chance = the same window rule (same definition and W, so the same window length) applied to no-change users at a pseudo onset and shape, i.e. what false alarms alone would score.

| group | variant | detected (14 d) | chance (14 d) | domain-correct (14 d) | detected (7 d) | detected (21 d) | median delay [CI] |
|---|---|---|---|---|---|---|---|
| stable | count_gated | 70.6% [64.7, 75.8] | 26.9% [21.8, 32.8] | 64.3% [58.3, 69.9] | 63.1% [57.1, 68.8] (chance 18.8%) | 72.5% [66.8, 77.7] (chance 34.3%) | 6 [5, 7] (IQR 4-9, n=180) |
| stable | count_ungated | 70.6% [64.7, 75.8] | 26.9% [21.8, 32.8] | 64.3% [58.3, 69.9] | 63.1% [57.1, 68.8] (chance 18.8%) | 72.5% [66.8, 77.7] (chance 34.3%) | 6 [5, 7] (IQR 4-9, n=180) |
| stable | calendar_gated | 71.4% [65.5, 76.6] | 34.7% [29.0, 40.8] | 62.4% [56.3, 68.1] | 67.8% [61.9, 73.3] (chance 25.7%) | 73.3% [67.6, 78.4] (chance 42.0%) | 6 [5, 6] (IQR 3-9, n=182) |
| stable | calendar_ungated | 71.4% [65.5, 76.6] | 34.7% [29.0, 40.8] | 62.4% [56.3, 68.1] | 67.8% [61.9, 73.3] (chance 26.1%) | 73.3% [67.6, 78.4] (chance 42.0%) | 6 [5, 6] (IQR 3-9, n=182) |
| high_variability | count_gated | 90.2% [85.8, 93.3] | 81.2% [75.9, 85.5] | 81.2% [75.9, 85.6] | 77.6% [71.9, 82.3] (chance 65.5%) | 95.5% [92.1, 97.5] (chance 89.8%) | 6 [5, 6] (IQR 3-9, n=221) |
| high_variability | count_ungated | 90.2% [85.8, 93.3] | 81.2% [75.9, 85.5] | 81.2% [75.9, 85.6] | 77.6% [71.9, 82.3] (chance 65.5%) | 95.5% [92.1, 97.5] (chance 89.8%) | 6 [5, 6] (IQR 3-9, n=221) |
| high_variability | calendar_gated | 87.8% [83.1, 91.3] | 87.5% [82.8, 91.0] | 80.8% [75.4, 85.3] | 78.4% [72.8, 83.1] (chance 67.5%) | 94.7% [91.1, 96.9] (chance 95.7%) | 5 [4, 6] (IQR 2-8, n=215) |
| high_variability | calendar_ungated | 87.8% [83.1, 91.3] | 87.5% [82.8, 91.0] | 80.8% [75.4, 85.3] | 78.4% [72.8, 83.1] (chance 67.5%) | 94.7% [91.1, 96.9] (chance 95.7%) | 5 [4, 5] (IQR 2-8, n=215) |
| sparse | count_gated | 56.4% [50.3, 62.3] | 9.5% [6.4, 13.9] | 54.1% [48.0, 60.0] | 31.3% [25.9, 37.2] (chance 7.5%) | 64.9% [58.9, 70.4] (chance 11.2%) | 12 [11, 12] (IQR 8-16, n=146) |
| sparse | count_ungated | 56.4% [50.3, 62.3] | 9.5% [6.4, 13.9] | 54.1% [48.0, 60.0] | 31.3% [25.9, 37.2] (chance 7.5%) | 64.9% [58.9, 70.4] (chance 11.2%) | 12 [11, 12] (IQR 8-16, n=146) |
| sparse | calendar_gated | 16.2% [12.2, 21.2] | 6.2% [3.8, 10.0] | 13.1% [9.5, 17.8] | 11.6% [8.2, 16.1] (chance 4.6%) | 17.8% [13.6, 22.9] (chance 7.9%) | 8 [6, 10] (IQR 5-13, n=42) |
| sparse | calendar_ungated | 49.4% [43.4, 55.5] | 30.7% [25.2, 36.8] | 38.2% [32.5, 44.3] | 36.3% [30.7, 42.3] (chance 22.4%) | 53.7% [47.6, 59.6] (chance 36.1%) | 8 [7, 10] (IQR 5-12, n=128) |
| low_baseline | count_gated | 45.7% [39.8, 51.7] | 30.2% [24.7, 36.4] | 32.1% [26.7, 37.9] | 40.4% [34.6, 46.4] (chance 21.3%) | 50.2% [44.2, 56.2] (chance 37.0%) | 6 [5, 7] (IQR 4-9, n=121) |
| low_baseline | count_ungated | 45.7% [39.8, 51.7] | 30.2% [24.7, 36.4] | 32.1% [26.7, 37.9] | 40.4% [34.6, 46.4] (chance 21.3%) | 50.2% [44.2, 56.2] (chance 37.0%) | 6 [5, 7] (IQR 4-9, n=121) |
| low_baseline | calendar_gated | 55.1% [49.1, 61.0] | 39.6% [33.5, 45.9] | 36.6% [31.0, 42.6] | 49.1% [43.1, 55.0] (chance 28.9%) | 60.8% [54.8, 66.4] (chance 52.3%) | 6 [5, 6] (IQR 3-8, n=146) |
| low_baseline | calendar_ungated | 55.5% [49.5, 61.3] | 39.6% [33.5, 45.9] | 36.6% [31.0, 42.6] | 49.4% [43.5, 55.4] (chance 28.9%) | 61.1% [55.1, 66.8] (chance 52.3%) | 6 [5, 6] (IQR 3-8, n=147) |

## Detection, sensitivity analysis, previous definition: window [full-change day, full-change day + W - 1] (changed users, all sizes pooled)

This was the first primary definition. It was replaced after the first results showed that alarms starting during a gradual ramp were counted as misses. For step changes both definitions are identical.

| group | variant | detected (14 d) | chance (14 d) | domain-correct (14 d) | detected (7 d) | detected (21 d) | median delay [CI] |
|---|---|---|---|---|---|---|---|
| stable | count_gated | 55.3% [49.2, 61.3] | 19.2% [14.7, 24.6] | 50.2% [44.1, 56.3] | 46.3% [40.3, 52.4] (chance 10.2%) | 59.2% [53.1, 65.1] (chance 26.5%) | 6 [5, 6] (IQR 4-14, n=141) |
| stable | count_ungated | 55.3% [49.2, 61.3] | 19.2% [14.7, 24.6] | 50.2% [44.1, 56.3] | 46.3% [40.3, 52.4] (chance 10.2%) | 59.2% [53.1, 65.1] (chance 26.5%) | 6 [5, 6] (IQR 4-14, n=141) |
| stable | calendar_gated | 54.5% [48.4, 60.5] | 25.3% [20.3, 31.1] | 48.6% [42.6, 54.7] | 48.6% [42.6, 54.7] (chance 14.3%) | 58.8% [52.7, 64.7] (chance 33.1%) | 5 [5, 6] (IQR 3-14, n=139) |
| stable | calendar_ungated | 54.5% [48.4, 60.5] | 25.3% [20.3, 31.1] | 48.6% [42.6, 54.7] | 48.6% [42.6, 54.7] (chance 14.3%) | 58.8% [52.7, 64.7] (chance 33.5%) | 5 [5, 6] (IQR 3-14, n=139) |
| high_variability | count_gated | 72.7% [66.8, 77.9] | 69.0% [63.1, 74.4] | 57.1% [50.9, 63.2] | 51.8% [45.6, 58.0] (chance 41.6%) | 84.1% [79.0, 88.1] (chance 81.6%) | 11 [7, 13] (IQR 4-17, n=178) |
| high_variability | count_ungated | 72.7% [66.8, 77.9] | 69.0% [63.1, 74.4] | 57.1% [50.9, 63.2] | 51.8% [45.6, 58.0] (chance 41.6%) | 84.1% [79.0, 88.1] (chance 81.6%) | 11 [7, 13] (IQR 4-17, n=178) |
| high_variability | calendar_gated | 75.1% [69.3, 80.1] | 76.5% [70.9, 81.3] | 59.6% [53.3, 65.5] | 56.7% [50.5, 62.8] (chance 46.7%) | 90.2% [85.8, 93.3] (chance 89.4%) | 12 [8, 14] (IQR 4-17, n=184) |
| high_variability | calendar_ungated | 75.1% [69.3, 80.1] | 76.5% [70.9, 81.3] | 59.6% [53.3, 65.5] | 56.7% [50.5, 62.8] (chance 46.7%) | 90.2% [85.8, 93.3] (chance 89.4%) | 12 [8, 14] (IQR 4-17, n=184) |
| sparse | count_gated | 47.5% [41.5, 53.6] | 4.6% [2.6, 8.0] | 45.9% [40.0, 52.0] | 22.0% [17.4, 27.4] (chance 2.5%) | 57.1% [51.1, 63.0] (chance 6.2%) | 13 [12, 13] (IQR 8-18, n=123) |
| sparse | count_ungated | 47.5% [41.5, 53.6] | 4.6% [2.6, 8.0] | 45.9% [40.0, 52.0] | 22.0% [17.4, 27.4] (chance 2.5%) | 57.1% [51.1, 63.0] (chance 6.2%) | 13 [12, 13] (IQR 8-18, n=123) |
| sparse | calendar_gated | 14.3% [10.5, 19.1] | 3.7% [2.0, 6.9] | 12.0% [8.6, 16.5] | 9.7% [6.6, 13.9] (chance 1.7%) | 15.8% [11.9, 20.8] (chance 5.4%) | 7 [6, 13] (IQR 5-13, n=37) |
| sparse | calendar_ungated | 37.5% [31.8, 43.5] | 22.0% [17.2, 27.6] | 29.7% [24.5, 35.6] | 23.2% [18.4, 28.7] (chance 12.4%) | 42.5% [36.6, 48.6] (chance 28.2%) | 9 [7, 12] (IQR 5-15, n=97) |
| low_baseline | count_gated | 29.4% [24.3, 35.2] | 20.4% [15.8, 26.0] | 18.5% [14.3, 23.6] | 23.0% [18.4, 28.5] (chance 9.8%) | 35.5% [30.0, 41.4] (chance 28.5%) | 6 [6, 8] (IQR 4-13, n=78) |
| low_baseline | count_ungated | 29.4% [24.3, 35.2] | 20.4% [15.8, 26.0] | 18.5% [14.3, 23.6] | 23.0% [18.4, 28.5] (chance 9.8%) | 35.5% [30.0, 41.4] (chance 28.5%) | 6 [6, 8] (IQR 4-13, n=78) |
| low_baseline | calendar_gated | 34.7% [29.2, 40.6] | 28.1% [22.7, 34.1] | 20.8% [16.3, 26.0] | 27.2% [22.2, 32.8] (chance 14.5%) | 44.5% [38.7, 50.5] (chance 43.0%) | 6 [5, 6] (IQR 4-13, n=92) |
| low_baseline | calendar_ungated | 34.7% [29.2, 40.6] | 28.1% [22.7, 34.1] | 20.8% [16.3, 26.0] | 27.2% [22.2, 32.8] (chance 14.5%) | 44.5% [38.7, 50.5] (chance 43.0%) | 6 [5, 6] (IQR 4-13, n=92) |

## Detection rate by change magnitude (primary, 14-day window)

| group | variant | 0.5 pt | 1 pt | 1.5 pt | 2 pt |
|---|---|---|---|---|---|
| stable | count_gated | 30.9% [21.2, 42.6] n=68 | 65.1% [52.8, 75.7] n=63 | 93.4% [85.5, 97.2] n=76 | 97.9% [89.1, 99.6] n=48 |
| stable | count_ungated | 30.9% [21.2, 42.6] n=68 | 65.1% [52.8, 75.7] n=63 | 93.4% [85.5, 97.2] n=76 | 97.9% [89.1, 99.6] n=48 |
| stable | calendar_gated | 42.6% [31.6, 54.5] n=68 | 57.1% [44.9, 68.6] n=63 | 92.1% [83.8, 96.3] n=76 | 97.9% [89.1, 99.6] n=48 |
| stable | calendar_ungated | 42.6% [31.6, 54.5] n=68 | 57.1% [44.9, 68.6] n=63 | 92.1% [83.8, 96.3] n=76 | 97.9% [89.1, 99.6] n=48 |
| high_variability | count_gated | 73.2% [60.4, 83.0] n=56 | 91.3% [82.3, 96.0] n=69 | 96.6% [88.5, 99.1] n=59 | 98.4% [91.3, 99.7] n=61 |
| high_variability | count_ungated | 73.2% [60.4, 83.0] n=56 | 91.3% [82.3, 96.0] n=69 | 96.6% [88.5, 99.1] n=59 | 98.4% [91.3, 99.7] n=61 |
| high_variability | calendar_gated | 71.4% [58.5, 81.6] n=56 | 89.9% [80.5, 95.0] n=69 | 89.8% [79.5, 95.3] n=59 | 98.4% [91.3, 99.7] n=61 |
| high_variability | calendar_ungated | 71.4% [58.5, 81.6] n=56 | 89.9% [80.5, 95.0] n=69 | 89.8% [79.5, 95.3] n=59 | 98.4% [91.3, 99.7] n=61 |
| sparse | count_gated | 18.5% [10.9, 29.6] n=65 | 48.4% [36.6, 60.4] n=64 | 70.3% [59.1, 79.5] n=74 | 91.1% [80.7, 96.1] n=56 |
| sparse | count_ungated | 18.5% [10.9, 29.6] n=65 | 48.4% [36.6, 60.4] n=64 | 70.3% [59.1, 79.5] n=74 | 91.1% [80.7, 96.1] n=56 |
| sparse | calendar_gated | 6.2% [2.4, 14.8] n=65 | 10.9% [5.4, 20.9] n=64 | 21.6% [13.8, 32.3] n=74 | 26.8% [17.0, 39.6] n=56 |
| sparse | calendar_ungated | 38.5% [27.6, 50.6] n=65 | 40.6% [29.5, 52.9] n=64 | 58.1% [46.7, 68.7] n=74 | 60.7% [47.6, 72.4] n=56 |
| low_baseline | count_gated | 39.1% [28.1, 51.3] n=64 | 45.7% [34.6, 57.3] n=70 | 54.1% [42.8, 64.9] n=74 | 42.1% [30.2, 55.0] n=57 |
| low_baseline | count_ungated | 39.1% [28.1, 51.3] n=64 | 45.7% [34.6, 57.3] n=70 | 54.1% [42.8, 64.9] n=74 | 42.1% [30.2, 55.0] n=57 |
| low_baseline | calendar_gated | 48.4% [36.6, 60.4] n=64 | 58.6% [46.9, 69.4] n=70 | 58.1% [46.7, 68.7] n=74 | 54.4% [41.6, 66.6] n=57 |
| low_baseline | calendar_ungated | 50.0% [38.1, 61.9] n=64 | 58.6% [46.9, 69.4] n=70 | 58.1% [46.7, 68.7] n=74 | 54.4% [41.6, 66.6] n=57 |

### Sensitivity analysis: detection by magnitude, previous definition (window from full-change day)

| group | variant | 0.5 pt | 1 pt | 1.5 pt | 2 pt |
|---|---|---|---|---|---|
| stable | count_gated | 23.5% [15.0, 34.9] n=68 | 57.1% [44.9, 68.6] n=63 | 76.3% [65.6, 84.5] n=76 | 64.6% [50.4, 76.6] n=48 |
| stable | count_ungated | 23.5% [15.0, 34.9] n=68 | 57.1% [44.9, 68.6] n=63 | 76.3% [65.6, 84.5] n=76 | 64.6% [50.4, 76.6] n=48 |
| stable | calendar_gated | 25.0% [16.2, 36.4] n=68 | 50.8% [38.8, 62.7] n=63 | 73.7% [62.8, 82.3] n=76 | 70.8% [56.8, 81.8] n=48 |
| stable | calendar_ungated | 25.0% [16.2, 36.4] n=68 | 50.8% [38.8, 62.7] n=63 | 73.7% [62.8, 82.3] n=76 | 70.8% [56.8, 81.8] n=48 |
| high_variability | count_gated | 62.5% [49.4, 74.0] n=56 | 71.0% [59.4, 80.4] n=69 | 86.4% [75.5, 93.0] n=59 | 70.5% [58.1, 80.4] n=61 |
| high_variability | count_ungated | 62.5% [49.4, 74.0] n=56 | 71.0% [59.4, 80.4] n=69 | 86.4% [75.5, 93.0] n=59 | 70.5% [58.1, 80.4] n=61 |
| high_variability | calendar_gated | 66.1% [53.0, 77.1] n=56 | 76.8% [65.6, 85.2] n=69 | 83.1% [71.5, 90.5] n=59 | 73.8% [61.6, 83.2] n=61 |
| high_variability | calendar_ungated | 66.1% [53.0, 77.1] n=56 | 76.8% [65.6, 85.2] n=69 | 83.1% [71.5, 90.5] n=59 | 73.8% [61.6, 83.2] n=61 |
| sparse | count_gated | 18.5% [10.9, 29.6] n=65 | 45.3% [33.7, 57.4] n=64 | 59.5% [48.1, 69.9] n=74 | 67.9% [54.8, 78.6] n=56 |
| sparse | count_ungated | 18.5% [10.9, 29.6] n=65 | 45.3% [33.7, 57.4] n=64 | 59.5% [48.1, 69.9] n=74 | 67.9% [54.8, 78.6] n=56 |
| sparse | calendar_gated | 6.2% [2.4, 14.8] n=65 | 10.9% [5.4, 20.9] n=64 | 17.6% [10.6, 27.8] n=74 | 23.2% [14.1, 35.8] n=56 |
| sparse | calendar_ungated | 36.9% [26.2, 49.1] n=65 | 34.4% [23.9, 46.6] n=64 | 37.8% [27.6, 49.2] n=74 | 41.1% [29.2, 54.1] n=56 |
| low_baseline | count_gated | 25.0% [16.0, 36.8] n=64 | 30.0% [20.5, 41.5] n=70 | 36.5% [26.4, 47.9] n=74 | 24.6% [15.2, 37.1] n=57 |
| low_baseline | count_ungated | 25.0% [16.0, 36.8] n=64 | 30.0% [20.5, 41.5] n=70 | 36.5% [26.4, 47.9] n=74 | 24.6% [15.2, 37.1] n=57 |
| low_baseline | calendar_gated | 31.2% [21.2, 43.4] n=64 | 37.1% [26.8, 48.9] n=70 | 39.2% [28.9, 50.6] n=74 | 29.8% [19.5, 42.7] n=57 |
| low_baseline | calendar_ungated | 31.2% [21.2, 43.4] n=64 | 37.1% [26.8, 48.9] n=70 | 39.2% [28.9, 50.6] n=74 | 29.8% [19.5, 42.7] n=57 |

## Detection by shape, and domain-correct detection by changed domain (primary, 14-day window)

| group | variant | step | gradual | gradual (previous definition) | domain-correct: sleep | domain-correct: social | domain-correct: mood |
|---|---|---|---|---|---|---|---|
| stable | count_gated | 71.9% [63.7, 78.8] | 69.2% [60.4, 76.7] | 36.7% [28.6, 45.6] | 68.2% [57.9, 77.0] | 63.3% [53.0, 72.6] | 61.0% [49.9, 71.2] |
| stable | calendar_gated | 68.9% [60.6, 76.1] | 74.2% [65.7, 81.2] | 38.3% [30.1, 47.3] | 62.5% [52.1, 71.9] | 63.3% [53.0, 72.6] | 61.0% [49.9, 71.2] |
| high_variability | count_gated | 84.2% [76.4, 89.8] | 95.4% [90.4, 97.9] | 62.6% [54.1, 70.4] | 84.4% [74.7, 90.9] | 76.8% [66.6, 84.6] | 82.6% [73.2, 89.1] |
| high_variability | calendar_gated | 81.6% [73.5, 87.6] | 93.1% [87.5, 96.3] | 69.5% [61.1, 76.7] | 79.2% [68.9, 86.8] | 80.5% [70.6, 87.6] | 82.6% [73.2, 89.1] |
| sparse | count_gated | 46.3% [38.2, 54.7] | 67.5% [58.8, 75.1] | 48.8% [40.1, 57.5] | 56.4% [45.4, 66.9] | 52.6% [42.7, 62.4] | 53.5% [43.0, 63.7] |
| sparse | calendar_gated | 17.6% [12.2, 24.9] | 14.6% [9.5, 21.9] | 10.6% [6.3, 17.2] | 10.3% [5.3, 19.0] | 20.0% [13.2, 29.1] | 8.1% [4.0, 15.9] |
| low_baseline | count_gated | 42.6% [34.4, 51.3] | 48.5% [40.3, 56.9] | 16.9% [11.5, 24.1] | 26.3% [18.6, 35.7] | 42.2% [32.1, 52.9] | 28.9% [20.3, 39.4] |
| low_baseline | calendar_gated | 52.7% [44.1, 61.1] | 57.4% [49.0, 65.4] | 17.6% [12.2, 24.9] | 27.3% [19.5, 36.8] | 53.0% [42.4, 63.4] | 31.3% [22.4, 41.9] |

## Worst group per variant (primary definition)

| variant | highest false alarms / user-month | lowest detection (14 d) |
|---|---|---|
| count_gated | high_variability: 1.95 [1.87, 2.04] | low_baseline: 45.7% [39.8, 51.7] |
| count_ungated | high_variability: 1.95 [1.86, 2.04] | low_baseline: 45.7% [39.8, 51.7] |
| calendar_gated | high_variability: 2.18 [2.10, 2.27] | sparse: 16.2% [12.2, 21.2] |
| calendar_ungated | high_variability: 2.19 [2.10, 2.27] | sparse: 49.4% [43.4, 55.5] |

## Alert precision by confidence label (all groups pooled)

Confidence is a three-level label based on data quantity only (how many check-ins are in each window); it does not look at the scores and is not a probability, so this is not a calibration analysis. Correct = the episode starts in a changed user's 14-day TP window; every other episode is incorrect. **Precision depends on the 50% prevalence of changed users chosen for the simulation.** Wilson intervals over episodes ignore clustering within users. Rows with fewer than 100 episodes are too few to conclude.

| variant | confidence of first alert | precision (primary) | precision (previous definition) | episodes |
|---|---|---|---|---|
| count_gated | moderate | 0.0% [0.0, 7.3] | 0.0% [0.0, 7.3] | 49 (too few episodes to conclude) |
| count_gated | strong | 21.6% [20.3, 22.8] | 14.5% [13.5, 15.6] | 4268 |
| count_ungated | low | 0.0% [0.0, 3.0] | 0.0% [0.0, 3.0] | 125 |
| count_ungated | moderate | 0.0% [0.0, 10.7] | 0.0% [0.0, 10.7] | 32 (too few episodes to conclude) |
| count_ungated | strong | 21.6% [20.3, 22.8] | 14.5% [13.5, 15.6] | 4268 |
| calendar_gated | moderate | 18.8% [16.9, 20.8] | 12.6% [11.1, 14.4] | 1520 |
| calendar_gated | strong | 17.1% [15.9, 18.4] | 10.8% [9.8, 11.9] | 3474 |
| calendar_ungated | low | 20.5% [17.4, 23.9] | 13.4% [10.9, 16.4] | 596 |
| calendar_ungated | moderate | 18.2% [16.3, 20.2] | 12.0% [10.4, 13.7] | 1471 |
| calendar_ungated | strong | 17.1% [15.9, 18.4] | 10.8% [9.8, 11.9] | 3474 |

### Grid: false-alarm episodes / user-month, count_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.06 | 0.08 | 0.09 | 0.11 | 0.15 | 0.20 | 0.21 | 0.23 |
| 0.45 | 0.06 | 0.13 | 0.15 | 0.22 | 0.24 | 0.31 | 0.35 | 0.38 |
| 0.60 | 0.11 | 0.21 | 0.24 | 0.41 | 0.47 | 0.61 | 0.68 | 0.73 |
| 0.75 | 0.21 | 0.37 | 0.46 | 0.68 | 0.88 | 1.04 | 1.14 | 1.28 |
| 0.90 | 0.32 | 0.58 | 0.73 | 0.96 | 1.11 | 1.36 | 1.53 | 1.73 |
| 1.05 | 0.47 | 0.73 | 0.94 | 1.23 | 1.47 | 1.77 | 1.97 | 2.19 |
| 1.20 | 0.56 | 0.90 | 1.18 | 1.47 | 1.79 | 2.07 | 2.30 | 2.55 |

### Grid: detection rate (primary, 14 d), count_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.39 | 0.51 | 0.55 | 0.60 | 0.60 | 0.62 | 0.60 | 0.61 |
| 0.45 | 0.44 | 0.55 | 0.62 | 0.64 | 0.62 | 0.65 | 0.65 | 0.69 |
| 0.60 | 0.45 | 0.58 | 0.66 | 0.71 | 0.73 | 0.74 | 0.78 | 0.78 |
| 0.75 | 0.47 | 0.65 | 0.67 | 0.73 | 0.80 | 0.83 | 0.87 | 0.90 |
| 0.90 | 0.55 | 0.65 | 0.70 | 0.79 | 0.88 | 0.87 | 0.93 | 0.92 |
| 1.05 | 0.58 | 0.66 | 0.74 | 0.85 | 0.87 | 0.90 | 0.93 | 0.97 |
| 1.20 | 0.55 | 0.73 | 0.74 | 0.85 | 0.91 | 0.92 | 0.93 | 0.92 |

### Grid: chance detection rate (primary, 14 d, no-change users), count_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.04 | 0.04 | 0.03 | 0.04 | 0.06 | 0.08 | 0.10 | 0.11 |
| 0.45 | 0.04 | 0.06 | 0.10 | 0.08 | 0.10 | 0.17 | 0.20 | 0.19 |
| 0.60 | 0.07 | 0.10 | 0.14 | 0.22 | 0.24 | 0.32 | 0.40 | 0.38 |
| 0.75 | 0.16 | 0.19 | 0.24 | 0.34 | 0.39 | 0.43 | 0.49 | 0.60 |
| 0.90 | 0.29 | 0.30 | 0.38 | 0.43 | 0.48 | 0.57 | 0.64 | 0.74 |
| 1.05 | 0.40 | 0.38 | 0.52 | 0.57 | 0.64 | 0.74 | 0.73 | 0.80 |
| 1.20 | 0.49 | 0.51 | 0.60 | 0.66 | 0.78 | 0.79 | 0.82 | 0.88 |

### Grid: false-alarm episodes / user-month, calendar_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.01 | 0.06 | 0.15 | 0.24 | 0.32 | 0.32 | 0.31 | 0.23 |
| 0.45 | 0.01 | 0.08 | 0.24 | 0.39 | 0.50 | 0.54 | 0.52 | 0.38 |
| 0.60 | 0.05 | 0.19 | 0.42 | 0.68 | 0.88 | 0.95 | 0.85 | 0.73 |
| 0.75 | 0.05 | 0.24 | 0.60 | 1.02 | 1.36 | 1.45 | 1.39 | 1.28 |
| 0.90 | 0.05 | 0.29 | 0.73 | 1.29 | 1.63 | 1.81 | 1.81 | 1.73 |
| 1.05 | 0.06 | 0.34 | 0.85 | 1.43 | 1.89 | 2.15 | 2.28 | 2.19 |
| 1.20 | 0.08 | 0.39 | 0.99 | 1.65 | 2.14 | 2.39 | 2.51 | 2.55 |

### Grid: detection rate (primary, 14 d), calendar_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.01 | 0.08 | 0.24 | 0.38 | 0.54 | 0.60 | 0.63 | 0.61 |
| 0.45 | 0.02 | 0.16 | 0.31 | 0.44 | 0.67 | 0.65 | 0.68 | 0.69 |
| 0.60 | 0.03 | 0.19 | 0.36 | 0.52 | 0.81 | 0.79 | 0.82 | 0.78 |
| 0.75 | 0.05 | 0.20 | 0.45 | 0.64 | 0.84 | 0.85 | 0.90 | 0.90 |
| 0.90 | 0.05 | 0.23 | 0.49 | 0.65 | 0.89 | 0.91 | 0.92 | 0.92 |
| 1.05 | 0.05 | 0.26 | 0.52 | 0.67 | 0.93 | 0.90 | 0.93 | 0.97 |
| 1.20 | 0.06 | 0.26 | 0.55 | 0.69 | 0.93 | 0.93 | 0.93 | 0.92 |

### Grid: chance detection rate (primary, 14 d, no-change users), calendar_gated (200 users per cell, baseline N(3.5, 0.5))

| noise SD \ check-in rate | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | 0.00 | 0.03 | 0.11 | 0.13 | 0.18 | 0.20 | 0.17 | 0.11 |
| 0.45 | 0.00 | 0.04 | 0.17 | 0.22 | 0.26 | 0.28 | 0.27 | 0.19 |
| 0.60 | 0.03 | 0.12 | 0.27 | 0.38 | 0.50 | 0.47 | 0.40 | 0.38 |
| 0.75 | 0.04 | 0.14 | 0.32 | 0.50 | 0.61 | 0.66 | 0.59 | 0.60 |
| 0.90 | 0.03 | 0.18 | 0.37 | 0.56 | 0.64 | 0.72 | 0.77 | 0.74 |
| 1.05 | 0.04 | 0.22 | 0.40 | 0.61 | 0.70 | 0.77 | 0.81 | 0.80 |
| 1.20 | 0.06 | 0.24 | 0.46 | 0.71 | 0.82 | 0.88 | 0.88 | 0.88 |

## Personalised threshold and tuned global control (evaluation only, not app behaviour)

Personalised rule: same as the current detector (count windows, gated), but each domain's threshold is `max(FLOOR, K * sd)`, where sd is the SD of the user's own normalised scores over up to 28 check-ins before the recent window (fixed 0.25 if fewer than 4). It needs up to 35 past check-ins; the app fetches 14.

Control (tuned global): one constant threshold T for every user and domain, otherwise the same detector. It needs no extra history.

Both were tuned on **tuning users** (seed 1, 150 per group) with the same objective, the mean over groups of (detection - chance), primary definition, W = 14. Results are on **held-out users** (seed 2, 500 per group) never used for tuning. Tuning and held-out users come from the same simulator and group settings, so this does not show either rule would work on other data.

Chosen: personalised K = 1.25, FLOOR = 0.1875; tuned global T = 0.2375.

| rule | objective on tuning users | objective on held-out users |
|---|---|---|
| current (fixed 0.25) | 0.375 | 0.338 |
| tuned global (T = 0.2375) | 0.379 | 0.343 |
| personalised (K = 1.25, FLOOR = 0.1875) | 0.400 | 0.393 |

Paired differences in the held-out objective (same users; 95% paired bootstrap):

| comparison | difference [95% CI] |
|---|---|
| tuned global - current | +0.005 [-0.002, +0.013] |
| personalised - current | +0.056 [+0.022, +0.090] |
| personalised - tuned global | +0.050 [+0.017, +0.085] |

### Tuning grids (tuning users only)

| K | FLOOR | objective |
|---|---|---|
| 0.5 | 0.125 | 0.086 |
| 0.5 | 0.1875 | 0.292 |
| 0.5 | 0.25 | 0.375 |
| 0.75 | 0.125 | 0.144 |
| 0.75 | 0.1875 | 0.295 |
| 0.75 | 0.25 | 0.375 |
| 1 | 0.125 | 0.242 |
| 1 | 0.1875 | 0.384 |
| 1 | 0.25 | 0.387 |
| 1.25 | 0.125 | 0.355 |
| 1.25 | 0.1875 | 0.400 **chosen** |
| 1.25 | 0.25 | 0.384 |
| 1.5 | 0.125 | 0.381 |
| 1.5 | 0.1875 | 0.386 |
| 1.5 | 0.25 | 0.379 |
| 2 | 0.125 | 0.307 |
| 2 | 0.1875 | 0.314 |
| 2 | 0.25 | 0.300 |
| 2.5 | 0.125 | 0.166 |
| 2.5 | 0.1875 | 0.169 |
| 2.5 | 0.25 | 0.166 |
| 3 | 0.125 | 0.100 |
| 3 | 0.1875 | 0.103 |
| 3 | 0.25 | 0.100 |

Global T (thresholds between possible delta values give identical results, hence plateaus):

| T | objective |
|---|---|
| 0.1 | 0.035 |
| 0.1125 | 0.089 |
| 0.125 | 0.089 |
| 0.1375 | 0.089 |
| 0.15 | 0.276 |
| 0.1625 | 0.276 |
| 0.175 | 0.276 |
| 0.1875 | 0.292 |
| 0.2 | 0.292 |
| 0.2125 | 0.292 |
| 0.225 | 0.379 |
| 0.2375 | 0.379 **chosen** |
| 0.25 | 0.375 |
| 0.2625 | 0.322 |
| 0.275 | 0.322 |
| 0.2875 | 0.252 |
| 0.3 | 0.252 |
| 0.3125 | 0.252 |
| 0.325 | 0.207 |
| 0.3375 | 0.207 |
| 0.35 | 0.207 |
| 0.3625 | 0.179 |
| 0.375 | 0.179 |
| 0.3875 | 0.179 |
| 0.4 | 0.153 |

### Held-out results: current vs tuned global vs personalised

| group | variant | false-alarm episodes / user-month | detected (14 d, primary) | chance (14 d) | detected - chance | domain-correct (14 d) | median delay [CI] |
|---|---|---|---|---|---|---|---|
| stable | current (count_gated) | 0.42 [0.37, 0.47] | 71.9% [66.0, 77.1] | 27.5% [22.3, 33.3] | 44.4 pts | 67.1% [61.0, 72.6] | 6 [5, 7] (IQR 4-11) |
| stable | tuned global T=0.2375 | 0.43 [0.38, 0.48] | 73.5% [67.7, 78.6] | 27.9% [22.7, 33.7] | 45.6 pts | 68.7% [62.7, 74.1] | 6 [6, 7] (IQR 4-10) |
| stable | personalised | 0.49 [0.44, 0.54] | 80.3% [74.9, 84.8] | 30.3% [24.9, 36.2] | 50.0 pts | 75.5% [69.8, 80.4] | 6 [5, 7] (IQR 3-10) |
| high_variability | current (count_gated) | 1.86 [1.78, 1.93] | 94.4% [90.7, 96.7] | 79.5% [74.2, 83.9] | 14.9 pts | 83.6% [78.3, 87.8] | 5 [4, 5] (IQR 2-8) |
| high_variability | tuned global T=0.2375 | 1.88 [1.81, 1.96] | 94.4% [90.7, 96.7] | 80.6% [75.4, 84.9] | 13.8 pts | 83.2% [77.8, 87.5] | 5 [4, 5] (IQR 2-8) |
| high_variability | personalised | 1.10 [1.04, 1.17] | 78.0% [72.3, 82.9] | 54.5% [48.5, 60.3] | 23.5 pts | 63.4% [57.0, 69.3] | 6 [5, 7] (IQR 3-11) |
| sparse | current (count_gated) | 0.13 [0.10, 0.16] | 57.3% [50.9, 63.3] | 5.8% [3.5, 9.3] | 51.5 pts | 54.8% [48.5, 60.9] | 11 [10, 12] (IQR 8-16) |
| sparse | tuned global T=0.2375 | 0.14 [0.11, 0.16] | 59.3% [53.0, 65.3] | 5.8% [3.5, 9.3] | 53.5 pts | 56.4% [50.1, 62.5] | 11 [10, 13] (IQR 8-16) |
| sparse | personalised | 0.17 [0.14, 0.20] | 65.6% [59.4, 71.3] | 8.5% [5.7, 12.5] | 57.1 pts | 62.7% [56.4, 68.5] | 11 [9, 12] (IQR 7-15) |
| low_baseline | current (count_gated) | 0.55 [0.49, 0.61] | 50.6% [44.5, 56.6] | 26.4% [21.2, 32.3] | 24.2 pts | 30.7% [25.4, 36.5] | 6 [6, 8] (IQR 4-11) |
| low_baseline | tuned global T=0.2375 | 0.56 [0.50, 0.62] | 50.6% [44.5, 56.6] | 26.4% [21.2, 32.3] | 24.2 pts | 30.7% [25.4, 36.5] | 6 [6, 7] (IQR 4-11) |
| low_baseline | personalised | 0.54 [0.48, 0.59] | 55.9% [49.9, 61.8] | 29.3% [23.9, 35.3] | 26.6 pts | 39.8% [34.1, 45.9] | 6 [6, 7] (IQR 4-10) |
