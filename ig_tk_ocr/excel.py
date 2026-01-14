"""Excel export with literal strings and an embedded account crop."""

from pathlib import Path
from .files import csv_row


def save_excel(results, path, rows=None, evidence_root=None):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from .review import evidence_path

    results = list(results)
    rows = [csv_row(result) for result in results] if rows is None else rows
    book = Workbook()
    sheet = book.active
    sheet.title = "Reviewed" if rows and "review_status" in rows[0] else "Results"
    headers = list(rows[0]) if rows else list(csv_row({"path": "", "status": ""}))
    sheet.append(headers + ["Screenshot at 3 s"])
    image_column = get_column_letter(len(headers) + 1)
    sheet.freeze_panes = "B2"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="222222")
    for row_index, (result, row) in enumerate(zip(results, rows), 2):
        sheet.append(list(row.values()))
        for cell in sheet[row_index]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.row_dimensions[row_index].height = 70
        shot = next((s for s in result.get("screenshots", []) if s["label"] == "3sec" and "path" in s), None)
        if shot:
            shot_path = evidence_path(shot["path"], Path(evidence_root or Path(path).parent))
            if shot_path.is_file():
                image = Image(shot_path)
                scale = min(1, 380 / image.width, 80 / image.height)
                image.width *= scale; image.height *= scale
                sheet.add_image(image, f"{image_column}{row_index}")
    for index, header in enumerate(headers, 1):
        sheet.column_dimensions[get_column_letter(index)].width = 42 if header == "path" else 25
    sheet.column_dimensions[image_column].width = 55
    sheet.auto_filter.ref = sheet.dimensions
    book.save(path)
    book.close()
