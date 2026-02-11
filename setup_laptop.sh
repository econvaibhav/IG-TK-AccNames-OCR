#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

usage() {
  echo "Usage: bash setup_laptop.sh [--paddle]"
  echo "Default: EasyOCR on CPU. --paddle: PaddleOCR on CPU."
}
if [[ $# -gt 1 ]]; then
  usage
  exit 2
fi
OCR_ENGINE="easyocr"
case "${1:-}" in
  "") ;;
  --paddle) OCR_ENGINE="paddle" ;;
  -h|--help) usage; exit 0 ;;
  *) usage; exit 2 ;;
esac
OCR_PYTHON="${OCR_PYTHON:-python3.12}"
if ! command -v "$OCR_PYTHON" >/dev/null 2>&1; then
  echo "Install Python 3.12 first: sudo dnf install -y python3.12"
  echo "Or choose an existing Python 3.10+ interpreter with OCR_PYTHON."
  exit 1
fi
"$OCR_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10+ is required; Python 3.12 is recommended.")'

# Reuse an existing environment without removing packages or cached models.
"$OCR_PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
if [[ "$OCR_ENGINE" == "easyocr" ]]; then
  # Install CPU wheels before EasyOCR so the laptop setup does not need CUDA.
  .venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi
.venv/bin/python -m pip install --prefer-binary -e ".[${OCR_ENGINE}]"
.venv/bin/python -m pip check
echo
echo "Setup complete. Run: .venv/bin/python run_laptop_test.py --engine ${OCR_ENGINE}"
