#!/usr/bin/env python3
"""Merge results/scores.json into results/evaluation.csv.

scores.json maps "model_promptid" -> {"transcribed": [...], "visual_quality": int,
"spatial_score": 0|0.5|1 (category E only), "error_type": str, "notes": str}.
exact_match is derived here from transcribed vs targets, never hand-typed.
Re-running is idempotent; rows not in scores.json are left untouched.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
scores = json.loads((ROOT / "results" / "scores.json").read_text())
path = ROOT / "results" / "evaluation.csv"
rows = list(csv.DictReader(path.open()))
for r in rows:
    key = f"{r['model']}_{r['prompt_id']}"
    if key not in scores:
        continue
    s = scores[key]
    targets = r["targets"].split(" | ")
    trans = s["transcribed"]
    assert len(trans) == len(targets), f"region count mismatch {key}"
    r["transcribed"] = " | ".join(trans)
    r["exact_match"] = "1" if trans == targets else "0"
    r["visual_quality"] = str(s["visual_quality"])
    if "spatial_score" in s:
        r["spatial_score"] = str(s["spatial_score"])
    r["error_type"] = s["error_type"]
    r["notes"] = s.get("notes", "")
with path.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
done = sum(1 for r in rows if r["transcribed"])
print(f"evaluation.csv: {done}/{len(rows)} rows transcribed")
