# Upload IG-TK-AccNames-OCR to GitHub

The downloaded project already includes a local Git repository and its commits.
Push that repository to retain the files and their history. Keep the `.git`
directory when moving the project. You do not need another initial commit.

The destination `econvaibhav/IG-TK-AccNames-OCR` already exists and is empty.
After signing in, follow step 3 to push the prepared repository directly.

## 1. Download and extract on Fedora

Save `IG-TK-AccNames-OCR.zip` in Downloads, then open Terminal:

```bash
sudo dnf install git gh unzip
mkdir -p ~/Projects/IG-TK-AccNames-OCR-Iltalehti
unzip ~/Downloads/IG-TK-AccNames-OCR.zip -d ~/Projects/IG-TK-AccNames-OCR-Iltalehti
cd ~/Projects/IG-TK-AccNames-OCR-Iltalehti/IG-TK-AccNames-OCR
```

Use a fresh extraction folder for this updated package. If you have already
extracted it elsewhere, open Terminal in that `IG-TK-AccNames-OCR` folder instead.

Check the branch and commits:

```bash
git status
git rev-list --count HEAD
git log --format='%h  %aI  %s' --reverse
```

The supplied branch is `main`. The history includes the original scripts and
the subsequent package, review, language and documentation changes.

## 2. Sign in to GitHub

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
```

Follow the browser instructions and sign in as `econvaibhav`. The `workflow`
scope allows uploading the included GitHub Actions workflow.

## 3. Push to the existing repository

The empty `econvaibhav/IG-TK-AccNames-OCR` repository is already created.
From the extracted project folder, run:

```bash
git remote add origin https://github.com/econvaibhav/IG-TK-AccNames-OCR.git
git push -u origin main
```

If Git says `remote origin already exists`, set its address and push:

```bash
git remote set-url origin https://github.com/econvaibhav/IG-TK-AccNames-OCR.git
git push -u origin main
```

Open <https://github.com/econvaibhav/IG-TK-AccNames-OCR>. The README, Iltalehti
example, screenshots, LaTeX workflow, code and all 27 prepared commits are
included. The Actions tab shows the automated Python checks once they run.

## 4. Run it locally

Uploading the repository does not require installing the OCR dependencies.
To run the application afterwards:

```bash
sudo dnf install python3.12
bash setup_laptop.sh --paddle
.venv/bin/ig-tk-accnames-ocr --list-languages
.venv/bin/ig-tk-accnames-ocr review examples/review_demo
```

The demo is the included 50.9-second Iltalehti Reel from a Finnish news-media
account, with its original `iltalehti` reading. Inspect the frames, leave the
name unchanged and **Mark as reviewed** checked, then click **Save changes**.
The page shows **Confirmed**. **Download Excel** contains the saved decisions
for the whole run, with `["iltalehti"]` in this row's `final_names`.

To run OCR again on the included clip with English and Finnish selected:

```bash
.venv/bin/python run_laptop_test.py --engine paddle --lang en fi
```

To reopen existing results with the new interface:

```bash
.venv/bin/ig-tk-accnames-ocr review "/full/path/to/your/previous/results"
```

This preserves saved decisions and does not repeat OCR. To use different
language models, process the original videos into a new output folder.

## 5. Process your European TikTok clips

The requested languages are English plus Bulgarian, Croatian, French,
Hungarian, Finnish, Swedish, German, Polish, Spanish and Portuguese:

```bash
OCR_RUN="results/tiktok_$(date +%Y%m%d_%H%M%S)"
.venv/bin/ig-tk-accnames-ocr run \
  "/home/vaibhavagarwal/Downloads/video_TK_clips" \
  --output "$OCR_RUN" \
  --recursive --layout tiktok --engine paddle \
  --lang en bg hr fr hu fi sv de pl es pt \
  --model-dir models --sample-fps 2 --min-votes 3 \
  --vote-margin 0 --max-samples 12 --screenshots --excel
.venv/bin/ig-tk-accnames-ocr review "$OCR_RUN"
```

For the broader 32-code preset, replace the language list with `--lang europe`.
It includes Greek and additional European languages and uses three script
recognizers. The explicit list above uses two, so it is lighter. Use
`--layout reels` for Instagram Reels. The README explains crops, full sampling
options, model downloads and limitations.

## Optional: restore the bundle

`IG-TK-AccNames-OCR.bundle` contains the same complete Git history. To create a
fresh working copy from it:

```bash
git clone IG-TK-AccNames-OCR.bundle IG-TK-AccNames-OCR
cd IG-TK-AccNames-OCR
git remote remove origin
```

Then follow the sign-in and push steps above.

## Official documentation

- [GitHub CLI installation on Linux](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)
- [Sign in with GitHub CLI](https://cli.github.com/manual/gh_auth_login)
