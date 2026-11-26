"""Report figures from the final campaign results (static PDF + PNG, plus a CSV of every number).

Uses the same loaders and conventions as pilot/analyze.py, so figures and rule verdicts agree:
C=1 averages each problem over seeds 0-2; C>1 uses seed 0; CIs are paired bootstraps over problems.

    python -m pilot.figures results/final_NVIDIA-H100-80GB-HBM3 --out results/figures

Figures (one panel per task; a configuration keeps the same color in every figure):
  1 latency_vs_load   median completion time vs concurrent debates C, for BASE, L1 only, L1+L2, L3
  2 speedup_vs_load   L1 speedup (BASE / L1+L2) vs C with the Rule 1 and Rule 2 reference lines
  3 caching_vs_load   L2 leave-one-out loss as % of T(L1+L2) vs C with the Rule 3 lines
  4 accuracy          accuracy change vs BASE at C=1 (pooled seeds), with the BASE-vs-BASE noise floor
  5 l3_breakdown      prefill tokens computed and median time for L1+L2, L3a, L3 at C=16
  6 h2_gap            per-problem gap to the critical-path bound vs within-round answer-length spread
"""

import argparse
import csv
import os
import random
import statistics
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pilot.analyze import accuracy_vs, boot_ratio, load, per_problem  # noqa: E402

SEEDS = (0, 1, 2)
LOADS = (1, 4, 16, 32)
TASKS = (("gsm8k", "GSM8K"), ("quality", "QuALITY"))
# Fixed categorical order (validated: adjacent CVD dE >= 11.8, normal-vision >= 20.5 on white).
CFG = {  # (mode, apc): (label, color, marker)
    ("seq", "on"): ("BASE", "#257de0", "o"),
    ("par", "on"): ("L1+L2", "#f47230", "s"),
    ("par", "off"): ("L1 only", "#00b894", "^"),
    ("l3", "on"): ("L1+L2+L3", "#f2a600", "D"),
    ("l3a", "on"): ("L1+L2+L3a", "#ee7fac", "v"),
    ("seq", "off"): ("Neither lever", "#6b6b6b", "x"),
}
INK, INK2, GRID = "#191919", "#666666", "#e6e6e6"
RNG = random.Random(0)
ROWS: List[Dict] = []  # table view: every plotted number


def style():
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "axes.edgecolor": INK2,
        "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "legend.frameon": False, "lines.linewidth": 2, "lines.markersize": 5, "savefig.dpi": 200,
        "pdf.fonttype": 42,
    })


def seeds_for(c):
    return SEEDS if c == 1 else (0,)


def boot_median(vals: List[float]) -> Tuple[float, float, float]:
    if not vals:
        return (float("nan"),) * 3
    bs = sorted(statistics.median(RNG.choices(vals, k=len(vals))) for _ in range(2000))
    return statistics.median(vals), bs[50], bs[1949]


def record(fig, task, series, x, y, lo=None, hi=None, unit=""):
    ROWS.append({"figure": fig, "task": task, "series": series, "x": x, "y": y, "ci_lo": lo, "ci_hi": hi, "unit": unit})


def place_labels(ax, items, gap_px=11):
    """Direct labels at each series' last point, nudged apart vertically so they never overlap."""
    if not items:
        return
    ax.get_ylim()  # force autoscale so the transform is final
    pts = sorted(((ax.transData.transform((x, y))[1], x, y, t) for x, y, t in items))
    placed = []
    for py, x, y, t in pts:
        target = py if not placed else max(py, placed[-1] + gap_px)
        placed.append(target)
        ax.annotate(t, (x, y), xytext=(6, (target - py) * 72 / ax.figure.dpi), textcoords="offset points",
                    va="center", fontsize=8, color=INK)


def xload(ax):
    ax.set_xscale("log", base=2)
    ax.set_xticks(LOADS)
    ax.set_xticklabels([str(c) for c in LOADS])
    ax.set_xlabel("Concurrent debates C")


def save(fig, out, name, rect=(0, 0, 1, 1)):
    fig.tight_layout(rect=rect)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"))
    plt.close(fig)


def fig_latency(runs, out):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))
    for ax, (task, title) in zip(axes, TASKS):
        ends = []
        for key in (("seq", "on"), ("par", "off"), ("par", "on"), ("l3", "on")):
            label, color, marker = CFG[key]
            xs, ys, lo, hi = [], [], [], []
            for c in LOADS:
                v = list(per_problem(runs, task, key[0], key[1], c, seeds_for(c)).values())
                if not v:
                    continue
                m, a, b = boot_median(v)
                xs.append(c); ys.append(m); lo.append(m - a); hi.append(b - m)
                record("latency_vs_load", task, label, c, m, a, b, "s")
            if xs:
                ax.errorbar(xs, ys, yerr=[lo, hi], color=color, marker=marker, capsize=2, label=label)
                ends.append((xs[-1], ys[-1], label))
        ax.set_title(title, loc="left")
        ax.set_ylabel("Median completion time (s)")
        ax.set_ylim(bottom=0)
        xload(ax)
        ax.set_xlim(0.8, 90)
        place_labels(ax, ends)
    h, l = axes[1].get_legend_handles_labels() if axes[1].lines else axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, 1.0))
    save(fig, out, "latency_vs_load", rect=(0, 0, 1, 0.9))


def fig_speedup(runs, out):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.6), sharey=True)
    color, marker = CFG[("par", "on")][1:]
    for ax, (task, title) in zip(axes, TASKS):
        xs, ys, lo, hi = [], [], [], []
        for c in LOADS:
            s = seeds_for(c)
            r = boot_ratio(per_problem(runs, task, "seq", "on", c, s), per_problem(runs, task, "par", "on", c, s))
            if r[0] != r[0]:
                continue
            xs.append(c); ys.append(r[0]); lo.append(r[0] - r[1]); hi.append(r[2] - r[0])
            record("speedup_vs_load", task, "L1 speedup (BASE / L1+L2)", c, *r, "x")
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], color=color, marker=marker, capsize=2)
            if xs[0] == 1:
                half = 1 + 0.5 * (ys[0] - 1)
                ax.axhline(half, color=INK2, linestyle=":", linewidth=1)
                ax.annotate("Rule 2: half the C=1 gain", (LOADS[-1], half), xytext=(0, 3),
                            textcoords="offset points", ha="right", fontsize=7.5, color=INK2)
        ax.axhline(1.5, color=INK2, linestyle="--", linewidth=1)
        ax.annotate("Rule 1: 1.5x at C=1", (LOADS[0], 1.5), xytext=(2, -10), textcoords="offset points",
                    fontsize=7.5, color=INK2)
        ax.axhline(1.0, color=INK, linewidth=0.8)
        ax.set_title(f"{title}: L1 speedup over BASE", loc="left")
        ax.set_ylabel("Speedup (x)")
        xload(ax)
    save(fig, out, "speedup_vs_load")


def fig_caching(runs, out):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.6))
    color, marker = CFG[("par", "off")][1:]
    for ax, (task, title) in zip(axes, TASKS):
        xs, ys, lo, hi = [], [], [], []
        for c in LOADS:
            s = seeds_for(c)
            off, on = per_problem(runs, task, "par", "off", c, s), per_problem(runs, task, "par", "on", c, s)
            r = boot_ratio(off, on)  # T(L1 only)/T(L1+L2); loss % = (ratio - 1) * 100
            if r[0] != r[0]:
                continue
            y = [100 * (v - 1) for v in r]
            xs.append(c); ys.append(y[0]); lo.append(y[0] - y[1]); hi.append(y[2] - y[0])
            record("caching_vs_load", task, "L2 leave-one-out loss", c, *y, "% of T(L1+L2)")
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], color=color, marker=marker, capsize=2)
        ref, text = (10, "Rule 3: 10% at C=16") if task == "quality" else (5, "Rule 3: below 5% at C=1")
        ax.axhline(ref, color=INK2, linestyle="--", linewidth=1)
        ax.annotate(text, (LOADS[0], ref), xytext=(2, 3), textcoords="offset points", fontsize=7.5, color=INK2)
        ax.axhline(0, color=INK, linewidth=0.8)
        ax.set_title(f"{title}: cost of turning caching off", loc="left")
        ax.set_ylabel("Extra time, % of T(L1+L2)")
        xload(ax)
    save(fig, out, "caching_vs_load")


def fig_accuracy(runs, out):
    rows = [(("par", "on"), ""), (("l3a", "on"), ""), (("l3", "on"), ""), (("par", "off"), ""),
            (("seq", "off"), ""), (("seq", "on"), "repeat")]
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.6), sharey=True)
    for ax, (task, title) in zip(axes, TASKS):
        ys, names = [], []
        for y, (key, tag) in enumerate(rows):
            seeds = (0,) if tag else SEEDS
            res = accuracy_vs(runs, task, key[0], key[1], 1, seeds, tag=tag)
            name = "BASE repeat (noise floor)" if tag else CFG[key][0]
            names.append(name); ys.append(y)
            if not res:
                continue
            lo, hi = paired_acc_ci(runs, task, key, tag, seeds)
            ax.errorbar([res["diff_pp"]], [y], xerr=[[res["diff_pp"] - lo], [hi - res["diff_pp"]]],
                        color=CFG[key][1], marker=CFG[key][2], capsize=2, linestyle="none")
            record("accuracy", task, name, 1, res["diff_pp"], lo, hi, "pp vs BASE")
        ax.axvspan(-100, -2, color="#efefef", zorder=0)
        ax.axvline(0, color=INK, linewidth=0.8)
        ax.axvline(-2, color=INK2, linestyle="--", linewidth=1)
        ax.annotate("Rule 5: -2 pp", (-2, -0.45), xytext=(-3, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=7.5, color=INK2)
        ax.set_yticks(ys)
        ax.set_yticklabels(names)
        ends = [abs(v) for r in ROWS if r["figure"] == "accuracy"
                for v in (r["ci_lo"], r["ci_hi"]) if v is not None]
        lim = max(ends + [6]) + 2
        ax.set_xlim(-lim, lim)
        ax.set_ylim(len(rows) - 0.5, -0.9)
        ax.set_title(f"{title}, C=1", loc="left")
        ax.set_xlabel("Accuracy change vs BASE (pp)")
    save(fig, out, "accuracy")


def paired_acc_ci(runs, task, key, tag, seeds):
    """95% paired bootstrap CI (pp) over (problem, seed) pairs."""
    a, b = {}, {}
    for s in seeds:
        for r in runs.get((task, key[0], key[1], 1, s, tag), []):
            a[(r["id"], s)] = int(bool(r["correct"]))
        for r in runs.get((task, "seq", "on", 1, s, ""), []):
            b[(r["id"], s)] = int(bool(r["correct"]))
    keys = sorted(set(a) & set(b))
    d = [a[k] - b[k] for k in keys]
    bs = sorted(100 * sum(RNG.choices(d, k=len(d))) / len(d) for _ in range(2000))
    return bs[50], bs[1949]


def fig_l3(runs, out, c=16):
    keys = (("par", "on"), ("l3a", "on"), ("l3", "on"))
    fig, axes = plt.subplots(2, 2, figsize=(7, 4.2))
    for col, (task, title) in enumerate(TASKS):
        for row, (field, ylabel, unit) in enumerate((("prefill", "Prefill tokens / debate", "tokens"),
                                                     ("T", "Median time (s)", "s"))):
            ax = axes[row][col]
            for x, key in enumerate(keys):
                v = list(per_problem(runs, task, key[0], key[1], c, (0,), field=field).values())
                if not v:
                    continue
                m, lo, hi = boot_median(v)
                ax.bar(x, m, width=0.6, color=CFG[key][1], edgecolor="white", linewidth=2)
                ax.errorbar(x, m, yerr=[[m - lo], [hi - m]], color=INK, capsize=2, linewidth=1)
                ax.annotate(f"{m:,.0f}" if field == "prefill" else f"{m:.1f}", (x, hi), xytext=(0, 3),
                            textcoords="offset points", ha="center", fontsize=7.5, color=INK)
                record("l3_breakdown", task, CFG[key][0], c, m, lo, hi, unit)
            ax.set_xticks(range(len(keys)))
            ax.set_xticklabels([CFG[k][0] for k in keys])
            ax.set_ylabel(ylabel)
            ax.grid(axis="x", visible=False)
            if row == 0:
                ax.set_title(f"{title}, C={c}", loc="left")
    save(fig, out, "l3_breakdown")


def fig_h2(runs, out):
    fig, axes = plt.subplots(1, 2, figsize=(7, 2.6))
    color = CFG[("seq", "on")][1]
    for ax, (task, title) in zip(axes, TASKS):
        base = {(r["id"], s): r for s in SEEDS for r in runs.get((task, "seq", "on", 1, s, ""), [])}
        par = {(r["id"], s): r for s in SEEDS for r in runs.get((task, "par", "on", 1, s, ""), [])}
        xs, ys = [], []
        for k in sorted(set(base) & set(par)):
            b, p = base[k], par[k]
            spread = 0
            for rnd in (0, 1):
                o = [c["out"] for c in p["calls"] if c["kind"] == "debate" and c["rnd"] == rnd]
                spread += max(o) - min(o) if o else 0
            gap = b["T"] / b["cp"] - b["T"] / p["T"]  # bound minus measured speedup
            xs.append(spread); ys.append(gap)
        rho = float("nan")
        if xs:
            ax.scatter(xs, ys, s=12, color=color, alpha=0.55, edgecolor="white", linewidth=0.5)
            rho = spearman(xs, ys)
            record("h2_gap", task, "median gap", "", statistics.median(ys), None, None, "x")
            record("h2_gap", task, "spearman rho", "", rho, None, None, "")
        ax.axhline(0, color=INK, linewidth=0.8)
        ax.set_title(f"{title}, C=1 (Spearman {rho:.2f}, n={len(xs)})", loc="left")
        ax.set_xlabel("Within-round answer-length spread (tokens)")
        ax.set_ylabel("Bound minus speedup (x)")
    save(fig, out, "h2_gap")


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=v.__getitem__)
        r = [0.0] * len(v)
        for k, i in enumerate(order):
            r[i] = k
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dir")
    ap.add_argument("--out", default="results/figures")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    style()
    runs = load(a.dir)
    for f in (fig_latency, fig_speedup, fig_caching, fig_accuracy, fig_l3, fig_h2):
        f(runs, a.out)
    with open(os.path.join(a.out, "figures_data.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0]) if ROWS else ["figure"])
        w.writeheader()
        w.writerows(ROWS)
    print(f"wrote 6 figures (pdf+png) and figures_data.csv ({len(ROWS)} rows) to {a.out}")


if __name__ == "__main__":
    main()
