#!/usr/bin/env python3
"""Create results/evaluation.csv template from manifest + prompts, and the
stratified 20-image second-pass list. Never overwrites existing scores:
re-running only appends missing rows. Transcription columns start empty
and must be filled by viewing each image."""
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prompts = {p["id"]: p for p in json.loads((ROOT / "data" / "prompts.json").read_text())["prompts"]}
manifest = list(csv.DictReader((ROOT / "results" / "manifest.csv").open()))
fields = ["model", "prompt_id", "category", "targets", "transcribed",
          "exact_match", "visual_quality", "spatial_score", "error_type", "notes"]
out = ROOT / "results" / "evaluation.csv"
existing = {}
if out.exists():
    existing = {(r["model"], r["prompt_id"]): r for r in csv.DictReader(out.open())}
rows = []
for m in manifest:
    key = (m["model"], m["prompt_id"])
    if key in existing:
        rows.append(existing[key])
        continue
    p = prompts[m["prompt_id"]]
    rows.append({"model": m["model"], "prompt_id": m["prompt_id"], "category": p["category"],
                 "targets": " | ".join(p["target"]), "transcribed": "",
                 "exact_match": "", "visual_quality": "",
                 "spatial_score": "" if p["category"] != "spatial_layout" else "",
                 "error_type": "", "notes": ""})
rows.sort(key=lambda r: (r["model"], r["prompt_id"]))
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(f"evaluation.csv: {len(rows)} rows")

# Second pass: only once the full 100-image manifest exists.
if len(manifest) < 100:
    print("second_pass.txt: skipped until manifest is complete (100 rows)")
else:
    rng = random.Random(20261026)
    sel = []
    for model in ("flux-schnell", "sd35-medium"):
        for cat in ("single_word", "short_phrase", "numbers_punctuation", "multiple_regions", "spatial_layout"):
            pool = sorted(r["prompt_id"] for r in rows if r["model"] == model and r["category"] == cat)
            sel.extend(f"{model}_{pid}" for pid in rng.sample(pool, 2))
    (ROOT / "results" / "second_pass.txt").write_text("\n".join(sorted(sel)) + "\n")
    print(f"second_pass.txt: {len(sel)} entries")
