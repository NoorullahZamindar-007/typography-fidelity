#!/usr/bin/env python3
"""Prepare the blind second pass (see docs/evaluation-protocol.md).

Usage: python3 src/second_pass.py
Reads results/second_pass.txt (20 entries, written by
make_evaluation_sheet.py once the manifest is complete) and copies
those images to results/second_pass_blind/ under shuffled names
(blind_01.webp, ...). The mapping lives only in
results/second_pass_key.csv, which the annotator must not open until
the blind re-transcription is done. Re-transcriptions go in
results/second_pass.csv with columns: blind_id, transcribed,
spatial_score, notes. Agreement is then checked against the original
evaluation sheet by joining on the key.
"""
import csv
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
entries = [l.strip() for l in (ROOT / "results" / "second_pass.txt").read_text().splitlines() if l.strip()]
assert len(entries) == 20, f"expected 20 second-pass entries, got {len(entries)}"
rng = random.Random(20261027)
order = entries[:]
rng.shuffle(order)
blind = ROOT / "results" / "second_pass_blind"
blind.mkdir(exist_ok=True)
key = []
for i, entry in enumerate(order, 1):
    model, pid = entry.rsplit("_", 1)
    src = next((ROOT / "images").glob(f"{entry}.*"))
    dst = blind / f"blind_{i:02d}{src.suffix}"
    shutil.copyfile(src, dst)
    key.append({"blind_id": dst.stem, "original": entry, "model": model, "prompt_id": pid})
with (ROOT / "results" / "second_pass_key.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["blind_id", "original", "model", "prompt_id"])
    w.writeheader()
    w.writerows(key)
tpl = ROOT / "results" / "second_pass.csv"
if not tpl.exists():
    with tpl.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["blind_id", "transcribed", "spatial_score", "notes"])
        w.writeheader()
        for k in key:
            w.writerow({"blind_id": k["blind_id"], "transcribed": "", "spatial_score": "", "notes": ""})
print(f"blind copies: {len(key)} in {blind} (key kept separate; do not open until re-transcription is done)")
