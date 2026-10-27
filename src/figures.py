#!/usr/bin/env python3
"""Figures from results/summary_by_category.csv and results/paired.csv only."""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
CATS = ["single_word", "short_phrase", "numbers_punctuation", "multiple_regions", "spatial_layout"]
LABELS = {"single_word": "Single word", "short_phrase": "Short phrase",
          "numbers_punctuation": "Numbers /\npunct.", "multiple_regions": "Multiple\nregions",
          "spatial_layout": "Spatial /\nlayout"}
MODELS = ["flux-schnell", "sd35-medium"]
NAMES = {"flux-schnell": "FLUX.1-schnell", "sd35-medium": "SD3.5 Medium"}

rows = list(csv.DictReader((ROOT / "results" / "summary_by_category.csv").open()))
by = {(r["model"], r["category"]): r for r in rows}

plt.rcParams.update({"font.size": 10})
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, metric, title in [
        (axes[0], "exact_rate", "Exact-match rate by category"),
        (axes[1], "mean_cer", "Mean CER by category (lower is better)")]:
    x = range(len(CATS))
    for i, m in enumerate(MODELS):
        vals = [float(by[(m, c)][metric]) for c in CATS]
        ax.bar([v + (i - 0.5) * 0.38 for v in x], vals, width=0.38, label=NAMES[m])
    ax.set_xticks(list(x))
    ax.set_xticklabels([LABELS[c] for c in CATS])
    ax.set_title(title)
    ax.set_ylim(0, 1.05 if metric == "exact_rate" else max(1.0, max(float(by[(m, c)][metric]) for m in MODELS for c in CATS) * 1.15))
axes[0].legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig1_by_category.png", dpi=200)
plt.close(fig)

# Paired scatter: visual quality vs CER, one point per prompt per model.
paired = list(csv.DictReader((ROOT / "results" / "paired.csv").open()))
fig, ax = plt.subplots(figsize=(6, 4.5))
for m, marker in [("flux-schnell", "o"), ("sd35-medium", "s")]:
    xs = [float(r[f"{m}_cer"]) for r in paired]
    ys = [float(r[f"{m}_visual"]) for r in paired]
    ax.scatter(xs, ys, marker=marker, alpha=0.6, label=NAMES[m])
ax.set_xlabel("Mean CER for the prompt (lower = more accurate text)")
ax.set_ylabel("Visual quality (1-5, spelling-blind)")
ax.set_title("Visual quality vs textual accuracy (100 images)")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig2_quality_vs_cer.png", dpi=200)
print("figures written")
