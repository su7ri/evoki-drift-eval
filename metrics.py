"""
Metrics for the drift detector on simulated users.

All numbers produced here depend on the simulator's assumptions (simulate.py).
They are not clinical validation and do not come from real users.

Definitions
- Alarm: a negative domain alert (MEDIUM or HIGH). Positive alerts are ignored.
- Run: one detector evaluation, right after a day's check-in.
- Episode: consecutive runs that fire. A day without a check-in (no run) does
  not split an episode. "Any-domain" episodes fire if any domain alarms;
  per-domain episodes only consider one domain.
- Alarm-day: a run that fires.
- Full-change day: step -> onset; gradual -> onset + 13 (ramp reaches full size).
- TP window, two definitions (W = 14 primary; 7 and 21 as sensitivity):
  * "primary"     : [onset, full-change day + W - 1]. For steps this is W days
                    from onset; for gradual changes it also covers the ramp.
  * "full_change" : [full-change day, full-change day + W - 1]. This was the
                    first primary definition. It was replaced after the first
                    results showed that alarms starting during a gradual ramp
                    were counted as misses. Kept as a sensitivity analysis.
  Windows may be cut off at day 89.
- Detected: an any-domain episode STARTS inside the TP window. Episodes already
  running when the window opens do not count.
- Domain-correct: a per-domain episode for the changed domain starts in the window.
- Delay: start of the first qualifying episode minus ONSET.
- False alarms per user-month: no-change users only; episodes starting on
  day >= 14, divided by (90 - 14) / 30 user-months. Alarm-days the same way.
- Chance detection: each no-change user gets a pseudo onset and shape drawn
  like a real change (seeded from the user id), and the SAME window rule is
  applied (same definition, same W, so the same window length: W days for a
  pseudo step, W + 13 days for a pseudo gradual change). This is the detection
  rate expected from false alarms alone.
- Precision by confidence: every any-domain episode starting on day >= 14, in
  all users. Correct = the user has a change and the episode starts in the
  14-day TP window (per definition); anything else is incorrect. Confidence =
  the label of the first run of the episode (all domains in one run share it,
  because it only depends on window counts).

Confidence intervals (95%)
- Proportions: Wilson score interval.
- False-alarm rates and median delay: percentile bootstrap over users
  (2000 resamples, fixed seed), which respects that one user can have many
  episodes. Precision uses Wilson over episodes, which ignores clustering
  within users and is therefore somewhat too narrow.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

import simulate as sim

WARMUP_DAYS = 14
WINDOWS = (7, 14, 21)
PRIMARY_WINDOW = 14
USER_MONTHS = (sim.N_DAYS - WARMUP_DAYS) / 30.0
BOOT_N = 2000
BOOT_SEED = 7


@dataclass(frozen=True)
class Episode:
    start: int
    end: int
    n_runs: int
    confidence: str


def episodes(runs: Sequence[sim.Run], domain: Optional[str] = None) -> List[Episode]:
    out, cur = [], None
    for r in runs:
        fire = (domain in r.neg) if domain else bool(r.neg)
        if fire:
            if cur is None:
                conf = r.neg[domain] if domain else next(iter(r.neg.values()))
                cur = [r.day, r.day, 1, conf]
            else:
                cur[1] = r.day
                cur[2] += 1
        elif cur is not None:
            out.append(Episode(*cur))
            cur = None
    if cur is not None:
        out.append(Episode(*cur))
    return out


def full_change_day(u: sim.SimUser) -> int:
    return u.onset if u.shape == "step" else u.onset + sim.GRADUAL_RAMP_DAYS - 1


DEFINITIONS = ("primary", "full_change")


def window(u: sim.SimUser, w: int, definition: str = "primary"):
    full = full_change_day(u)
    start = u.onset if definition == "primary" else full
    return start, full + w - 1


def in_window(day: int, u: sim.SimUser, w: int, definition: str = "primary") -> bool:
    lo, hi = window(u, w, definition)
    return lo <= day <= hi


@dataclass
class UserResult:
    uid: str
    group: str
    has_change: bool
    domain: Optional[str]
    size: Optional[float]
    shape: Optional[str]
    fa_episodes: int = 0
    fa_alarm_days: int = 0
    fa_by_domain: Dict[str, int] = field(default_factory=dict)
    # keyed by (definition, W)
    detected: Dict[tuple, bool] = field(default_factory=dict)
    detected_domain: Dict[tuple, bool] = field(default_factory=dict)
    delay: Dict[tuple, Optional[int]] = field(default_factory=dict)
    chance: Dict[tuple, bool] = field(default_factory=dict)     # no-change users only
    episode_marks: List[tuple] = field(default_factory=list)   # (confidence, {definition: correct})


def pseudo_change(u: sim.SimUser) -> sim.SimUser:
    """A fake onset/shape for a no-change user, drawn like a real change."""
    rng = np.random.default_rng(zlib.crc32(u.uid.encode()))
    onset = int(rng.integers(sim.ONSET_RANGE[0], sim.ONSET_RANGE[1] + 1))
    shape = ("step", "gradual")[rng.integers(2)]
    return sim.SimUser(u.uid, u.group, True, None, onset, shape, None)


def score_user(u: sim.SimUser, runs: Sequence[sim.Run]) -> UserResult:
    res = UserResult(u.uid, u.group, u.has_change, u.change_domain, u.size, u.shape)
    any_eps = episodes(runs)

    for e in any_eps:
        if e.start >= WARMUP_DAYS:
            correct = {d: bool(u.has_change and in_window(e.start, u, PRIMARY_WINDOW, d))
                       for d in DEFINITIONS}
            res.episode_marks.append((e.confidence, correct))

    if not u.has_change:
        res.fa_episodes = sum(e.start >= WARMUP_DAYS for e in any_eps)
        res.fa_alarm_days = sum(bool(r.neg) and r.day >= WARMUP_DAYS for r in runs)
        for d in sim.DOMAINS:
            res.fa_by_domain[d] = sum(e.start >= WARMUP_DAYS for e in episodes(runs, d))
        fake = pseudo_change(u)
        for d in DEFINITIONS:
            for w in WINDOWS:
                res.chance[(d, w)] = any(in_window(e.start, fake, w, d) for e in any_eps)
        return res

    dom_eps = episodes(runs, u.change_domain)
    for d in DEFINITIONS:
        for w in WINDOWS:
            hits = [e for e in any_eps if in_window(e.start, u, w, d)]
            res.detected[(d, w)] = bool(hits)
            res.delay[(d, w)] = (hits[0].start - u.onset) if hits else None
            res.detected_domain[(d, w)] = any(in_window(e.start, u, w, d) for e in dom_eps)
    return res


def evaluate(users: Sequence[sim.SimUser], variant: str) -> List[UserResult]:
    return [score_user(u, sim.evaluate_user(u, variant)) for u in users]


# ---------------------------------------------------------------------------
# Intervals
# ---------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (math.nan, math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, c - h), min(1.0, c + h))


def boot(values: Sequence[float], stat, seed: int = BOOT_SEED):
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return (math.nan, math.nan, math.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(BOOT_N, len(v)))
    reps = np.array([stat(v[i]) for i in idx])
    return (float(stat(v)), float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5)))


def fa_rate(results: Sequence[UserResult], attr: str = "fa_episodes"):
    vals = [getattr(r, attr) / USER_MONTHS for r in results if not r.has_change]
    return boot(vals, np.mean)


def detection(results: Sequence[UserResult], w: int = PRIMARY_WINDOW, domain_correct: bool = False,
              definition: str = "primary", **filters):
    rs = [r for r in results if r.has_change and all(getattr(r, k) == v for k, v in filters.items())]
    key = "detected_domain" if domain_correct else "detected"
    k = sum(getattr(r, key)[(definition, w)] for r in rs)
    return wilson(k, len(rs)) + (len(rs),)


def chance_detection(results: Sequence[UserResult], w: int = PRIMARY_WINDOW, definition: str = "primary"):
    rs = [r for r in results if not r.has_change]
    return wilson(sum(r.chance[(definition, w)] for r in rs), len(rs)) + (len(rs),)


def delay(results: Sequence[UserResult], w: int = PRIMARY_WINDOW, definition: str = "primary"):
    d = [r.delay[(definition, w)] for r in results if r.has_change and r.delay[(definition, w)] is not None]
    med = boot(d, np.median)
    q1, q3 = (np.percentile(d, 25), np.percentile(d, 75)) if d else (math.nan, math.nan)
    return med + (float(q1), float(q3), len(d))


def precision_by_confidence(results: Sequence[UserResult], definition: str = "primary"):
    out = {}
    for conf in ("low", "moderate", "strong"):
        marks = [c[definition] for r in results for (lab, c) in r.episode_marks if lab == conf]
        out[conf] = wilson(sum(marks), len(marks)) + (len(marks),)
    return out


# ---------------------------------------------------------------------------
# Noise x check-in-rate grid
# ---------------------------------------------------------------------------

GRID_NOISE = (0.3, 0.45, 0.6, 0.75, 0.9, 1.05, 1.2)
GRID_RATE = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
GRID_USERS = 200
GRID_VARIANTS = ("count_gated", "calendar_gated")


def grid(n_users: int = GRID_USERS, seed: int = sim.SEED + 1):
    """Each cell reuses the same per-user random streams (common random numbers),
    so differences between cells come from noise SD and check-in rate only."""
    streams = np.random.SeedSequence(seed).spawn(n_users)
    out = {v: {k: np.full((len(GRID_NOISE), len(GRID_RATE)), np.nan) for k in ("fa", "det", "chance")}
           for v in GRID_VARIANTS}
    for i, sd in enumerate(GRID_NOISE):
        for j, p in enumerate(GRID_RATE):
            spec = sim.GroupSpec(p_checkin=p, noise_sd=sd)
            users = [sim.simulate_user("grid", k, np.random.default_rng(s), spec=spec)
                     for k, s in enumerate(streams)]
            for v in GRID_VARIANTS:
                res = evaluate(users, v)
                out[v]["fa"][i, j] = np.mean([r.fa_episodes / USER_MONTHS for r in res if not r.has_change])
                out[v]["det"][i, j] = np.mean([r.detected[("primary", PRIMARY_WINDOW)]
                                               for r in res if r.has_change])
                out[v]["chance"][i, j] = np.mean([r.chance[("primary", PRIMARY_WINDOW)]
                                                  for r in res if not r.has_change])
    return out
