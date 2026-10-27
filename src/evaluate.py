#!/usr/bin/env python3
"""Score the evaluation sheet and write summary tables.

Inputs: results/evaluation.csv (one row per prompt per model; transcribed
text is entered by the annotator, see docs/evaluation-protocol.md).
Outputs: results/summary_by_model.csv, results/summary_by_category.csv,
results/paired.csv and results/stats.json. CER is recomputed here from
transcribed vs target, never trusted from the sheet.
"""
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    rows = list(csv.DictReader((ROOT / "results" / "evaluation.csv").open()))
    assert rows, "evaluation.csv is empty"
    # Recompute per-region CER from the sheet's target/transcribed fields.
    # The sheet stores one row per prompt; targets and transcriptions are
    # separated by ' | ' in the same order as prompts.json.
    by_model = defaultdict(list)
    by_cat = defaultdict(list)
    paired = {}
    for r in rows:
        targets = r["targets"].split(" | ") if r["targets"] else []
        trans = r["transcribed"].split(" | ") if r["transcribed"] else []
        assert len(trans) == len(targets), f"region count mismatch {r}"
        cers = [lev(t, s) / len(t) if t else 0.0 for t, s in zip(targets, trans)]
        r["mean_cer"] = statistics.fmean(cers) if cers else 0.0
        r["exact"] = 1 if all(t == s for t, s in zip(targets, trans)) else 0
        r["n_regions_exact"] = sum(t == s for t, s in zip(targets, trans))
        r["n_regions"] = len(targets)
        by_model[r["model"]].append(r)
        by_cat[(r["model"], r["category"])].append(r)
        paired.setdefault(r["prompt_id"], {})[r["model"]] = r

    def summarise(group):
        n = len(group)
        exact = sum(r["exact"] for r in group)
        lo, hi = wilson(exact, n)
        cer = statistics.fmean(r["mean_cer"] for r in group)
        regions = sum(r["n_regions"] for r in group)
        reg_exact = sum(r["n_regions_exact"] for r in group)
        vis = [float(r["visual_quality"]) for r in group]
        spatial = [float(r["spatial_score"]) for r in group if r["spatial_score"] != ""]
        return {
            "n": n, "exact_n": exact, "exact_rate": exact / n,
            "exact_wilson_lo": lo, "exact_wilson_hi": hi,
            "mean_cer": cer, "cer_sd": statistics.pstdev([r["mean_cer"] for r in group]) if n > 1 else 0.0,
            "region_exact": reg_exact, "regions": regions,
            "region_exact_rate": reg_exact / regions if regions else 0.0,
            "mean_visual_quality": statistics.fmean(vis),
            "mean_spatial": statistics.fmean(spatial) if spatial else None,
            "n_spatial": len(spatial),
        }

    summary = {m: summarise(g) for m, g in by_model.items()}
    cat_rows = []
    for (m, c), g in sorted(by_cat.items()):
        s = summarise(g)
        cat_rows.append({"model": m, "category": c, **s})
    with (ROOT / "results" / "summary_by_category.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cat_rows[0].keys()))
        w.writeheader(); w.writerows(cat_rows)

    # Paired comparison on the 50 shared prompts.
    models = sorted(by_model)
    assert len(models) == 2
    a, b = models
    both = discord_a = discord_b = 0
    diffs = []
    for pid, d in paired.items():
        if a in d and b in d:
            ea, eb = d[a]["exact"], d[b]["exact"]
            both += ea and eb
            discord_a += ea and not eb
            discord_b += eb and not ea
            diffs.append(d[a]["mean_cer"] - d[b]["mean_cer"])
    # McNemar exact (binomial) two-sided p-value.
    n_disc = discord_a + discord_b
    if n_disc:
        from math import comb
        k = min(discord_a, discord_b)
        p_mc = sum(comb(n_disc, i) for i in range(k + 1)) * (0.5 ** n_disc) * 2
        p_mc = min(1.0, p_mc)
    else:
        p_mc = 1.0
    mean_diff = statistics.fmean(diffs) if diffs else 0.0
    # Bootstrap 95% CI for the mean paired CER difference (fixed seed).
    import random
    rng = random.Random(20261026)
    boots = []
    for _ in range(10000):
        boots.append(statistics.fmean(rng.choice(diffs) for _ in diffs))
    boots.sort()
    stats = {
        "models": models,
        "by_model": summary,
        "paired": {
            "n_prompts": len(diffs),
            "both_exact": both,
            "only_first_exact": discord_a,
            "only_second_exact": discord_b,
            "mcnemar_two_sided_p": p_mc,
            "mean_cer_difference_first_minus_second": mean_diff,
            "cer_difference_bootstrap_ci95": [boots[250], boots[9750]],
        },
    }
    (ROOT / "results" / "stats.json").write_text(json.dumps(stats, indent=2))
    with (ROOT / "results" / "paired.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["prompt_id", "category",
                                           f"{a}_exact", f"{b}_exact",
                                           f"{a}_cer", f"{b}_cer",
                                           f"{a}_visual", f"{b}_visual"])
        w.writeheader()
        for pid, d in sorted(paired.items()):
            w.writerow({"prompt_id": pid, "category": d[a]["category"],
                        f"{a}_exact": d[a]["exact"], f"{b}_exact": d[b]["exact"],
                        f"{a}_cer": round(d[a]["mean_cer"], 4), f"{b}_cer": round(d[b]["mean_cer"], 4),
                        f"{a}_visual": d[a]["visual_quality"], f"{b}_visual": d[b]["visual_quality"]})
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
