"""PaddleOCR 3 adapter; the voting pipeline keeps one common detection format."""

from pathlib import Path
import shutil
import tarfile
import tempfile
from urllib.request import urlopen

from .languages import (PADDLE_CYRILLIC_LANGUAGES, PADDLE_V6_LANGUAGES,
                        resolve_languages)


def local_model(name, root, download_enabled):
    """Cache official inference weights without depending on a hub health check."""
    folder = root / name
    required = ("inference.json", "inference.pdiparams", "inference.yml")
    if all((folder / file).is_file() for file in required):
        return folder
    if not download_enabled:
        raise ValueError(f"Offline Paddle model missing or incomplete: {folder}")
    if folder.exists():
        raise ValueError(f"Incomplete model folder: {folder}. Rename it before downloading again.")
    root.mkdir(parents=True, exist_ok=True)
    url = f"https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/{name}_infer.tar"
    print(f"Downloading {name} into {root}", flush=True)
    with tempfile.TemporaryDirectory(prefix="ocr_model_", dir=root) as tmp:
        archive = Path(tmp) / "model.tar"
        with urlopen(url, timeout=60) as response, archive.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        unpacked = Path(tmp) / "unpacked"
        unpacked.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                target = (unpacked / member.name).resolve()
                if not target.is_relative_to(unpacked.resolve()) or not (member.isfile() or member.isdir()):
                    raise RuntimeError("Unexpected member in model archive")
            tar.extractall(unpacked)
        candidates = [p.parent for p in unpacked.rglob("inference.yml")
                      if all((p.parent / file).is_file() for file in required)]
        if len(candidates) != 1:
            raise RuntimeError(f"Incomplete inference archive for {name}")
        candidates[0].rename(folder)
    return folder


def paddle_recognizers(languages, size="small"):
    """Select script-capable recognition models; preserve the ordinary v6 path."""
    if size not in {"tiny", "small", "medium"}:
        raise ValueError("Paddle model size must be tiny, small or medium")
    requested = set(resolve_languages(languages, "paddle"))
    if size == "tiny" and "japan" in requested:
        raise ValueError("Japanese needs --paddle-size small or medium")
    names = []
    # English is included in the Cyrillic/Greek model. A separate Latin reader is
    # needed only for other v6 languages, or when no specialist was requested.
    specialized = requested & (PADDLE_CYRILLIC_LANGUAGES | {"el"})
    if requested & (PADDLE_V6_LANGUAGES - {"en"}) or not specialized:
        names.append(f"PP-OCRv6_{size}_rec")
    if requested & PADDLE_CYRILLIC_LANGUAGES:
        names.append("cyrillic_PP-OCRv5_mobile_rec")
    if "el" in requested:
        names.append("el_PP-OCRv5_mobile_rec")
    return names


def overlapping_boxes(first, second):
    """Match identical readings in the same region; never combine different text."""
    if first is None or second is None:
        return False
    def bounds(box):
        xs, ys = zip(*box)
        return min(xs), min(ys), max(xs), max(ys)
    ax, ay, ar, ab = bounds(first)
    bx, by, br, bb = bounds(second)
    intersection = max(0, min(ar, br)-max(ax, bx)) * max(0, min(ab, bb)-max(ay, by))
    union = (ar-ax)*(ab-ay) + (br-bx)*(bb-by) - intersection
    return union > 0 and intersection / union >= .5


class PaddleReader:
    def __init__(self, config, size="small", model_directory=None, download_enabled=True):
        if config.gpu:
            raise ValueError("The supplied Paddle setup is CPU-only; omit --gpu")
        self.recognition_models = paddle_recognizers(config.languages, size)
        self.detection_model = f"PP-OCRv6_{size}_det"
        self.model_names = [self.detection_model, *self.recognition_models]
        self.last_detection_models = []
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError('PaddleOCR is missing. Run: python -m pip install -e ".[paddle,excel]"') from exc
        legacy_cache = Path.home() / ".cache" / "instagram-account-ocr"
        default_cache = Path.home() / ".cache" / "ig-tk-accnames-ocr"
        root = Path(model_directory) if model_directory else (
            default_cache if default_cache.exists() or not legacy_cache.exists() else legacy_cache)
        self.models = []
        try:
            detector = local_model(self.detection_model, root, download_enabled)
            for name in self.recognition_models:
                recognizer = local_model(name, root, download_enabled)
                self.models.append(PaddleOCR(
                    text_detection_model_name=self.detection_model,
                    text_detection_model_dir=str(detector),
                    text_recognition_model_name=name,
                    text_recognition_model_dir=str(recognizer),
                    use_doc_orientation_classify=False, use_doc_unwarping=False,
                    use_textline_orientation=False, device="cpu", cpu_threads=4,
                    enable_mkldnn=False, text_det_limit_side_len=640,
                    text_det_limit_type="max",
                ))
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not initialize Paddle OCR models: {exc}") from exc
        print("Recognition: " + ", ".join(self.recognition_models), flush=True)
        if len(self.models) > 1:
            print("Mixed scripts: each crop runs through multiple models. Conflicting readings remain for review.", flush=True)

    def readtext(self, image, **_):
        detections, sources = [], []
        for model, name in zip(self.models, self.recognition_models):
            for result in model.predict(image):
                texts = result["rec_texts"]
                scores = result["rec_scores"]
                boxes = result.get("rec_polys", [None] * len(texts))
                if len(texts) != len(scores) or len(texts) != len(boxes):
                    raise RuntimeError("PaddleOCR returned inconsistent detection arrays")
                for box, text, score in zip(boxes, texts, scores):
                    text, score = str(text), float(score)
                    duplicate = next((index for index, (old_box, old_text, _) in enumerate(detections)
                                      if text.casefold() == old_text.casefold()
                                      and overlapping_boxes(box, old_box)), None)
                    if duplicate is None:
                        detections.append((box, text, score))
                        sources.append([name])
                    else:
                        old_box, old_text, old_score = detections[duplicate]
                        detections[duplicate] = (old_box, old_text, max(score, old_score))
                        sources[duplicate].append(name)
        # Different readings of one region stay separate. Votes.add_frame gives a
        # label at most one vote per frame, even if multiple readers recognize it.
        self.last_detection_models = sources
        return detections
