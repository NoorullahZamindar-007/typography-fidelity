# Evaluation protocol (fixed before scoring)

## Annotator
One annotator (the author) transcribed every image and scored spatial
placement and visual quality. OCR was used only as a cross-check where
available; the manual transcription is the ground truth for all reported
metrics. No image was rescored after seeing the summary statistics.

## Transcription rules
- Transcribe exactly what is legible in the image, region by region, in
  the order listed in `data/prompts.json`. Do not correct spelling.
- If a region is absent, illegible, or garbled beyond any plausible
  reading, transcribe it as an empty string and note `missing` or
  `garbled` in `error_type`. A missing region therefore has CER = 1.
- Case, digits and punctuation count. `HELLO` transcribed as `HELO`
  is not exact. Extra words outside the requested regions are recorded
  in `notes` but do not change the target-region CER, except where they
  make the target itself ambiguous (noted as `extra_text`).
- For multi-region prompts, each region is scored separately; the
  prompt CER is the mean of its region CERs.

## Error types (one per prompt, the dominant failure)
- `none`: all targets exact.
- `substitution`: a character is replaced by another (e.g. O for 0).
- `deletion`: a character is dropped.
- `insertion`: an extra character is added inside a target.
- `missing`: a whole region is absent or unreadable.
- `garbled`: letters are present but form no plausible reading.
- `extra_text`: requested text is present but additional text intrudes.
- `spatial`: text is present but in the wrong place (spatial prompts).
- `mixed`: two or more of the above in different regions.

## Spatial score (category E only)
- 1: every requested placement is correct.
- 0.5: at least one placement correct, another wrong or missing.
- 0: no requested placement correct, including missing text.
Placement is judged from the rendered image (left/right/top/bottom/
above/below and corners), not from the prompt wording.

## Visual quality (1-5, spelling-blind)
Score composition, coherence, artefacts and how well the text sits in
the scene. A misspelled word that is cleanly rendered does NOT lower
this score; a correctly spelled word on a broken, incoherent image
does not raise it. Anchors are in `config.json`.

## Second-pass check
After the first pass, 20 images (20%, stratified by model and
category, selected by a fixed list in `results/second_pass.txt`) were
re-transcribed from shuffled filenames with the original transcription
hidden. Disagreements are listed in `results/second_pass.csv` and the
final transcription is the one that matches the image on re-inspection.
This is a within-annotator reliability check, not a claim of two
independent human annotators.

## Statistics
See `src/evaluate.py`. Exact-match rates use Wilson 95% intervals.
Paired exact-match comparison uses McNemar's exact test. The paired
CER difference uses a 10,000-draw bootstrap (seed 20261026). With
n = 50 prompts per model, results are exploratory: confidence
intervals are reported and no causal claim about model architecture
is made from two Space deployments alone.
