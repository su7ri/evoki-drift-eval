"""Checks for the episode / window definitions in metrics.py and simulator basics."""

import numpy as np

import metrics as m
import simulate as sim
from simulate import Run


def test_episode_not_split_by_missing_day():
    # runs on days 20, 21, (22 missing), 23 all fire -> one episode
    runs = [Run(20, {"sleep": "strong"}), Run(21, {"sleep": "strong"}), Run(23, {"mood": "strong"})]
    eps = m.episodes(runs)
    assert len(eps) == 1 and eps[0].start == 20 and eps[0].end == 23 and eps[0].n_runs == 3


def test_episode_split_by_non_firing_run():
    runs = [Run(20, {"sleep": "moderate"}), Run(21, {}), Run(22, {"sleep": "strong"})]
    eps = m.episodes(runs)
    assert [(e.start, e.confidence) for e in eps] == [(20, "moderate"), (22, "strong")]


def test_per_domain_episodes():
    runs = [Run(20, {"sleep": "strong"}), Run(21, {"mood": "strong"}), Run(22, {"sleep": "strong"})]
    assert [e.start for e in m.episodes(runs, "sleep")] == [20, 22]
    assert len(m.episodes(runs)) == 1


def _user(shape, onset=50):
    return sim.SimUser("x", "stable", True, "sleep", onset, shape, 1.0)


def test_tp_window_primary_and_full_change():
    step, grad = _user("step"), _user("gradual")
    assert m.full_change_day(step) == 50 and m.full_change_day(grad) == 63
    # step: both definitions are [onset, onset + 13]
    for d in m.DEFINITIONS:
        assert m.window(step, 14, d) == (50, 63)
    # gradual: primary covers the ramp, full_change starts at full size
    assert m.window(grad, 14, "primary") == (50, 76)
    assert m.window(grad, 14, "full_change") == (63, 76)
    assert m.in_window(55, grad, 14, "primary") and not m.in_window(55, grad, 14, "full_change")


def test_ramp_alarm_counts_only_under_primary():
    u = _user("gradual")
    runs = [Run(10, {"sleep": "strong"}), Run(11, {}), Run(55, {"sleep": "strong"})]
    r = m.score_user(u, runs)
    assert r.detected[("primary", 14)] and r.delay[("primary", 14)] == 5     # 55 - onset 50
    assert not r.detected[("full_change", 14)]
    # day-10 episode excluded (warm-up); day-55 episode correct only under primary
    assert r.episode_marks == [("strong", {"primary": True, "full_change": False})]


def test_chance_uses_same_window_length():
    u = sim.SimUser("stable-000", "stable", False, None, None, None, None)
    fake = m.pseudo_change(u)
    lo, hi = m.window(fake, 14, "primary")
    assert hi - lo + 1 == (14 if fake.shape == "step" else 27)


def test_change_profile_reaches_full_size():
    p = sim.change_profile(90, 50, "gradual", 2.0)
    assert p[49] == 0 and p[62] < 2.0 and p[63] == 2.0
    assert sim.change_profile(90, 50, "step", 2.0)[50] == 2.0


def test_simulation_is_reproducible():
    a = sim.simulate_all(n_per_group=3)
    b = sim.simulate_all(n_per_group=3)
    assert [c for u in a for c in u.check_ins] == [c for u in b for c in u.check_ins]


def test_scores_on_real_scales():
    for u in sim.simulate_all(n_per_group=20):
        for c in u.check_ins:
            assert 1 <= c.sleep <= 5 and 1 <= c.mood <= 5 and 0 <= c.social <= 2


def test_wilson():
    p, lo, hi = m.wilson(50, 100)
    assert p == 0.5 and abs(lo - 0.404) < 0.001 and abs(hi - 0.596) < 0.001


def test_personalised_fixed_path_matches_detector():
    import personalised as pers
    for u in sim.simulate_all(n_per_group=3, seed=123):
        stats = pers.precompute(u)
        assert pers.fixed_runs(stats) == sim.evaluate_user(u, "count_gated")
        # K = 0 with FLOOR = 0.25 is the fixed rule
        assert pers.runs_for(stats, 0.0, 0.25) == sim.evaluate_user(u, "count_gated")


def test_personalised_threshold_rule():
    import personalised as pers
    assert pers.threshold(float("nan"), 1.25, 0.1875) == 0.25
    assert pers.threshold(0.1, 1.25, 0.1875) == 0.1875
    assert abs(pers.threshold(0.3, 1.25, 0.1875) - 0.375) < 1e-12


def test_global_rule_at_025_is_current_detector():
    import personalised as pers
    for u in sim.simulate_all(n_per_group=3, seed=321):
        assert pers.global_runs(pers.precompute(u), 0.25) == sim.evaluate_user(u, "count_gated")
