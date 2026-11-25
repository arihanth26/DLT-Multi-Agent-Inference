"""Supply-Chain Disruption Response (SCD): seeded scenarios with solver-computed gold answers.

A primary supplier of one SKU goes offline. The planner must pick one of four recovery plans
(A-D). Each scenario's dossier gives everything needed to cost the plans exactly: daily demand,
stock on hand, open purchase orders, alternate suppliers, freight lanes and the cost policy.
The gold answer is the plan with the lowest total cost over the horizon, computed by
`plan_cost` below (a day-by-day lost-sales inventory simulation). Scenarios where the best two
plans are within MARGIN of each other are rejected, so every gold answer is unambiguous.

No external data: scenario i of seed s is always the same, so runs reproduce from code alone.

Usage:
    python -m data.supply_chain.generate --n 300 --seed 0 --out data/supply_chain/scd_seed0.jsonl
"""

import argparse
import json
import math
import random
from typing import Any, Dict, List, Tuple

HORIZON = 56          # days costed
MARGIN = 0.05         # best plan must beat the runner-up by at least 5% of its cost
LETTERS = "ABCD"

FAMILIES = [
    ("6205-2RS deep-groove ball bearing", "BRG"),
    ("M8 stainless hex fastener kit", "FST"),
    ("24 V brushless DC motor, 60 W", "MTR"),
    ("12 V DC-DC power module", "PWR"),
    ("NBR hydraulic seal, 50 mm", "SEL"),
    ("Cat6 shielded patch cable, 2 m", "CBL"),
    ("Aluminium heat sink, 40 mm", "HSK"),
    ("Pneumatic solenoid valve, 1/4 in", "VLV"),
]
REGIONS = {"domestic": ["Truck", "Rail"], "overseas": ["Ocean", "Air"]}
SUPPLIER_NAMES = ["Apex Industrial", "Brightline Mfg", "Cobalt Parts", "Delta Precision",
                  "Everfield Supply", "Fujin Components", "Granite Works", "Harbor Metals",
                  "Ironwood Tech", "Jadeport Trading", "Keystone Fab", "Lumen Electric"]
# lane: (transit days range, per-unit cost range in $, fixed $ per shipment)
LANES = {"Ocean": ((18, 30), (0.40, 1.00), 800),
         "Rail": ((10, 16), (0.80, 1.60), 400),
         "Truck": ((2, 5), (1.50, 3.00), 250),
         "Air": ((1, 3), (4.00, 9.00), 150)}


# ----------------------------------------------------------------------------- solver

def shipments(order: Dict[str, Any], sup: Dict[str, Any], lane: Dict[str, Any]) -> List[Tuple[int, int]]:
    """(arrival day, qty) chunks: the supplier ships at most its weekly capacity per week,
    starting after its lead time; each chunk then spends the lane's transit days in transit."""
    out, left, k = [], order["qty"], 0
    while left > 0:
        q = min(left, sup["cap_week"])
        out.append((sup["lead"] + 7 * k + lane["transit"], q))
        left -= q
        k += 1
    return out


def plan_cost(sc: Dict[str, Any], plan: List[Dict[str, Any]]) -> Dict[str, float]:
    """Total cost of a plan over HORIZON days: purchase + freight + lost sales + holding.
    Units arriving after the horizon are still bought and shipped (they are paid for)."""
    sups = {s["name"]: s for s in sc["suppliers"]}
    lanes = {l["name"]: l for l in sc["lanes"]}
    arrivals: Dict[int, int] = {}
    for po in sc["open_pos"]:
        if po["arrive"] >= sc["outage_days"]:          # deliveries during the outage are lost
            arrivals[po["arrive"]] = arrivals.get(po["arrive"], 0) + po["qty"]
    purchase = freight = 0.0
    for o in plan:
        s, l = sups[o["supplier"]], lanes[o["lane"]]
        purchase += o["qty"] * s["unit_cost"]
        for day, q in shipments(o, s, l):
            freight += l["fixed"] + q * l["per_unit"]
            arrivals[day] = arrivals.get(day, 0) + q
    inv, short, held = sc["on_hand"], 0, 0
    for t in range(HORIZON):
        inv += arrivals.get(t, 0)
        sold = min(inv, sc["demand"][t])
        short += sc["demand"][t] - sold
        inv -= sold
        held += inv
    lost = short * sc["penalty"]
    hold = held * sc["holding"]
    return {"purchase": round(purchase, 2), "freight": round(freight, 2),
            "lost_sales": round(lost, 2), "holding": round(hold, 2), "units_short": short,
            "total": round(purchase + freight + lost + hold, 2)}


# ----------------------------------------------------------------------------- generator

def _round_up(q: float, moq: int) -> int:
    return max(moq, int(math.ceil(q / moq)) * moq)


def _base(rng: random.Random, idx: int) -> Dict[str, Any]:
    family, code = rng.choice(FAMILIES)
    mu = rng.randint(80, 240)
    week = [rng.uniform(0.85, 1.15) for _ in range(7)]
    demand = [max(0, round(mu * week[t % 7] * rng.uniform(0.85, 1.15))) for t in range(HORIZON)]
    base_cost = round(rng.uniform(4, 40), 2)
    outage = rng.randint(14, 35)
    primary = rng.choice(SUPPLIER_NAMES)
    open_pos = [{"po": f"PO-{rng.randint(40000, 49999)}", "supplier": primary,
                 "arrive": d, "qty": int(round(14 * mu, -1))} for d in (7, 21, 35, 49)]
    names = rng.sample([n for n in SUPPLIER_NAMES if n != primary], rng.randint(5, 7))
    suppliers = []
    for n in names:
        region = rng.choice(list(REGIONS))
        far = region == "overseas"
        suppliers.append({
            "name": n, "region": region,
            "unit_cost": round(base_cost * rng.uniform(0.95, 1.25 if far else 1.6), 2),
            "lead": rng.randint(5, 14) if far else rng.randint(2, 8),
            "cap_week": int(round(7 * mu * rng.uniform(0.4, 1.4), -1)),
            "moq": rng.choice([100, 200, 250, 500]),
        })
    lanes = []
    for name, ((t0, t1), (c0, c1), fixed) in LANES.items():
        lanes.append({"name": name, "transit": rng.randint(t0, t1),
                      "per_unit": round(rng.uniform(c0, c1), 2), "fixed": fixed})
    return {"id": f"scd-{idx}", "family": family, "sku": f"{code}-{rng.randint(1000, 9999)}",
            "demand": demand, "on_hand": int(round(mu * rng.uniform(5, 12), -1)),
            "outage_days": outage, "primary": primary, "open_pos": open_pos,
            "suppliers": suppliers, "lanes": lanes, "base_cost": base_cost,
            "penalty": round(base_cost * rng.uniform(1.5, 4.0), 2),
            "holding": round(base_cost * rng.uniform(0.001, 0.004), 4)}


def _candidates(rng: random.Random, sc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pool of realistic recovery plans: wait, single-supplier orders, and fast/slow splits."""
    lost_po = sum(p["qty"] for p in sc["open_pos"] if p["arrive"] < sc["outage_days"])
    gap = max(lost_po, sum(sc["demand"]) - sc["on_hand"]
              - sum(p["qty"] for p in sc["open_pos"] if p["arrive"] >= sc["outage_days"]))
    pool = [{"desc": f"Order nothing; wait for {sc['primary']} to recover.", "orders": []}]
    for s in sc["suppliers"]:
        fast, slow = REGIONS[s["region"]][0], REGIONS[s["region"]][1]
        if s["region"] == "overseas":
            fast, slow = "Air", "Ocean"
        for frac in (0.6, 1.0):
            q = _round_up(gap * frac, s["moq"])
            for lane in (fast, slow):
                pool.append({"desc": f"Order {q:,} units from {s['name']}, shipped by {lane}.",
                             "orders": [{"supplier": s["name"], "lane": lane, "qty": q}]})
        q1 = _round_up(gap * 0.3, s["moq"])
        q2 = _round_up(gap * 0.7, s["moq"])
        pool.append({"desc": f"Split order from {s['name']}: {q1:,} units by {fast} now, "
                             f"{q2:,} units by {slow}.",
                     "orders": [{"supplier": s["name"], "lane": fast, "qty": q1},
                                {"supplier": s["name"], "lane": slow, "qty": q2}]})
    rng.shuffle(pool)
    return pool


def make_scenario(seed: int, idx: int) -> Dict[str, Any]:
    """Scenario idx of a seed; retries internally until the gold plan is unambiguous."""
    rng = random.Random(f"scd-{seed}-{idx}")
    while True:
        sc = _base(rng, idx)
        pool = _candidates(rng, sc)
        for _ in range(40):
            plans = rng.sample(pool, 4)
            costs = [plan_cost(sc, p["orders"]) for p in plans]
            totals = sorted(c["total"] for c in costs)
            if totals[1] - totals[0] >= MARGIN * totals[1]:
                gold = min(range(4), key=lambda k: costs[k]["total"])
                sc.update(options=[p["desc"] for p in plans], plans=[p["orders"] for p in plans],
                          costs=costs, gold=LETTERS[gold])
                sc["dossier"] = render_dossier(rng, sc)
                sc["question"] = QUESTION
                return sc


# ----------------------------------------------------------------------------- text

QUESTION = (f"Which recovery plan gives the lowest total cost over the {HORIZON}-day planning "
            "horizon (purchase + freight + lost-sales penalty + holding), under the cost policy above?")


def _table(head: List[str], rows: List[List[Any]]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def render_dossier(rng: random.Random, sc: Dict[str, Any]) -> str:
    """Planner's dossier: everything needed to cost the plans, plus realistic context tables
    for sibling SKUs (not needed for the answer), so the shared prefix is ~3-4k tokens."""
    d = sc["demand"]
    demand_rows = [[f"Week {w + 1}"] + d[7 * w:7 * w + 7] + [sum(d[7 * w:7 * w + 7])] for w in range(8)]
    sup_rows = [[s["name"], s["region"], f"${s['unit_cost']:.2f}", s["lead"], f"{s['cap_week']:,}",
                 s["moq"], "/".join(REGIONS[s["region"]] if s["region"] == "domestic" else ["Ocean", "Air"])]
                for s in sc["suppliers"]]
    lane_rows = [[l["name"], l["transit"], f"${l['per_unit']:.2f}", f"${l['fixed']:,}"] for l in sc["lanes"]]
    po_rows = [[p["po"], p["supplier"], f"day {p['arrive']}", f"{p['qty']:,}"] for p in sc["open_pos"]]
    sib = [[f"{sc['sku'][:3]}-{rng.randint(1000, 9999)}"] + [rng.randint(300, 2200) for _ in range(8)]
           + [rng.randint(500, 9000), rng.choice(["A", "B", "C"])] for _ in range(24)]
    all_sups = [sc["primary"]] + [s["name"] for s in sc["suppliers"]]
    score = [[n] + [f"{rng.uniform(82, 99.5):.1f}%" for _ in range(4)]
             + [f"{rng.uniform(0.2, 3.5):.1f}%", rng.choice(["Approved", "Approved", "Under review"])]
             for n in all_sups]
    receipts = [[f"day -{rng.randint(1, 90)}", f"PO-{rng.randint(30000, 39999)}", rng.choice(all_sups),
                 f"{sc['sku'][:3]}-{rng.randint(1000, 9999)}", f"{rng.randint(2, 60) * 50:,}",
                 rng.choice(["on time", "on time", "on time", "2 days late", "5 days late", "short 3%"])]
                for _ in range(36)]
    receipts.sort(key=lambda r: int(r[0].split("-")[1]))
    return "\n\n".join([
        f"# Supply disruption dossier: {sc['sku']} ({sc['family']})",
        "Prepared by the S&OP team of Northwind Components (a fictional mid-size industrial "
        "distributor). All quantities are units; all costs are US dollars. Day 0 is today.",
        "## 1. Disruption notice\n"
        f"Our primary supplier for {sc['sku']}, {sc['primary']}, has declared force majeure after a "
        f"plant shutdown. It will ship nothing for the next {sc['outage_days']} days (days 0 to "
        f"{sc['outage_days'] - 1}). Purchase orders due to arrive during the outage will NOT arrive "
        "and are cancelled without charge. Orders due on or after the recovery day arrive as scheduled.",
        f"## 2. Inventory position\nOn hand today (start of day 0): {sc['on_hand']:,} units. "
        "Safety-stock target: 7 days of average demand (informational; not part of the cost).",
        "## 3. Open purchase orders with the primary supplier\n"
        + _table(["PO", "Supplier", "Arrival", "Quantity"], po_rows),
        f"## 4. Daily demand forecast, days 0-{HORIZON - 1}\n"
        + _table(["Week", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "Total"], demand_rows),
        "## 5. Approved alternate suppliers\n"
        + _table(["Supplier", "Region", "Unit cost", "Lead time (days)", "Capacity / week",
                  "MOQ", "Lanes"], sup_rows),
        "## 6. Freight lanes\n" + _table(["Lane", "Transit (days)", "Cost / unit", "Fixed / shipment"],
                                          lane_rows),
        "## 7. Cost policy and planning rules\n"
        f"- Unmet demand is lost (no backorders) and costs ${sc['penalty']:.2f} per unit short.\n"
        f"- Holding cost: ${sc['holding']:.4f} per unit per day, on end-of-day stock.\n"
        "- A supplier ships at most its weekly capacity per week. The first shipment leaves after "
        "the supplier's lead time; each further shipment leaves 7 days after the previous one.\n"
        "- Each shipment arrives after the lane's transit time, is available at the start of that "
        "day, and pays the lane's fixed fee plus its per-unit cost.\n"
        "- Everything ordered is paid for at the unit cost, even if it arrives after the horizon.\n"
        f"- Costs are counted over days 0-{HORIZON - 1} only.",
        "## 8. Context: sibling SKUs in the same family (weekly forecast, not affected)\n"
        + _table(["SKU", "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "On hand", "ABC"], sib),
        "## 9. Context: supplier scorecard, on-time delivery by quarter (not part of the cost)\n"
        + _table(["Supplier", "Q1", "Q2", "Q3", "Q4", "Defect rate", "Status"], score),
        "## 10. Context: receipts log, last 90 days, all SKUs in the family (not part of the cost)\n"
        + _table(["Received", "PO", "Supplier", "SKU", "Quantity", "Note"], receipts),
    ])


def to_problem(sc: Dict[str, Any]) -> Dict[str, Any]:
    """Harness view: the fields the prompts and scoring need (costs kept for analysis)."""
    keep = ("id", "dossier", "question", "options", "gold", "costs", "sku")
    return {k: sc[k] for k in keep}


def load_scenarios(n: int, seed: int = 0) -> List[Dict[str, Any]]:
    """n scenarios fixed by seed (the same call always returns the same scenarios)."""
    return [to_problem(make_scenario(seed, i)) for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None, help="Optional JSONL path; prints stats either way.")
    a = ap.parse_args()
    probs = load_scenarios(a.n, a.seed)
    if a.out:
        with open(a.out, "w") as f:
            for p in probs:
                f.write(json.dumps(p) + "\n")
    golds = {L: sum(p["gold"] == L for p in probs) for L in LETTERS}
    chars = sorted(len(p["dossier"]) for p in probs)
    print(f"{len(probs)} scenarios, seed {a.seed}; gold letters {golds}; "
          f"dossier chars median {chars[len(chars) // 2]} (~{chars[len(chars) // 2] // 4} tokens)")


if __name__ == "__main__":
    main()
