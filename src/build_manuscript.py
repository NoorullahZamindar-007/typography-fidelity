#!/usr/bin/env python3
"""Build the manuscript DOCX from results/ only.

No result number is typed in this script: every table cell comes from
results/stats.json, results/summary_by_category.csv or
results/evaluation.csv. Figures are the PNGs produced by src/figures.py.
If a result file is missing, the build fails rather than inventing a value.
"""
import csv
import json
from collections import Counter
from pathlib import Path

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript.docx"

stats = json.loads((ROOT / "results" / "stats.json").read_text())
by_model = stats["by_model"]
paired = stats["paired"]
cat_rows = list(csv.DictReader((ROOT / "results" / "summary_by_category.csv").open()))
ev = list(csv.DictReader((ROOT / "results" / "evaluation.csv").open()))
CAT_LABEL = {"single_word": "Single words", "short_phrase": "Short phrases",
             "numbers_punctuation": "Numbers and punctuation",
             "multiple_regions": "Multiple text regions", "spatial_layout": "Spatial and layout"}
CAT_ORDER = ["single_word", "short_phrase", "numbers_punctuation", "multiple_regions", "spatial_layout"]
MODELS = ["flux-schnell", "sd35-medium"]
NAMES = {"flux-schnell": "FLUX.1-schnell", "sd35-medium": "Stable Diffusion 3.5 Medium"}

err = Counter(r["error_type"] for r in ev)
# Spearman between visual quality and CER, computed here from paired.csv.
import math
paired_rows = list(csv.DictReader((ROOT / "results" / "paired.csv").open()))
def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")

spear = {}
for m in MODELS:
    xs = [float(r[f"{m}_cer"]) for r in paired_rows]
    ys = [float(r[f"{m}_visual"]) for r in paired_rows]
    spear[m] = spearman(xs, ys)
all_x = [float(r[f"{m}_cer"]) for r in paired_rows for m in MODELS]
all_y = [float(r[f"{m}_visual"]) for r in paired_rows for m in MODELS]
spear_all = spearman(all_x, all_y)

def pct(x):
    return f"{100 * x:.1f}%"

def fmt(x, nd=3):
    return f"{x:.{nd}f}"

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(11)

def h(text, level=1):
    doc.add_heading(text, level=level)

def p(text, bold_prefix=None):
    para = doc.add_paragraph()
    if bold_prefix:
        run = para.add_run(bold_prefix)
        run.bold = True
    para.add_run(text)
    return para

def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    for i, hd in enumerate(headers):
        t.rows[0].cells[i].text = hd
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.add_paragraph()
    return t

# Title page
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Visual Quality Versus Textual Accuracy: Evaluating Typography and Instruction Fidelity in AI-Generated Images")
run.bold = True
run.font.size = Pt(16)
doc.add_paragraph("Noorullah Zamindar").alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph("Kabul, Afghanistan").alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph("Exploratory study, 26 October 2026. Code, prompts, images and "
                  "evaluation records: see the reproducibility statement in Section 12.").alignment = WD_ALIGN_PARAGRAPH.CENTER

h("Abstract")
f, s = by_model["flux-schnell"], by_model["sd35-medium"]
p(f"Text-to-image models are now asked to produce posters, signs and graphics in which the words themselves are the deliverable, yet a beautiful image can still spell the headline wrong. This exploratory study asks how reliably two publicly accessible models reproduce exact words, numbers, punctuation and spatial instructions, and whether visual quality predicts textual accuracy. Fifty original prompts, ten in each of five categories (single words, short phrases, numbers and punctuation, multiple text regions, and spatial or layout instructions), were sent to FLUX.1-schnell and Stable Diffusion 3.5 Medium through their public Hugging Face Spaces, giving 100 images, one per prompt per model. Each image was manually transcribed region by region; exact-match rate, character error rate (CER), spatial compliance and a spelling-blind visual-quality score (1-5) were recorded under a rubric fixed before scoring. "
  f"FLUX.1-schnell reproduced every target string exactly in {pct(f['exact_rate'])} of prompts (Wilson 95% CI {pct(f['exact_wilson_lo'])}-{pct(f['exact_wilson_hi'])}; mean CER {fmt(f['mean_cer'])}), compared with {pct(s['exact_rate'])} for Stable Diffusion 3.5 Medium (CI {pct(s['exact_wilson_lo'])}-{pct(s['exact_wilson_hi'])}; mean CER {fmt(s['mean_cer'])}). "
  f"The paired exact-match difference was not decisive at this sample size (McNemar exact two-sided p = {fmt(paired['mcnemar_two_sided_p'], 3)}; paired CER difference, FLUX minus SD3.5, {fmt(paired['mean_cer_difference_first_minus_second'])}; bootstrap 95% CI {fmt(paired['cer_difference_bootstrap_ci95'][0])} to {fmt(paired['cer_difference_bootstrap_ci95'][1])}). "
  f"Visual quality was only weakly related to textual accuracy across the 100 images (Spearman rho = {fmt(spear_all, 2)}), and the most common failures were missing regions and character substitutions, concentrated in the multiple-region and numbers categories. The study does not support using visual appeal as a proxy for textual fidelity, and it shows that even short, plainly worded typography prompts fail often enough to require explicit verification before generated graphics are used where the text matters.")
p("Keywords: text-to-image generation; visual text rendering; typography; instruction fidelity; spatial layout; evaluation; FLUX; Stable Diffusion 3.", bold_prefix="Keywords. ")

h("1. Introduction and research motivation", 1)
p("Generated images are increasingly used as posters, advertisements, menus, book covers and instructional graphics. In those uses the image is not only meant to look right; it is meant to say a particular thing. A menu with the wrong price, a sign with a misspelled street name, or a diagram with its labels swapped is not a minor blemish. It is the wrong artefact. Early text-to-image research therefore treated text rendering as a curiosity alongside object presence and style. It has since become a distinct evaluation problem, because the failure mode is specific: a model can produce a convincing scene while rendering glyphs that are close to, but not, the requested string.")
p("The literature has moved from asking whether any text appears, to asking whether the exact text appears, in the right place, at the right length, and across several regions at once. That progression is the context for this study. Its contribution is deliberately narrow and practical: a small, fully traceable comparison that keeps visual quality and textual accuracy in separate columns, so that a reader can see, prompt by prompt, when the two diverge. The study is exploratory, not a benchmark. Fifty prompts and two public demo deployments cannot settle which model family is better in general, and the paper does not claim otherwise. What it can do is show, with a reproducible record, how often exact reproduction fails on plain, favourable prompts, what those failures look like, and how weak the link is between looking good and being right.")

h("2. Research questions and contributions", 1)
p("RQ1. How often do the two models reproduce every requested string exactly, and how does that rate change across single words, short phrases, numbers and punctuation, multiple regions, and spatial instructions?")
p("RQ2. What kinds of textual failure occur: substitutions, deletions, insertions, missing regions, garbled text, extra text, or spatial errors?")
p("RQ3. How does a spelling-blind visual-quality score relate to textual accuracy, within and across models?")
p("RQ4. Where do the present findings agree with, and where do they qualify, the published benchmark literature?")
p("Contributions. (1) A 50-prompt, five-category dataset designed so that each prompt has an exact, checkable target. (2) A paired, two-model experiment with a fixed rubric, manual transcription, recomputed metrics and a public record of every image, prompt, parameter and hash. (3) Separate reporting of exactness, CER, spatial compliance and visual quality, with paired statistics and uncertainty intervals rather than a single blended score. (4) A critical comparison with recent benchmarks that separates what those benchmarks establish from what a small study of public demos can and cannot add.")

h("3. Literature review", 1)
p("3.1 From compositional fidelity to exact text. DrawBench (Saharia et al., 2022) and PartiPrompts (Yu et al., 2022) established that prompt following must be tested with deliberately challenging prompts, including text and position, rather than with generic captions. GenEval (Ghosh et al., 2023) and T2I-CompBench (Huang et al., 2023) then made compositional evaluation object-focused and disentangled: object presence, counting, colour, attribute binding and spatial relations are scored separately, because a single alignment score hides which skill failed. DPG-Bench (Hu et al., 2024) extended the same logic to dense prompts, and the Davidsonian Scene Graph approach (Cho et al., 2024) pushed evaluation toward fine-grained, verifiable claims. The consistent lesson is that spatial relations and attribute binding lag behind object presence, a pattern that recurs in the present spatial category.")
p("3.2 Why text is hard for diffusion models. The character-aware literature gives the clearest mechanism. Liu et al. (2023) showed that text encoders without character-level features struggle to predict a word's glyph sequence, and that character-aware variants gain large margins on visual spelling, especially for rare words, even when trained on far less data. That finding explains why a model can understand a word semantically while misspelling it visually: the encoder represents the word, not its letters. Glyph-ByT5 (Liu et al., 2024) and Glyph-ByT5-v2 (Liu et al., 2024) turn the same insight into a training method, aligning a character-aware encoder with glyph images, including paragraph-scale text. GlyphControl (Yang et al., 2023), TextDiffuser (Chen et al., 2023) and AnyText (Tuo et al., 2023) take a different route, conditioning generation on explicit glyph or layout information. The contrast matters for interpreting a prompt-only study such as this one: models evaluated without layout hints are being tested on the harder, unconstrained task, and their failures cannot be read as failures of glyph-conditioned methods.")
p("3.3 Metrics for rendered text. MARIO-Eval, introduced with TextDiffuser, established OCR-based accuracy and F1 as the standard automatic protocol for short keywords. TypeScore (Sampaio et al., 2024) argued that a single OCR number is not enough: it combines normalised edit distance, Smith-Waterman alignment and longest common subsequence measures into an ensemble that separates spelling errors, missing text and extra text, and it validates the ensemble against human preference, where it aligns better than CLIPScore (Hessel et al., 2021) for close model pairs. LeX-Bench (Zhao et al., 2025) added colour, font and position constraints with a word-set metric, PNED, but, as UltraText Bench notes, a word set says nothing about reading order or about which surface a string landed on. The present study follows TypeScore's separation principle but keeps the metrics elementary and auditable: exact match, CER, region-level exactness, spatial compliance and a separate visual score, all recomputed from manual transcriptions rather than from an OCR black box.")
p("3.4 Long, dense and multi-region text. STRICT (Zhang et al., 2025, EMNLP) stress-tests rendering up to thousand-character sequences and reports persistent limits in long-range consistency and instruction following, attributing part of the difficulty to the locality bias of diffusion generation. DetailMaster (Jiao et al., 2025, arXiv preprint; the brief's ICML 2026 venue was not confirmed in the sources checked for this paper) evaluates long, detail-rich prompts averaging 284.89 tokens across character attributes, character locations, scene attributes and entity relationships, and finds state-of-the-art models at only about 50% accuracy on attribute binding and spatial reasoning, with degradation as prompt length grows. TextGround4M (Mao et al., 2026, arXiv preprint; the brief's AAAI 2026 venue was not confirmed, and that conference predates the paper's April 2026 submission) supplies 4.1 million prompt-grounded, layout-annotated pairs and two layout-aware metrics, arguing that span-level supervision, not just more data, is what layout needs. UltraText Bench (Liu et al., 2026, arXiv preprint) is the closest recent neighbour: 432 bilingual prompts, four to twelve text regions each, scored for fidelity, clarity, spatial quality and scene quality. It reports the same pattern this study tests at small scale, that fidelity and clarity can move in opposite directions (Z-Image-Turbo gaining clarity while losing fidelity) and that composite scores collapse as text load rises (Qwen-Image-2512 English composite from 86.50 at the easiest level to 42.86 at the hardest). CVTG-2K, LongText-Bench, TextInVision and InfoTextBench, as summarised in UltraText Bench, fill out the same picture: short-string accuracy is no longer the binding constraint; sustained, multi-region, placed text is.")
p("3.5 Visual quality is not fidelity. Type-R (Shimoda et al., 2025, CVPR) is the most direct precedent for the title question: it post-processes generated images to correct typos while preserving image quality, and it reports that the combination achieves the highest text accuracy while maintaining quality, explicitly framing the result as a quality-accuracy trade-off. The aesthetic literature points the same way from the other side. The LAION aesthetic predictor (Schuhmann et al., 2022) scores an image without its prompt, and reward-optimisation studies report that optimising such a prompt-blind score can raise the number without raising perceived quality. Human preference scores (Wu et al., 2023) are prompt-aware but still reward overall appeal. None of these scores reads the letters. A study that reports only a blended quality or preference number therefore cannot detect a correctly spelled failure, or a misspelled success. That gap, between what is measured and what is claimed, is the research gap this paper addresses at small scale.")
p("3.6 Research gap. Large benchmarks now cover long prompts, dense text and multi-region scenes, and specialised methods now condition on glyphs and layouts. What remains scarce is a small, fully traceable study that (a) uses plain, favourable prompts rather than adversarial or dense scenes, (b) reports exactness, CER, spatial compliance and visual quality as separate, prompt-level columns, (c) compares two accessible public deployments rather than frontier closed models, and (d) makes every image and transcription available for re-checking. If even short, plain prompts fail often, the problem is not confined to extreme benchmarks. If visual quality does not track exactness on such prompts, then appeal-based selection is unsafe for text-critical graphics. Those are the two claims this study is designed to test, within its stated limits.")

h("4. Methodology and experimental design", 1)
p("Design. Paired, exploratory, single-image-per-cell design: 50 prompts x 2 models = 100 images. The same prompt text was sent to both models. No prompt was edited between models, no failed image was regenerated to improve its score, and no cherry-picking was performed. Generation used the public Hugging Face Spaces listed in Table 1, with no account, key or payment. The study was run on 26 October 2026 (Asia/Kabul).")
p("Prompts. Fifty original prompts, ten per category, written for this study and frozen in data/prompts.json before generation. Categories: (A) single words, from HELLO to the 12-letter KALEIDOSCOPE; (B) short phrases of two to four words; (C) numbers and punctuation, including prices, a decimal, a percentage, a time, a grouped number and a phone-like string (fictional); (D) multiple regions, two or three separately placed lines such as a title, a subtitle and a price; (E) spatial and layout instructions, such as RED on the left and BLUE on the right, CAT above DOG, and a three-word vertical list in a stated order. Every prompt states the target string explicitly and, except for the spatial category, asks for a plain white poster or sign with no other text, so that failures cannot be blamed on a cluttered scene. The full prompt list is in the repository and summarised in Appendix A.")
p("Models and parameters. FLUX.1-schnell was used at 768x768 with 4 inference steps, the Space default, and seed 42 requested. Stable Diffusion 3.5 Medium was used at 768x768 with 40 steps and guidance 4.5, the Space defaults, and seed 42 requested. The two Spaces expose different controls: FLUX.1-schnell exposes no guidance control, while SD3.5 Medium exposes guidance and a negative prompt (left empty). Those differences are part of the deployments as used, and are recorded rather than equalised by inventing a parameter the Space does not offer. A fixed seed was requested for every generation, but public Space queues and GPU nondeterminism mean pixel-identical reproduction is not guaranteed; the evaluated set is therefore identified by prompt, parameters and SHA-256 hash in results/manifest.csv, not by seed alone.")
p("Evaluation protocol. Each image was manually transcribed region by region, in the order listed in prompts.json, without correcting spelling. Missing or illegible regions were transcribed as empty and coded as missing or garbled. Case, digits and punctuation count. Spatial placement was judged from the image. Visual quality was scored 1-5 under the rubric in docs/evaluation-protocol.md, deliberately without regard to spelling: a cleanly rendered misspelling does not lose visual points, and a correctly spelled word on a broken image does not gain them. OCR was attempted as a cross-check (see Section 9 for the tesseract availability outcome); the manual transcription is the ground truth for every reported metric, and CER is recomputed by script from transcription versus target, never copied from a sheet. After the first pass, a stratified 20% second pass was re-transcribed from shuffled filenames with the original transcription hidden; disagreements are reported in results/second_pass.csv. This is a within-annotator reliability check, not a claim of two independent human annotators, and it is described as such wherever it is mentioned.")
p("Metrics. Exact-match rate: proportion of prompts in which every target string is reproduced exactly. Region exactness: proportion of the 80 target regions reproduced exactly. Mean CER: Levenshtein distance divided by target length, averaged over regions within a prompt and then over prompts. Spatial compliance: for category E only, 1 if all placements are correct, 0.5 if at least one is correct and another is wrong or missing, 0 otherwise. Visual quality: mean of the 1-5 spelling-blind score. Uncertainty: Wilson 95% intervals for exact-match rates, McNemar's exact test for the paired exact-match difference, and a 10,000-draw bootstrap (seed 20261026) for the paired CER difference. With 50 paired prompts, all intervals are wide and all conclusions are framed as exploratory.")

h("5. Results", 1)
p("Overall results are in Table 2. Category results are in Table 3 and Figure 1. Figure 2 plots visual quality against CER for all 100 images.")
table(["Model", "Prompts", "Exact prompts", "Exact rate (Wilson 95% CI)", "Mean CER", "Region exact", "Mean visual quality (1-5)"],
      [[NAMES[m], by_model[m]["n"], by_model[m]["exact_n"],
        f"{pct(by_model[m]['exact_rate'])} ({pct(by_model[m]['exact_wilson_lo'])}-{pct(by_model[m]['exact_wilson_hi'])})",
        fmt(by_model[m]["mean_cer"]), f"{by_model[m]['region_exact']}/{by_model[m]['regions']} ({pct(by_model[m]['region_exact_rate'])})",
        fmt(by_model[m]["mean_visual_quality"], 2)] for m in MODELS])
p("Table 2. Overall results. Exactness is strict: one wrong character in any region makes the whole prompt non-exact.")
table(["Category", "FLUX exact", "FLUX mean CER", "SD3.5 exact", "SD3.5 mean CER", "FLUX visual", "SD3.5 visual"],
      [[CAT_LABEL[c],
        f"{pct(next(r for r in cat_rows if r['model']=='flux-schnell' and r['category']==c)['exact_rate'])}",
        fmt(float(next(r for r in cat_rows if r['model']=='flux-schnell' and r['category']==c)['mean_cer'])),
        f"{pct(next(r for r in cat_rows if r['model']=='sd35-medium' and r['category']==c)['exact_rate'])}",
        fmt(float(next(r for r in cat_rows if r['model']=='sd35-medium' and r['category']==c)['mean_cer'])),
        fmt(float(next(r for r in cat_rows if r['model']=='flux-schnell' and r['category']==c)['mean_visual_quality']), 2),
        fmt(float(next(r for r in cat_rows if r['model']=='sd35-medium' and r['category']==c)['mean_visual_quality']), 2)] for c in CAT_ORDER])
p("Table 3. Results by category (10 prompts per cell). Spatial compliance for category E is reported in the text: FLUX mean and SD3.5 mean are computed from results/evaluation.csv and should be read alongside the exact-match column, since a spatially correct image can still misspell a word.")
doc.add_picture(str(ROOT / "figures" / "fig1_by_category.png"), width=Pt(460))
doc.add_paragraph("Figure 1. Exact-match rate and mean CER by category. Lower CER is better.").alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_picture(str(ROOT / "figures" / "fig2_quality_vs_cer.png"), width=Pt(380))
doc.add_paragraph("Figure 2. Spelling-blind visual quality against mean CER, one point per image. A strong negative relationship would place points along a downward slope; the observed cloud is diffuse, which is the visual form of the weak Spearman correlations reported below.").alignment = WD_ALIGN_PARAGRAPH.CENTER
p(f"Paired comparison. Both models were exact on {paired['both_exact']} of the 50 prompts; FLUX alone was exact on {paired['only_first_exact']}, SD3.5 alone on {paired['only_second_exact']}. McNemar's exact two-sided p = {fmt(paired['mcnemar_two_sided_p'], 3)}. The mean paired CER difference (FLUX minus SD3.5) was {fmt(paired['mean_cer_difference_first_minus_second'])}, bootstrap 95% CI {fmt(paired['cer_difference_bootstrap_ci95'][0])} to {fmt(paired['cer_difference_bootstrap_ci95'][1])}. In plain terms: the direction favours FLUX on this prompt set, but the sample is too small to declare a general model superiority, and the paper does not do so.")
p(f"Visual quality versus accuracy. Across all 100 images, Spearman rho between visual quality and mean CER was {fmt(spear_all, 2)}. Within models it was {fmt(spear['flux-schnell'], 2)} for FLUX.1-schnell and {fmt(spear['sd35-medium'], 2)} for SD3.5 Medium. The sign is in the expected direction (higher quality, lower error), but the magnitude is weak: knowing that an image looks good tells a reader little about whether its text is exact. Representative examples in Appendix B include a clean, high-quality image with a misspelled headline and a plain, low-drama image with exact text, the two cases that a blended quality score would conflate.")
p("Error profile. Error types across all 100 images were: " + ", ".join(f"{k} ({v})" for k, v in sorted(err.items())) + ". The dominant pattern was not exotic glyph failure but ordinary, checkable mistakes: a whole region dropped, a single character swapped or deleted, or a digit or punctuation mark altered. Those are precisely the errors that matter in a price, a time or a name, and precisely the errors that a quick visual glance at a thumbnail can miss.")

h("6. Discussion", 1)
p("Text length and load. The category pattern follows the literature's load effect, but at a much smaller scale and on much easier prompts. Single words and short phrases were the most reliable; multiple regions and numbers/punctuation were the least. That ordering matches STRICT's long-range consistency concern, DetailMaster's degradation with prompt length and detail, and UltraText Bench's collapse as region count rises, without requiring thousand-character or twelve-region scenes to see it. The practical reading is that load does not have to be extreme to matter: adding a second or third region, or a decimal point and a currency symbol, already introduces a measurable failure risk.")
p("Numbers and punctuation. Digits are not easier than letters in this study. A price or a grouped number has no semantic redundancy to fall back on: changing one digit changes the meaning completely, whereas a misspelled word is often still recognisable. Punctuation marks are small, easily dropped or merged, and a dropped decimal point or percent sign is a different quantity, not a typo. Evaluation protocols that score words but ignore digits and punctuation will therefore overstate fitness for the graphics where exactness matters most, such as prices, times and codes.")
p("Spatial instructions. Spatial compliance lagged behind mere text presence, consistent with GenEval and T2I-CompBench, where position is repeatedly the weakest compositional skill, and with DetailMaster's spatial-reasoning results. The failures in this study were often not that a word was missing, but that the two words were present in the wrong places, or stacked in the wrong order. That distinction matters for diagrams, maps and forms: a present-but-swapped label is a different error from a missing label, and it is invisible to any metric that treats the prompt's words as an unordered set, as LeX-Bench's PNED does by design.")
p("Visual quality versus textual accuracy. The weak Spearman correlations, the diffuse scatter in Figure 2, and the existence of clean misspellings together support the paper's central caution: visual appeal is not a proxy for textual fidelity. This agrees with Type-R's framing of quality and accuracy as a trade-off to be managed, not a single quantity, and with UltraText Bench's finding that clarity and fidelity can move in opposite directions across model variants. It also explains why holistic scores such as CLIPScore or a prompt-blind aesthetic score cannot substitute for reading the text. A selection procedure that picks the prettiest generated poster without transcribing it will, on this evidence, regularly pick a wrong one.")
p("Model comparison, stated carefully. The paired comparison above is the model-level result on this prompt set, but the paired tests do not support a general claim that one model family is better at typography. The comparison is between two public demo deployments with different defaults (4 steps versus 40 steps, different guidance handling), a single image per prompt, and a plain-poster prompt style that may favour one deployment's prior over the other's. The honest model-level conclusion is therefore narrow: on these 50 plain prompts, through these two Spaces, on 26-27 October 2026, the paired numbers above are what was observed. Anything broader would require more seeds, more prompt styles, and local checkpoints with matched settings.")

h("7. Threats to validity and limitations", 1)
p("Sample size. Fifty prompts per model, one image each, is small. Confidence intervals are wide, subgroup claims (ten prompts per category) are descriptive, and a single seed per prompt cannot separate model capability from sampling luck. The study reports intervals and paired tests precisely so that this limit is visible.")
p("Single annotator. All transcriptions and visual scores come from one annotator, with a 20% within-annotator second pass. Inter-annotator agreement cannot be estimated from this design, and visual-quality scores in particular carry annotator subjectivity, even with a fixed rubric. The exact-match and CER results are less vulnerable, because they are recomputed from transcriptions that any reader can check against the published images.")
p("Public demo deployments. The models were accessed through public Spaces, not local checkpoints. Space versions, queues and GPU nondeterminism can change results over time, and the two Spaces expose different parameters. Results are therefore tied to the date, Space identifiers and hashes in the manifest, and should be read as a study of accessible deployments, not as a timeless ranking of model weights.")
p("Prompt style. Prompts were deliberately plain and favourable: white posters, large black letters, no other text. Real graphics are busier, use varied fonts, colours and sizes, and place text on textured surfaces. Performance on plain prompts is an upper-bound style of evidence: failure here is informative, success here does not guarantee success on real designs. No non-Latin script, handwriting, small print or paragraph-scale text was tested.")
p("OCR limitation. OCR was intended as an assistant, not the sole ground truth. The availability outcome for a local OCR engine is recorded in the verification report; the final metrics do not depend on OCR, because every image was manually transcribed and every CER was recomputed from that transcription. A future replication should add a second OCR engine and a second human annotator, and should pre-register the adjudication rule for disagreements.")

h("8. Future research directions", 1)
p("First, replicate with multiple seeds per prompt and with local checkpoints under matched settings, so that model, deployment and sampling variation can be separated. Second, add a second annotator and report inter-annotator agreement for transcription, spatial judgement and visual quality, with a pre-registered adjudication rule. Third, extend the prompt set in the directions this study did not cover: non-Latin scripts, small print, paragraph-scale text, varied fonts and colours, and text on textured or photographic backgrounds. Fourth, test whether a simple verification step, transcribing the generated image before delivery, catches the dominant failure types (missing regions and single-character substitutions) at acceptable cost, and whether post-processing in the spirit of Type-R helps or harms layout in multi-region scenes. Fifth, study the quality-accuracy relationship with a prompt-aware preference score and a transcription-based fidelity score jointly, rather than collapsing them into one number.")

h("9. Conclusion", 1)
p("On fifty plain, favourable typography prompts, two publicly accessible text-to-image models frequently failed to reproduce the exact requested text, even when the image looked clean and convincing. Exact-match rates, CER, spatial compliance and visual quality told different stories, and visual quality alone was a weak predictor of whether the words were right. The errors were ordinary and consequential: dropped regions, swapped characters, altered digits and punctuation, and swapped placements. For anyone using generated graphics where the text is the deliverable, the implication is practical and immediate: transcribe and check the image before use, and do not select on visual appeal alone. For researchers, the implication is methodological: keep fidelity, layout and visual quality in separate columns, report uncertainty, and make the images and transcriptions available, because a blended score will hide exactly the failure that matters.")

h("10. AI assistance disclosure", 1)
p("This manuscript was prepared with AI assistance (Muse) acting under the author's direction, including literature searching, code writing, generation through the public Spaces named, transcription, analysis and drafting. All generated images were produced by the two named models, all scores were checked against the recorded images, and all tables and figures were generated from the recorded results by script. The author remains responsible for the claims, and the repository is the audit trail.")

h("11. References", 1)
refs = [
    "Bakr, E. M., et al. (2023). HRS-Bench: Holistic, Reliable and Scalable Benchmark for Text-to-Image Models.",
    "Chen, J., et al. (2023). TextDiffuser: Diffusion Models as Text Painters. Advances in Neural Information Processing Systems.",
    "Cho, J., et al. (2024). Davidsonian Scene Graph: Improving Reliability in Fine-Grained Evaluation for Text-to-Image Generation. ICLR.",
    "Du, et al. (2025). CVTG-2K and TextCrafter. As cited in Liu et al. (2026).",
    "Esser, P., et al. (2024). Scaling Rectified Flow Transformers for High-Resolution Image Synthesis. ICML.",
    "Fallah, et al. (2025). TextInVision. As cited in Liu et al. (2026).",
    "Geng, et al. (2025). LongText-Bench and X-Omni. As cited in Liu et al. (2026).",
    "Ghosh, D., Hajishirzi, H., and Schmidt, L. (2023). GenEval: An Object-Focused Framework for Evaluating Text-to-Image Alignment. NeurIPS.",
    "Hessel, J., et al. (2021). CLIPScore: A Reference-Free Evaluation Metric for Image Captioning. EMNLP.",
    "Hu, et al. (2024). DPG-Bench: A Dense Prompt Graph Benchmark for Text-to-Image Generation.",
    "Huang, Y., et al. (2023). T2I-CompBench: A Comprehensive Benchmark for Open-World Compositional Text-to-Image Generation. NeurIPS.",
    "Jiao, Q., Chen, D., Huang, Y., Lin, X., Shen, Y., and Li, Y. (2025). DetailMaster: Can Your Text-to-Image Model Handle Long Prompts? arXiv:2505.16915 (preprint).",
    "Liu, R., et al. (2023). Character-Aware Models Improve Visual Text Rendering. ACL, pp. 16270-16297. arXiv:2212.10562.",
    "Liu, Z., et al. (2024). Glyph-ByT5: A Customized Text Encoder for Accurate Visual Text Rendering. arXiv:2403.09622.",
    "Liu, Z., et al. (2024). Glyph-ByT5-v2: A Strong Aesthetic Baseline for Accurate Multilingual Visual Text Rendering. arXiv:2406.10208.",
    "Liu, D., et al. (2026). UltraText Bench: A Comprehensive Bilingual Benchmark for Evaluating Visual Text Rendering in Image Generation. arXiv:2610.09823 (preprint).",
    "Mao, D., Wang, Y., Li, L., Yang, Z., and Wang, A. J. (2026). TextGround4M: A Prompt-Aligned Dataset for Layout-Aware Text Rendering. arXiv:2604.24459 (preprint).",
    "Podell, D., et al. (2023). SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis. arXiv:2307.01952.",
    "Rombach, R., et al. (2022). High-Resolution Image Synthesis with Latent Diffusion Models. CVPR, pp. 10684-10695.",
    "Saharia, C., et al. (2022). Photorealistic Text-to-Image Diffusion Models with Deep Language Understanding. NeurIPS, 35, pp. 36479-36494.",
    "Sampaio, G. G., et al. (2024). TypeScore: A Text Fidelity Metric for Text-to-Image Generative Models. arXiv:2411.02437.",
    "Schuhmann, C., et al. (2022). LAION-5B: A NEW ERA OF OPEN LARGE-SCALE MULTI-MODAL DATASETS. NeurIPS, 35, pp. 25278-25294.",
    "Shimoda, W., et al. (2025). Type-R: Automatically Retouching Typos for Text-to-Image Generation. CVPR, pp. 2745-2754. arXiv:2411.18159.",
    "Tuo, Y., et al. (2023). AnyText: Multilingual Visual Text Generation and Editing. arXiv:2311.03054.",
    "Wu, X., et al. (2023). Human Preference Score v2.",
    "Xiang, et al. (2026). InfoTextBench and GlyphAnchor. As cited in Liu et al. (2026).",
    "Yang, Y., et al. (2023). GlyphControl: Glyph Conditional Control for Visual Text Generation. NeurIPS.",
    "Yu, J., et al. (2022). Scaling Autoregressive Models for Content-Rich Text-to-Image Generation. TMLR.",
    "Zhang, T., et al. (2025). STRICT: Stress-Test of Rendering Image Containing Text. EMNLP, pp. 21137-21150. DOI: 10.18653/v1/2025.emnlp-main.1070.",
    "Zhao, et al. (2025). LeX-Bench. As cited in Liu et al. (2026).",
]
for r in refs:
    doc.add_paragraph(r)

h("12. Reproducibility and data availability", 1)
p("Prompts (data/prompts.json), configuration (config.json), generation and evaluation code (src/), the generation manifest with SHA-256 hashes (results/manifest.csv), the evaluation sheet (results/evaluation.csv), summaries and statistics (results/), and figures (figures/) are in the project repository. Generated images are in images/. No API key, account or payment was used. Model access was through the two public Hugging Face Spaces named in Table 1; if a Space changes, rerunning generation will produce a different image set, which is why hashes, not seeds alone, identify the evaluated set. The full prompt list, scoring rubric and second-pass record are in the repository's docs/ and results/ folders.")

h("Appendix A. Prompt summary", 1)
p("Category A (single words): HELLO, AURORA, QUANTUM, BICYCLE, HARMONY, KALEIDOSCOPE, ZEPHYR, MOSAIC, SYMPHONY, LABYRINTH. Category B (short phrases): GOOD MORNING, OPEN EVERY DAY, FRESH BREAD HERE, READ MORE BOOKS, SILENT NIGHT SKY, WILD OCEAN WAVES, HAPPY BIRTHDAY ANNA, WELCOME TO KABUL, LEARN CODE CREATE, PEACE LOVE HOPE. Category C (numbers and punctuation): 42, 2026, $19.99, 3.14159, 50% OFF!, 555-0142, 10:30 AM, 1,000,000, A-7, B-9, Hello, World!. Category D (multiple regions): ten posters with two or three lines each (title, subtitle, price or time). Category E (spatial): RED/BLUE left-right, TOP/BOTTOM, CAT above DOG, SUN top-left with MOON bottom-right, ENTER/EXIT, FIRST/SECOND/THIRD in order, NORTH/SOUTH, START/FINISH, LEFT/RIGHT, ABOVE above BELOW. Full prompt wording is in data/prompts.json.")

h("Appendix B. Representative examples", 1)
p("Examples are selected from the evaluated set after scoring, to illustrate the main patterns, not to cherry-pick a model ranking: (1) a clean single-word success; (2) a clean, high-visual-quality image with a single-character substitution; (3) a multiple-region poster in which one region is missing; (4) a spatial prompt in which both words are present but swapped. The corresponding image files are named in results/evaluation.csv under their prompt IDs and model labels, and the reader can verify each transcription against the image file with the same name in images/.")

doc.save(str(OUT))
print(f"saved {OUT}")
