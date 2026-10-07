"""
Python port of Evoki's drift detector.

Source of truth (git commit f389fc6383ae6416a84afea227639b4faa6f8dbb):
  - DriftDetection.swift        (DD)
  - ClinicalScoreSupport.swift  (CSS)
  - HomeViewModel.swift         (HVM) - caller
  - InMemoryRepositories.swift  (REPO) - data fetch

`detect()` mirrors DriftDetection.detect line by line. Two switches are
evaluation-only and are NOT app behaviour:
  - gating=False      -> TrendConfidence.hasEnoughDataForAlert treated as always true
  - windows="calendar" -> last 7 calendar days vs previous 7 calendar days
                          (the app uses last 7 *check-ins* vs previous 7 check-ins)
Defaults (gating=True, windows="count") reproduce the app exactly.

Narrative text is not ported; it never affects whether an alert fires.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np

SLEEP = "sleepQuality"
SOCIAL = "socialConnection"
MOOD = "moodDepression"

NEGATIVE = "NEGATIVE"
POSITIVE = "POSITIVE"

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

# Alert kinds (not a Swift field; added so callers can tell the three alert
# sources in DriftDetection.detect apart).
KIND_DOMAIN = "domain"          # DD:14-33 via detectScoreDrift
KIND_ADHERENCE = "adherence"    # DD:35-43 (unreachable, see adherence note below)
KIND_COMBINED_POSITIVE = "combined_positive"  # DD:45-54


@dataclass(frozen=True)
class CheckIn:
    """Only the DailyCheckIn fields the detector reads (DD:15-31, REPO:36-43, 69)."""
    date: str            # "yyyy-MM-dd"; the app sorts by this string
    sleep: int           # UI: 1...5 (EvokiComponents.swift:195)
    mood: int            # UI: 1...5 (CheckInView.swift:286)
    social: int          # UI: 0...2 (CheckInView.swift:333)
    modified: float = 0.0  # stand-in for lastModifiedAt ?? updatedAt ?? completedAt


@dataclass(frozen=True)
class Alert:
    kind: str
    direction: str
    severity: str
    domain: Optional[str] = None
    # Not stored on the Swift DriftAlert; recorded here for analysis only.
    confidence: Optional[str] = None
    delta: Optional[float] = None


# ---------------------------------------------------------------------------
# ClinicalScoreSupport (CSS)
# ---------------------------------------------------------------------------

def _normalize(score: int, lo: int, hi: int) -> float:
    # CSS:27-31
    if not hi > lo:
        return 0.0
    clamped = max(lo, min(hi, score))
    return float(clamped - lo) / float(hi - lo)


def normalized_sleep(score: int) -> float:
    return _normalize(score, 1, 5)   # CSS:4-6


def normalized_mood(score: int) -> float:
    return _normalize(score, 1, 5)   # CSS:8-10


def normalized_social(score: int) -> float:
    return _normalize(score, 0, 2)   # CSS:16-18


def check_in_confidence(recent_count: int, previous_count: Optional[int] = None) -> str:
    # CSS:20-25. A three-level label based on data quantity only.
    comparison = min(recent_count, previous_count if previous_count is not None else recent_count)
    if comparison >= 6:
        return "strong"
    if comparison >= 4:
        return "moderate"
    return "low"


def has_enough_data_for_alert(confidence: str) -> bool:
    return confidence != "low"   # CSS:39-41


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _swift_sum(values: Sequence[float]) -> float:
    # Swift's `reduce(0, +)` is a plain left-to-right Double sum. Python's
    # built-in sum() uses compensated summation on 3.12+, which can differ in
    # the last bit and flip results that land exactly on +/-0.25.
    total = 0.0
    for v in values:
        total = total + v
    return total


def _mean(values: Sequence[float]) -> float:
    # DD:66-67 and DD:109-112 (both divide the reduce-sum by count).
    if not values:
        return 0.0
    return _swift_sum(values) / float(len(values))


# ---------------------------------------------------------------------------
# Data fetch as done by the app before calling detect()
# ---------------------------------------------------------------------------

def app_fetch(all_check_ins: Sequence[CheckIn], n: int = 14) -> List[CheckIn]:
    """REPO:36-43 + REPO:67-70: keep the latest edit per date, sort by date
    string, return the last n."""
    latest = {}
    for c in all_check_ins:
        cur = latest.get(c.date)
        if cur is None or cur.modified < c.modified:
            latest[c.date] = c
    ordered = sorted(latest.values(), key=lambda c: c.date)
    return ordered[-n:] if n > 0 else []


def run_app_pipeline(all_check_ins: Sequence[CheckIn], gating: bool = True,
                     windows: str = "count", today: Optional[str] = None) -> List[Alert]:
    """HVM:257-261: fetch last 14, require >= 3, then detect()."""
    check_ins = app_fetch(all_check_ins, n=14 if windows == "count" else 10_000)
    if len(check_ins) < 3:   # HVM:259
        return []
    return detect(check_ins, gating=gating, windows=windows, today=today)


# ---------------------------------------------------------------------------
# DriftDetection (DD)
# ---------------------------------------------------------------------------

def _split_count(ordered: List[CheckIn]):
    # DD:7-8: windows are counted in check-ins, not days.
    recent = ordered[-7:]
    previous = ordered[:len(ordered) - len(recent)][-7:]
    return recent, previous


def _split_calendar(ordered: List[CheckIn], today: str):
    # Evaluation-only variant: recent = [today-6, today], previous = [today-13, today-7].
    t = _dt.date.fromisoformat(today)
    r_start = (t - _dt.timedelta(days=6)).isoformat()
    p_start = (t - _dt.timedelta(days=13)).isoformat()
    recent = [c for c in ordered if r_start <= c.date <= today]
    previous = [c for c in ordered if p_start <= c.date < r_start]
    return recent, previous


def detect(check_ins: Sequence[CheckIn], gating: bool = True,
           windows: str = "count", today: Optional[str] = None) -> List[Alert]:
    ordered = sorted(check_ins, key=lambda c: c.date)   # DD:6
    if windows == "count":
        recent, previous = _split_count(ordered)
    elif windows == "calendar":
        if today is None:
            raise ValueError("calendar windows need `today`")
        recent, previous = _split_calendar(ordered, today)
    else:
        raise ValueError(windows)

    if not len(recent) >= 4:   # DD:10
        return []

    alerts: List[Alert] = []

    for domain, norm, field in (
        (SLEEP, normalized_sleep, "sleep"),     # DD:14-19
        (SOCIAL, normalized_social, "social"),  # DD:21-26
        (MOOD, normalized_mood, "mood"),        # DD:28-33
    ):
        a = _detect_score_drift(
            [norm(getattr(c, field)) for c in recent],
            [norm(getattr(c, field)) for c in previous],
            domain, gating,
        )
        if a is not None:
            alerts.append(a)

    # DD:35-43. Swift computes this in Float (32-bit). It requires
    # count >= 4 AND count/7 < 0.43 (i.e. count <= 3) at once, so it never fires.
    adherence_rate = np.float32(len(recent)) / np.float32(7.0)
    if len(recent) >= 4 and adherence_rate < np.float32(0.43):
        alerts.append(Alert(kind=KIND_ADHERENCE, direction=NEGATIVE, severity=MEDIUM))

    # DD:45-54
    positive_areas = _detect_positive_drift(recent, previous)
    if len(positive_areas) >= 2:
        alerts.append(Alert(kind=KIND_COMBINED_POSITIVE, direction=POSITIVE, severity=LOW))

    return alerts


def _detect_score_drift(recent: List[float], previous: List[float],
                        domain: str, gating: bool) -> Optional[Alert]:
    # DD:59-88
    if not recent or not previous:   # DD:62
        return None
    confidence = check_in_confidence(len(recent), len(previous))   # DD:63
    if gating and not has_enough_data_for_alert(confidence):         # DD:64
        return None

    recent_avg = _mean(recent)
    prev_avg = _mean(previous)
    delta = recent_avg - prev_avg   # DD:68

    if delta <= -0.25:   # DD:70
        severity = HIGH if (delta <= -0.38 and confidence == "strong") else MEDIUM   # DD:75
        return Alert(kind=KIND_DOMAIN, direction=NEGATIVE, severity=severity,
                     domain=domain, confidence=confidence, delta=delta)
    elif delta >= 0.25:  # DD:78
        return Alert(kind=KIND_DOMAIN, direction=POSITIVE, severity=LOW,
                     domain=domain, confidence=confidence, delta=delta)
    return None


def _detect_positive_drift(recent: List[CheckIn], previous: List[CheckIn]) -> List[str]:
    # DD:90-107 (strict ">" and a 0.18 margin, unlike the 0.25 domain rule)
    if not (len(recent) >= 4 and len(previous) >= 4):
        return []
    positive = []
    for domain, norm, field in (
        (SLEEP, normalized_sleep, "sleep"),
        (SOCIAL, normalized_social, "social"),
        (MOOD, normalized_mood, "mood"),
    ):
        r = _mean([norm(getattr(c, field)) for c in recent])
        p = _mean([norm(getattr(c, field)) for c in previous])
        if r > p + 0.18:
            positive.append(domain)
    return positive


def negative_domain_alerts(alerts: Sequence[Alert]) -> List[Alert]:
    """The alerts this evaluation scores: negative domain alerts (MEDIUM or HIGH)."""
    return [a for a in alerts if a.kind == KIND_DOMAIN and a.direction == NEGATIVE]
