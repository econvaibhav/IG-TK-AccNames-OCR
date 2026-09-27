# IG-TK-AccNames-OCR

== **Extract Account Names from IG/TK Reels + FULLY Human Review possible for 100% ACCURACY!** ==

The package works with video files already on your computer. It finds the account
area, reads sampled frames in both directions, and keeps repeated candidates
alongside the original text (To ensure higher accuracy for account name detection). **You can make the final decision in a local review page, if needed (full integraton)**.

No Instagram login or OCR API key is required.

**European language options:** Bulgarian, Croatian, French, Hungarian, Finnish,
Swedish, German, Polish, Spanish and Portuguese, plus English. Use
`--engine paddle --lang europe` for the broader **32-language/script preset**.

![Account review page with frame evidence, account names, review checkboxes and Excel export](visuals/Review_Preview.png)

*Example from a Finnish news-media Instagram video (Iltalehti).*

[How it works](#how-the-account-crop-works) · [Review and Excel](#review-and-excel) ·
[Installation](#installation) · [Process a folder](#process-a-folder) ·
[Languages](#languages-and-ocr-models) · [Troubleshooting](#troubleshooting)

## What it does

- Processes one clip or a folder, with optional subfolder discovery.
- Offers EasyOCR and PaddleOCR, with explicit languages or a European preset
  covering Latin, Cyrillic and Greek model routes.
- Compares forward and backward readings and counts support (same OCR reading) across frames.
- Saves six review moments: **1 second, 3 seconds, 1 second before the end,
  25%, 50% and 75%** of the clip.
- Shows both the account crop and the full frame, with an enlarged view on click.
- Lets you confirm a correct reading without changing it, edit a name, or mark it
  unreadable using checkboxes.
- Updates one Excel workbook for the entire run, while retaining original OCR
  results and saved correction history.

## How the account crop works

Every frame is resized to a **540 × 960** working image. Crop coordinates below
refer to that resized image, not the original video resolution.

### 1. Find the profile-circle area

For Reels, the first region of interest (ROI) is a narrow strip on the lower
left: `(x=10, y=560, width=69, height=250)`. The code searches for circular
profile images inside it and selects the lowest detected circle.

![First ROI: the lower-left profile-circle search area in the sample frame](visuals/ROI_01_profile_search.png)

### 2. Crop the adjoining account text

The second ROI starts beside the selected circle and measures **380 × 40**
working pixels. Bounds checks keep it inside the image. In the sample's
3-second frame, this produces `(x=75, y=751, width=380, height=40)`.

![Second ROI: the selected profile circle and adjoining account-text crop](visuals/ROI_02_account_crop.png)

### 3. Read the crop and retain the evidence

![Enlarged final account crop showing iltalehti and the Follow control](visuals/ROI_03_account_text.png)

OCR reads this crop. Candidate filtering removes common interface text such as
`Follow` and `Following`, while preserving uncertain readings for review. If no
profile circle is found, that sampled frame supplies no OCR crop; the review
still keeps the full frame where it can be decoded.

TikTok uses a fixed lower-left crop, initially
`(x=0, y=650, width=270, height=230)`. **The TikTok layout is experimental**, so
TikTok results are flagged for review. It does not use the Reels circle detector; however, upon looking at manual review for HEPP Data, TikTok also performs very well! 

## Sampling, votes and frame evidence

![Black-and-white LaTeX workflow from clips and crop selection through OCR, review and Excel](visuals/OCR_Workflow.png)

For each clip, the pipeline:

1. Samples frames from the beginning and reads the account crop.
2. Counts each candidate once per frame and stops when the leading candidate
   reaches the vote threshold, or the sample limit/end is reached.
3. Repeats from the end of the clip toward the beginning.
4. Compares the leading candidates from both directions.
5. Saves independent review frames at the six requested time points.

`agreement` means the retained readings match across the two passes. 

`similar` means their text is similar enough for pairing

`disagreement` leaves unmatched candidates. 

`one_sided` and `no_text` indicate a reading in only one direction or
neither. 

The 25%, 50% and 75% frames are **time quartiles**. Frame timing
uses the video FPS and frame count, so it assumes constant-frame-rate timing.

## Review and Excel

**IG/TK Review** is the local browser interface. Each clip has its own evidence
and saved decision, while the whole run shares one Excel workbook.

1. Compare the candidate names with the account crops and full frames. Click a
   full-frame thumbnail to enlarge it.
2. Keep the name if it is correct, or edit it. Enter **one account per line**.
   Spaces and commas within a display name are preserved.
3. Leave **Mark as reviewed** checked and click **Save changes**. An unchanged
   reading is recorded as **Confirmed**; an edited reading becomes **Corrected**.
4. If the evidence is insufficient, select **Cannot read** and save. Add a note
   when it helps explain the issue.
5. Use **Download Excel** for the latest saved workbook. It is also written
   directly to the run folder as `reviewed.xlsx`.


| Review status | Meaning | `final_names` | `needs_manual_review` |
| --- | --- | --- | --- |
| `unreviewed` | No completed review, or a saved draft | Original OCR candidates | `True` |
| `confirmed` | You accepted the original reading | Accepted names | `False` |
| `corrected` | You changed the reading and accepted it | Corrected names | `False` |
| `unreadable` | The account cannot be read reliably | Empty list | `True` |

**Use `final_names` together with `review_status` for analysis.** Names are stored
as a JSON list in the Excel cell, for example `["iltalehti"]`, so a
clip can retain more than one account. Draft edits are saved in the review state
but do not replace the original candidates in `final_names` until accepted.

### See the review steps

**Before review.** The original PaddleOCR reading is `iltalehti`. The two
passes agree; inspect the frame evidence to confirm the visible account name.

![Iltalehti sample before review, with the original iltalehti reading](visuals/Review_Before.png)

**Six moments from the same clip.** Existing fixed times and the three time
quartiles provide crops and full-frame context together.

![Six actual review moments from the included sample clip](visuals/Review_Frames.png)

**Inspect the full frame.** Click a thumbnail to enlarge the original frame when
the small account crop is ambiguous or appears misplaced.

![Enlarged full-frame view of the included sample in the review lightbox](visuals/Review_Full_Frame.png)

**Confirm the reading.** The close-up shows the unchanged `iltalehti` name,
review checkboxes and saved status. The workbook is refreshed from the same
saved review state.

![Actual confirmed form showing iltalehti, review checkboxes and the saved Excel status](visuals/Review_Save.png)

The complete saved review is shown in the screenshot at the top of this README.

## Installation

### Install the command directly from GitHub

For your own clips, you can install the package without keeping a repository
checkout. 

On Fedora (What I use, should be similar in most other), create a Python 3.12 environment and select the Paddle extra:

```bash
sudo dnf install -y git python3.12
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install "ig-tk-accnames-ocr[paddle] @ git+https://github.com/econvaibhav/IG-TK-AccNames-OCR.git@v0.5.0"
.venv/bin/ig-tk-accnames-ocr --version
.venv/bin/ig-tk-accnames-ocr --help
```

This installs the `ig-tk-accnames-ocr` command and review assets. Use its `run`
and `review` commands with your own video and result paths, as shown below.
The installed package does not include the sample video or `run_laptop_test.py`;
clone the repository to try the complete example.

### Choose the dependencies you need

| Installation from a local checkout | What it includes |
| --- | --- |
| `python -m pip install .` | Video utilities, browser review and Excel support; no OCR engine. |
| `python -m pip install ".[paddle]"` | The base package plus PaddleOCR and PaddlePaddle. |
| `python -m pip install ".[easyocr]"` | The base package plus EasyOCR and its dependencies. |

Choose an OCR extra before running fresh OCR. The base package is sufficient for
opening an existing results folder and saving reviews. 

### Clone and try the included example

Clone the GitHub repository for the included video, review demo and helper
scripts. On Fedora:

```bash
sudo dnf install -y git python3.12
git clone https://github.com/econvaibhav/IG-TK-AccNames-OCR.git
cd IG-TK-AccNames-OCR
bash setup_laptop.sh --paddle
.venv/bin/python run_laptop_test.py --engine paddle --lang en fi
```

The included `examples/iltalehti_reel.mp4` is a real **50.9-second Iltalehti Reel**
from a Finnish news-media account. The test
creates a new `results/laptop_...` folder and opens its review page. 

To choose EasyOCR instead, the default setup installs EasyOCR with CPU
PyTorch and torchvision:

```bash
bash setup_laptop.sh
.venv/bin/python run_laptop_test.py --lang en
```

### Open a ready-made review

The repository includes the real sample's PaddleOCR output, so you can try the
review without running OCR or downloading model weights. After setup:

```bash
.venv/bin/ig-tk-accnames-ocr review examples/review_demo
```

For a review-only installation in a fresh checkout, use:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/ig-tk-accnames-ocr review examples/review_demo
```

## Run a clip

The installed command works with one video as well as folders:

```bash
OCR_RUN="results/clip_$(date +%Y%m%d_%H%M%S)"
.venv/bin/ig-tk-accnames-ocr run "/path/to/your/clip.mp4" \
  --output "$OCR_RUN" --engine paddle --lang en de pl bg \
  --layout tiktok --model-dir models \
  --sample-fps 2 --min-votes 3 --vote-margin 0 --max-samples 12 \
  --screenshots --excel
.venv/bin/ig-tk-accnames-ocr review "$OCR_RUN"
```

Use `--layout reels` for Instagram Reels. These quick-test settings sample
approximately **2 frames per second**, stop a direction once a candidate receives
**3 votes**, and attempt at most **12 frames per direction**. 

Add `--no-review` to that helper to finish after
writing the results, or `--no-open` to run its review server without opening a
browser automatically.

## Process a folder

This example processes the TikTok clips in the laptop folder used for testing,
including its subfolders. It enables ten European language groups plus
English; replace the language list with `--lang europe` for the broader preset:

```bash
OCR_RUN="results/tiktok_$(date +%Y%m%d_%H%M%S)"

OMP_NUM_THREADS=1 MKL_NUM_THREADS=4 \
.venv/bin/ig-tk-accnames-ocr run \
  "/home/name/Downloads/video_TK_clips" \
  --output "$OCR_RUN" \
  --recursive \
  --layout tiktok \
  --engine paddle \
  --lang en bg hr fr hu fi sv de pl es pt \
  --model-dir models \
  --sample-fps 2 \
  --min-votes 3 \
  --vote-margin 0 \
  --max-samples 12 \
  --screenshots \
  --excel

.venv/bin/ig-tk-accnames-ocr review "$OCR_RUN"
```

Supported extensions are `.mp4`, `.avi`, `.mov`, `.mkv`, `.flv`, `.wmv`, `.m4v`
and `.webm`

## Crop and sampling settings

### Adjust a crop

Use `--roi x,y,width,height` with `--layout tiktok` or `--layout fixed`:

```bash
.venv/bin/python run_laptop_test.py \
  --video "/path/to/tiktok_clip.mp4" \
  --engine paddle --lang en de pl bg \
  --layout tiktok --roi 0,600,440,280
```

This is an example wider crop

Use `--layout fixed --roi ...` for a fixed Instagram crop; fixed mode retains
Instagram-style candidate filtering. For the Reels circle-search strip, the main
CLI also accepts `--circle-roi x,y,width,height`.

### Adjust processing depth

| Option | Main CLI default | Effect |
| --- | --- | --- |
| `--sample-fps` | `20` | Approximate sampling rate per direction; cannot exceed available frames. |
| `--min-votes` | `11` | Stop a direction when a candidate reaches this many supporting frames. |
| `--vote-margin` | `3` | Retain candidates within this many votes of the leader. |
| `--max-samples` | `0` | Limit attempted frames per direction; `0` means no sample cap. |
| `--min-confidence` | `0` | Discard detections below this OCR confidence. |
| `--similarity` | `0.8` | Threshold for pairing candidate text between directions. |
| `--min-duration` | `0` | Skip clips shorter than this many seconds. |

## Languages and OCR models

Use `--lang` followed by the languages you expect. The default remains `en pl`.
Language selection works with `run_laptop_test.py`, `run` and `batch`.

Common European country/language selections, plus English:

| Country or context | Language | Code |
| --- | --- | --- |
| Across datasets | English | `en` |
| Bulgaria | Bulgarian | `bg` |
| Croatia | Croatian | `hr` |
| France | French | `fr` |
| Hungary | Hungarian | `hu` |
| Finland | Finnish | `fi` |
| Sweden | Swedish | `sv` |
| Germany | German | `de` |
| Poland | Polish | `pl` |
| Spain | Spanish | `es` |
| Portugal | Portuguese | `pt` |


### European presets

Use `--lang europe` as a convenient broader preset:

```bash
.venv/bin/python run_laptop_test.py \
  --video "/path/to/your/clip.mp4" \
  --layout tiktok --engine paddle --lang europe
```

The preset expands to these 32 language/script codes:

```text
en bg hr fr hu fi sv de pl es pt el it nl da no cs sk sl ro et lv lt ga mt is uk ru rs_latin rs_cyrillic sq tr
```

## Files in a run

| File or folder | Purpose |
| --- | --- |
| `results.xlsx` | Original OCR workbook, created with `--excel`. |
| `reviewed.xlsx` | Current saved review, one row per clip, refreshed when opening or saving the review. |
| `review_state.json` | Saved decisions, names, notes and correction history; created on the first save. |
| `details.jsonl` | Original results and raw frame observations: text, confidence, candidates, model sources and crop coordinates. |
| `run.json` | Input, settings, model names and installed package versions. |
| `screenshots/` | Account crops and full frames for the six review moments where available. |
| `review.html`, `review.css`, `review.js` | The generated local review interface. |
| `results.csv` | Original machine-readable export, retained for script compatibility. |

Excel is the review interface's only download format. The review no longer
creates a `reviewed.csv` file; an old one from a previous version is not refreshed.
The original OCR outputs are not overwritten by manual review.


## Repository guide

| Location | Contents |
| --- | --- |
| `ig_tk_ocr/core.py` | Configuration, candidate filtering, votes and comparisons. |
| `ig_tk_ocr/vision.py` | Video access, crops and reader selection. |
| `ig_tk_ocr/engines.py` | Paddle models and normalized detections. |
| `ig_tk_ocr/languages.py` | Language codes, aliases, European presets and engine compatibility checks. |
| `ig_tk_ocr/pipeline.py` | Forward/reverse scans and review frames. |
| `ig_tk_ocr/files.py` | Video discovery, manifests and original tabular results. |
| `ig_tk_ocr/review.py` | Local server, durable review state and Excel refresh. |
| `ig_tk_ocr/review_page.py`, `ig_tk_ocr/static/` | Review HTML, CSS and browser behaviour. |
| `ig_tk_ocr/excel.py` | Workbook formatting and embedded frame crops. |
| `examples/` | The real sample clip and a ready-made review. |
| `tests/` | Automated checks. |
| `visuals/` | LaTeX diagram, rendered figures and crop examples. |
| `legacy/` | Nine original scripts retained as references; use the package for current runs. |

The Python package is `ig_tk_ocr`; you can also run it with
`python -m ig_tk_ocr`. The installed command is `ig-tk-accnames-ocr`.

The `legacy` scripts contain their original fixed paths, dependencies and run
settings. 

## References

- [PaddleOCR source and releases](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR pipeline and Python API](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md)
- [PaddleOCR text recognition models](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/module_usage/text_recognition.html)
- [PaddleOCR multilingual models, including Bulgarian](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md)
- [EasyOCR documentation and languages](https://www.jaided.ai/easyocr/documentation/)
- [PyTorch installation](https://pytorch.org/get-started/locally/)
