# Visual Quality Versus Textual Accuracy

Exploratory study of how reliably two publicly accessible
text-to-image models reproduce exact words, numbers, punctuation and
spatial instructions, and how visual quality relates to textual accuracy.

## Models (no key, no account, public demo Spaces)
- **FLUX.1-schnell** — Hugging Face Space `black-forest-labs/FLUX.1-schnell`,
  768x768, 4 steps (Space default), seed 42 requested.
- **Stable Diffusion 3.5 Medium** — Hugging Face Space
  `stabilityai/stable-diffusion-3-5-medium`, 768x768, 40 steps,
  guidance 4.5 (Space defaults), seed 42 requested.

These are the Spaces' public demos, not local checkpoints. A fixed
seed is requested, but Space queue/GPU nondeterminism means exact
pixel reproducibility is not guaranteed; prompt, parameters and file
hashes are recorded in `results/manifest.csv` so the evaluated set is
exactly identified.

## Reproduce
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 src/generate.py flux-schnell   # 50 images
python3 src/generate.py sd35-medium   # 50 images
# Fill results/evaluation.csv from docs/evaluation-protocol.md
# (template: results/evaluation_template.csv)
python3 src/evaluate.py
python3 src/verify.py
python3 src/figures.py
```
Generation uses only the public Gradio API of the two Spaces above.
No API key is required and no cost was incurred. If a Space is down,
generation stops and the failure is recorded; do not substitute a
different model and keep the old label.

Known Space behaviour (26 Oct 2026): a minority of queue entries stall
indefinitely even while the same Space answers fresh requests in
seconds. `src/generate.py` therefore caps each queue wait (75 s for
FLUX.1-schnell, 300 s for SD3.5 Medium) and retries a stalled prompt with
a fresh event, up to 3 attempts; a successfully returned image is never
regenerated. Attempts are recorded in `results/manifest.csv`.

Model change (27 Oct 2026): the second model was originally Stable
Diffusion 3 Medium, but its official Space refused generation through
its web UI with a ZeroGPU quota error (60 s requested vs 50 s left;
page said try again in 10:27:36) and API calls to it hung instead of
returning a job. No SD3 image was ever generated. On 27 Oct the user
chose to drop SD3 entirely rather than wait for its quota, and
**Stable Diffusion 3.5 Medium** was selected as the replacement: a
different checkpoint, verified working through the same Gradio API
shape. The old SD3 label was not reused for the new model.

## Structure
- `data/prompts.json` — 50 original prompts, 10 per category, with
  exact target strings.
- `config.json` — models, sizes, seeds, scoring definitions.
- `src/generate.py` — generation + manifest with SHA-256 hashes.
- `src/evaluate.py` — recomputed CER, Wilson intervals, McNemar test,
  bootstrap CI for the paired CER difference.
- `src/verify.py` — file/hash/label/range checks.
- `src/figures.py` — figures from `results/` only, never hand-typed.
- `results/` — manifest, evaluation sheet, summaries, stats.
- `images/` — generated images (see licensing note below).
- `docs/evaluation-protocol.md` — scoring rubric fixed before scoring.

## Licensing and limits
Code in this repository is MIT-licensed. Generated images are outputs
of the two public demo models listed above; FLUX.1 and Stable
Diffusion 3 model licences and the Spaces' terms apply to the
underlying models, and this repository makes no claim of ownership
over model weights. Prompts are original to this study. Fictional
names, prices and phone-like strings are used; no real personal data
appears in the dataset. This is a small exploratory study (n = 50
prompts per model, one image each); it is not a benchmark and its
intervals are wide by design.
