"""Run both directions and retain the frame evidence behind every result."""

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from .core import Votes, clean_candidates, compare_passes, frame_indices, handle_like
from .vision import crop_frame, cv_module, open_video


def scan(cap, fps, count, reader, config, reverse=False):
    cv = cv_module()
    votes = Votes()
    observations = []
    examined = decoded = crops = 0
    stopped = False
    for index in frame_indices(count, fps, config.sample_fps, reverse, config.max_samples):
        examined += 1
        cap.set(cv.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            continue
        decoded += 1
        _, crop, box = crop_frame(frame, config)
        if crop is None:
            continue
        crops += 1
        # paragraph=False preserves confidence and avoids merging labels with Follow.
        detections = reader.readtext(crop, detail=1, paragraph=False, text_threshold=0.8)
        labels = []
        platform = "tiktok" if config.layout == "tiktok" else "instagram"
        for _, text, confidence in detections:
            confidence = float(confidence)
            accepted = clean_candidates(str(text), platform) if confidence >= config.min_confidence else []
            labels.extend(accepted)
            observations.append({
                "direction": "reverse" if reverse else "forward",
                "frame": index, "seconds": round(index / fps, 4),
                "raw_text": str(text), "confidence": confidence,
                "candidates": accepted, "roi": list(box),
            })
        votes.add_frame(labels)
        top = votes.top(config.vote_margin)
        if top and top[0]["votes"] >= config.min_votes:
            stopped = True
            break
    return {
        "candidates": votes.top(config.vote_margin),
        "frames_attempted": examined, "frames_decoded": decoded, "crops_found": crops,
        "decode_failures": examined - decoded, "enough_votes": stopped,
        "observations": observations,
    }


def screenshots(cap, fps, count, config, folder):
    """Save legacy time points plus duration quartiles, with full-frame context."""
    cv = cv_module()
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    duration = count / fps
    requests = [("1sec", 1.0), ("3sec", 3.0), ("end_minus_1sec", max(0, duration - 1)),
                ("25percent", duration * .25), ("50percent", duration * .5),
                ("75percent", duration * .75)]
    for label, second in requests:
        if second >= duration:
            saved.append({"label": label, "error": "outside_clip"})
            continue
        index = min(count - 1, max(0, round(second * fps)))
        cap.set(cv.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            saved.append({"label": label, "frame": index, "error": "decode_failed"})
            continue
        resized, crop, box = crop_frame(frame, config)
        # A missing circle must not masquerade as a successful username crop.
        path = folder / f"{label}{'' if crop is not None else '_no_roi'}.png"
        if not cv.imwrite(str(path), crop if crop is not None else resized):
            raise OSError(f"Could not save screenshot: {path}")
        full_path = folder / f"{label}_full.jpg"
        if not cv.imwrite(str(full_path), frame, [cv.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError(f"Could not save full frame: {full_path}")
        saved.append({"label": label, "frame": index, "seconds": round(index/fps, 4),
                      "requested_seconds": second, "full_path": str(full_path),
                      "roi_found": crop is not None, "path": str(path), "roi": box})
    return saved


def process_video(path, reader, config, screenshot_root=None):
    path = Path(path)
    result = {"path": str(path), "layout": config.layout, "config": asdict(config)}
    with open_video(path) as (cap, fps, count):
        result.update({"fps": fps, "total_frames": count, "duration_seconds": count / fps})
        if count / fps < config.min_duration:
            result.update(status="skipped_short", union_names=[], matches=[], needs_review=True,
                          review_reasons=["below_minimum_duration"])
            return result
        forward = scan(cap, fps, count, reader, config)
        reverse = scan(cap, fps, count, reader, config, reverse=True)
        comparison = compare_passes(forward["candidates"], reverse["candidates"], config.similarity)
        reasons = []
        if comparison["status"] != "agreement":
            reasons.append(comparison["status"])
        if not forward["enough_votes"] or not reverse["enough_votes"]:
            reasons.append("low_support")
        if forward["decode_failures"] or reverse["decode_failures"]:
            reasons.append("decode_failure")
        if len(comparison["union_names"]) > 1:
            reasons.append("multiple_labels")
        if config.layout == "tiktok":
            reasons.append("experimental_tiktok_layout")
        elif any(not handle_like(n) for n in comparison["union_names"]):
            reasons.append("nonstandard_label")
        result.update(comparison, forward=forward, reverse=reverse,
                      needs_review=bool(reasons), review_reasons=reasons)
        if screenshot_root:
            identity = sha256(str(path.resolve()).encode()).hexdigest()[:12]
            result["screenshots"] = screenshots(
                cap, fps, count, config, Path(screenshot_root) / f"{path.stem}_{identity}"
            )
    return result
