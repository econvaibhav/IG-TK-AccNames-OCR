# Example clip and review

`part_16_reel.mp4` is the unchanged 8.8-second Reel from the supplied example.
The visible account is `thestoryofourhome.pl`.

`review_demo/` contains a real EasyOCR run. Its repeated `thestoryofourhome-pl`
reading remains uncorrected so you can try the review yourself:

```bash
python -m instagram_ocr review examples/review_demo
```

Edit the hyphen to a dot, leave **Mark as reviewed** checked, and click **Save
changes**. The shared `reviewed.xlsx` will contain the correction. For a name
that is already right, simply save without editing. The reference name is never
passed to the OCR engine as an expected answer.
