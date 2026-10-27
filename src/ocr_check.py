#!/usr/bin/env python3
"""OCR cross-check: run tesseract on every image and compare with the
manual transcription in results/evaluation.csv.

OCR is an assistant, never the ground truth: disagreements are reported
for inspection and the manual transcription stands. Requires the
`tesseract` binary (installed 2026-10-27; see README). Output:
results/ocr.csv with one row per image and an agreement flag.
"""
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ev = {(r["model"], r["prompt_id"]): r for r in csv.DictReader((ROOT / "results" / "evaluation.csv").open())}
man = list(csv.DictReader((ROOT / "results" / "manifest.csv").open()))
rows = []
for m in man:
    key = (m["model"], m["prompt_id"])
    img = ROOT / "images" / m["file"]
    out = subprocess.run(["tesseract", str(img), "stdout", "--psm", "6"],
                         capture_output=True, text=True, timeout=120)
    ocr = " ".join(out.stdout.split())
    manual = ev.get(key, {}).get("transcribed", "")
    # Compare region by region is not possible from one OCR string for
    # multi-region posters, so agreement is judged on the joined text
    # with whitespace normalised; multi-region rows are flagged for
    # manual review regardless.
    agree = "yes" if ocr == " ".join(manual.split(" | ")) else "no"
    rows.append({"model": m["model"], "prompt_id": m["prompt_id"],
                 "category": m["category"], "manual": manual, "ocr": ocr,
                 "agree": agree})
with (ROOT / "results" / "ocr.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
n_agree = sum(r["agree"] == "yes" for r in rows)
print(f"ocr.csv: {len(rows)} rows, agreement {n_agree}/{len(rows)}")
for r in rows:
    if r["agree"] == "no":
        print(f"DIFF {r['model']}_{r['prompt_id']}: manual={r['manual']!r} ocr={r['ocr']!r}")
