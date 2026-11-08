from io import BytesIO, StringIO
import csv

from app.config.settings import Settings


def make_settings(**overrides) -> Settings:
    """Build settings without reading a local `.env` file."""
    return Settings(_env_file=None, **overrides)


def csv_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def xlsx_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
