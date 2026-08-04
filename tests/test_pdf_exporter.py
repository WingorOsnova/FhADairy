from pypdf import PdfReader

from fachabi_diary.models import DailyEntry, Profile, WeeklyReport
from fachabi_diary.services.pdf_exporter import PdfExporter


def test_pdf_export_creates_readable_file(tmp_path) -> None:
    output = tmp_path / "bericht.pdf"
    report = WeeklyReport(
        report_number=1,
        week_start="2026-08-03",
        week_end="2026-08-09",
        report_date="2026-08-07",
        location="Berlin",
        entries=[DailyEntry("2026-08-03", 8, "Projektstruktur kennengelernt.")],
    )

    PdfExporter(__import__("pathlib").Path("assets/formblatt9.pdf")).export_week(Profile(), report, output)

    reader = PdfReader(str(output))
    text = reader.pages[0].extract_text()
    assert len(reader.pages) == 1
    assert "Lysenko" in text
    assert "Projektstruktur kennengelernt" in text
