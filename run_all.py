"""
Reproduce every table and figure:  python run_all.py
Writes results/summary.md, results/*.csv and figures/*.png.

All numbers are from SIMULATED users and depend on the simulator's assumptions.
They are not clinical validation and do not come from real users.
"""

from __future__ import annotations

import csv
import os
import time

import numpy as np

import metrics as m
import personalised as pers
import simulate as sim

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("results", exist_ok=True)
os.makedirs("figures", exist_ok=True)

VARIANTS = list(sim.VARIANTS)
GROUPS = list(sim.GROUPS)

INK, INK2, GRID_C = "#0b0b0b", "#52514e", "#e6e5e0"
# Validated categorical slots 1-4; aqua/yellow are below 3:1 contrast, so every
# chart also uses marker shape + line style, and every number is in summary.md.
VCOLOR = {"count_gated": "#2a78d6", "count_ungated": "#eb6834",
          "calendar_gated": "#1baf7a", "calendar_ungated": "#eda100"}
VMARK = {"count_gated": "o", "count_ungated": "s", "calendar_gated": "^", "calendar_ungated": "D"}
VLS = {"count_gated": "-", "count_ungated": "--", "calendar_gated": "-", "calendar_ungated": "--"}
VLABEL = {"count_gated": "count, gated (current app)", "count_ungated": "count, ungated",
          "calendar_gated": "calendar, gated", "calendar_ungated": "calendar, ungated"}


def pct(t):
    return f"{100 * t[0]:.1f}% [{100 * t[1]:.1f}, {100 * t[2]:.1f}]"


def num(t, d=2):
    return f"{t[0]:.{d}f} [{t[1]:.{d}f}, {t[2]:.{d}f}]"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def write_csv(name, header, rows):
    with open(f"results/{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# The Evoki app commit whose detector was ported (not this repository's own commit).
APP_COMMIT = "f389fc6383ae6416a84afea227639b4faa6f8dbb"


def main():
    t0 = time.time()
    users = sim.simulate_all()
    R = {v: m.evaluate(users, v) for v in VARIANTS}
    by_group = {v: {g: [r for r in R[v] if r.group == g] for g in GROUPS} for v in VARIANTS}
    print(f"evaluated {len(users)} users x {len(VARIANTS)} variants in {time.time() - t0:.0f}s")

    md = ["# Results (simulated data only)", "",
          "All numbers come from simulated users and depend on the assumptions in "
          "`simulate.py`. They are not clinical validation and do not come from real users.", "",
          f"App commit: `{APP_COMMIT}`. Seed `{sim.SEED}`. "
          f"{sim.N_USERS_PER_GROUP} users per group, {sim.N_DAYS} days. "
          "Brackets are 95% intervals (Wilson for proportions, user-level bootstrap for rates "
          "and median delay).", ""]

    # --- Group sizes ---------------------------------------------------------
    rows = []
    for g in GROUPS:
        gu = [u for u in users if u.group == g]
        rows.append([g, len(gu), sum(u.has_change for u in gu),
                     f"{np.mean([len(u.check_ins) for u in gu]) / sim.N_DAYS:.2f}"])
    md += ["## Groups (behaviour types, not demographics)", "",
           md_table(["group", "users", "with change", "mean check-in rate"], rows), ""]

    # --- False alarms --------------------------------------------------------
    rows, csv_rows = [], []
    for g in GROUPS:
        for v in VARIANTS:
            ep = m.fa_rate(by_group[v][g])
            dy = m.fa_rate(by_group[v][g], "fa_alarm_days")
            rows.append([g, v, num(ep), num(dy)])
            csv_rows.append([g, v, *ep, *dy])
    md += ["## False alarms per user-month (no-change users, days 14-89)", "",
           "Episodes are the primary metric. An episode is consecutive firing runs; "
           "days without a check-in do not split it.", "",
           md_table(["group", "variant", "episodes / user-month", "alarm-days / user-month"], rows), ""]
    write_csv("false_alarms", ["group", "variant", "episodes", "ep_lo", "ep_hi",
                               "alarm_days", "ad_lo", "ad_hi"], csv_rows)

    # False alarms per alerting domain (count_gated)
    rows = []
    for g in GROUPS:
        res = [r for r in by_group["count_gated"][g] if not r.has_change]
        rows.append([g] + [num(m.boot([r.fa_by_domain[d] / m.USER_MONTHS for r in res], np.mean))
                           for d in sim.DOMAINS])
    md += ["### False-alarm episodes per user-month by alerting domain (count, gated)", "",
           md_table(["group"] + list(sim.DOMAINS), rows), ""]

    # --- Detection -----------------------------------------------------------
    DEF_TITLE = {
        "primary": "primary definition: window [onset, full-change day + W - 1]",
        "full_change": "sensitivity analysis, previous definition: window "
                       "[full-change day, full-change day + W - 1]",
    }
    for defn in m.DEFINITIONS:
        rows, csv_rows = [], []
        for g in GROUPS:
            for v in VARIANTS:
                res = by_group[v][g]
                det = {w: m.detection(res, w, definition=defn) for w in m.WINDOWS}
                chn = {w: m.chance_detection(res, w, definition=defn) for w in m.WINDOWS}
                dc = m.detection(res, 14, domain_correct=True, definition=defn)
                dl = m.delay(res, definition=defn)
                rows.append([g, v, pct(det[14]), pct(chn[14]), pct(dc),
                             f"{pct(det[7])} (chance {100 * chn[7][0]:.1f}%)",
                             f"{pct(det[21])} (chance {100 * chn[21][0]:.1f}%)",
                             f"{dl[0]:.0f} [{dl[1]:.0f}, {dl[2]:.0f}] (IQR {dl[3]:.0f}-{dl[4]:.0f}, n={dl[5]})"])
                csv_rows.append([g, v, *det[14][:3], *chn[14][:3], *dc[:3], *det[7][:3], *chn[7][:3],
                                 *det[21][:3], *chn[21][:3], *dl])
        intro = []
        if defn == "primary":
            intro = ["Full-change day: step -> onset; gradual -> onset + 13. Detected = an any-domain "
                     "episode starts inside the window. For steps the window is W days from onset; "
                     "for gradual changes it also covers the 13-day ramp. Domain-correct = the changed "
                     "domain's own episode starts in the 14-day window. Delay = episode start minus "
                     "onset, in days.", "",
                     "**Read detection next to the chance column.** Chance = the same window rule "
                     "(same definition and W, so the same window length) applied to no-change users at "
                     "a pseudo onset and shape, i.e. what false alarms alone would score.", ""]
        else:
            intro = ["This was the first primary definition. It was replaced after the first results "
                     "showed that alarms starting during a gradual ramp were counted as misses. For "
                     "step changes both definitions are identical.", ""]
        md += [f"## Detection, {DEF_TITLE[defn]} (changed users, all sizes pooled)", ""] + intro + [
            md_table(["group", "variant", "detected (14 d)", "chance (14 d)", "domain-correct (14 d)",
                      "detected (7 d)", "detected (21 d)", "median delay [CI]"], rows), ""]
        write_csv(f"detection_{defn}", ["group", "variant", "det14", "det14_lo", "det14_hi",
                                        "chance14", "chance14_lo", "chance14_hi",
                                        "dom14", "dom14_lo", "dom14_hi", "det7", "det7_lo", "det7_hi",
                                        "chance7", "chance7_lo", "chance7_hi",
                                        "det21", "det21_lo", "det21_hi",
                                        "chance21", "chance21_lo", "chance21_hi",
                                        "delay_median", "delay_lo", "delay_hi", "delay_q1", "delay_q3",
                                        "delay_n"], csv_rows)

    # By magnitude
    for defn in m.DEFINITIONS:
        rows, csv_rows = [], []
        for g in GROUPS:
            for v in VARIANTS:
                cells = []
                for sz in sim.CHANGE_SIZES:
                    d = m.detection(by_group[v][g], 14, size=sz, definition=defn)
                    cells.append(pct(d) + f" n={d[3]}")
                    csv_rows.append([g, v, sz, *d])
                rows.append([g, v] + cells)
        title = ("## Detection rate by change magnitude (primary, 14-day window)" if defn == "primary" else
                 "### Sensitivity analysis: detection by magnitude, previous definition (window from "
                 "full-change day)")
        md += [title, "", md_table(["group", "variant"] + [f"{sz:g} pt" for sz in sim.CHANGE_SIZES], rows), ""]
        write_csv(f"detection_by_size_{defn}", ["group", "variant", "size", "rate", "lo", "hi", "n"], csv_rows)

    # By shape and by domain (count_gated and calendar_gated), both definitions
    rows = []
    for g in GROUPS:
        for v in ("count_gated", "calendar_gated"):
            rows.append([g, v]
                        + [pct(m.detection(by_group[v][g], 14, shape=sh)) for sh in ("step", "gradual")]
                        + [pct(m.detection(by_group[v][g], 14, shape="gradual", definition="full_change"))]
                        + [pct(m.detection(by_group[v][g], 14, domain_correct=True, domain=d))
                           for d in sim.DOMAINS])
    md += ["## Detection by shape, and domain-correct detection by changed domain (primary, 14-day window)", "",
           md_table(["group", "variant", "step", "gradual", "gradual (previous definition)"]
                    + [f"domain-correct: {d}" for d in sim.DOMAINS], rows), ""]

    # --- Worst group ---------------------------------------------------------
    rows = []
    for v in VARIANTS:
        fa = {g: m.fa_rate(by_group[v][g]) for g in GROUPS}
        de = {g: m.detection(by_group[v][g], 14) for g in GROUPS}
        gf = max(fa, key=lambda g: fa[g][0])
        gd = min(de, key=lambda g: de[g][0])
        rows.append([v, f"{gf}: {num(fa[gf])}", f"{gd}: {pct(de[gd])}"])
    md += ["## Worst group per variant (primary definition)", "",
           md_table(["variant", "highest false alarms / user-month", "lowest detection (14 d)"], rows), ""]

    # --- Precision by confidence ---------------------------------------------
    rows, csv_rows = [], []
    for v in VARIANTS:
        pc = m.precision_by_confidence(R[v], "primary")
        po = m.precision_by_confidence(R[v], "full_change")
        for conf, t in pc.items():
            if t[3]:
                note = " (too few episodes to conclude)" if t[3] < 100 else ""
                rows.append([v, conf, pct(t), pct(po[conf]), f"{t[3]}{note}"])
                csv_rows.append([v, conf, *t, *po[conf][:3]])
    md += ["## Alert precision by confidence label (all groups pooled)", "",
           "Confidence is a three-level label based on data quantity only (how many check-ins "
           "are in each window); it does not look at the scores and is not a probability, so this "
           "is not a calibration analysis. Correct = the episode starts in a changed user's 14-day "
           "TP window; every other episode is incorrect. **Precision depends on the 50% prevalence "
           "of changed users chosen for the simulation.** Wilson intervals over episodes ignore "
           "clustering within users. Rows with fewer than 100 episodes are too few to conclude.", "",
           md_table(["variant", "confidence of first alert", "precision (primary)",
                     "precision (previous definition)", "episodes"], rows), ""]
    write_csv("precision_by_confidence", ["variant", "confidence", "precision", "lo", "hi", "n",
                                          "prev_precision", "prev_lo", "prev_hi"], csv_rows)

    # --- Grid ----------------------------------------------------------------
    t1 = time.time()
    G = m.grid()
    print(f"grid done in {time.time() - t1:.0f}s")
    for v in m.GRID_VARIANTS:
        for key, label in (("fa", "false-alarm episodes / user-month"), ("det", "detection rate (primary, 14 d)"),
                           ("chance", "chance detection rate (primary, 14 d, no-change users)")):
            hdr = ["noise SD \\ check-in rate"] + [f"{p:.1f}" for p in m.GRID_RATE]
            rows = [[f"{sd:.2f}"] + [f"{x:.2f}" for x in G[v][key][i]] for i, sd in enumerate(m.GRID_NOISE)]
            md += [f"### Grid: {label}, {v} ({m.GRID_USERS} users per cell, baseline N(3.5, 0.5))", "",
                   md_table(hdr, rows), ""]
            write_csv(f"grid_{key}_{v}", hdr, rows)

    # --- Personalised threshold (held-out seeds) -----------------------------
    t2 = time.time()
    (pk, pf), table, tg, gtable, base = pers.tune()
    hu, cur, glob, per = pers.evaluate_held_out(pk, pf, tg)
    print(f"personalised + global tuning and held-out evaluation in {time.time() - t2:.0f}s")
    d_gc = pers.paired_objective_diff(cur, glob)
    d_pc = pers.paired_objective_diff(cur, per)
    d_pg = pers.paired_objective_diff(glob, per)
    md += ["## Personalised threshold and tuned global control (evaluation only, not app behaviour)", "",
           "Personalised rule: same as the current detector (count windows, gated), but each domain's "
           f"threshold is `max(FLOOR, K * sd)`, where sd is the SD of the user's own normalised scores "
           f"over up to {pers.HIST_N} check-ins before the recent window (fixed 0.25 if fewer than "
           f"{pers.MIN_HIST}). It needs up to {pers.HIST_N + 7} past check-ins; the app fetches 14.", "",
           "Control (tuned global): one constant threshold T for every user and domain, otherwise the "
           "same detector. It needs no extra history.", "",
           f"Both were tuned on **tuning users** (seed {pers.TUNE_SEED}, {pers.TUNE_USERS_PER_GROUP} per "
           "group) with the same objective, the mean over groups of (detection - chance), primary "
           f"definition, W = 14. Results are on **held-out users** (seed {pers.EVAL_SEED}, "
           f"{pers.EVAL_USERS_PER_GROUP} per group) never used for tuning. Tuning and held-out users come "
           "from the same simulator and group settings, so this does not show either rule would work on "
           "other data.", "",
           f"Chosen: personalised K = {pk:g}, FLOOR = {pf:g}; tuned global T = {tg:g}.", "",
           "| rule | objective on tuning users | objective on held-out users |",
           "|---|---|---|",
           f"| current (fixed 0.25) | {base:.3f} | {pers.objective(cur):.3f} |",
           f"| tuned global (T = {tg:g}) | {max(o for _, o in gtable):.3f} | {pers.objective(glob):.3f} |",
           f"| personalised (K = {pk:g}, FLOOR = {pf:g}) | {max(t[2] for t in table):.3f} | "
           f"{pers.objective(per):.3f} |", "",
           "Paired differences in the held-out objective (same users; 95% paired bootstrap):", "",
           "| comparison | difference [95% CI] |", "|---|---|",
           f"| tuned global - current | {d_gc[0]:+.3f} [{d_gc[1]:+.3f}, {d_gc[2]:+.3f}] |",
           f"| personalised - current | {d_pc[0]:+.3f} [{d_pc[1]:+.3f}, {d_pc[2]:+.3f}] |",
           f"| personalised - tuned global | {d_pg[0]:+.3f} [{d_pg[1]:+.3f}, {d_pg[2]:+.3f}] |", "",
           "### Tuning grids (tuning users only)", "",
           md_table(["K", "FLOOR", "objective"],
                    [[f"{k:g}", f"{fl:g}", f"{o:.3f}" + (" **chosen**" if (k, fl) == (pk, pf) else "")]
                     for k, fl, o in table]), "",
           "Global T (thresholds between possible delta values give identical results, hence plateaus):", "",
           md_table(["T", "objective"],
                    [[f"{t:g}", f"{o:.3f}" + (" **chosen**" if t == tg else "")] for t, o in gtable]), ""]
    rows, csv_rows = [], []
    for g in GROUPS:
        for name, res in (("current (count_gated)", cur), (f"tuned global T={tg:g}", glob),
                          ("personalised", per)):
            rs = [r for r in res if r.group == g]
            fa, de, ch, dl = m.fa_rate(rs), m.detection(rs), m.chance_detection(rs), m.delay(rs)
            dc = m.detection(rs, domain_correct=True)
            rows.append([g, name, num(fa), pct(de), pct(ch), f"{100 * (de[0] - ch[0]):.1f} pts", pct(dc),
                         f"{dl[0]:.0f} [{dl[1]:.0f}, {dl[2]:.0f}] (IQR {dl[3]:.0f}-{dl[4]:.0f})"])
            csv_rows.append([g, name, *fa, *de[:3], *ch[:3], *dc[:3], *dl])
    md += ["### Held-out results: current vs tuned global vs personalised", "",
           md_table(["group", "variant", "false-alarm episodes / user-month", "detected (14 d, primary)",
                     "chance (14 d)", "detected - chance", "domain-correct (14 d)", "median delay [CI]"],
                    rows), ""]
    write_csv("personalised_held_out", ["group", "variant", "fa", "fa_lo", "fa_hi", "det", "det_lo",
                                        "det_hi", "chance", "chance_lo", "chance_hi", "dom", "dom_lo",
                                        "dom_hi", "delay_median", "delay_lo", "delay_hi", "delay_q1",
                                        "delay_q3", "delay_n"], csv_rows)
    write_csv("personalised_tuning", ["K", "FLOOR", "objective"], table)
    write_csv("global_tuning", ["T", "objective"], gtable)

    with open("results/summary.md", "w") as f:
        f.write("\n".join(md))
    print("wrote results/summary.md")

    make_figures(by_group, G)
    personalised_figure(cur, glob, per, pk, pf, tg)
    sim.sample_plot()
    print(f"total {time.time() - t0:.0f}s")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID_C, lw=0.8)
    ax.set_axisbelow(True)


def make_figures(by_group, G):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    foot = "Simulated data only; depends on simulator assumptions. Not clinical validation."
    offsets = np.linspace(-0.27, 0.27, len(VARIANTS))

    # 1. False alarms per user-month by group
    fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
    for k, v in enumerate(VARIANTS):
        ts = [m.fa_rate(by_group[v][g]) for g in GROUPS]
        x = np.arange(len(GROUPS)) + offsets[k]
        y = [t[0] for t in ts]
        ax.errorbar(x, y, yerr=[[t[0] - t[1] for t in ts], [t[2] - t[0] for t in ts]],
                    fmt=VMARK[v], color=VCOLOR[v], ms=7, lw=2, capsize=0, label=VLABEL[v])
    ax.set_xticks(range(len(GROUPS)), GROUPS)
    ax.set_ylabel("false-alarm episodes per user-month", color=INK2, fontsize=9)
    ax.set_ylim(bottom=0)
    ax.set_title("False alarms (no-change users, days 14-89), 95% bootstrap CI\n" + foot, loc="left",
                 fontsize=10, color=INK)
    _style(ax)
    fig.legend(loc="outside lower center", ncol=4, frameon=False, fontsize=8)
    fig.savefig("figures/false_alarms.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    # 2. Detection by magnitude, small multiples per group (primary + sensitivity)
    for defn, fname, desc in (
        ("primary", "detection_by_magnitude.png",
         "primary: window [onset, full-change day + 13]"),
        ("full_change", "detection_by_magnitude_previous_definition.png",
         "SENSITIVITY, previous definition: window [full-change day, full-change day + 13]"),
    ):
        fig, axes = plt.subplots(1, len(GROUPS), figsize=(12, 3.6), sharey=True, constrained_layout=True)
        for ax, g in zip(axes, GROUPS):
            for v in VARIANTS:
                ts = [m.detection(by_group[v][g], 14, size=sz, definition=defn) for sz in sim.CHANGE_SIZES]
                y = [t[0] for t in ts]
                ax.errorbar(sim.CHANGE_SIZES, y, yerr=[[t[0] - t[1] for t in ts], [t[2] - t[0] for t in ts]],
                            marker=VMARK[v], ls=VLS[v], color=VCOLOR[v], ms=6, lw=2, capsize=0,
                            label=VLABEL[v])
            ch = m.chance_detection(by_group["count_gated"][g], definition=defn)[0]
            ax.axhline(ch, color=INK2, ls=":", lw=1.5, label="chance level, count gated (no-change users)")
            ax.set_title(g, loc="left", fontsize=10, color=INK)
            ax.set_xticks(sim.CHANGE_SIZES)
            ax.set_xlabel("decline (points on 1-5 scale)", color=INK2, fontsize=8)
            ax.set_ylim(0, 1.02)
            _style(ax)
        axes[0].set_ylabel("detected (W = 14)", color=INK2, fontsize=9)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
        fig.suptitle(f"Detection rate by change magnitude ({desc}; 95% Wilson CI). " + foot
                     + "\nWhere only one line of a colour pair is visible, gated and ungated give "
                     "identical results.", fontsize=9, color=INK)
        fig.savefig(f"figures/{fname}", dpi=130, bbox_inches="tight")
        plt.close(fig)

    # 3. Detection delay from onset
    fig, ax = plt.subplots(figsize=(9, 4), constrained_layout=True)
    for k, v in enumerate(VARIANTS):
        ds = [m.delay(by_group[v][g]) for g in GROUPS]
        x = np.arange(len(GROUPS)) + offsets[k]
        y = [d[0] for d in ds]
        ax.errorbar(x, y, yerr=[[d[0] - d[3] for d in ds], [d[4] - d[0] for d in ds]],
                    fmt=VMARK[v], color=VCOLOR[v], ms=7, lw=2, capsize=0, label=VLABEL[v])
    ax.set_xticks(range(len(GROUPS)), GROUPS)
    ax.set_ylabel("days from onset to first detecting episode", color=INK2, fontsize=9)
    ax.set_ylim(bottom=0)
    ax.set_title("Detection delay from onset among detected users (primary definition): median and IQR\n" + foot, loc="left",
                 fontsize=10, color=INK)
    _style(ax)
    fig.legend(loc="outside lower center", ncol=4, frameon=False, fontsize=8)
    fig.savefig("figures/detection_delay.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    # 4. Precision by confidence label
    fig, ax = plt.subplots(figsize=(8, 3.8), constrained_layout=True)
    labels = ("low", "moderate", "strong")
    for k, v in enumerate(VARIANTS):
        pc = m.precision_by_confidence([r for g in GROUPS for r in by_group[v][g]])
        xs, ys, lo, hi = [], [], [], []
        for i, lab in enumerate(labels):
            t = pc[lab]
            if t[3]:
                xs.append(i + offsets[k]); ys.append(t[0]); lo.append(t[0] - t[1]); hi.append(t[2] - t[0])
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt=VMARK[v], color=VCOLOR[v], ms=7, lw=2,
                    capsize=0, label=VLABEL[v])
    ax.set_xticks(range(3), [f"{l}\n(first alert of episode)" for l in labels])
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("share of episodes that are correct", color=INK2, fontsize=9)
    ax.set_title("Alert precision by confidence label (a data-quantity label, not a probability)\n"
                 + foot + " Depends on the simulated 50% change prevalence.",
                 loc="left", fontsize=10, color=INK)
    _style(ax)
    fig.legend(loc="outside lower center", ncol=4, frameon=False, fontsize=8)
    fig.savefig("figures/precision_by_confidence.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    # 5. Grid heatmaps (sequential, one hue; shared scale per row)
    fig, axes = plt.subplots(3, 2, figsize=(11, 11), constrained_layout=True)
    for row, (key, label, cmap) in enumerate((("fa", "false-alarm episodes / user-month", "Oranges"),
                                              ("det", "detection rate (14-day window)", "Blues"),
                                              ("chance", "chance detection (no-change users)", "Blues"))):
        vmax = max(np.nanmax(G[v][key]) for v in m.GRID_VARIANTS)
        vmax = 1.0 if key != "fa" else vmax
        for col, v in enumerate(m.GRID_VARIANTS):
            ax = axes[row, col]
            data = G[v][key]
            im = ax.imshow(data, cmap=cmap, vmin=0, vmax=vmax, origin="lower", aspect="auto")
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    val = data[i, j]
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7,
                            color="white" if val > 0.6 * vmax else INK)
            ax.set_xticks(range(len(m.GRID_RATE)), [f"{p:.1f}" for p in m.GRID_RATE])
            ax.set_yticks(range(len(m.GRID_NOISE)), [f"{s:.2f}" for s in m.GRID_NOISE])
            ax.set_xlabel("check-in rate", color=INK2, fontsize=8)
            ax.set_ylabel("noise SD (1-5 scale)", color=INK2, fontsize=8)
            ax.set_title(f"{VLABEL[v]}: {label}", loc="left", fontsize=9, color=INK)
            ax.tick_params(colors=INK2, labelsize=8)
        fig.colorbar(im, ax=axes[row, :], shrink=0.85)
    fig.suptitle(f"Noise x check-in-rate grid ({m.GRID_USERS} users per cell, half with a change). "
                 + foot, fontsize=9, color=INK)
    fig.savefig("figures/grid_heatmap.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("wrote figures/*.png")


PCOLOR = "#e87ba4"   # categorical slot 5 (new entity); low contrast, so marker shape + tables too
GCOLOR = "#008300"   # categorical slot 6 (tuned global control)


def personalised_figure(cur, glob, per, pk, pf, tg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = (("count_gated", cur, VCOLOR["count_gated"], "o", "current (fixed 0.25)"),
              ("global", glob, GCOLOR, "^", f"tuned global (T={tg:g})"),
              ("personalised", per, PCOLOR, "s", f"personalised (K={pk:g}, FLOOR={pf:g})"))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True)
    x0 = np.arange(len(GROUPS))
    for k, (name, res, col, mk, lab) in enumerate(series):
        x = x0 + (k - 1) * 0.22
        by = [[r for r in res if r.group == g] for g in GROUPS]
        fa = [m.fa_rate(rs) for rs in by]
        de = [m.detection(rs) for rs in by]
        ch = [m.chance_detection(rs) for rs in by]
        dl = [m.delay(rs) for rs in by]
        axes[0].errorbar(x, [t[0] for t in fa], yerr=[[t[0] - t[1] for t in fa], [t[2] - t[0] for t in fa]],
                         fmt=mk, color=col, ms=7, lw=2, label=lab)
        axes[1].errorbar(x, [t[0] for t in de], yerr=[[t[0] - t[1] for t in de], [t[2] - t[0] for t in de]],
                         fmt=mk, color=col, ms=7, lw=2, label=lab + ": detected")
        axes[1].scatter(x, [t[0] for t in ch], marker=mk, s=40, facecolors="none", edgecolors=col, lw=1.5,
                        label=lab + ": chance", zorder=3)
        axes[2].errorbar(x, [d[0] for d in dl], yerr=[[d[0] - d[3] for d in dl], [d[4] - d[0] for d in dl]],
                         fmt=mk, color=col, ms=7, lw=2, label=lab)
    titles = ("false-alarm episodes / user-month (95% CI)",
              "detected (filled) and chance (hollow), primary, 14 d",
              "delay from onset: median and IQR (days)")
    for ax, t in zip(axes, titles):
        ax.set_xticks(x0, GROUPS, fontsize=8)
        ax.set_title(t, loc="left", fontsize=9, color=INK)
        ax.set_ylim(bottom=0)
        _style(ax)
    axes[1].set_ylim(0, 1.02)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    fig.suptitle("Held-out simulated users: current vs tuned global threshold vs personalised threshold. "
                 "Both tuned on separate seeds of the SAME simulator. Simulated data only; "
                 "not clinical validation.",
                 fontsize=9, color=INK)
    fig.savefig("figures/personalised_threshold.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("wrote figures/personalised_threshold.png")


if __name__ == "__main__":
    main()
