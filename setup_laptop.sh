#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

OCR_PYTHON="${OCR_PYTHON:-python3.12}"
OCR_EXTRA="excel"
if [[ "${1:-}" == "--paddle" ]]; then
  OCR_EXTRA="excel,paddle"
elif [[ $# -gt 0 ]]; then
  echo "Usage: bash setup_laptop.sh [--paddle]"
  exit 2
fi
if ! command -v "$OCR_PYTHON" >/dev/null 2>&1; then
  echo "Install Python 3.12 first: sudo dnf install -y python3.12"
  exit 1
fi

"$OCR_PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
# Install the CPU build first so this laptop test does not need CUDA.
.venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -e ".[${OCR_EXTRA}]"
.venv/bin/python -m pip check
echo
echo "Setup complete. Run: .venv/bin/python run_laptop_test.py"

