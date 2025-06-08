# Instagram Account OCR

Read account names from Instagram Reels, compare readings from the beginning and
end of each clip, and inspect the results alongside the cropped video frames.

![OCR workflow](visuals/OCR_Workflow.png)

## Try it on your Fedora laptop

The included `examples/part_16_reel.mp4` is an unchanged 8.8-second clip from your
uploaded OCR examples. The visible name is **`thestoryofourhome.pl`**.

Open a terminal in this extracted `instagram-ocr` folder and run:

```bash
sudo dnf install -y python3.12
bash setup_laptop.sh
.venv/bin/python run_laptop_test.py
```

The setup creates a local `.venv` and installs the CPU version of PyTorch,
EasyOCR, OpenCV and Excel support. The first test also downloads EasyOCR's model
files into `models/`. Keep the terminal open while this finishes.

The test samples two frames per second and stops once a name has three votes
in each direction, with a maximum of twelve samples per direction. These are
small laptop-test settings. Results are freshly computed from the clip.

When it finishes, the result opens in your browser. Each run creates a separate
folder inside `results/` containing:

| File | What to check |
| --- | --- |
| `review.html` | Forward and reverse names, vote counts, and three cropped screenshots. |
| `results.xlsx` | The result table and the 3-second screenshot. |
| `results.csv` | One row for the clip, including its review status. |
| `details.jsonl` | Raw OCR text, confidence, frame numbers and crop coordinates. |
| `run.json` | The settings and installed package versions used for this run. |

Compare the detected name with `thestoryofourhome.pl`, including the dot before
`pl`. OCR can read punctuation incorrectly even when both directions agree.
Review flags identify missing readings, disagreements and other cases to inspect.

In the checked CPU run, both passes returned `thestoryofourhome-pl` with three
votes each. The output was `agreement`, with `needs_review=True` and
`nonstandard_label` because of the hyphen. Your fresh run may read it differently;
compare the output with the image rather than treating agreement as accuracy.

To run it again, use `.venv/bin/python run_laptop_test.py`; setup is only needed
once. If the browser does not open automatically, open the `review.html` path
printed in the terminal. To send back a useful result, copy the printed
Candidates, Comparison, Forward and Reverse lines, or share the CSV and crops.

## Try another Reel or a folder

```bash
.venv/bin/python run_laptop_test.py --video "/path/to/your/reel.mp4"

.venv/bin/python -m instagram_ocr run "/path/to/clips" \
  --output results/my_clips --lang en pl --screenshots --excel
```

The folder command uses the main defaults: 20 requested samples/second and
11 votes before early stopping. Choose a new output folder for each run.
Use `--lang en hu` for Hungarian or another EasyOCR-compatible language set.
The circle crop is tuned to the Reels layout; ordinary feed posts may need
`--layout fixed --roi x,y,width,height` in the 540 × 960 working frame.

## Edit the diagram

Open `visuals/OCR_Workflow.tex` in Overleaf, or compile it with pdfLaTeX:

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory visuals visuals/OCR_Workflow.tex
```

The compiled PDF and PNG are already included, so LaTeX is not needed to test OCR.

## Code

`core.py` handles filtering and voting; `vision.py` finds the crop;
`pipeline.py` processes both directions; `files.py` and `excel.py` export the
results. The command line is in `instagram_ocr/__main__.py`.

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Installation references: [Fedora Python 3.12](https://packages.fedoraproject.org/pkgs/python3.12/python3.12/),
[PyTorch](https://pytorch.org/get-started/locally/),
[EasyOCR](https://www.jaided.ai/easyocr/documentation/).
