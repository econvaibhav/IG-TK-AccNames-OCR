# Example clip and review

`iltalehti_reel.mp4` is the unchanged supplied `part_46.mp4`, renamed for this
example. It is a 50.9-second, 60-fps, 720 × 1600 Reel from the Finnish news-media
account `iltalehti`.

`review_demo/` contains a real PaddleOCR run with `--lang en fi`. Both passes
read `iltalehti` with three votes. The result remains unreviewed so you can try
confirming it yourself:

```bash
.venv/bin/ig-tk-accnames-ocr review examples/review_demo
```

Inspect the frames, leave `iltalehti` unchanged and **Mark as reviewed** checked,
and click **Save changes**. The page shows **Confirmed** and `reviewed.xlsx`
contains `["iltalehti"]` in `final_names`. The reference name is never passed
to the OCR engine as an expected answer.

To compute a fresh result from the included clip:

```bash
.venv/bin/python run_laptop_test.py --engine paddle --lang en fi
```
