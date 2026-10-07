"""
Synthetic check-in generator for evaluating detector.py.

IMPORTANT: the groups below are BEHAVIOUR TYPES (how regularly and how
consistently someone answers the check-in). They are not demographics and do
not represent age, sex, diagnosis or any other population group. All numbers
are assumptions chosen for this evaluation, not estimates from real users.

Model, per user and per domain (sleep, social, mood):
    latent[t] = baseline + noise[t] - change[t]
    noise     = AR(1), phi = 0.3, stationary SD = group noise_sd
    observed  = clamp(floor(latent + 0.5), scale_min, scale_max)
    a check-in exists on day t with probability p_checkin (independent days)
Domains are simulated independently of each other.

Units: noise_sd and change sizes are stated on the 1-5 scale (sleep, mood).
Social uses a 0-2 scale, so its baseline, noise and change are multiplied by
0.5 (the same fraction of the scale range), so the latent normalised effect is
equal across domains. Example: a "1 point" change is -1.0 on sleep/mood and
-0.5 on social; both are -0.25 normalised. After rounding, social has only
3 levels, so the observed effect is coarser; results are reported per domain.

Ground truth: 50% of users have exactly one true decline in one randomly
chosen domain; the other domains stay stable. Onset day uniform in [40, 60],
shape step (full size from onset) or gradual (linear ramp reaching full size
on day onset+13). Size uniform from {0.5, 1, 1.5, 2} points.

Run `python simulate.py` to write figures/sample_users.png.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

import detector as det

SEED = 20261006
N_DAYS = 90
N_USERS_PER_GROUP = 500
START_DATE = dt.date(2026, 1, 1)

DOMAINS = ("sleep", "social", "mood")
DOMAIN_TO_DETECTOR = {"sleep": det.SLEEP, "social": det.SOCIAL, "mood": det.MOOD}
SCALE = {"sleep": (1, 5), "social": (0, 2), "mood": (1, 5)}
UNIT = {"sleep": 1.0, "social": 0.5, "mood": 1.0}   # 1-5-scale points -> domain points

CHANGE_SIZES = (0.5, 1.0, 1.5, 2.0)
ONSET_RANGE = (40, 60)        # inclusive
GRADUAL_RAMP_DAYS = 14
AR_PHI = 0.3


@dataclass(frozen=True)
class GroupSpec:
    """Behaviour type (not a demographic group)."""
    p_checkin: float
    noise_sd: float                  # on the 1-5 scale; social uses x0.5
    baseline_mean: float = 3.5       # on the 1-5 scale; social = (x - 1) * 0.5
    baseline_sd: float = 0.5


GROUPS: Dict[str, GroupSpec] = {
    # Answers most days, small day-to-day swings.
    "stable": GroupSpec(p_checkin=0.9, noise_sd=0.5),
    # Answers most days, large day-to-day swings.
    "high_variability": GroupSpec(p_checkin=0.9, noise_sd=1.0),
    # Same swings as "stable", but ~60% of days have no check-in.
    "sparse": GroupSpec(p_checkin=0.4, noise_sd=0.5),
    # Answers most days, baseline near the bottom of the scale (floor effect:
    # a decline can only partly show because scores are clamped at the minimum).
    "low_baseline": GroupSpec(p_checkin=0.9, noise_sd=0.5, baseline_mean=1.8, baseline_sd=0.3),
}


@dataclass
class SimUser:
    uid: str
    group: str
    has_change: bool
    change_domain: Optional[str]
    onset: Optional[int]
    shape: Optional[str]
    size: Optional[float]               # 1-5-scale points
    latent: Dict[str, np.ndarray] = field(repr=False, default_factory=dict)
    check_ins: List[det.CheckIn] = field(repr=False, default_factory=list)


def day_to_date(day: int) -> str:
    return (START_DATE + dt.timedelta(days=day)).isoformat()


def _domain_baseline(spec: GroupSpec, domain: str, rng: np.random.Generator) -> float:
    b = rng.normal(spec.baseline_mean, spec.baseline_sd)     # 1-5 scale
    lo, hi = SCALE[domain]
    if domain == "social":
        b = (b - 1.0) * 0.5
    return float(np.clip(b, lo, hi))


def _ar1(n: int, sd: float, rng: np.random.Generator) -> np.ndarray:
    e = np.empty(n)
    e[0] = rng.normal(0, sd)
    innov_sd = sd * np.sqrt(1 - AR_PHI ** 2)
    for t in range(1, n):
        e[t] = AR_PHI * e[t - 1] + rng.normal(0, innov_sd)
    return e


def change_profile(n: int, onset: int, shape: str, size: float) -> np.ndarray:
    days = np.arange(n)
    if shape == "step":
        frac = (days >= onset).astype(float)
    else:
        frac = np.clip((days - onset + 1) / GRADUAL_RAMP_DAYS, 0.0, 1.0)
    return size * frac


def simulate_user(group: str, idx: int, rng: np.random.Generator,
                  spec: Optional[GroupSpec] = None) -> SimUser:
    """`spec` overrides GROUPS[group] (used by the noise x check-in-rate grid)."""
    spec = spec or GROUPS[group]
    has_change = bool(rng.random() < 0.5)
    domain = onset = shape = size = None
    if has_change:
        domain = DOMAINS[rng.integers(len(DOMAINS))]
        onset = int(rng.integers(ONSET_RANGE[0], ONSET_RANGE[1] + 1))
        shape = ("step", "gradual")[rng.integers(2)]
        size = float(CHANGE_SIZES[rng.integers(len(CHANGE_SIZES))])

    latent, observed = {}, {}
    for d in DOMAINS:
        base = _domain_baseline(spec, d, rng)
        x = base + _ar1(N_DAYS, spec.noise_sd * UNIT[d], rng)
        if has_change and d == domain:
            x = x - change_profile(N_DAYS, onset, shape, size) * UNIT[d]
        lo, hi = SCALE[d]
        latent[d] = x
        observed[d] = np.clip(np.floor(x + 0.5), lo, hi).astype(int)

    present = rng.random(N_DAYS) < spec.p_checkin
    check_ins = [
        det.CheckIn(date=day_to_date(t), sleep=int(observed["sleep"][t]),
                    mood=int(observed["mood"][t]), social=int(observed["social"][t]))
        for t in range(N_DAYS) if present[t]
    ]
    return SimUser(uid=f"{group}-{idx:03d}", group=group, has_change=has_change,
                   change_domain=domain, onset=onset, shape=shape, size=size,
                   latent=latent, check_ins=check_ins)


def simulate_all(n_per_group: int = N_USERS_PER_GROUP, seed: int = SEED,
                 groups=tuple(GROUPS)) -> List[SimUser]:
    """One independent random stream per user, so results for a user do not
    change if other groups or users are added."""
    users = []
    group_seeds = np.random.SeedSequence(seed).spawn(len(GROUPS))
    for g, gss in zip(GROUPS, group_seeds):
        if g not in groups:
            continue
        for i, uss in enumerate(gss.spawn(n_per_group)):
            users.append(simulate_user(g, i, np.random.default_rng(uss)))
    return users


# ---------------------------------------------------------------------------
# Daily evaluation: one run per day, right after that day's check-in.
# ---------------------------------------------------------------------------

VARIANTS = {
    "count_gated": dict(windows="count", gating=True),     # current app behaviour
    "count_ungated": dict(windows="count", gating=False),
    "calendar_gated": dict(windows="calendar", gating=True),
    "calendar_ungated": dict(windows="calendar", gating=False),
}


@dataclass(frozen=True)
class Run:
    day: int
    neg: Dict[str, str]     # simulator domain -> confidence label, negative domain alerts only


def evaluate_user(user: SimUser, variant) -> List[Run]:
    """`variant` is a key of VARIANTS, or a callable(history, today) -> alerts
    (used by personalised.py)."""
    if callable(variant):
        detect_fn = variant
    else:
        kw = VARIANTS[variant]
        detect_fn = lambda history, today: det.run_app_pipeline(history, today=today, **kw)
    runs = []
    for i, c in enumerate(user.check_ins):
        history = user.check_ins[: i + 1]          # data available on that day
        alerts = detect_fn(history, c.date)
        neg = {}
        for a in det.negative_domain_alerts(alerts):
            sim_domain = next(k for k, v in DOMAIN_TO_DETECTOR.items() if v == a.domain)
            neg[sim_domain] = a.confidence
        day = (dt.date.fromisoformat(c.date) - START_DATE).days
        runs.append(Run(day=day, neg=neg))
    return runs


# ---------------------------------------------------------------------------
# Sample plot
# ---------------------------------------------------------------------------

def sample_plot(path: str = "figures/sample_users.png") -> None:
    import os
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
    OBS, ALARM = "#2a78d6", "#eb6834"

    # Deterministic pick: first changed user with a >= 1 point change, and first
    # unchanged user, per group.
    users = simulate_all(n_per_group=40)
    picks = []
    for g in GROUPS:
        gu = [u for u in users if u.group == g]
        picks.append(next(u for u in gu if u.has_change and u.size >= 1.0))
        picks.append(next(u for u in gu if not u.has_change))

    fig, axes = plt.subplots(len(GROUPS), 2, figsize=(11, 2.3 * len(GROUPS)),
                             sharex=True, constrained_layout=True)
    for ax, u in zip(axes.flat, picks):
        d = u.change_domain or "sleep"
        lo, hi = SCALE[d]
        days = [(dt.date.fromisoformat(c.date) - START_DATE).days for c in u.check_ins]
        vals = [getattr(c, d) for c in u.check_ins]
        runs = evaluate_user(u, "count_gated")
        same = [r.day for r in runs if d in r.neg]
        other = [r.day for r in runs if r.neg and d not in r.neg]

        ax.plot(range(N_DAYS), np.clip(u.latent[d], lo - 0.5, hi + 0.5), color=INK2,
                lw=1, alpha=0.6, label="latent (before rounding)")
        ax.scatter(days, vals, s=14, color=OBS, zorder=3, label="check-in score")
        if u.has_change:
            ax.axvline(u.onset, color=INK2, ls="--", lw=1)
            title = f"{u.group} | {d} decline {u.size:g} pt, {u.shape}, onset day {u.onset}"
        else:
            title = f"{u.group} | no change (showing {d})"
        ax.scatter(same, [hi + 0.45] * len(same), marker="v", s=30, color=ALARM,
                   zorder=4, label="alert: this domain")
        ax.scatter(other, [hi + 0.45] * len(other), marker="x", s=24, color=INK2,
                   zorder=4, label="alert: other domain")
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_ylim(lo - 0.6, hi + 0.7)
        ax.set_yticks(range(lo, hi + 1))
        ax.grid(axis="y", color=GRID, lw=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=INK2, labelsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("day", color=INK2, fontsize=9)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False, fontsize=9)
    fig.suptitle("Simulated users (synthetic data). Alerts: current detector "
                 "(count windows, gated), negative domain alerts only",
                 fontsize=10, color=INK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    print("wrote", path)


if __name__ == "__main__":
    sample_plot()
