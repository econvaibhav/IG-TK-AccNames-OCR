# Earlier scripts

These scripts retain the original implementations. Use the package in the repository root for current runs; these versions have fixed paths, run settings and dependencies.

| File | What it does |
| --- | --- |
| `roi_preview.py` | Displays the profile-circle search area and the adjoining account crop. |
| `frame_ocr.py` | Runs English/Bulgarian EasyOCR on each detected crop and records text and confidence. |
| `OCR_IG.py` | Processes Instagram clips forward and backward, counts repeated readings and compares candidates. |
| `OCR_TK.py` | Uses a fixed lower-left crop for TikTok with forward/backward reading and name filtering. |
| `generate_array.py` | Builds a list of video folders for array jobs. |
| `main_array.py` | Dispatches each folder to the Instagram or TikTok pipeline. |
| `main_ocr_array.sh` | Runs one folder per Slurm task. |
| `ocr_ig_excel.py` | Adds clip-length filtering and an Excel workbook with a 3-second account crop. |
| `video_duration.py` | Totals the duration of videos under a folder. |

The scripts preserve their original contents, including environment-specific paths. `OCR_IG.py` and `OCR_TK.py` keep the names expected by `main_array.py`. Older result files and full recording inventories are not included here.
