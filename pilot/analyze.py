"""Final analysis: preregistered decision rules, guardrail, H2, factorial and the SCD extension.

Reads every results/final_<GPU>/*.jsonl written by slurm/campaign.sbatch (one configuration per
file) and prints a markdown report. Results from different GPU directories are never pooled.

    python -m pilot.analyze results/final_NVIDIA-H100-80GB-HBM3 > results/final_report.md
    python -m pilot.analyze results/final_NVIDIA-H100-80GB-HBM3 --json results/final_numbers.json

Conventions (fixed before the final data were seen; see docs/project_plan.md revision log):
  - BASE = seq with caching on. L1 = par. L2 = caching. L1+L2 = par on. L3 = l3 (on).
  - A configuration's T at C=1 averages each problem's T over seeds 0-2, then takes the median.
  - Speedup = median T(BASE) / median T(config). CIs: paired bootstrap over problems, 4000 resamples.
  - Under load (C>1) a single seed is used, as preregistered.
  - Accuracy pools problems x seeds; exact McNemar on the discordant (problem, seed) pairs.
  - Prefill tokens computed = prompt tokens - cached tokens, summed over a task's calls (warm-ups included).
"""

import argparse
import glob
import json
import math
import os
import random
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

B = 4000
RNG = random.Random(0)

Key = Tuple[str, str, str, int, int, str]  # task, mode, apc, conc, seed, tag


def load(d: str) -> Dict[Key, List[Dict[str, Any]]]:
    runs: Dict[Key, List[Dict[str, Any]]] = {}
    for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
        tag = "repeat" if "_repeat" in os.path.basename(f) else ""
        recs = [json.loads(l) for l in open(f) if l.strip()]
        if not recs:
            continue
        r0 = recs[0]
        runs[(r0["task"], r0["mode"], r0["apc"], int(r0["conc"]), int(r0["seed"]), tag)] = recs
    return runs


def prefill(r: Dict[str, Any]) -> int:
    return sum((c["prompt"] or 0) - (c["cached"] or 0) for c in r["calls"])


def per_problem(runs, task, mode, apc, conc, seeds, field="T", tag="") -> Dict[str, float]:
    """Problem id -> value averaged over the given seeds (only problems present in every seed)."""
    acc: Dict[str, List[float]] = defaultdict(list)
    present = []
    for s in seeds:
        recs = runs.get((task, mode, apc, conc, s, tag))
        if not recs:
            continue
        present.append(s)
        for r in recs:
            acc[r["id"]].append(prefill(r) if field == "prefill" else r[field])
    if not present:
        return {}
    return {k: sum(v) / len(v) for k, v in acc.items() if len(v) == len(present)}


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def boot_ratio(a: Dict[str, float], b: Dict[str, float]) -> Tuple[float, float, float]:
    """median(a)/median(b) on shared problems, with a paired 95% bootstrap CI."""
    ids = sorted(set(a) & set(b))
    if not ids:
        return (float("nan"),) * 3
    pt = med([a[i] for i in ids]) / med([b[i] for i in ids])
    bs = []
    for _ in range(B):
        s = [RNG.choice(ids) for _ in ids]
        bs.append(med([a[i] for i in s]) / med([b[i] for i in s]))
    bs.sort()
    return pt, bs[int(0.025 * B)], bs[int(0.975 * B) - 1]


def boot_diff(a, b) -> Tuple[float, float, float]:
    """median(a) - median(b) on shared problems, paired bootstrap CI."""
    ids = sorted(set(a) & set(b))
    if not ids:
        return (float("nan"),) * 3
    pt = med([a[i] for i in ids]) - med([b[i] for i in ids])
    bs = []
    for _ in range(B):
        s = [RNG.choice(ids) for _ in ids]
        bs.append(med([a[i] for i in s]) - med([b[i] for i in s]))
    bs.sort()
    return pt, bs[int(0.025 * B)], bs[int(0.975 * B) - 1]


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for b, c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def accuracy_vs(runs, task, mode, apc, conc, seeds, base=("seq", "on"), tag="", base_tag=""):
    """Pooled accuracy difference (pp) vs BASE on shared (problem, seed) pairs + McNemar."""
    pairs_a, pairs_b = {}, {}
    for s in seeds:
        for r in runs.get((task, mode, apc, conc, s, tag), []):
            pairs_a[(r["id"], s)] = bool(r["correct"])
        for r in runs.get((task, base[0], base[1], conc, s, base_tag), []):
            pairs_b[(r["id"], s)] = bool(r["correct"])
    keys = sorted(set(pairs_a) & set(pairs_b))
    if not keys:
        return None
    acc_a = sum(pairs_a[k] for k in keys) / len(keys)
    acc_b = sum(pairs_b[k] for k in keys) / len(keys)
    b = sum(pairs_a[k] and not pairs_b[k] for k in keys)
    c = sum(pairs_b[k] and not pairs_a[k] for k in keys)
    p = mcnemar_exact(b, c)
    diff = 100 * (acc_a - acc_b)
    return {"n": len(keys), "acc": acc_a, "base_acc": acc_b, "diff_pp": diff, "better": b,
            "worse": c, "p": p, "regression": diff < -2.0 or (c > b and p < 0.05)}


def fmt(x, d=2):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def ci(t, d=2):
    return f"{fmt(t[0], d)} [{fmt(t[1], d)}, {fmt(t[2], d)}]"


# ----------------------------------------------------------------------------- report

def config_table(runs) -> List[str]:
    out = ["| Task | Mode | APC | C | Seed | n | median T (s) | p95 T (s) | prefill tok/task | cache hit | accuracy |",
           "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in sorted(runs, key=lambda k: (k[0], k[3], k[4], k[1], k[2], k[5])):
        recs = runs[k]
        Ts = sorted(r["T"] for r in recs)
        p95 = Ts[max(0, math.ceil(0.95 * len(Ts)) - 1)]
        pr = sum(c["prompt"] or 0 for r in recs for c in r["calls"])
        ca = sum(c["cached"] or 0 for r in recs for c in r["calls"])
        out.append(f"| {k[0]} | {k[1]}{' (repeat)' if k[5] else ''} | {k[2]} | {k[3]} | {k[4]} | {len(recs)} | "
                   f"{fmt(med(Ts))} | {fmt(p95)} | {med([prefill(r) for r in recs]):.0f} | "
                   f"{fmt(ca / pr if pr else float('nan'))} | {fmt(sum(r['correct'] for r in recs) / len(recs))} |")
    return out


def rules(runs, numbers) -> List[str]:
    S = (0, 1, 2)
    out = ["| Rule | Quantity | Value [95% CI] | Threshold | Verdict |", "|---|---|---|---|---|"]

    def T(task, mode, apc, conc, seeds=S, field="T"):
        return per_problem(runs, task, mode, apc, conc, seeds if conc == 1 else (0,), field)

    # Rule 1: L1 at C=1 (BASE -> L1+L2, i.e. add L1 to BASE).
    r1 = {}
    for task in ("gsm8k", "quality"):
        r1[task] = boot_ratio(T(task, "seq", "on", 1), T(task, "par", "on", 1))
        ok = r1[task][0] >= 1.5 and r1[task][1] > 1.2
        out.append(f"| 1 | {task} L1 speedup at C=1 | {ci(r1[task])} | >= 1.5, lower bound > 1.2 | "
                   f"{'met' if ok else 'not met'} |")
    numbers["rule1"] = r1

    # Rule 2: L1 add-one gain at C=32 < half its C=1 value.
    for task in ("gsm8k", "quality"):
        g1 = r1[task][0] - 1
        s32 = boot_ratio(T(task, "seq", "on", 32), T(task, "par", "on", 32))
        g32 = s32[0] - 1
        ok = not math.isnan(g32) and g32 < 0.5 * g1
        out.append(f"| 2 | {task} L1 gain C=32 vs C=1 | {fmt(g32)} vs {fmt(g1)} "
                   f"(C=32 speedup {ci(s32)}) | < half | {'met' if ok else 'not met'} |")
        numbers.setdefault("rule2", {})[task] = {"gain_c1": g1, "speedup_c32": s32}

    # Rule 3: L2 leave-one-out loss = T(par off) - T(par on).
    l1q = boot_diff(T("quality", "par", "off", 1), T("quality", "par", "on", 1))
    l16 = boot_diff(T("quality", "par", "off", 16), T("quality", "par", "on", 16))
    t16 = med(list(T("quality", "par", "on", 16).values()))
    ok_q = l16[0] >= 2 * l1q[0] and l16[0] >= 0.10 * t16
    out.append(f"| 3 | QuALITY L2 loss C=16 vs C=1 | {ci(l16)} s vs {ci(l1q)} s "
               f"({fmt(100 * l16[0] / t16 if t16 else float('nan'), 1)}% of T) | >= 2x and >= 10% | "
               f"{'met' if ok_q else 'not met'} |")
    lg = boot_diff(T("gsm8k", "par", "off", 1), T("gsm8k", "par", "on", 1))
    tg = med(list(T("gsm8k", "par", "on", 1).values()))
    share = 100 * lg[0] / tg if tg else float("nan")
    out.append(f"| 3 | GSM8K L2 loss at C=1 | {ci(lg)} s ({fmt(share, 1)}% of T) | < 5% | "
               f"{'met' if share < 5 else 'not met'} |")
    numbers["rule3"] = {"quality_c1": l1q, "quality_c16": l16, "gsm8k_c1": lg, "gsm8k_share_pct": share}

    # Rule 4: L3 on QuALITY at C=16 vs L1+L2.
    pa, pl = T("quality", "par", "on", 16, field="prefill"), T("quality", "l3", "on", 16, field="prefill")
    ids = sorted(set(pa) & set(pl))
    cut = 100 * (1 - sum(pl[i] for i in ids) / sum(pa[i] for i in ids)) if ids else float("nan")
    tr = boot_ratio(T("quality", "l3", "on", 16), T("quality", "par", "on", 16))
    tcut = 100 * (1 - tr[0])
    ok4 = cut >= 30 and tcut >= 10
    out.append(f"| 4 | QuALITY L3 at C=16: prefill cut, median T cut | {fmt(cut, 1)}%, {fmt(tcut, 1)}% "
               f"(T ratio {ci(tr)}) | >= 30%, >= 10% | {'met' if ok4 else 'not met'} |")
    numbers["rule4"] = {"prefill_cut_pct": cut, "T_ratio": tr}

    # Rule 5: accuracy guardrail at C=1 (pooled seeds), with BASE-vs-BASE noise floor.
    for task in ("gsm8k", "quality"):
        nf = accuracy_vs(runs, task, "seq", "on", 1, (0,), tag="repeat")
        if nf:
            out.append(f"| 5 | {task} noise floor: BASE repeat vs BASE (seed 0) | {fmt(nf['diff_pp'], 1)} pp, "
                       f"{nf['better']}/{nf['worse']} discordant, p={fmt(nf['p'], 3)} | reference | - |")
        for mode, apc in (("par", "on"), ("l3a", "on"), ("l3", "on"), ("par", "off"), ("seq", "off")):
            a = accuracy_vs(runs, task, mode, apc, 1, S)
            if not a:
                continue
            out.append(f"| 5 | {task} {mode} apc={apc} vs BASE, C=1 | {fmt(a['diff_pp'], 1)} pp "
                       f"({fmt(100 * a['acc'], 1)}% vs {fmt(100 * a['base_acc'], 1)}%, n={a['n']}, "
                       f"{a['better']}/{a['worse']}, p={fmt(a['p'], 3)}) | not < -2.0 pp, not sig. lower | "
                       f"{'REGRESSION' if a['regression'] else 'held'} |")
            numbers.setdefault("rule5", {})[f"{task}_{mode}_{apc}"] = a
    return out


def h2_and_factorial(runs, numbers) -> List[str]:
    out = ["", "## H2: critical path and factorial at C=1", "",
           "| Task | L1 speedup | Critical-path bound | Share of bound | Answer-length spread (tokens, median) |",
           "|---|---:|---:|---:|---:|"]
    for task in ("gsm8k", "quality"):
        base = per_problem(runs, task, "seq", "on", 1, (0, 1, 2))
        par = per_problem(runs, task, "par", "on", 1, (0, 1, 2))
        cp = per_problem(runs, task, "par", "on", 1, (0, 1, 2), field="cp")
        ids = sorted(set(base) & set(par) & set(cp))
        if not ids:
            continue
        sp = med([base[i] for i in ids]) / med([par[i] for i in ids])
        bound = med([base[i] for i in ids]) / med([cp[i] for i in ids])
        spread = []
        for s in (0, 1, 2):
            for r in runs.get((task, "par", "on", 1, s, ""), []):
                for rnd in (0, 1):
                    outs = [c["out"] for c in r["calls"] if c["rnd"] == rnd and c["kind"] == "debate"]
                    if outs:
                        spread.append(max(outs) - min(outs))
        out.append(f"| {task} | {sp:.2f} | {bound:.2f} | {100 * sp / bound:.0f}% | {med(spread):.0f} |")
    out += ["", "| Task | T seq/off | T par/off | T seq/on (BASE) | T par/on | Interaction (s) |",
            "|---|---:|---:|---:|---:|---:|"]
    for task in ("gsm8k", "quality"):
        m = {(md, a): med(list(per_problem(runs, task, md, a, 1, (0, 1, 2)).values()))
             for md in ("seq", "par") for a in ("off", "on")}
        inter = (m[("seq", "off")] - m[("par", "off")]) - (m[("seq", "on")] - m[("par", "on")])
        out.append(f"| {task} | {fmt(m[('seq', 'off')])} | {fmt(m[('par', 'off')])} | {fmt(m[('seq', 'on')])} | "
                   f"{fmt(m[('par', 'on')])} | {fmt(inter)} |")
        numbers.setdefault("factorial", {})[task] = {f"{k[0]}_{k[1]}": v for k, v in m.items()} | {"interaction": inter}
    return out


def scd(runs, numbers) -> List[str]:
    if not any(k[0] == "scd" for k in runs):
        return []
    out = ["", "## Supply-chain extension (exploratory)", "",
           "| C | Config | median T (s) | Speedup vs BASE [95% CI] | Stage-3 share of T | prefill tok/task | "
           "accuracy (final) | accuracy (stage-2 vote) |", "|---:|---|---:|---|---:|---:|---:|---:|"]
    for conc in (1, 16):
        base = per_problem(runs, "scd", "seq", "on", conc, (0,))
        for mode, apc in (("seq", "on"), ("seq", "off"), ("par", "off"), ("par", "on"), ("l3a", "on"),
                          ("l3", "on"), ("single", "on")):
            recs = runs.get(("scd", mode, apc, conc, 0, ""))
            if not recs:
                continue
            t = per_problem(runs, "scd", mode, apc, conc, (0,))
            sp = boot_ratio(base, t)
            st3 = med([r["stage3_s"] / r["T"] for r in recs if r["T"]])
            vote = [r["vote_correct"] for r in recs if r.get("vote_correct") is not None]
            out.append(f"| {conc} | {mode} apc={apc} | {fmt(med(list(t.values())))} | {ci(sp)} | "
                       f"{fmt(100 * st3, 0)}% | {med([prefill(r) for r in recs]):.0f} | "
                       f"{fmt(sum(r['correct'] for r in recs) / len(recs))} | "
                       f"{fmt(sum(vote) / len(vote)) if vote else 'n/a'} |")
            numbers.setdefault("scd", {})[f"{mode}_{apc}_C{conc}"] = {"speedup": sp, "stage3_share": st3}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Final analysis of one results/final_<GPU> directory.")
    ap.add_argument("dir")
    ap.add_argument("--json", default=None, help="Also write the headline numbers to this JSON file.")
    a = ap.parse_args()
    runs = load(a.dir)
    numbers: Dict[str, Any] = {"dir": a.dir, "configs": len(runs)}
    lines = [f"# Final results: {a.dir}", "", f"{len(runs)} configurations loaded.", "",
             "## Preregistered decision rules", ""] + rules(runs, numbers)
    lines += h2_and_factorial(runs, numbers) + scd(runs, numbers)
    lines += ["", "## All configurations", ""] + config_table(runs)
    print("\n".join(lines))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(numbers, f, indent=1, default=str)


if __name__ == "__main__":
    main()
