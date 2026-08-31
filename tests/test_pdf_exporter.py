import warnings

from pypdf import PdfReader

from fachabi_diary.models import DailyEntry, Profile, WeeklyReport
from fachabi_diary.services.pdf_exporter import PdfExporter


def test_pdf_export_creates_readable_file(tmp_path) -> None:
    output = tmp_path / "bericht.pdf"
    report = WeeklyReport(
        report_number=1,
        week_start="2026-08-03",
        week_end="2026-08-09",
        report_date="2026-08-03",
        location="Berlin",
        entries=[DailyEntry("2026-08-03", 8, "Projektstruktur kennengelernt.")],
    )

    PdfExporter(__import__("pathlib").Path("assets/formblatt9.pdf")).export_week(Profile(), report, output)

    reader = PdfReader(str(output))
    text = reader.pages[0].extract_text()
    assert len(reader.pages) == 1
    assert "Lysenko" in text
    assert "Projektstruktur kennengelernt" in text
    assert "Berlin, 09.08.2026" in text
    assert "Berlin, 03.08.2026" not in text


def test_combined_pdf_keeps_reports_on_separate_pages(tmp_path) -> None:
    output = tmp_path / "berichte.pdf"
    reports = [
        WeeklyReport(
            report_number=1,
            week_start="2026-08-03",
            week_end="2026-08-09",
            report_date="2026-08-07",
            location="Berlin",
            entries=[DailyEntry("2026-08-03", 8, "Eintrag nur erste Woche.")],
        ),
        WeeklyReport(
            report_number=2,
            week_start="2026-08-10",
            week_end="2026-08-16",
            report_date="2026-08-14",
            location="Berlin",
            entries=[DailyEntry("2026-08-10", 8, "Eintrag nur zweite Woche.")],
        ),
    ]

    PdfExporter(__import__("pathlib").Path("assets/formblatt9.pdf")).export_many(Profile(), reports, output)

    reader = PdfReader(str(output))
    first_page = reader.pages[0].extract_text()
    second_page = reader.pages[1].extract_text()
    assert len(reader.pages) == 2
    assert "Eintrag nur erste Woche" in first_page
    assert "Eintrag nur zweite Woche" not in first_page
    assert "Eintrag nur zweite Woche" in second_page
    assert "Eintrag nur erste Woche" not in second_page


def test_pdf_export_does_not_warn_about_unassigned_pages(tmp_path) -> None:
    output = tmp_path / "bericht.pdf"
    report = WeeklyReport(
        report_number=1,
        week_start="2026-08-03",
        week_end="2026-08-09",
        report_date="2026-08-07",
        location="Berlin",
        entries=[DailyEntry("2026-08-03", 8, "PDF-Warnung vermeiden.")],
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        PdfExporter(__import__("pathlib").Path("assets/formblatt9.pdf")).export_week(Profile(), report, output)

    messages = [str(warning.message) for warning in caught]
    assert not any("replace_contents" in message for message in messages)
