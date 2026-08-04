from __future__ import annotations

from io import BytesIO
from pathlib import Path
from textwrap import wrap

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from fachabi_diary.models import Profile, WeeklyReport
from fachabi_diary.services.report_formatter import format_activity_bullets, format_date


class PdfExportError(RuntimeError):
    pass


class PdfExporter:
    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path

    def export_week(self, profile: Profile, report: WeeklyReport, output_path: Path) -> None:
        self.export_many(profile, [report], output_path)

    def export_many(self, profile: Profile, reports: list[WeeklyReport], output_path: Path) -> None:
        if not self.template_path.exists():
            raise PdfExportError(
                f"PDF-Vorlage fehlt: {self.template_path}. Bitte Formblatt 9 als assets/formblatt9.pdf ablegen."
            )
        writer = PdfWriter()
        template_reader = PdfReader(str(self.template_path))
        for report in reports:
            template_page = template_reader.pages[0]
            page = template_page.clone(writer)
            overlay_reader = PdfReader(self._overlay(profile, report))
            page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            writer.write(handle)

    def _overlay(self, profile: Profile, report: WeeklyReport) -> BytesIO:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 10)
        self._draw(c, profile.surname, 128, 765)
        self._draw(c, profile.first_name, 360, 765)
        self._draw(c, str(report.report_number), 495, 721)
        self._draw(c, format_date(report.week_start), 200, 700)
        self._draw(c, format_date(report.week_end), 360, 700)
        self._draw(c, f"{profile.company_name}, {profile.company_address}", 128, 742, 82)
        self._draw(c, profile.internship_field, 128, 724, 70)
        self._draw_multiline(c, format_activity_bullets(report.entries, report.general_notes), 72, 635, 92, 15)
        self._draw(c, f"{report.location}, {format_date(report.report_date)}", 98, 158, 45)
        c.save()
        buffer.seek(0)
        return buffer

    def _draw(self, c: canvas.Canvas, text: str, x: int, y: int, width: int | None = None) -> None:
        value = text
        if width:
            value = wrap(text, width=width)[0] if text else ""
        c.drawString(x, y, value)

    def _draw_multiline(self, c: canvas.Canvas, text: str, x: int, y: int, width: int, max_lines: int) -> None:
        c.setFont("Helvetica", 9)
        line_no = 0
        for raw_line in text.splitlines():
            for line in wrap(raw_line, width=width) or [""]:
                if line_no >= max_lines:
                    c.drawString(x, y - line_no * 13, "- Weitere Einträge siehe App.")
                    return
                c.drawString(x, y - line_no * 13, line)
                line_no += 1
