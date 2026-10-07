"""
Personalised-threshold variant (evaluation only; NOT app behaviour).

Identical to the current detector (count windows, gating, recent >= 4,
non-empty previous, same confidence rule) except for the domain threshold:

    thr_d = max(FLOOR, K * sd_d)

sd_d = sample SD (ddof = 1) of the user's own normalised scores for domain d
over the check-ins BEFORE the recent window (at most HIST_N = 28 of them).
If fewer than MIN_HIST = 4 such check-ins exist, thr_d = 0.25 (the app's
fixed value). Negative alert: delta <= -thr_d. (Positive alerts are not
scored and are not computed here.)

Note: this needs up to 35 past check-ins, while the app currently fetches 14.

Parameter choice (K, FLOOR) uses TUNING users only (seed TUNE_SEED). Results
are reported on HELD-OUT users (seed EVAL_SEED), which are never used for
tuning. Both sets come from the same simulator and the same group settings,
so this does not show that the rule would transfer to other data.

Tuning objective, fixed before tuning: maximise the mean over the four groups
of (detection rate - chance rate), primary TP definition, W = 14. Ties go to
the smaller K, then the larger FLOOR.

Control ("tuned global"): one constant threshold T for every user and domain
(delta <= -T), tuned on the SAME tuning users with the SAME objective over
GLOBAL_GRID, and evaluated on the SAME held-out users. Ties go to the larger T.
If the personalised rule is not better than this control, its gains come from
a different overall threshold level, not from personalisation. The control
needs no extra history beyond what the app already fetches.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

import detector as det
import metrics as m
import simulate as sim

HIST_N = 28
MIN_HIST = 4
TUNE_SEED = 1
EVAL_SEED = 2
TUNE_USERS_PER_GROUP = 150
EVAL_USERS_PER_GROUP = sim.N_USERS_PER_GROUP

K_GRID = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
FLOOR_GRID = (0.125, 0.1875, 0.25)
GLOBAL_GRID = tuple(round(0.1 + 0.0125 * i, 4) for i in range(25))   # 0.10 ... 0.40

NORM = {"sleep": det.normalized_sleep, "social": det.normalized_social, "mood": det.normalized_mood}


@dataclass(frozen=True)
class DayStats:
    day: int
    confidence: str
    delta: Dict[str, float]        # empty if no domain alert is possible on this run
    sd: Dict[str, float]           # nan if fewer than MIN_HIST history check-ins


def precompute(user: sim.SimUser) -> List[DayStats]:
    """Per run: confidence, delta and historical SD per domain. Thresholds are
    applied later, so tuning does not recompute these."""
    out = []
    cis = user.check_ins                      # one per date, already in date order
    for i, c in enumerate(cis):
        day = (np.datetime64(c.date) - np.datetime64(sim.START_DATE.isoformat())).astype(int)
        ordered = cis[: i + 1]
        recent = ordered[-7:]
        previous = ordered[: len(ordered) - len(recent)][-7:]
        hist = ordered[: len(ordered) - len(recent)][-HIST_N:]
        conf = det.check_in_confidence(len(recent), len(previous))
        ok = (len(ordered) >= 3 and len(recent) >= 4 and len(previous) > 0
              and det.has_enough_data_for_alert(conf))
        delta, sd = {}, {}
        if ok:
            for d, norm in NORM.items():
                r = [norm(getattr(x, d)) for x in recent]
                p = [norm(getattr(x, d)) for x in previous]
                delta[d] = det._mean(r) - det._mean(p)
                h = [norm(getattr(x, d)) for x in hist]
                sd[d] = float(np.std(h, ddof=1)) if len(h) >= MIN_HIST else float("nan")
        out.append(DayStats(int(day), conf, delta, sd))
    return out


def threshold(sd: float, k: float, floor: float) -> float:
    if np.isnan(sd):
        return 0.25
    return max(floor, k * sd)


def runs_for(stats: Sequence[DayStats], k: float, floor: float) -> List[sim.Run]:
    runs = []
    for s in stats:
        neg = {d: s.confidence for d, dl in s.delta.items() if dl <= -threshold(s.sd[d], k, floor)}
        runs.append(sim.Run(day=s.day, neg=neg))
    return runs


def global_runs(stats: Sequence[DayStats], t: float) -> List[sim.Run]:
    """One constant threshold for every user and domain."""
    return [sim.Run(day=s.day, neg={d: s.confidence for d, dl in s.delta.items() if dl <= -t})
            for s in stats]


def fixed_runs(stats: Sequence[DayStats]) -> List[sim.Run]:
    """The current fixed 0.25 threshold computed from the same statistics."""
    return global_runs(stats, 0.25)


def objective(results: Sequence[m.UserResult]) -> float:
    vals = []
    for g in sim.GROUPS:
        rs = [r for r in results if r.group == g]
        vals.append(m.detection(rs)[0] - m.chance_detection(rs)[0])
    return float(np.mean(vals))


def tune():
    """Returns (best personalised (K, FLOOR), personalised table, best global T,
    global table, objective of the fixed 0.25 rule), all on tuning users."""
    users = sim.simulate_all(n_per_group=TUNE_USERS_PER_GROUP, seed=TUNE_SEED)
    stats = [precompute(u) for u in users]
    table = []
    for k in K_GRID:
        for fl in FLOOR_GRID:
            res = [m.score_user(u, runs_for(s, k, fl)) for u, s in zip(users, stats)]
            table.append((k, fl, objective(res)))
    best = max(table, key=lambda t: (round(t[2], 10), -t[0], t[1]))
    gtable = []
    for t in GLOBAL_GRID:
        res = [m.score_user(u, global_runs(s, t)) for u, s in zip(users, stats)]
        gtable.append((t, objective(res)))
    gbest = max(gtable, key=lambda r: (round(r[1], 10), r[0]))
    baseline = objective([m.score_user(u, fixed_runs(s)) for u, s in zip(users, stats)])
    return (best[0], best[1]), table, gbest[0], gtable, baseline


def evaluate_held_out(k: float, floor: float, t_global: float):
    users = sim.simulate_all(n_per_group=EVAL_USERS_PER_GROUP, seed=EVAL_SEED)
    stats = [precompute(u) for u in users]
    current = [m.score_user(u, sim.evaluate_user(u, "count_gated")) for u in users]
    glob = [m.score_user(u, global_runs(s, t_global)) for u, s in zip(users, stats)]
    pers = [m.score_user(u, runs_for(s, k, floor)) for u, s in zip(users, stats)]
    return users, current, glob, pers


def paired_objective_diff(res_a: Sequence[m.UserResult], res_b: Sequence[m.UserResult],
                          n_boot: int = m.BOOT_N, seed: int = m.BOOT_SEED):
    """Objective(b) - objective(a) on the SAME users, with a 95% paired bootstrap
    interval (users resampled within each group, separately for changed and
    no-change users, identically for both variants)."""
    rng = np.random.default_rng(seed)
    point = objective(res_b) - objective(res_a)
    parts = []
    for g in sim.GROUPS:
        a = [r for r in res_a if r.group == g]
        b = {r.uid: r for r in res_b if r.group == g}
        da = np.array([r.detected[("primary", m.PRIMARY_WINDOW)] for r in a if r.has_change], float)
        db = np.array([b[r.uid].detected[("primary", m.PRIMARY_WINDOW)] for r in a if r.has_change], float)
        ca = np.array([r.chance[("primary", m.PRIMARY_WINDOW)] for r in a if not r.has_change], float)
        cb = np.array([b[r.uid].chance[("primary", m.PRIMARY_WINDOW)] for r in a if not r.has_change], float)
        i = rng.integers(0, len(da), size=(n_boot, len(da)))
        j = rng.integers(0, len(ca), size=(n_boot, len(ca)))
        parts.append((db[i].mean(1) - da[i].mean(1)) - (cb[j].mean(1) - ca[j].mean(1)))
    reps = np.mean(parts, axis=0)
    return point, float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))
