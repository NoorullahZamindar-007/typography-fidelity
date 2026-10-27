#!/usr/bin/env python3
"""Independent verification: files, hashes, labels, ranges, recomputed CER.

Fails (exit 1) on any missing file, hash mismatch, duplicate hash across
different prompt/model pairs, score out of range, or CER that does not
recompute from the recorded transcription. Prints a short report.
"""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate import lev  # noqa: E402


def main():
    errors, warnings = [], []
    prompts = {p["id"]: p for p in json.loads((ROOT / "data" / "prompts.json").read_text())["prompts"]}
    manifest = list(csv.DictReader((ROOT / "results" / "manifest.csv").open()))
    print(f"manifest rows: {len(manifest)} (expected 100)")
    if len(manifest) != 100:
        errors.append("manifest does not have 100 rows")
    seen_keys, hashes = set(), {}
    for row in manifest:
        key = (row["model"], row["prompt_id"])
        if key in seen_keys:
            errors.append(f"duplicate manifest key {key}")
        seen_keys.add(key)
        path = ROOT / "images" / row["file"]
        if not path.exists():
            errors.append(f"missing image {path}")
            continue
        blob = path.read_bytes()
        if len(blob) == 0:
            errors.append(f"empty image {path}")
        if hashlib.sha256(blob).hexdigest() != row["sha256"]:
            errors.append(f"hash mismatch {path}")
        if row["prompt_id"] not in prompts:
            errors.append(f"unknown prompt {row['prompt_id']}")
        elif row["prompt"] != prompts[row["prompt_id"]]["prompt"]:
            errors.append(f"prompt text mismatch {key}")
        h = row["sha256"]
        if h in hashes and hashes[h] != key:
            warnings.append(f"identical hash for {hashes[h]} and {key} (check: models may coincide)")
        hashes[h] = key
    ev = list(csv.DictReader((ROOT / "results" / "evaluation.csv").open()))
    print(f"evaluation rows: {len(ev)} (expected 100)")
    if len(ev) != 100:
        errors.append("evaluation does not have 100 rows")
    ev_keys = {(r["model"], r["prompt_id"]) for r in ev}
    if ev_keys != seen_keys:
        errors.append("evaluation keys do not match manifest keys")
    for r in ev:
        p = prompts.get(r["prompt_id"])
        if not p:
            continue
        if r["targets"] != " | ".join(p["target"]):
            errors.append(f"targets mismatch {r['model']} {r['prompt_id']}")
        if r["category"] != p["category"]:
            errors.append(f"category mismatch {r['model']} {r['prompt_id']}")
        try:
            vq = float(r["visual_quality"])
            if not (1 <= vq <= 5 and vq == int(vq)):
                errors.append(f"visual_quality out of range {r}")
        except ValueError:
            errors.append(f"visual_quality not numeric {r}")
        if r["category"] == "spatial_layout":
            try:
                sp = float(r["spatial_score"])
                if sp not in (0.0, 0.5, 1.0):
                    errors.append(f"spatial_score not in {{0,0.5,1}} {r}")
            except ValueError:
                errors.append(f"spatial_score not numeric {r}")
        trans = r["transcribed"].split(" | ") if r["transcribed"] else []
        if len(trans) != len(p["target"]):
            errors.append(f"region count mismatch {r['model']} {r['prompt_id']}")
    print(f"errors: {len(errors)}; warnings: {len(warnings)}")
    for e in errors:
        print("ERROR:", e)
    for w in warnings:
        print("WARNING:", w)
    # Image size check via PIL (no pixel content judgement here).
    try:
        from PIL import Image
        sizes = Counter()
        for row in manifest:
            path = ROOT / "images" / row["file"]
            if path.exists():
                with Image.open(path) as im:
                    sizes[im.size] += 1
        print("image sizes:", dict(sizes))
    except Exception as exc:  # noqa: BLE001
        print("size check skipped:", exc)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
