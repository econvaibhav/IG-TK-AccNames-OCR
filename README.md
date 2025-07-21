# Instagram Account OCR

Read account handles from recorded Reels, inspect six moments in each clip, and
save corrections from a local browser into Excel and CSV.

![Workflow](visuals/OCR_Workflow.png)

## Try the newer model on your Fedora laptop

The included `examples/part_16_reel.mp4` is your original 8.8-second example.
Open a terminal in this extracted `instagram-ocr` folder:

```bash
sudo dnf install -y python3.12
bash setup_laptop.sh --paddle
.venv/bin/python run_laptop_test.py --engine paddle
```

Setup installs CPU dependencies. The first run downloads the two **PP-OCRv6
small** models into `models/` (about 30 MB together). Once downloaded, the OCR
runs locally. No Instagram login or OCR API key is needed.

Keep the terminal open: it starts a local review page and opens your browser.
If it does not open, copy the `http://127.0.0.1:.../` URL printed in the terminal.
Press **Ctrl+C** to stop the review; saved corrections remain on disk.

Already installed the previous package? Extract this version into a new folder
and run setup there. To use the existing EasyOCR option:

```bash
bash setup_laptop.sh
.venv/bin/python run_laptop_test.py
```

Each test samples two frames per second, stops at three votes per direction,
and attempts at most twelve frames in each direction. These are quick-test
settings. Every run computes fresh results in a new `results/laptop_...` folder.
Use `--no-review` to finish after processing without starting the browser server.

## Try the review immediately

A real EasyOCR result is included so you can test the correction flow without
running OCR or downloading models. After setup:

```bash
.venv/bin/python -m instagram_ocr review examples/review_demo
```

Change `thestoryofourhome-pl` to `thestoryofourhome.pl` and save. Check
`examples/review_demo/reviewed.xlsx` or download it from the page.

## Correct a result

1. Inspect the existing **1 s, 3 s and end − 1 s** views, plus **25%, 50% and 75%**
   of the clip duration. These are time quartiles. Each has the account crop,
   full frame, actual timestamp and frame index; click the full frame to enlarge.
2. Enter the actual handle shown in the images, including dots and underscores.
   Use commas if more than one account is visible.
3. Choose **Confirmed**, **Corrected**, or **Cannot read**, add a note if useful,
   then click **Save correction**. Typing a changed name selects Corrected.
4. Use **Download Excel** or **CSV**. The same files are also updated directly in
   that run's folder. If Excel locks the workbook, close it and click
   **Refresh exports**; the saved correction is retained.

**`final_names` is the reviewed account field.** Check `review_status` alongside
it. Unreviewed rows still contain the original OCR candidates; Cannot read rows
have an empty `final_names`. Both remain flagged by `needs_manual_review`.
The original `status` and `needs_review` columns describe the automatic OCR pass.

This connection runs **review → Excel/CSV**. Editing a downloaded workbook does
not update the browser. Corrections update the result, not the OCR model.

Reopen a previous run without doing OCR again:

```bash
.venv/bin/python -m instagram_ocr review results/laptop_YOUR_RUN_FOLDER
```

Opening `review.html` directly provides a preview. Use the command above for
saving and downloads. Keep the whole run folder together when moving it.

## What changed with the newer OCR?

[PP-OCRv6](https://github.com/PaddlePaddle/PaddleOCR/releases/tag/v3.7.0) was
released on **11 June 2026**. The small model is a practical option for this
laptop experiment; EasyOCR remains the default for existing commands. The
multilingual recognizer supports English and Polish together.

The checked CPU runs on the supplied clip produced:

| Engine | Forward | Reverse | Visible handle |
| --- | --- | --- | --- |
| EasyOCR 1.7.2 | `thestoryofourhome-pl` · 3 votes | `thestoryofourhome-pl` · 3 votes | `thestoryofourhome.pl` |
| PP-OCRv6 small | `thestoryofourhome.pl` · 3 votes | `thestoryofourhome.pl` · 3 votes | `thestoryofourhome.pl` |

This is one clip, not a general accuracy benchmark. Two agreeing passes can make
the same punctuation error. The six review images provide evidence independent
of which frames reached the vote threshold.

PaddleOCR 3.7.0 / PaddlePaddle 3.3.1 were checked on Linux CPU. MKL-DNN is disabled
in the adapter because its accelerated path failed on this runtime. Other laptop
platforms and the tiny/medium variants have not been tested here. Model names,
settings and dependency versions are recorded in `run.json`.

## Your own videos

```bash
.venv/bin/python run_laptop_test.py --engine paddle --video "/path/to/reel.mp4"

.venv/bin/python -m instagram_ocr run "/path/to/clips" \
  --output results/my_clips --engine paddle --model-dir models \
  --screenshots --excel
.venv/bin/python -m instagram_ocr review results/my_clips
```

Folder processing uses 20 requested samples/second and 11 votes per direction.
Choose a new output folder for each OCR run. Add `--recursive` for subfolders.
`--paddle-size tiny` or `medium` selects another PP-OCRv6 size; small is the tested
choice. Use `--offline --model-dir models` when its weights are already present.

The circle crop is tuned to Reels. Other layouts can use
`--layout fixed --roi x,y,width,height` in the 540 × 960 working frame.
Fixed times beyond a short clip are marked unavailable. Quartile frames use the
nearest bounded frame index; constant-frame-rate timing is assumed.

## Output files

| File | Contents |
| --- | --- |
| `review.html`, `review.css`, `review.js` | Local review interface. |
| `screenshots/` | Six account crops and full frames when available. |
| `results.csv`, `results.xlsx` | Original OCR results; Excel embeds the 3-second crop. |
| `details.jsonl` | Original raw text, confidence, frame numbers and crop coordinates. |
| `run.json` | Engine, settings and installed versions. |
| `review_state.json` | Saved decisions, names, notes and correction history. |
| `reviewed.csv`, `reviewed.xlsx` | Original fields plus final names and review status. |

The correction and reviewed files appear when you start the review and save.
Use the search box and Unresolved only filter to work through a larger folder.

## Code and diagram

`core.py` filters and votes; `vision.py` locates crops; `engines.py` adapts PP-OCRv6;
`pipeline.py` scans and saves frames. `review.py` handles the local server and
corrections, `review_page.py` renders the page, and `excel.py` writes workbooks.

```bash
.venv/bin/python -m unittest discover -s tests -v
pdflatex -interaction=nonstopmode -halt-on-error -output-directory visuals visuals/OCR_Workflow.tex
```

The PDF and PNG are included. LaTeX is not needed to run OCR. The diagram source
can also be opened in Overleaf.

References: [PaddleOCR models and Python API](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md),
[EasyOCR](https://www.jaided.ai/easyocr/documentation/),
[PyTorch CPU installation](https://pytorch.org/get-started/locally/).
