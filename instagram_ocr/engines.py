"""PaddleOCR 3 adapter; the voting pipeline keeps one common detection format."""

from pathlib import Path
import shutil
import tarfile
import tempfile
from urllib.request import urlopen


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


class PaddleReader:
    def __init__(self, config, size="small", model_directory=None, download_enabled=True):
        if size not in {"tiny", "small", "medium"}:
            raise ValueError("Paddle model size must be tiny, small or medium")
        if config.gpu:
            raise ValueError("The supplied Paddle setup is CPU-only; omit --gpu")
        # These models share a multilingual recognizer, including English and Polish.
        supported = set("en pl ch chinese_cht af az bs ca cs cy da de es et eu fi fr ga gl hr hu id is it ku la lb lt lv mi ms mt nl no oc pt qu rm ro rs_latin sk sl sq sv sw tl tr uz vi french german".split())
        if size != "tiny":
            supported.add("japan")
        if not set(config.languages) <= supported:
            raise ValueError("The selected PP-OCRv6 model does not support this --lang set")
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError('PaddleOCR is missing. Run: python -m pip install -e ".[paddle,excel]"') from exc
        kwargs = dict(
            text_detection_model_name=f"PP-OCRv6_{size}_det",
            text_recognition_model_name=f"PP-OCRv6_{size}_rec",
            use_doc_orientation_classify=False, use_doc_unwarping=False,
            use_textline_orientation=False, device="cpu", cpu_threads=4, enable_mkldnn=False,
            text_det_limit_side_len=640, text_det_limit_type="max",
        )
        root = Path(model_directory) if model_directory else Path.home() / ".cache" / "instagram-account-ocr"
        try:
            for stage, suffix in (("detection", "det"), ("recognition", "rec")):
                folder = local_model(f"PP-OCRv6_{size}_{suffix}", root, download_enabled)
                kwargs[f"text_{stage}_model_dir"] = str(folder)
            self.model = PaddleOCR(**kwargs)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not initialize PP-OCRv6: {exc}") from exc

    def readtext(self, image, **_):
        detections = []
        for result in self.model.predict(image):
            # OCRResult is dict-like; no image serialization or API service needed.
            texts = result["rec_texts"]
            scores = result["rec_scores"]
            boxes = result.get("rec_polys", [None] * len(texts))
            if len(texts) != len(scores) or len(texts) != len(boxes):
                raise RuntimeError("PaddleOCR returned inconsistent detection arrays")
            detections.extend((box, str(text), float(score))
                              for box, text, score in zip(boxes, texts, scores))
        return detections
