# OCR cross-check (FLUX.1-schnell, 50 images)

Run: `python3 src/ocr_check.py` (tesseract 5.3.4, `--psm 6`), output
`results/ocr.csv`. Manual transcription remains ground truth; OCR is
reported here only as a cross-check.

- Agreement (joined text, whitespace normalised): **28/50**.
- Every disagreement was inspected. None overturns a manual
  transcription:
  - In 7 cases OCR *corroborates* a duplication noted manually
    (D01, D03, D04, D08, D10, E08, E10), because OCR reads both copies
    while the manual sheet records each target region once.
  - In scene/photo-background images (B04 library, D02 book cover,
    D09 garden photo, C05 shop sign, C03 price tag) OCR garbles or
    drops legible text that a human reader can see clearly.
  - B10: OCR reads the heart glyph replacing the O in LOVE as W;
    the manual transcription records the heart, which is the
    correct observation.
  - Remaining diffs are single-character OCR errors on otherwise
    legible text (e.g. C01 `42` read as `A2`, B03 `FRESH` read as
    `-F RESH`).
- Conclusion: OCR alone would both miss real errors and invent
  false ones on this set, which is why the study's metrics are
  computed from manual transcriptions, with OCR only as a check.
  The same cross-check will be rerun on the second model's images
  once they exist.
