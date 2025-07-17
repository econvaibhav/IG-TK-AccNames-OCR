# Example clip and review

`part_16_reel.mp4` is the unchanged 8.8-second Reel from the supplied archive.
The visible account is `thestoryofourhome.pl`.

`review_demo/` contains a checked EasyOCR run on that clip. Its repeated
`thestoryofourhome-pl` reading deliberately remains uncorrected so you can try
the review yourself. Open the HTML to preview, or start the editable review:

```bash
python -m instagram_ocr review examples/review_demo
```

The model is not given the visible reference name. It is only a human check.
