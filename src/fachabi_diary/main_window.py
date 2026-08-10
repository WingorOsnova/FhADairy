from __future__ import annotations

import sys
import textwrap
from datetime import datetime, date, timedelta
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QDate, QProcess, QPropertyAnimation, QSize, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QDoubleSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .design import SIDEBAR_WIDTH, WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH
from .icons import blue_icon, lucide_icon
from .models import DailyEntry, Profile, STATUSES, WeeklyReport, serialize_working_days
from .repositories import ProfileRepository, WeeklyReportRepository
from .services.pdf_exporter import PdfExportError, PdfExporter
from .services.report_formatter import GERMAN_WEEKDAYS, format_date, format_hours, has_exportable_activity
from .services.text_assistant import LocalTextAssistant


def _monday_for(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _week_start_for_report(contract_start: str, report_number: int) -> date:
    first_week_start = _monday_for(date.fromisoformat(contract_start))
    return first_week_start + timedelta(days=(report_number - 1) * 7)


def _activity_preview(text: str, line_width: int = 72) -> str:
    text = text.strip()
    if not text:
        return "Noch keine Tätigkeit eingetragen"
    paragraphs = [" ".join(part.split())
                  for part in text.splitlines() if part.strip()]
    lines: list[str] = []
    for paragraph in paragraphs:
        lines.extend(
            textwrap.wrap(
                paragraph,
                width=line_width,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )
    return "\n".join(lines)


def _format_exported_at(value: str) -> str:
    if not value.strip():
        return "Noch nicht erstellt"
    try:
        exported_at = datetime.fromisoformat(value)
    except ValueError:
        return value
    return exported_at.strftime("%d.%m.%Y, %H:%M")


def _open_local_path(path: Path) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _reveal_local_path(path: Path) -> bool:
    if sys.platform == "darwin":
        return QProcess.startDetached("open", ["-R", str(path)])
    if sys.platform.startswith("win"):
        return QProcess.startDetached("explorer", ["/select,", str(path)])
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


def _empty_profile() -> Profile:
    today = date.today()
    return Profile(
        surname="",
        first_name="",
        company_name="",
        company_address="",
        internship_field="",
        contract_start=today.isoformat(),
        contract_end=(today + timedelta(days=365)).isoformat(),
        default_location="",
    )


def _profile_validation_error(profile: Profile) -> str | None:
    required_fields = (
        ("Nachname", profile.surname),
        ("Vorname", profile.first_name),
        ("Praxisstelle", profile.company_name),
        ("Adresse", profile.company_address),
        ("Fachrichtung", profile.internship_field),
        ("Standard-Ort", profile.default_location),
    )
    missing = [label for label, value in required_fields if not value.strip()]
    if missing:
        return "Bitte ausfüllen: " + ", ".join(missing) + "."
    try:
        start = date.fromisoformat(profile.contract_start)
        end = date.fromisoformat(profile.contract_end)
    except ValueError:
        return "Bitte gültige Vertragsdaten eintragen."
    if end < start:
        return "Das Vertragsende darf nicht vor dem Vertragsbeginn liegen."
    return None


class ProfileDialog(QDialog):
    def __init__(self, profile: Profile | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profil einrichten")
        self._profile = profile or _empty_profile()
        self.setMinimumSize(760, 620)
        self.resize(800, 640)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        heading = QLabel("Profil einrichten")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        profile_panel = QFrame()
        profile_panel.setObjectName("panel")
        form = QFormLayout(profile_panel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(16)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.surname = QLineEdit(self._profile.surname)
        self.first_name = QLineEdit(self._profile.first_name)
        self.company_name = QLineEdit(self._profile.company_name)
        self.company_address = QLineEdit(self._profile.company_address)
        self.internship_field = QLineEdit(self._profile.internship_field)
        self.contract_start = QDateEdit(QDate.fromString(
            self._profile.contract_start, "yyyy-MM-dd"))
        self.contract_end = QDateEdit(QDate.fromString(
            self._profile.contract_end, "yyyy-MM-dd"))
        self.default_location = QLineEdit(self._profile.default_location)
        placeholders = (
            (self.surname, "Nachname"),
            (self.first_name, "Vorname"),
            (self.company_name, "Praxisstelle"),
            (self.company_address, "Adresse der Praxisstelle"),
            (self.internship_field, "z. B. Softwareentwicklung / IT"),
            (self.default_location, "z. B. Berlin"),
        )
        for widget, placeholder in placeholders:
            widget.setPlaceholderText(placeholder)
        for widget in (
            self.surname,
            self.first_name,
            self.company_name,
            self.company_address,
            self.internship_field,
            self.contract_start,
            self.contract_end,
            self.default_location,
        ):
            widget.setMinimumHeight(38)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for widget in (self.contract_start, self.contract_end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Nachname", self.surname)
        form.addRow("Vorname", self.first_name)
        form.addRow("Praxisstelle", self.company_name)
        form.addRow("Adresse", self.company_address)
        form.addRow("Fachrichtung", self.internship_field)
        form.addRow("Vertrag von", self.contract_start)
        form.addRow("Vertrag bis", self.contract_end)
        form.addRow("Standard-Ort", self.default_location)
        layout.addWidget(profile_panel)

        working_panel = QFrame()
        working_panel.setObjectName("panel")
        working_layout = QVBoxLayout(working_panel)
        working_layout.setContentsMargins(18, 16, 18, 16)
        working_layout.setSpacing(10)
        working_title = QLabel("Arbeitswoche")
        working_title.setObjectName("sectionLabel")
        checks = QHBoxLayout()
        checks.setSpacing(10)
        self.working_day_checks: list[QCheckBox] = []
        working_days = self._profile.working_day_indexes
        for index, name in enumerate(GERMAN_WEEKDAYS):
            check = QCheckBox(name)
            check.setObjectName("dayCheck")
            check.setChecked(index in working_days)
            check.setMinimumHeight(36)
            check.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.working_day_checks.append(check)
            checks.addWidget(check, 1)
        working_layout.addWidget(working_title)
        working_layout.addLayout(checks)
        layout.addWidget(working_panel)

        buttons = QHBoxLayout()
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        cancel = QPushButton("Abbrechen")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def profile(self) -> Profile:
        return Profile(
            id=self._profile.id,
            surname=self.surname.text().strip(),
            first_name=self.first_name.text().strip(),
            company_name=self.company_name.text().strip(),
            company_address=self.company_address.text().strip(),
            internship_field=self.internship_field.text().strip(),
            contract_start=self.contract_start.date().toString("yyyy-MM-dd"),
            contract_end=self.contract_end.date().toString("yyyy-MM-dd"),
            default_location=self.default_location.text().strip(),
            working_days=serialize_working_days(
                {index for index, check in enumerate(self.working_day_checks) if check.isChecked()}
            ),
        )

    def accept(self) -> None:
        error = _profile_validation_error(self.profile())
        if error:
            QMessageBox.warning(self, "Profil", error)
            return
        super().accept()


class SettingsDialog(QDialog):
    def __init__(self, profile: Profile, template_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self._profile = profile
        self.setMinimumSize(820, 620)
        self.resize(860, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        heading = QLabel("Einstellungen")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        profile_panel = QFrame()
        profile_panel.setObjectName("panel")
        profile_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form = QFormLayout(profile_panel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(16)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.surname = QLineEdit(profile.surname)
        self.first_name = QLineEdit(profile.first_name)
        self.company_name = QLineEdit(profile.company_name)
        self.company_address = QLineEdit(profile.company_address)
        self.internship_field = QLineEdit(profile.internship_field)
        self.contract_start = QDateEdit(
            QDate.fromString(profile.contract_start, "yyyy-MM-dd"))
        self.contract_end = QDateEdit(
            QDate.fromString(profile.contract_end, "yyyy-MM-dd"))
        self.default_location = QLineEdit(profile.default_location)
        for widget in (
            self.surname,
            self.first_name,
            self.company_name,
            self.company_address,
            self.internship_field,
            self.contract_start,
            self.contract_end,
            self.default_location,
        ):
            widget.setMinimumHeight(38)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for widget in (self.contract_start, self.contract_end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Nachname", self.surname)
        form.addRow("Vorname", self.first_name)
        form.addRow("Praxisstelle", self.company_name)
        form.addRow("Adresse", self.company_address)
        form.addRow("Fachrichtung", self.internship_field)
        form.addRow("Vertrag von", self.contract_start)
        form.addRow("Vertrag bis", self.contract_end)
        form.addRow("Standard-Ort", self.default_location)
        layout.addWidget(profile_panel)

        working_panel = QFrame()
        working_panel.setObjectName("panel")
        working_layout = QVBoxLayout(working_panel)
        working_layout.setContentsMargins(18, 16, 18, 16)
        working_layout.setSpacing(10)
        working_title = QLabel("Arbeitswoche")
        working_title.setObjectName("sectionLabel")
        working_hint = QLabel("Markiere die Tage, an denen normalerweise gearbeitet wird.")
        working_hint.setObjectName("mutedLabel")
        working_hint.setWordWrap(True)
        checks = QHBoxLayout()
        checks.setSpacing(10)
        self.working_day_checks: list[QCheckBox] = []
        working_days = profile.working_day_indexes
        for index, name in enumerate(GERMAN_WEEKDAYS):
            check = QCheckBox(name)
            check.setObjectName("dayCheck")
            check.setChecked(index in working_days)
            check.setMinimumHeight(36)
            check.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.working_day_checks.append(check)
            checks.addWidget(check, 1)
        working_layout.addWidget(working_title)
        working_layout.addWidget(working_hint)
        working_layout.addLayout(checks)
        layout.addWidget(working_panel)

        info_panel = QFrame()
        info_panel.setObjectName("panel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.setSpacing(8)
        template_state = "gefunden" if template_path.exists() else "fehlt"
        template_label = QLabel(
            f"PDF-Vorlage: {template_state}\n{template_path}")
        template_label.setObjectName("mutedLabel")
        template_label.setWordWrap(True)
        storage_label = QLabel(
            "Daten werden lokal in SQLite gespeichert. Cloud, Login und Sync sind deaktiviert.")
        storage_label.setObjectName("mutedLabel")
        storage_label.setWordWrap(True)
        info_layout.addWidget(template_label)
        info_layout.addWidget(storage_label)
        layout.addWidget(info_panel)

        buttons = QHBoxLayout()
        cancel = QPushButton("Abbrechen")
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def profile(self) -> Profile:
        return Profile(
            id=self._profile.id,
            surname=self.surname.text().strip(),
            first_name=self.first_name.text().strip(),
            company_name=self.company_name.text().strip(),
            company_address=self.company_address.text().strip(),
            internship_field=self.internship_field.text().strip(),
            contract_start=self.contract_start.date().toString("yyyy-MM-dd"),
            contract_end=self.contract_end.date().toString("yyyy-MM-dd"),
            default_location=self.default_location.text().strip(),
            working_days=serialize_working_days(
                {index for index, check in enumerate(self.working_day_checks) if check.isChecked()}
            ),
        )

    def accept(self) -> None:
        error = _profile_validation_error(self.profile())
        if error:
            QMessageBox.warning(self, "Einstellungen", error)
            return
        super().accept()


class ExportResultDialog(QDialog):
    def __init__(self, output_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.output_path = output_path
        self.setWindowTitle("PDF erstellt")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setObjectName("exportResultIcon")
        icon.setPixmap(blue_icon("file-text", 28).pixmap(28, 28))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(48, 48)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("PDF erstellt")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(output_path.name)
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addWidget(icon)
        header.addLayout(title_box, 1)
        layout.addLayout(header)

        path_label = QLabel(str(output_path))
        path_label.setObjectName("exportPathLabel")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        buttons = QHBoxLayout()
        close = QPushButton("Schließen")
        reveal = QPushButton("Im Finder anzeigen" if sys.platform == "darwin" else "Im Ordner anzeigen")
        reveal.setIcon(lucide_icon("folder-open"))
        open_pdf = QPushButton("Öffnen")
        open_pdf.setObjectName("primaryButton")
        open_pdf.setIcon(lucide_icon("external-link", "#FFFFFF"))
        close.clicked.connect(self.reject)
        reveal.clicked.connect(self.reveal_file)
        open_pdf.clicked.connect(self.open_file)
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(reveal)
        buttons.addWidget(open_pdf)
        layout.addLayout(buttons)

    def open_file(self) -> None:
        if not _open_local_path(self.output_path):
            QMessageBox.warning(self, "PDF", "Die PDF-Datei konnte nicht geöffnet werden.")

    def reveal_file(self) -> None:
        if not _reveal_local_path(self.output_path):
            QMessageBox.warning(self, "PDF", "Der Speicherort konnte nicht geöffnet werden.")


class ReportDetailsDialog(QDialog):
    def __init__(self, report: WeeklyReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Berichtsdaten bearbeiten")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Berichtsdaten")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        form = QFormLayout()
        form.setSpacing(12)
        self.number = QSpinBox()
        self.number.setRange(1, 999)
        self.number.setValue(report.report_number)
        self.week_start = QDateEdit(
            QDate.fromString(report.week_start, "yyyy-MM-dd"))
        self.week_end = QDateEdit(
            QDate.fromString(report.week_end, "yyyy-MM-dd"))
        self.report_date = QDateEdit(
            QDate.fromString(report.report_date, "yyyy-MM-dd"))
        for widget in (self.week_start, self.week_end, self.report_date):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
        self.location = QLineEdit(report.location)
        self.status = QLineEdit(report.status)
        form.addRow("Bericht Nr.", self.number)
        form.addRow("Zeitraum von", self.week_start)
        form.addRow("Zeitraum bis", self.week_end)
        form.addRow("Ort", self.location)
        form.addRow("Datum", self.report_date)
        form.addRow("Status", self.status)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        cancel = QPushButton("Abbrechen")
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def apply_to(self, report: WeeklyReport) -> WeeklyReport:
        report.report_number = self.number.value()
        report.week_start = self.week_start.date().toString("yyyy-MM-dd")
        report.week_end = self.week_end.date().toString("yyyy-MM-dd")
        report.report_date = self.report_date.date().toString("yyyy-MM-dd")
        report.location = self.location.text().strip() or "Berlin"
        report.status = self.status.text().strip(
        ) if self.status.text().strip() in STATUSES else report.status
        return report


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str = "", icon_name: str = "file-text") -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        self.setMinimumSize(160, 112)
        self.setMaximumHeight(112)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 13)
        layout.setSpacing(10)
        header = QHBoxLayout()
        header.setSpacing(9)
        marker = QLabel()
        marker.setPixmap(blue_icon(icon_name, 19).pixmap(19, 19))
        marker.setObjectName("cardIconBox")
        marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        marker.setFixedSize(30, 30)
        label = QLabel(title)
        label.setObjectName("cardTitle")
        label.setWordWrap(True)
        header.addWidget(marker)
        header.addWidget(label, 1)
        self.value = QLabel(value)
        self.value.setObjectName("cardValue")
        self.value.setWordWrap(True)
        self.value.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)
        layout.addStretch()
        layout.addWidget(self.value)


class HoverLiftButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setColor(QColor(10, 102, 255, 70))
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)
        self._blur_animation = QPropertyAnimation(
            self._shadow, b"blurRadius", self)
        self._offset_animation = QPropertyAnimation(
            self._shadow, b"yOffset", self)
        for animation in (self._blur_animation, self._offset_animation):
            animation.setDuration(140)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event) -> None:
        self._animate_shadow(18, 4)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_shadow(0, 0)
        super().leaveEvent(event)

    def _animate_shadow(self, blur: float, y_offset: float) -> None:
        self._blur_animation.stop()
        self._offset_animation.stop()
        self._blur_animation.setStartValue(self._shadow.blurRadius())
        self._blur_animation.setEndValue(blur)
        self._offset_animation.setStartValue(self._shadow.yOffset())
        self._offset_animation.setEndValue(y_offset)
        self._blur_animation.start()
        self._offset_animation.start()


class StatusChip(QLabel):
    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.setObjectName("statusChip")
        self.setProperty("status", status)


class ReportListItem(QFrame):
    selected = Signal(int)

    def __init__(self, report: WeeklyReport, active: bool = False) -> None:
        super().__init__()
        self.report = report
        self.setObjectName("reportListItem")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(92)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        self.stripe = QFrame()
        self.stripe.setObjectName("selectedStripe")
        self.stripe.setFixedWidth(3)
        body = QVBoxLayout()
        body.setSpacing(5)
        self.title = QLabel(f"Bericht Nr. {report.report_number}")
        self.title.setObjectName("reportItemTitle")
        period = QLabel(
            f"{format_date(report.week_start)} - {format_date(report.week_end)}")
        period.setObjectName("mutedLabel")
        chip = StatusChip(report.status)
        body.addWidget(self.title)
        body.addWidget(period)
        body.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.stripe)
        layout.addLayout(body, 1)
        self.set_active(active)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.report.id is not None:
            self.selected.emit(self.report.id)
        super().mousePressEvent(event)

    def set_active(self, active: bool) -> None:
        for widget in (self, self.stripe, self.title):
            widget.setProperty("active", active)
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class DayEntryDialog(QDialog):
    def __init__(self, entry: DailyEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tagesnotiz bearbeiten")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setSpacing(12)
        self.date_edit = QDateEdit(
            QDate.fromString(entry.entry_date, "yyyy-MM-dd"))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.hours = QDoubleSpinBox()
        self.hours.setRange(0, 24)
        self.hours.setDecimals(2)
        self.hours.setSingleStep(0.5)
        self.hours.setSuffix(" Std.")
        self.hours.setValue(entry.hours)
        self.activity = QTextEdit(entry.activity_text)
        self.activity.setMinimumHeight(150)
        self.activity.setPlaceholderText("Was hast du an diesem Tag gemacht?")
        form.addRow("Datum", self.date_edit)
        form.addRow("Stunden", self.hours)
        form.addRow("Tätigkeit", self.activity)
        buttons = QHBoxLayout()
        cancel = QPushButton("Abbrechen")
        save = QPushButton("Übernehmen")
        save.setObjectName("primaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def entry(self) -> DailyEntry:
        return DailyEntry(
            entry_date=self.date_edit.date().toString("yyyy-MM-dd"),
            hours=self.hours.value(),
            activity_text=self.activity.toPlainText().strip(),
        )


class DayRow(QFrame):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dayRow")
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Minimum)
        self._entry = DailyEntry(date.today().isoformat())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 12, 16, 12)
        layout.setSpacing(18)
        self.day_label = QLabel("Montag")
        self.day_label.setObjectName("dayName")
        self.date_label = QLabel("01.01.2026")
        self.date_label.setObjectName("mutedLabel")
        date_box = QVBoxLayout()
        date_box.setSpacing(3)
        date_box.addWidget(self.day_label)
        date_box.addWidget(self.date_label)
        date_wrap = QWidget()
        date_wrap.setObjectName("dayDateCell")
        date_wrap.setFixedWidth(128)
        date_wrap.setLayout(date_box)
        self.hours_label = QLabel("0 Std.")
        self.hours_label.setObjectName("hoursValue")
        self.hours_label.setFixedWidth(92)
        self.activity_label = QLabel("Noch keine Tätigkeit eingetragen")
        self.activity_label.setObjectName("activityText")
        self.activity_label.setWordWrap(True)
        self.activity_label.setTextFormat(Qt.TextFormat.PlainText)
        self.activity_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.activity_label.setMinimumWidth(0)
        self.activity_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.edit_button = QPushButton()
        self.edit_button.setObjectName("iconButton")
        self.edit_button.setIcon(lucide_icon("pencil"))
        self.edit_button.setToolTip("Tagesnotiz bearbeiten")
        self.edit_button.setFixedSize(42, 42)
        self.edit_button.clicked.connect(self.edit)
        layout.addWidget(date_wrap)
        layout.addWidget(self.hours_label)
        layout.addWidget(self.activity_label, 1)
        layout.addWidget(self.edit_button)

    def set_entry(self, entry: DailyEntry) -> None:
        self._entry = entry
        self.refresh()

    def entry(self) -> DailyEntry:
        return self._entry

    def edit(self) -> None:
        dialog = DayEntryDialog(self._entry, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._entry = dialog.entry()
            self.refresh()
            self.changed.emit()
            window = self.window()
            if hasattr(window, "_feedback"):
                window._feedback("Tagesnotiz übernommen")

    def refresh(self) -> None:
        day = QDate.fromString(self._entry.entry_date, "yyyy-MM-dd")
        names = ["Montag", "Dienstag", "Mittwoch",
                 "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        self.day_label.setText(names[day.dayOfWeek() - 1])
        self.date_label.setText(day.toString("dd.MM.yyyy"))
        self.hours_label.setText(f"{format_hours(self._entry.hours)} Std.")
        self.activity_label.setText(
            _activity_preview(self._entry.activity_text))
        self.updateGeometry()

    def _update_day_label(self) -> None:
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(
        self,
        profile: Profile,
        profiles: ProfileRepository,
        reports: WeeklyReportRepository,
        template_path: Path,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Fachabi Diary")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.profile = profile
        self.profiles = profiles
        self.reports = reports
        self.template_path = template_path
        self.exporter = PdfExporter(template_path)
        self.text_assistant = LocalTextAssistant()
        self.last_export_path: Path | None = None
        self.current_report: WeeklyReport | None = None
        self.day_rows: list[DayRow] = []
        self._loading_report = False
        self._report_dirty = False
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(900)
        self.autosave_timer.timeout.connect(self._autosave_current)
        self.toast = QLabel(self)
        self.toast.setObjectName("toast")
        self.toast_opacity = QGraphicsOpacityEffect(self.toast)
        self.toast.setGraphicsEffect(self.toast_opacity)
        self.toast_animation = QPropertyAnimation(
            self.toast_opacity, b"opacity", self)
        self.toast_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toast_hide_connected = False
        self.toast.hide()
        self._build_ui()
        self._build_ai_overlay()
        self.refresh_list()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content(), 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(22, 24, 16, 24)
        layout.setSpacing(18)
        logo_row = QHBoxLayout()
        logo = QLabel("FD")
        logo.setObjectName("logoBox")
        logo.setFixedSize(58, 58)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QVBoxLayout()
        title = QLabel("Fachabi Diary")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Praktikumsnachweis")
        subtitle.setObjectName("mutedLabel")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        logo_row.addWidget(logo)
        logo_row.addLayout(brand)
        layout.addLayout(logo_row)
        top_divider = QFrame()
        top_divider.setObjectName("sidebarDivider")
        top_divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(top_divider)
        section = QLabel("Wochenberichte")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)
        self.report_list_scroll = QScrollArea()
        self.report_list_scroll.setObjectName("reportListScroll")
        self.report_list_scroll.setWidgetResizable(True)
        self.report_list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.report_list_widget = QWidget()
        self.report_list_layout = QVBoxLayout(self.report_list_widget)
        self.report_list_layout.setContentsMargins(0, 0, 0, 0)
        self.report_list_layout.setSpacing(8)
        self.report_list_scroll.setWidget(self.report_list_widget)
        layout.addWidget(self.report_list_scroll, 1)
        bottom_divider = QFrame()
        bottom_divider.setObjectName("sidebarDivider")
        bottom_divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(bottom_divider)
        company_card = QFrame()
        company_card.setObjectName("companyFooter")
        company_layout = QHBoxLayout(company_card)
        company_layout.setContentsMargins(14, 12, 14, 12)
        company_layout.setSpacing(10)
        company_icon = QLabel()
        company_icon.setObjectName("companyIcon")
        company_icon.setPixmap(blue_icon("building", 20).pixmap(20, 20))
        company_text = QVBoxLayout()
        company_text.setSpacing(2)
        self.company_footer = QLabel(self.profile.company_name)
        self.company_footer.setObjectName("companyName")
        company_role = QLabel("Praxisstelle")
        company_role.setObjectName("companyRole")
        company_text.addWidget(self.company_footer)
        company_text.addWidget(company_role)
        company_layout.addWidget(company_icon)
        company_layout.addLayout(company_text, 1)
        layout.addWidget(company_card)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_toolbar())
        body = QHBoxLayout()
        body.setContentsMargins(22, 22, 22, 18)
        body.setSpacing(0)
        self.editor_stack = QStackedWidget()
        self.empty_state = self._build_empty_state()
        self.editor_view = self._build_editor()
        self.editor_stack.addWidget(self.empty_state)
        self.editor_stack.addWidget(self.editor_view)
        body.addWidget(self.editor_stack, 1)
        layout.addLayout(body, 1)
        self.action_bar = self._build_action_bar()
        layout.addWidget(self.action_bar)
        return content

    def _build_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(22, 16, 22, 16)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen...")
        self.search.setMinimumWidth(260)
        self.search.setMaximumWidth(620)
        self.search.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search.addAction(lucide_icon("search"),
                              QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self.refresh_list)
        new_button = HoverLiftButton("Neue Woche")
        new_button.setObjectName("primaryButton")
        new_button.setIcon(lucide_icon("plus", "#FFFFFF"))
        new_button.clicked.connect(self.new_week)
        export_all = QPushButton("Export")
        export_all.setIcon(lucide_icon("upload"))
        export_all.clicked.connect(self.export_all)
        settings = QPushButton("Einstellungen")
        settings.setIcon(lucide_icon("settings"))
        settings.clicked.connect(self.edit_profile)
        layout.addWidget(self.search, 1)
        layout.addStretch()
        layout.addWidget(new_button)
        layout.addWidget(export_all)
        layout.addWidget(settings)
        return toolbar

    def _build_empty_state(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("emptyState")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addStretch()
        icon = QLabel()
        icon.setObjectName("emptyIcon")
        icon.setPixmap(blue_icon("file-text", 36).pixmap(36, 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Erstelle eine Woche")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel("Noch kein Wochenbericht vorhanden.")
        text.setObjectName("emptyText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch()
        return wrapper

    def _build_editor(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("editorScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.number_card = SummaryCard("Bericht Nr.", "01", "file-text")
        self.period_card = SummaryCard("Zeitraum", "", "calendar")
        self.hours_card = SummaryCard("Gesamtstunden", "0", "clock")
        self.period_card.value.setWordWrap(False)
        self.number_card.setFixedWidth(160)
        self.period_card.setFixedWidth(320)
        self.hours_card.setFixedWidth(180)
        edit_details = QPushButton("Berichtsdaten")
        edit_details.setObjectName("ghostButton")
        edit_details.setIcon(lucide_icon("pencil"))
        edit_details.setToolTip("Berichtsdaten bearbeiten")
        edit_details.setFixedHeight(42)
        edit_details.setFixedWidth(160)
        edit_details.clicked.connect(self.edit_report_details)
        cards.addWidget(self.number_card)
        cards.addWidget(self.period_card)
        cards.addWidget(self.hours_card)
        cards.addStretch()
        cards.addWidget(edit_details, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(cards)

        self.pdf_panel = QFrame()
        self.pdf_panel.setObjectName("pdfStatusPanel")
        pdf_layout = QHBoxLayout(self.pdf_panel)
        pdf_layout.setContentsMargins(18, 14, 18, 14)
        pdf_layout.setSpacing(14)
        pdf_icon = QLabel()
        pdf_icon.setObjectName("pdfStatusIcon")
        pdf_icon.setPixmap(blue_icon("file-pdf", 22).pixmap(22, 22))
        pdf_text = QVBoxLayout()
        pdf_text.setSpacing(3)
        self.pdf_status_title = QLabel("Letzter Export")
        self.pdf_status_title.setObjectName("sectionLabel")
        self.pdf_status_file = QLabel("Noch kein PDF erstellt")
        self.pdf_status_file.setObjectName("pdfStatusFile")
        self.pdf_status_file.setWordWrap(True)
        self.pdf_status_meta = QLabel("PDF erstellen, um Vorschau-Aktionen zu aktivieren.")
        self.pdf_status_meta.setObjectName("mutedLabel")
        self.pdf_status_meta.setWordWrap(True)
        pdf_text.addWidget(self.pdf_status_title)
        pdf_text.addWidget(self.pdf_status_file)
        pdf_text.addWidget(self.pdf_status_meta)
        self.open_pdf_button = QPushButton("Öffnen")
        self.open_pdf_button.setIcon(lucide_icon("external-link"))
        self.open_pdf_button.clicked.connect(self.open_last_pdf)
        self.reveal_pdf_button = QPushButton("Im Finder")
        self.reveal_pdf_button.setIcon(lucide_icon("folder-open"))
        self.reveal_pdf_button.clicked.connect(self.reveal_last_pdf)
        self.recreate_pdf_button = QPushButton("Neu erstellen")
        self.recreate_pdf_button.setObjectName("primaryButton")
        self.recreate_pdf_button.setIcon(lucide_icon("file-pdf", "#FFFFFF"))
        self.recreate_pdf_button.clicked.connect(self.export_current)
        for button in (self.open_pdf_button, self.reveal_pdf_button, self.recreate_pdf_button):
            button.setFixedHeight(38)
        pdf_layout.addWidget(pdf_icon, 0, Qt.AlignmentFlag.AlignTop)
        pdf_layout.addLayout(pdf_text, 1)
        pdf_layout.addWidget(self.open_pdf_button, 0, Qt.AlignmentFlag.AlignVCenter)
        pdf_layout.addWidget(self.reveal_pdf_button, 0, Qt.AlignmentFlag.AlignVCenter)
        pdf_layout.addWidget(self.recreate_pdf_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.pdf_panel)

        self.number = QSpinBox()
        self.number.setRange(1, 999)
        self.week_start = QDateEdit()
        self.week_end = QDateEdit()
        self.report_date = QDateEdit(QDate.currentDate())
        for widget in (self.week_start, self.week_end, self.report_date):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
            widget.dateChanged.connect(self.update_summary)
            widget.dateChanged.connect(self._mark_dirty)
        self.number.valueChanged.connect(self.update_summary)
        self.number.valueChanged.connect(self._mark_dirty)
        self.location = QLineEdit()
        self.location.textChanged.connect(self.update_summary)
        self.location.textChanged.connect(self._mark_dirty)
        self.status = QLabel("Entwurf")
        self.status.setObjectName("statusPill")

        self.days_panel = QFrame()
        self.days_panel.setObjectName("panel")
        self.days_layout = QVBoxLayout(self.days_panel)
        self.days_layout.setContentsMargins(0, 0, 0, 0)
        self.days_layout.setSpacing(0)
        layout.addWidget(self.days_panel)

        notes_panel = QFrame()
        notes_panel.setObjectName("panel")
        notes_layout = QVBoxLayout(notes_panel)
        notes_layout.setContentsMargins(18, 14, 18, 18)
        label = QLabel("Wochennotiz")
        label.setObjectName("sectionLabel")
        self.notes = QTextEdit()
        self.notes.setFixedHeight(78)
        self.notes.textChanged.connect(self._mark_dirty)
        notes_layout.addWidget(label)
        notes_layout.addWidget(self.notes)
        layout.addWidget(notes_panel)
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_ai_overlay(self) -> None:
        self.ai_button = QPushButton(self)
        self.ai_button.setObjectName("aiFloatingButton")
        self.ai_button.setIcon(lucide_icon("sparkles", "#FFFFFF", 22))
        self.ai_button.setIconSize(QSize(22, 22))
        self.ai_button.setToolTip("KI-Hilfe")
        self.ai_button.setFixedSize(54, 54)
        self.ai_button.clicked.connect(self.toggle_ai_bubble)

        self.ai_bubble = QFrame(self)
        self.ai_bubble.setObjectName("aiBubble")
        self.ai_bubble.setFixedWidth(292)
        bubble_layout = QVBoxLayout(self.ai_bubble)
        bubble_layout.setContentsMargins(18, 18, 18, 18)
        bubble_layout.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(blue_icon("sparkles", 18).pixmap(18, 18))
        title = QLabel("KI-Hilfe")
        title.setObjectName("panelTitle")
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        bubble_layout.addLayout(header)

        text = QLabel("Optionale KI-Unterstützung.")
        text.setObjectName("mutedLabel")
        text.setWordWrap(True)
        bubble_layout.addWidget(text)

        for label, icon_name, callback in (
            ("Tagesnotiz verbessern", "pencil", self.improve_selected_day_note),
            ("Woche zusammenfassen", "list", self.summarize_week_note),
            ("Formeller Text", "file-text", self.formalize_week_text),
        ):
            button = QPushButton(label)
            button.setObjectName("aiActionButton")
            button.setIcon(blue_icon(icon_name))
            button.clicked.connect(callback)
            bubble_layout.addWidget(button)

        self.ai_bubble_opacity = QGraphicsOpacityEffect(self.ai_bubble)
        self.ai_bubble.setGraphicsEffect(self.ai_bubble_opacity)
        self.ai_bubble_animation = QPropertyAnimation(
            self.ai_bubble_opacity, b"opacity", self)
        self.ai_bubble_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.ai_bubble_hide_connected = False
        self.ai_bubble.hide()
        self._position_overlays()

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(22, 14, 22, 14)
        layout.setSpacing(10)
        self.total = QLabel("0 Std.")
        self.total.setObjectName("totalLabel")
        self.total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        save = HoverLiftButton("Speichern")
        save.setObjectName("primaryButton")
        save.setIcon(lucide_icon("save", "#FFFFFF"))
        export = QPushButton("PDF erstellen")
        export.setIcon(lucide_icon("file-pdf"))
        delete = QPushButton("Löschen")
        delete.setObjectName("dangerButton")
        delete.setIcon(lucide_icon("trash", "#D92D20"))
        more = QPushButton("Weitere")
        more.setObjectName("moreButton")
        more.setIcon(lucide_icon("more-horizontal"))
        for button, width in (
            (save, 150),
            (export, 150),
            (delete, 128),
            (more, 132),
        ):
            button.setFixedSize(width, 42)
            button.setSizePolicy(QSizePolicy.Policy.Fixed,
                                 QSizePolicy.Policy.Fixed)
        self.more_menu = QMenu(self)
        self.open_last_pdf_action = QAction("Letzten PDF öffnen", self)
        self.open_last_pdf_action.setIcon(lucide_icon("external-link"))
        self.open_last_pdf_action.triggered.connect(self.open_last_pdf)
        self.reveal_last_pdf_action = QAction(
            "Im Finder anzeigen" if sys.platform == "darwin" else "Im Ordner anzeigen",
            self,
        )
        self.reveal_last_pdf_action.setIcon(lucide_icon("folder-open"))
        self.reveal_last_pdf_action.triggered.connect(self.reveal_last_pdf)
        printed_action = QAction("Gedruckt markieren", self)
        printed_action.setIcon(lucide_icon("printer"))
        printed_action.triggered.connect(lambda: self.mark_status("Gedruckt"))
        signed_action = QAction("Unterschrieben markieren", self)
        signed_action.setIcon(lucide_icon("signature"))
        signed_action.triggered.connect(
            lambda: self.mark_status("Unterschrieben"))
        weekend_action = QAction("Wochenende eintragen", self)
        weekend_action.setIcon(lucide_icon("calendar"))
        weekend_action.triggered.connect(self.fill_weekend_defaults)
        self.more_menu.addAction(self.open_last_pdf_action)
        self.more_menu.addAction(self.reveal_last_pdf_action)
        self.more_menu.addSeparator()
        self.more_menu.addAction(printed_action)
        self.more_menu.addAction(signed_action)
        self.more_menu.addAction(weekend_action)
        more.clicked.connect(lambda: self.more_menu.exec(
            more.mapToGlobal(more.rect().bottomRight())))
        save.clicked.connect(self.save_current)
        export.clicked.connect(self.export_current)
        delete.clicked.connect(self.delete_current)
        layout.addWidget(self.total)
        layout.addStretch()
        for button in (save, export, delete, more):
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        return bar

    def refresh_list(self, selected_id: int | None = None) -> None:
        selected = selected_id
        if isinstance(selected_id, str):
            selected = self.current_report.id if self.current_report else None
        search = self.search.text().strip().lower() if hasattr(self, "search") else ""
        reports = self.reports.list()
        while self.report_list_layout.count():
            item = self.report_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        if not reports:
            self.report_list_layout.addStretch()
            self.current_report = None
            self._show_empty_state()
            return
        self._show_editor_state()
        first_visible_id = None
        for report in reports:
            label = self._report_list_label(report)
            if search and search not in label.lower():
                continue
            if first_visible_id is None:
                first_visible_id = report.id
            active = selected == report.id or (
                selected is None and self.current_report and self.current_report.id == report.id)
            item = ReportListItem(report, active)
            item.selected.connect(self.load_report_by_id)
            self.report_list_layout.addWidget(item)
        self.report_list_layout.addStretch()
        if selected is not None:
            self.load_report_by_id(selected)
        elif self.current_report is None and first_visible_id is not None:
            self.load_report_by_id(first_visible_id)

    def _show_empty_state(self) -> None:
        self.editor_stack.setCurrentWidget(self.empty_state)
        self.action_bar.hide()
        self._update_last_pdf_actions()
        if hasattr(self, "ai_button"):
            self.ai_bubble.hide()
            self.ai_button.hide()

    def _show_editor_state(self) -> None:
        self.editor_stack.setCurrentWidget(self.editor_view)
        self.action_bar.show()
        if hasattr(self, "ai_button"):
            self.ai_button.show()

    def _report_list_label(self, report: WeeklyReport) -> str:
        return f"Bericht Nr. {report.report_number}\n{format_date(report.week_start)} - {format_date(report.week_end)}\n{report.status}"

    def load_report_by_id(self, report_id: int) -> None:
        current_id = self.current_report.id if self.current_report else None
        if current_id == report_id:
            self._set_active_report_item(report_id)
            return
        if not self._save_pending_changes(blocking=True):
            if current_id is not None:
                self._set_active_report_item(current_id)
            return
        self.current_report = self.reports.get(report_id)
        self.show_report(self.current_report)
        self._set_active_report_item(report_id)

    def _set_active_report_item(self, report_id: int) -> None:
        for index in range(self.report_list_layout.count()):
            widget = self.report_list_layout.itemAt(index).widget()
            if isinstance(widget, ReportListItem):
                widget.set_active(widget.report.id == report_id)

    def show_report(self, report: WeeklyReport) -> None:
        self._loading_report = True
        try:
            self.number.setValue(report.report_number)
            self.week_start.setDate(QDate.fromString(
                report.week_start, "yyyy-MM-dd"))
            self.week_end.setDate(QDate.fromString(report.week_end, "yyyy-MM-dd"))
            self.report_date.setDate(QDate.fromString(
                report.report_date, "yyyy-MM-dd"))
            self.location.setText(report.location)
            self.notes.setPlainText(report.general_notes)
            self.status.setText(report.status)
            self._set_day_entries(report)
            self.update_summary()
            self._update_last_pdf_actions()
        finally:
            self._loading_report = False
        self._set_clean()

    def _set_day_entries(self, report: WeeklyReport) -> None:
        while self.days_layout.count():
            item = self.days_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.day_rows = []
        entries = report.entries[:7] or self._empty_week_entries(
            report.week_start)
        for entry in entries[:7]:
            row = DayRow()
            row.set_entry(entry)
            row.changed.connect(self._handle_day_row_changed)
            self.days_layout.addWidget(row)
            self.day_rows.append(row)
        self.days_layout.addStretch()

    def _empty_week_entries(self, week_start: str) -> list[DailyEntry]:
        start = date.fromisoformat(week_start)
        return [
            DailyEntry(date.fromordinal(
                start.toordinal() + offset).isoformat())
            for offset in range(7)
        ]

    def new_week(self) -> None:
        if not self._save_pending_changes(blocking=True):
            return
        report_number = self.reports.next_number()
        start = _week_start_for_report(
            self.profile.contract_start, report_number)
        report = WeeklyReport.new(
            report_number, start, self.profile.default_location)
        self._apply_non_working_defaults(report)
        report_id = self.reports.save(report)
        self.refresh_list(report_id)
        self._confirm("Woche erstellt")

    def _apply_non_working_defaults(self, report: WeeklyReport) -> bool:
        changed = False
        for entry in report.entries:
            weekday = date.fromisoformat(entry.entry_date).weekday()
            if self.profile.is_working_day(weekday) or entry.activity_text.strip():
                continue
            entry.hours = 0
            entry.activity_text = "Wochenende"
            changed = True
        return changed

    def _first_activity_row(self) -> DayRow | None:
        for row in self.day_rows:
            text = row.entry().activity_text.strip()
            if text and text.casefold() != "wochenende":
                return row
        return None

    def improve_selected_day_note(self) -> None:
        if self.current_report is None:
            return
        row = self._first_activity_row()
        if row is None:
            self._feedback("Keine Tagesnotiz")
            return
        entry = row.entry()
        improved = self.text_assistant.improve_activity(entry.activity_text)
        if not improved:
            self._feedback("Keine Tagesnotiz")
            return
        row.set_entry(
            DailyEntry(
                entry_date=entry.entry_date,
                hours=entry.hours,
                activity_text=improved,
                id=entry.id,
                weekly_report_id=entry.weekly_report_id,
            )
        )
        self._handle_day_row_changed()
        self._confirm("Tagesnotiz verbessert")

    def summarize_week_note(self) -> None:
        if self.current_report is None:
            return
        summary = self.text_assistant.summarize_week(self.read_report())
        if not summary:
            self._feedback("Keine Einträge")
            return
        self.notes.setPlainText(summary)
        self._mark_dirty()
        self._confirm("Wochennotiz erstellt")

    def formalize_week_text(self) -> None:
        if self.current_report is None:
            return
        formalized = self.text_assistant.formalize_report(self.read_report())
        changed = False
        for row, entry in zip(self.day_rows, formalized.entries):
            if row.entry().activity_text != entry.activity_text:
                changed = True
            row.set_entry(entry)
        if self.notes.toPlainText().strip() != formalized.general_notes.strip():
            changed = True
        self.notes.setPlainText(formalized.general_notes)
        if changed:
            self._handle_day_row_changed()
        else:
            self.update_summary()
        self._confirm("Text formeller" if changed else "Text geprüft")

    def fill_weekend_defaults(self) -> None:
        if self.current_report is None:
            return
        changed = False
        for row in self.day_rows:
            entry = row.entry()
            weekday = date.fromisoformat(entry.entry_date).weekday()
            if self.profile.is_working_day(weekday) or entry.activity_text.strip():
                continue
            row.set_entry(
                DailyEntry(
                    entry_date=entry.entry_date,
                    hours=0,
                    activity_text="Wochenende",
                    id=entry.id,
                    weekly_report_id=entry.weekly_report_id,
                )
            )
            changed = True
        if changed:
            self._handle_day_row_changed()
        else:
            self.update_summary()
        self._confirm(
            "Wochenende eingetragen" if changed else "Wochenende bereits gesetzt")

    def read_report(self) -> WeeklyReport:
        entries = [row.entry() for row in self.day_rows]
        return WeeklyReport(
            id=self.current_report.id if self.current_report else None,
            report_number=self.number.value(),
            week_start=self.week_start.date().toString("yyyy-MM-dd"),
            week_end=self.week_end.date().toString("yyyy-MM-dd"),
            report_date=self.report_date.date().toString("yyyy-MM-dd"),
            location=self.location.text().strip() or self.profile.default_location,
            general_notes=self.notes.toPlainText().strip(),
            status=self.status.text() if self.status.text() in STATUSES else "Entwurf",
            last_pdf_path=self.current_report.last_pdf_path if self.current_report else "",
            last_pdf_exported_at=self.current_report.last_pdf_exported_at if self.current_report else "",
            entries=entries,
        )

    def validate_report(self, report: WeeklyReport, for_export: bool = False) -> bool:
        if QDate.fromString(report.week_end, "yyyy-MM-dd") < QDate.fromString(report.week_start, "yyyy-MM-dd"):
            QMessageBox.warning(
                self, "Prüfung", "Das Enddatum darf nicht vor dem Startdatum liegen.")
            return False
        if for_export and not has_exportable_activity(report):
            QMessageBox.warning(
                self, "Prüfung", "Für den PDF-Export ist mindestens eine Tätigkeit erforderlich.")
            return False
        if report.total_hours == 0:
            QMessageBox.warning(self, "Prüfung", "Die Wochenstunden sind 0.")
        return True

    def save_current(self, notify: bool = True) -> bool:
        if self.current_report is None:
            return False
        self.autosave_timer.stop()
        try:
            report = self.read_report()
            if not self.validate_report(report):
                return False
            report_id = self.reports.save(report)
            self.current_report = self.reports.get(report_id)
        except Exception as exc:
            self._report_dirty = True
            self._feedback("Speichern fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", str(exc))
            return False
        self._set_clean()
        self.refresh_list(report_id)
        if notify:
            self._confirm("Gespeichert")
        return True

    def _persist_current_report_state(self) -> int | None:
        if self.current_report is None:
            return None
        report = self.read_report()
        report_id = self.reports.save(report)
        self.current_report = self.reports.get(report_id)
        return report_id

    def _handle_day_row_changed(self) -> None:
        self.update_summary()
        self._mark_dirty()

    def _mark_dirty(self, *args) -> None:
        if self._loading_report or self.current_report is None:
            return
        self._report_dirty = True
        self.autosave_timer.start()

    def _set_clean(self) -> None:
        self._report_dirty = False
        self.autosave_timer.stop()

    def _autosave_current(self) -> None:
        self._save_pending_changes(blocking=False)

    def _save_pending_changes(self, blocking: bool = False) -> bool:
        if self.current_report is None or not self._report_dirty:
            return True
        self.autosave_timer.stop()
        try:
            self._persist_current_report_state()
        except Exception as exc:
            self._report_dirty = True
            if blocking:
                QMessageBox.critical(self, "Speichern", str(exc))
            else:
                self._feedback("Autosave fehlgeschlagen")
            return False
        self._set_clean()
        return True

    def export_current(self) -> None:
        if self.current_report is None or not self.save_current(notify=False):
            return
        report = self.reports.get(self.current_report.id)
        if not self.validate_report(report, for_export=True):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF speichern", f"bericht-{report.report_number}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            output_path = Path(path)
            self.exporter.export_week(self.profile, report, output_path)
            self.reports.set_export_result(
                report.id,
                str(output_path),
                self._status_after_export(report.status),
                datetime.now().isoformat(timespec="seconds"),
            )
            self.current_report = self.reports.get(report.id)
            self.show_report(self.current_report)
            self.refresh_list(report.id)
            self._handle_export_success(output_path, "PDF erstellt")
        except PdfExportError as exc:
            self._feedback("PDF fehlgeschlagen")
            QMessageBox.critical(self, "PDF", str(exc))

    def export_all(self) -> None:
        if not self._save_pending_changes(blocking=True):
            return
        reports = [report for report in self.reports.list(
        ) if has_exportable_activity(report)]
        if not reports:
            QMessageBox.warning(
                self, "PDF", "Es gibt keine exportierbaren Berichte.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Alle Berichte speichern", "berichte.pdf", "PDF (*.pdf)")
        if path:
            try:
                output_path = Path(path)
                self.exporter.export_many(self.profile, reports, output_path)
                self._handle_export_success(output_path, "Export erstellt")
            except PdfExportError as exc:
                self._feedback("Export fehlgeschlagen")
                QMessageBox.critical(self, "PDF", str(exc))

    def _handle_export_success(self, output_path: Path, message: str) -> None:
        self.last_export_path = output_path
        self._update_last_pdf_actions()
        self._confirm(message)
        ExportResultDialog(output_path, self).exec()

    def _status_after_export(self, status: str) -> str:
        return "Bereit" if status == "Entwurf" else status

    def _last_pdf_path(self) -> Path | None:
        if self.current_report is None or not self.current_report.last_pdf_path.strip():
            return None
        return Path(self.current_report.last_pdf_path)

    def _update_last_pdf_actions(self) -> None:
        if not hasattr(self, "open_last_pdf_action"):
            return
        path = self._last_pdf_path()
        has_path = path is not None
        file_exists = bool(path and path.exists())
        self.open_last_pdf_action.setVisible(has_path)
        self.reveal_last_pdf_action.setVisible(has_path)
        self.open_last_pdf_action.setEnabled(file_exists)
        self.reveal_last_pdf_action.setEnabled(file_exists)
        self._update_pdf_status_panel()

    def _update_pdf_status_panel(self) -> None:
        if not hasattr(self, "pdf_status_file"):
            return
        path = self._last_pdf_path()
        if self.current_report is None or path is None:
            self.pdf_status_file.setText("Noch kein PDF erstellt")
            self.pdf_status_meta.setText("PDF erstellen, um Vorschau-Aktionen zu aktivieren.")
            self.open_pdf_button.setEnabled(False)
            self.reveal_pdf_button.setEnabled(False)
            return
        file_exists = path.exists()
        self.pdf_status_file.setText(path.name)
        exported_at = _format_exported_at(self.current_report.last_pdf_exported_at)
        state = "bereit" if file_exists else "Datei nicht gefunden"
        self.pdf_status_meta.setText(f"{exported_at} · {state} · {self.current_report.status}")
        self.open_pdf_button.setEnabled(file_exists)
        self.reveal_pdf_button.setEnabled(file_exists)

    def open_last_pdf(self) -> None:
        path = self._last_pdf_path()
        if path is None:
            self._feedback("Kein PDF")
            return
        if not path.exists():
            self._feedback("PDF nicht gefunden")
            return
        if not _open_local_path(path):
            QMessageBox.warning(self, "PDF", "Die PDF-Datei konnte nicht geöffnet werden.")

    def reveal_last_pdf(self) -> None:
        path = self._last_pdf_path()
        if path is None:
            self._feedback("Kein PDF")
            return
        if not path.exists():
            self._feedback("PDF nicht gefunden")
            return
        if not _reveal_local_path(path):
            QMessageBox.warning(self, "PDF", "Der Speicherort konnte nicht geöffnet werden.")

    def mark_status(self, status: str) -> None:
        if self.current_report is None:
            return
        if not self._save_pending_changes(blocking=True):
            return
        self.reports.set_status(self.current_report.id, status)
        self.current_report = self.reports.get(self.current_report.id)
        self.refresh_list(self.current_report.id)
        self.show_report(self.current_report)
        self._confirm("Status geändert")

    def delete_current(self) -> None:
        if self.current_report is None:
            return
        result = QMessageBox.question(
            self, "Löschen", "Diesen Bericht wirklich löschen?")
        if result == QMessageBox.StandardButton.Yes:
            self._set_clean()
            self.reports.delete(self.current_report.id)
            self.current_report = None
            self.refresh_list()
            self._confirm("Gelöscht")

    def edit_profile(self) -> None:
        dialog = SettingsDialog(self.profile, self.template_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = self.current_report.id if self.current_report else None
            try:
                self.autosave_timer.stop()
                selected_id = self._persist_current_report_state() or selected_id
                self.profile = dialog.profile()
                self.profiles.save(self.profile)
                self.company_footer.setText(self.profile.company_name)
                self._set_clean()
            except Exception as exc:
                self._report_dirty = True
                self._feedback("Einstellungen fehlgeschlagen")
                QMessageBox.critical(self, "Fehler", str(exc))
                return
            self.refresh_list(selected_id)
            self._confirm("Einstellungen gespeichert")

    def edit_report_details(self) -> None:
        if self.current_report is None:
            return
        report = self.read_report()
        dialog = ReportDetailsDialog(report, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.apply_to(report)
        if not self.validate_report(updated):
            return
        report_id = self.reports.save(updated)
        self.current_report = self.reports.get(report_id)
        self._set_clean()
        self.refresh_list(report_id)
        self.show_report(self.current_report)
        self._confirm("Berichtsdaten gespeichert")

    def update_summary(self) -> None:
        total = sum(row.entry().hours for row in self.day_rows)
        self.total.setText(f"{format_hours(total)} Std.")
        self.hours_card.value.setText(f"{format_hours(total)} Std.")
        self.number_card.value.setText(f"{self.number.value():02d}")
        self.period_card.value.setText(
            f"{self.week_start.date().toString('dd.MM.yyyy')} - {self.week_end.date().toString('dd.MM.yyyy')}"
        )

    def _feedback(self, message: str) -> None:
        self.toast.setText(message)
        self.toast.adjustSize()
        margin = 24
        x = self.width() - self.toast.width() - margin
        y = 88
        self.toast.move(max(margin, x), y)
        self.toast.show()
        self.toast.raise_()
        self._animate_toast(0.0, 1.0, 140)
        QTimer.singleShot(1900, lambda: self._animate_toast(
            1.0, 0.0, 260, hide=True))

    def _confirm(self, message: str) -> None:
        self._feedback(message)

    def toggle_ai_bubble(self) -> None:
        if self.ai_bubble.isVisible():
            self._animate_ai_bubble(1.0, 0.0, 140, hide=True)
            return
        self.ai_bubble.adjustSize()
        self._position_overlays()
        self.ai_bubble_opacity.setOpacity(0.0)
        self.ai_bubble.show()
        self.ai_bubble.raise_()
        self.ai_button.raise_()
        self._animate_ai_bubble(0.0, 1.0, 150)

    def _position_overlays(self) -> None:
        if not hasattr(self, "ai_button"):
            return
        margin = 24
        bottom_gap = 94
        button_x = max(SIDEBAR_WIDTH + margin, self.width() -
                       self.ai_button.width() - margin)
        button_y = max(90, self.height() -
                       self.ai_button.height() - bottom_gap)
        self.ai_button.move(button_x, button_y)

        self.ai_bubble.adjustSize()
        bubble_x = max(SIDEBAR_WIDTH + margin, self.width() -
                       self.ai_bubble.width() - margin)
        bubble_y = max(84, button_y - self.ai_bubble.height() - 12)
        self.ai_bubble.move(bubble_x, bubble_y)
        self.ai_button.raise_()
        if self.ai_bubble.isVisible():
            self.ai_bubble.raise_()
            self.ai_button.raise_()

    def _animate_ai_bubble(self, start: float, end: float, duration: int, hide: bool = False) -> None:
        self.ai_bubble_animation.stop()
        self.ai_bubble_animation.setDuration(duration)
        self.ai_bubble_animation.setStartValue(start)
        self.ai_bubble_animation.setEndValue(end)
        if self.ai_bubble_hide_connected:
            self.ai_bubble_animation.finished.disconnect()
            self.ai_bubble_hide_connected = False
        if hide:
            self.ai_bubble_animation.finished.connect(self.ai_bubble.hide)
            self.ai_bubble_hide_connected = True
        self.ai_bubble_animation.start()

    def _animate_toast(self, start: float, end: float, duration: int, hide: bool = False) -> None:
        self.toast_animation.stop()
        self.toast_animation.setDuration(duration)
        self.toast_animation.setStartValue(start)
        self.toast_animation.setEndValue(end)
        if self.toast_hide_connected:
            self.toast_animation.finished.disconnect()
            self.toast_hide_connected = False
        if hide:
            self.toast_animation.finished.connect(self.toast.hide)
            self.toast_hide_connected = True
        self.toast_animation.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_overlays()

    def closeEvent(self, event) -> None:
        if self._save_pending_changes(blocking=True):
            super().closeEvent(event)
            return
        result = QMessageBox.question(
            self,
            "Schließen",
            "Änderungen konnten nicht automatisch gespeichert werden. Trotzdem schließen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            super().closeEvent(event)
        else:
            event.ignore()
