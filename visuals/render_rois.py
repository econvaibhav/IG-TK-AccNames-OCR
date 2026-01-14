"""Recreate the README's crop figures from the included Iltalehti sample.

Run from the repository root: .venv/bin/python visuals/render_rois.py
Use the same environment as the OCR run: OpenCV versions can shift circle fits.
All reported coordinates refer to the 540 x 960 resized video frame.
"""
from pathlib import Path
import sys
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ig_tk_ocr.core import Config
from ig_tk_ocr.vision import crop_frame


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default(size=size)


def text(draw, xy, value, size=23, bold=False):
    draw.text(xy, value, fill="black", font=font(size, bold), spacing=11)


def rectangle(draw, box):
    draw.rectangle(box, outline="white", width=7)
    draw.rectangle(box, outline="black", width=2)


def line(draw, points):
    draw.line(points, fill="white", width=7)
    draw.line(points, fill="black", width=2)


def main():
    output = Path(__file__).resolve().parent
    cap = cv2.VideoCapture(str(ROOT / "examples" / "iltalehti_reel.mp4"))
    if not cap.isOpened():
        raise RuntimeError("Cannot open the sample clip")
    try:
        frame_index = round(3 * cap.get(cv2.CAP_PROP_FPS))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Cannot read the sample's 3-second frame")
    finally:
        cap.release()
    config = Config()
    resized, crop, box = crop_frame(frame, config)
    if crop is None:
        raise RuntimeError("No account region was found in the sample")
    # Repeat the exact detector to annotate its selected circle, not an estimate.
    x, y, width, height = config.circle_roi
    search = resized[y:y+height, x:x+width]
    blurred = cv2.GaussianBlur(search, (9, 9), 2)
    circles = []
    for channel in cv2.split(blurred):
        found = cv2.HoughCircles(
            channel, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
            param1=100, param2=30, minRadius=10, maxRadius=30,
        )
        if found is not None:
            circles.extend(found[0])
    cx, cy, radius = (int(round(float(v))) for v in max(circles, key=lambda c: c[1]))
    center = (x + cx, y + cy)
    left, top, crop_width, crop_height = box
    expected_box = (
        max(0, min(center[0] + radius, config.width - crop_width)),
        max(0, min(center[1] - crop_height // 2, config.height - crop_height)),
        crop_width, crop_height,
    )
    assert expected_box == box
    rgb = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
    search_image = Image.fromarray(cv2.cvtColor(search, cv2.COLOR_BGR2RGB))
    crop_image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

    stage1 = Image.new("RGB", (1120, 1010), "white")
    draw = ImageDraw.Draw(stage1)
    text(draw, (40, 28), "1 / Find the profile circle", 30, True)
    sx, sy, scale = 40, 104, 5 / 6
    stage1.paste(rgb.resize((450, 800), Image.Resampling.LANCZOS), (sx, sy))
    rectangle(draw, (sx, sy, sx+450, sy+800))
    roi_box = (sx+x*scale, sy+y*scale, sx+(x+width)*scale, sy+(y+height)*scale)
    rectangle(draw, roi_box)
    text(draw, (632, 116), "First region of interest", 26, True)
    text(draw, (632, 166), "Search a narrow strip at the\nlower left of the resized frame.", 22)
    text(draw, (632, 247), "x = 10   y = 560\nwidth = 69   height = 250", 22)
    zx, zy, zoom = 731, 355, 2
    stage1.paste(search_image.resize((width*zoom, height*zoom), Image.Resampling.LANCZOS), (zx, zy))
    rectangle(draw, (zx, zy, zx+width*zoom, zy+height*zoom))
    line(draw, [(roi_box[2], roi_box[1]), (555, roi_box[1]), (zx-24, zy), (zx, zy)])
    line(draw, [(roi_box[2], roi_box[3]), (555, roi_box[3]), (zx-24, zy+height*zoom), (zx, zy+height*zoom)])
    text(draw, (632, 876), "Search strip enlarged 2x", 20)
    text(draw, (40, 951), "Sample at 3 s. All coordinates use the resized 540 x 960 frame.", 22)
    stage1.save(output / "ROI_01_profile_search.png")

    stage2 = Image.new("RGB", (1200, 734), "white")
    draw = ImageDraw.Draw(stage2)
    text(draw, (40, 28), "2 / Crop the account region", 30, True)
    text(draw, (60, 109), "Selected circle", 25, True)
    text(draw, (574, 109), "Second region of interest", 25, True)
    ix, iy, context_top, zoom = 60, 207, 700, 2
    context = rgb.crop((0, context_top, config.width, 910))
    stage2.paste(context.resize((1080, 420), Image.Resampling.LANCZOS), (ix, iy))
    rectangle(draw, (ix, iy, ix+1080, iy+420))
    center_x, center_y = ix+center[0]*zoom, iy+(center[1]-context_top)*zoom
    radius_zoom = radius*zoom
    circle_box = (center_x-radius_zoom, center_y-radius_zoom, center_x+radius_zoom, center_y+radius_zoom)
    draw.ellipse(circle_box, outline="white", width=7)
    draw.ellipse(circle_box, outline="black", width=2)
    crop_box = (ix+left*zoom, iy+(top-context_top)*zoom,
                ix+(left+crop_width)*zoom, iy+(top-context_top+crop_height)*zoom)
    rectangle(draw, crop_box)
    line(draw, [(center_x, 154), (center_x, circle_box[1]-4)])
    line(draw, [(795, 154), (795, crop_box[1]-4)])
    text(draw, (60, 653), f"Circle: center ({center[0]}, {center[1]}), radius {radius}.  Crop: ({left}, {top}, {crop_width}, {crop_height}).", 22)
    text(draw, (60, 689), "The lowest detected circle anchors the crop immediately to its right.", 22)
    stage2.save(output / "ROI_02_account_crop.png")

    stage3 = Image.new("RGB", (1200, 282), "white")
    draw = ImageDraw.Draw(stage3)
    text(draw, (40, 24), "3 / Read the cropped text", 30, True)
    stage3.paste(crop_image.resize((1140, 120), Image.Resampling.LANCZOS), (30, 89))
    rectangle(draw, (30, 89, 1170, 209))
    text(draw, (30, 239), "380 x 40 pixels, enlarged 3x. Interface labels such as Follow are filtered after OCR.", 22)
    stage3.save(output / "ROI_03_account_text.png")
    print(f"OpenCV {cv2.__version__}; frame {frame_index}; circle center={center}, "
          f"radius={radius}; account crop={box}")


if __name__ == "__main__":
    main()
