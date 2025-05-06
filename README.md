# Instagram account OCR

Extract account labels from recorded Instagram and TikTok clips. The package
samples frames in both directions and retains the candidate readings for review.

```bash
python -m pip install -e '.[excel]'
python -m instagram_ocr run /path/to/clips --layout reels --output results/test --screenshots --excel
```

Use `python -m instagram_ocr --help` for commands and options. The original
scripts are in `legacy/`.
