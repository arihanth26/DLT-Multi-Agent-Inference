"""Summarize pilot rows into the quantities the preregistered decision rules use.

Pilot sizes are small (tens of problems, one seed, C up to 4), so treat these as direction
checks and as a test of the pipeline, not as results against the thresholds.

Usage:
    python -m pilot.summarize results/pilot/pilot_<jobid>.jsonl
"""

import json
import random
import statistics as st
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

Key = Tuple[str, int, str, str]  # (task, conc, mode, apc)
LABEL = {("seq", "on"): "BASE (seq, APC on)", ("seq", "off"): "neither lever",
         ("par", "off"): "L1 only", ("par", "on"): "L1+L2",
         ("l3a", "on"): "L1+L2+L3a warm", ("l3", "on"): "L1+L2+L3 full",
         ("single", "on"): "single agent"}


def load(path: str) -> Dict[Key, List[dict]]:
    groups: Dict[Key, List[dict]] = defaultdict(list)
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            groups[(r["task"], r["conc"], r["mode"], r["apc"])].append(r)
    return groups


def med(rows: List[dict]) -> float:
    return st.median(r["T"] for r in rows)


def prefill_per_task(rows: List[dict]) -> float:
    """Prompt tokens actually computed (not served from cache), per task, warm-ups included."""
    return sum(c["prompt"] - c["cached"] for r in rows for c in r["calls"]) / len(rows)


def boot_ratio_lb(a: List[dict], b: List[dict], iters: int = 2000) -> float:
    """2.5th percentile of median(T_a)/median(T_b), resampling problems (paired by id)."""
    ta, tb = {r["id"]: r["T"] for r in a}, {r["id"]: r["T"] for r in b}
    ids = sorted(set(ta) & set(tb))
    if len(ids) < 5:
        return float("nan")
    rng = random.Random(0)
    vals = []
    for _ in range(iters):
        s = [rng.choice(ids) for _ in ids]
        vals.append(st.median(ta[i] for i in s) / st.median(tb[i] for i in s))
    vals.sort()
    return vals[int(0.025 * iters)]


def paired(a: List[dict], b: List[dict], field: str) -> Tuple[int, int, int, int]:
    """Compare two configurations problem by problem.

    Returns (rows where `field` matches, a correct but b wrong, b correct but a wrong, n shared).
    The two discordant counts are what a McNemar test uses.
    """
    A, B = {r["id"]: r for r in a}, {r["id"]: r for r in b}
    ids = set(A) & set(B)
    same = sum(A[i][field] == B[i][field] for i in ids)
    a_only = sum(A[i]["correct"] and not B[i]["correct"] for i in ids)
    b_only = sum(B[i]["correct"] and not A[i]["correct"] for i in ids)
    return same, a_only, b_only, len(ids)


def main(path: str) -> None:
    g = load(path)
    print(f"# Pilot summary: {path}\n")
    print("## All configurations")
    print(f"{'task':8}{'C':>3}  {'config':22}{'n':>4}{'medT s':>8}{'p95T':>7}{'xBASE':>7}{'acc':>6}"
          f"{'prefill/task':>13}{'cached%':>8}{'ans tok':>8}{'T/cp':>6}")
    for k in sorted(g, key=lambda k: (k[0], k[1], list(LABEL).index((k[2], k[3])))):
        rows = g[k]
        T = sorted(r["T"] for r in rows)
        calls = [c for r in rows for c in r["calls"]]
        pt, ca = sum(c["prompt"] for c in calls), sum(c["cached"] for c in calls)
        base = g.get((k[0], k[1], "seq", "on"))
        x = med(base) / med(rows) if base else float("nan")
        ans = st.mean(t for r in rows for t in r["answer_tokens"])
        print(f"{k[0]:8}{k[1]:>3}  {LABEL[(k[2], k[3])]:22}{len(rows):>4}{med(rows):>8.2f}"
              f"{T[int(0.95 * (len(T) - 1))]:>7.2f}{x:>7.2f}{sum(r['correct'] for r in rows) / len(rows):>6.2f}"
              f"{prefill_per_task(rows):>13.0f}{100 * ca / max(pt, 1):>8.1f}{ans:>8.0f}"
              f"{st.median(r['T'] / r['cp'] for r in rows):>6.2f}")

    print("\n## Preregistered quantities (pilot scale)")
    for task in sorted({k[0] for k in g}):
        for c in sorted({k[1] for k in g if k[0] == task}):
            G = lambda m, apc: g.get((task, c, m, apc))  # noqa: E731
            print(f"\n### {task}, C={c}")
            if G("seq", "on") and G("par", "on"):
                s = med(G("seq", "on")) / med(G("par", "on"))
                print(f"Rule 1/2  L1 speedup T_BASE/T_L1 = {s:.2f}  (95% bootstrap LB "
                      f"{boot_ratio_lb(G('seq', 'on'), G('par', 'on')):.2f}); add-one gain {s - 1:.2f}")
            if G("par", "off") and G("par", "on"):
                loss = med(G("par", "off")) - med(G("par", "on"))
                print(f"Rule 3    L2 leave-one-out loss = {loss:.2f}s = {100 * loss / med(G('par', 'on')):.1f}% of T(both)")
            if G("seq", "off") and G("seq", "on"):
                print(f"          (APC on vs off under sequential dispatch: {med(G('seq', 'off')) - med(G('seq', 'on')):.2f}s)")
            for m in ("l3a", "l3"):
                if G(m, "on") and G("par", "on"):
                    dp = prefill_per_task(G(m, "on")) / max(prefill_per_task(G("par", "on")), 1) - 1
                    dt = med(G(m, "on")) / med(G("par", "on")) - 1
                    print(f"Rule 4    {m}: prefill tokens computed {100 * dp:+.0f}% vs L1+L2, "
                          f"median T {100 * dt:+.0f}%  (preregistered: <= -30% and <= -10% at C=16)")
            if G("seq", "on"):
                cp = st.median(r["T"] / r["cp"] for r in G("seq", "on"))
                print(f"H2        critical-path bound on L1 speedup (median T_seq/cp) = {cp:.2f}")
            # Guardrail and input-equivalence checks against BASE.
            for m, apc in (("par", "on"), ("par", "off"), ("l3a", "on"), ("l3", "on"), ("seq", "off")):
                if G(m, apc) and G("seq", "on"):
                    same, b_only, m_only, n = paired(G("seq", "on"), G(m, apc), "final")
                    acc_d = 100 * (m_only - b_only) / n
                    print(f"Rule 5    {LABEL[(m, apc)]:20} vs BASE: final answers agree {same}/{n}; "
                          f"accuracy {acc_d:+.1f} pp (discordant: BASE-only {b_only}, config-only {m_only})")
            for m in ("seq", "par", "l3a"):
                rows = G(m, "on")
                if rows:
                    r1 = [c for r in rows for c in r["calls"] if c["kind"] == "debate" and c["rnd"] == 0 and c["agent"] > 0]
                    if r1:
                        share = 100 * sum(c["cached"] for c in r1) / max(sum(c["prompt"] for c in r1), 1)
                        print(f"H4        {m:4}: round-1 prompt served from cache for agents 2-3: {share:.0f}%")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/pilot/pilot.jsonl")
