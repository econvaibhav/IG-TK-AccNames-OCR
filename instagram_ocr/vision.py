"""Video access and the original circle-based crop, with bounded coordinates."""

from contextlib import contextmanager
import math


def cv_module():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is missing. Run: python -m pip install -e .") from exc
    return cv2


@contextmanager
def open_video(path):
    cv = cv_module()
    cap = cv.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {path}")
        fps = float(cap.get(cv.CAP_PROP_FPS))
        count = float(cap.get(cv.CAP_PROP_FRAME_COUNT))
        if not math.isfinite(fps) or fps <= 0 or not math.isfinite(count) or count < 1:
            raise ValueError(f"Invalid FPS or frame count: {path}")
        yield cap, fps, int(count)
    finally:
        cap.release()


def crop_frame(frame, config):
    """Return (resized frame, crop or None, crop box or None)."""
    cv = cv_module()
    frame = cv.resize(frame, (config.width, config.height))
    if config.layout != "reels":
        box = config.fixed_roi or (0, 650, config.width // 2, 230)
    else:
        x, y, w, h = config.circle_roi
        roi = frame[y:y+h, x:x+w]
        blurred = cv.GaussianBlur(roi, (9, 9), 2)
        circles = []
        for channel in cv.split(blurred):
            found = cv.HoughCircles(
                channel, cv.HOUGH_GRADIENT, dp=1.2, minDist=100,
                param1=100, param2=30, minRadius=10, maxRadius=30,
            )
            if found is not None:
                circles.extend(found[0])
        if not circles:
            return frame, None, None
        # Original later versions select the lowest circle, not the largest radius.
        cx, cy, radius = (int(round(float(v))) for v in max(circles, key=lambda c: c[1]))
        crop_w, crop_h = config.crop_size
        left = max(0, min(x + cx + radius, config.width - crop_w))
        top = max(0, min(y + cy - crop_h // 2, config.height - crop_h))
        box = (left, top, crop_w, crop_h)
    left, top, w, h = box
    crop = frame[top:top+h, left:left+w]
    if crop.size == 0:
        return frame, None, None
    return frame, crop, box


def make_reader(config, model_directory=None, download_enabled=True, engine="easyocr", paddle_size="small"):
    if engine == "paddle":
        from .engines import PaddleReader
        return PaddleReader(config, paddle_size, model_directory, download_enabled)
    if engine != "easyocr":
        raise ValueError(f"Unknown OCR engine: {engine}")
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError("EasyOCR is missing. Run: python -m pip install -e .") from exc
    kwargs = {"gpu": config.gpu, "download_enabled": download_enabled}
    if model_directory:
        kwargs["model_storage_directory"] = str(model_directory)
    return easyocr.Reader(list(config.languages), **kwargs)
