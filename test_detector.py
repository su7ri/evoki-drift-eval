"""
Hand-checked cases for detector.py. Each case lists the arithmetic so it can
be checked by hand and reproduced in the app (enter the check-ins, open Home).

Normalisation: sleep/mood (x-1)/4 -> 1:0, 2:0.25, 3:0.5, 4:0.75, 5:1.0
               social x/2         -> 0:0, 1:0.5, 2:1.0
Run: python -m pytest -q
"""

import datetime as dt

import detector as d
from detector import CheckIn


def make(sleep, social, mood, start="2026-01-01", step_days=1):
    """Consecutive check-ins (one per `step_days`) from parallel score lists."""
    t0 = dt.date.fromisoformat(start)
    return [
        CheckIn(date=(t0 + dt.timedelta(days=i * step_days)).isoformat(),
                sleep=s, social=so, mood=m)
        for i, (s, so, m) in enumerate(zip(sleep, social, mood))
    ]


def summary(alerts):
    return [(a.kind, a.domain, a.direction, a.severity) for a in alerts]


# --- Case 1: mirrors the existing Swift test ClinicalSafetyTests.swift:9-19 ---
# sleep prev 7x5 -> mean 1.0; recent 7x2 -> mean 0.25; delta -0.75 <= -0.25.
# confidence min(7,7)=7 -> strong; -0.75 <= -0.38 -> HIGH. social/mood unchanged.
def test_case1_sleep_drop_strong_high():
    c = make([5] * 7 + [2] * 7, [2] * 14, [4] * 14)
    assert summary(d.detect(c)) == [("domain", d.SLEEP, "NEGATIVE", "HIGH")]


# --- Case 2: fewer than 4 check-ins -> nothing (DD:10; HVM:259 needs >= 3) ---
def test_case2_too_few():
    c = make([1, 1, 1], [0] * 3, [1] * 3)
    assert d.detect(c) == []
    assert d.run_app_pipeline(c) == []


# --- Case 3: 7 check-ins, huge drop inside them -> nothing (previous empty, DD:62) ---
def test_case3_first_week_never_alerts():
    c = make([5, 5, 5, 1, 1, 1, 1], [2] * 7, [5] * 7)
    assert d.detect(c) == []


# --- Case 4: exactly on the threshold fires (<= is inclusive) ---
# sleep prev 7x4 -> 0.75; recent 7x3 -> 0.5; delta exactly -0.25 -> fires.
# strong, but -0.25 > -0.38 -> MEDIUM.
def test_case4_exact_threshold_fires_medium():
    c = make([4] * 7 + [3] * 7, [2] * 14, [4] * 14)
    a = d.detect(c)
    assert summary(a) == [("domain", d.SLEEP, "NEGATIVE", "MEDIUM")]
    assert a[0].delta == -0.25


# --- Case 5: just under the threshold -> nothing ---
# sleep prev 7x4 -> 0.75; recent 6x3 + 1x4 -> 3.75/7 = 0.5357; delta -0.214.
def test_case5_below_threshold():
    c = make([4] * 7 + [3] * 6 + [4], [2] * 14, [4] * 14)
    assert d.detect(c) == []


# --- Case 6: social on its 0-2 scale ---
# social prev 7x2 -> 1.0; recent 4x1 + 3x2 -> (2+3)/7 = 0.714; delta -0.286.
# strong, -0.286 > -0.38 -> MEDIUM.
def test_case6_social_drop_medium():
    c = make([4] * 14, [2] * 7 + [1] * 4 + [2] * 3, [4] * 14)
    assert summary(d.detect(c)) == [("domain", d.SOCIAL, "NEGATIVE", "MEDIUM")]


# --- Case 7: gating. 10 check-ins -> recent 7, previous 3 ---
# confidence min(7,3)=3 -> low -> blocked. Without gating: delta -0.75 fires,
# but confidence is low (not strong) -> MEDIUM.
def test_case7_gating_blocks_previous_of_three():
    c = make([5] * 3 + [2] * 7, [2] * 10, [4] * 10)
    assert d.detect(c, gating=True) == []
    assert summary(d.detect(c, gating=False)) == [("domain", d.SLEEP, "NEGATIVE", "MEDIUM")]


# --- Case 8: moderate vs strong changes severity, not firing ---
# 11 check-ins -> previous 4 -> moderate -> MEDIUM even at delta -0.75.
# 13 check-ins -> previous 6 -> strong   -> HIGH.
def test_case8_moderate_vs_strong():
    c11 = make([5] * 4 + [2] * 7, [2] * 11, [4] * 11)
    c13 = make([5] * 6 + [2] * 7, [2] * 13, [4] * 13)
    a11, a13 = d.detect(c11), d.detect(c13)
    assert summary(a11) == [("domain", d.SLEEP, "NEGATIVE", "MEDIUM")]
    assert a11[0].confidence == "moderate"
    assert summary(a13) == [("domain", d.SLEEP, "NEGATIVE", "HIGH")]
    assert a13[0].confidence == "strong"


# --- Case 9: gating only matters for 8-10 total check-ins ---
# Same sharp drop in the last 7; gated and ungated agree for N outside 8..10.
def test_case9_gating_only_changes_n_8_to_10():
    differs = []
    for n in range(4, 15):
        c = make([5] * (n - 7) + [2] * min(n, 7) if n > 7 else [2] * n,
                 [2] * n, [4] * n)
        g = d.negative_domain_alerts(d.detect(c, gating=True))
        u = d.negative_domain_alerts(d.detect(c, gating=False))
        if summary(g) != summary(u):
            differs.append(n)
    assert differs == [8, 9, 10]


# --- Case 10: count windows ignore calendar gaps ---
# previous 7 check-ins are ~2 months before the recent 7. Count windows still
# compare them (fires); calendar windows (evaluation variant) find previous empty.
def test_case10_count_windows_ignore_gaps():
    old = make([5] * 7, [2] * 7, [4] * 7, start="2026-01-01")
    new = make([2] * 7, [2] * 7, [4] * 7, start="2026-03-01")
    c = old + new
    assert summary(d.detect(c)) == [("domain", d.SLEEP, "NEGATIVE", "HIGH")]
    assert d.detect(c, windows="calendar", today="2026-03-07") == []


# --- Case 11: sparse user, count windows span weeks ---
# One check-in every 3 days, 14 check-ins over 40 days. Count windows fire;
# calendar windows on the last day hold only 3 recent check-ins (< 4) -> nothing.
def test_case11_sparse_user_calendar_vs_count():
    c = make([5] * 7 + [2] * 7, [2] * 14, [4] * 14, step_days=3)
    assert summary(d.detect(c)) == [("domain", d.SLEEP, "NEGATIVE", "HIGH")]
    assert d.detect(c, windows="calendar", today=c[-1].date) == []


# --- Case 12: latest edit per date wins (REPO:36-43) ---
# Day 14 saved twice: first sleep 2, later edited to 5. With the edit the
# recent mean is (6x0.25 + 1.0)/7 = 0.357; delta vs 1.0 = -0.643 -> still fires,
# but the older record must be dropped (one row per date, 14 rows total).
def test_case12_latest_edit_wins():
    c = make([5] * 7 + [2] * 7, [2] * 14, [4] * 14)
    edited = CheckIn(date=c[-1].date, sleep=5, social=2, mood=4, modified=1.0)
    rows = d.app_fetch(c + [edited])
    assert len(rows) == 14
    assert rows[-1].sleep == 5


# --- Case 13: adherence alert is unreachable (DD:35-43) ---
def test_case13_adherence_never_fires():
    for n in range(0, 30):
        c = make([3] * n, [1] * n, [3] * n)
        assert all(a.kind != d.KIND_ADHERENCE for a in d.detect(c))


# --- Case 14: positive alerts (ported, not scored) ---
# sleep 3->4 and mood 3->4: delta +0.25 each -> two POSITIVE LOW domain alerts;
# both also exceed +0.18 -> one combined positive alert.
def test_case14_positive_alerts_ported():
    c = make([3] * 7 + [4] * 7, [1] * 14, [3] * 7 + [4] * 7)
    assert summary(d.detect(c)) == [
        ("domain", d.SLEEP, "POSITIVE", "LOW"),
        ("domain", d.MOOD, "POSITIVE", "LOW"),
        ("combined_positive", None, "POSITIVE", "LOW"),
    ]
    assert d.negative_domain_alerts(d.detect(c)) == []


# --- Case 15: out-of-range scores are clamped (CSS:29) ---
def test_case15_clamping():
    assert d.normalized_sleep(0) == 0.0 and d.normalized_sleep(9) == 1.0
    assert d.normalized_social(-1) == 0.0 and d.normalized_social(3) == 1.0
    assert d.normalized_social(1) == 0.5   # matches ClinicalSafetyTests.swift:24
