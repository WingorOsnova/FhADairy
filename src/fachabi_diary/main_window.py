from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import DailyEntry, Profile, STATUSES, WeeklyReport
from .repositories import ProfileRepository, WeeklyReportRepository
from .services.pdf_exporter import PdfExportError, PdfExporter
from .services.report_formatter import format_date, has_exportable_activity


class ProfileDialog(QDialog):
    def __init__(self, profile: Profile | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profil einrichten")
        self._profile = profile or Profile()
        self.setMinimumWidth(520)
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self.surname = QLineEdit(self._profile.surname)
        self.first_name = QLineEdit(self._profile.first_name)
        self.company_name = QLineEdit(self._profile.company_name)
        self.company_address = QLineEdit(self._profile.company_address)
        self.internship_field = QLineEdit(self._profile.internship_field)
        self.contract_start = QDateEdit(QDate.fromString(self._profile.contract_start, "yyyy-MM-dd"))
        self.contract_end = QDateEdit(QDate.fromString(self._profile.contract_end, "yyyy-MM-dd"))
        self.default_location = QLineEdit(self._profile.default_location)
        for widget in (self.contract_start, self.contract_end):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
        layout.addRow("Nachname", self.surname)
        layout.addRow("Vorname", self.first_name)
        layout.addRow("Praxisstelle", self.company_name)
        layout.addRow("Adresse", self.company_address)
        layout.addRow("Bereich", self.internship_field)
        layout.addRow("Vertrag von", self.contract_start)
        layout.addRow("Vertrag bis", self.contract_end)
        layout.addRow("Standard-Ort", self.default_location)
        buttons = QHBoxLayout()
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        cancel = QPushButton("Abbrechen")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addRow(buttons)

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
            default_location=self.default_location.text().strip() or "Berlin",
        )


class SettingsDialog(QDialog):
    def __init__(self, profile: Profile, template_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self._profile = profile
        self.setMinimumWidth(680)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(18)

        heading = QLabel("Einstellungen")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        profile_panel = QFrame()
        profile_panel.setObjectName("panel")
        form = QFormLayout(profile_panel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)
        self.surname = QLineEdit(profile.surname)
        self.first_name = QLineEdit(profile.first_name)
        self.company_name = QLineEdit(profile.company_name)
        self.company_address = QLineEdit(profile.company_address)
        self.internship_field = QLineEdit(profile.internship_field)
        self.contract_start = QDateEdit(QDate.fromString(profile.contract_start, "yyyy-MM-dd"))
        self.contract_end = QDateEdit(QDate.fromString(profile.contract_end, "yyyy-MM-dd"))
        self.default_location = QLineEdit(profile.default_location)
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

        info_panel = QFrame()
        info_panel.setObjectName("panel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.setSpacing(8)
        template_state = "gefunden" if template_path.exists() else "fehlt"
        template_label = QLabel(f"PDF-Vorlage: {template_state}\n{template_path}")
        template_label.setObjectName("mutedLabel")
        template_label.setWordWrap(True)
        storage_label = QLabel("Daten werden lokal in SQLite gespeichert. Cloud, Login und Sync sind deaktiviert.")
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
            default_location=self.default_location.text().strip() or "Berlin",
        )


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str = "", accent: str = "") -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        marker = QLabel(accent)
        marker.setObjectName("cardMarker")
        label = QLabel(title)
        label.setObjectName("mutedLabel")
        self.value = QLabel(value)
        self.value.setObjectName("cardValue")
        self.value.setWordWrap(True)
        layout.addWidget(marker)
        layout.addSpacing(18)
        layout.addWidget(label)
        layout.addWidget(self.value)


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
        self.date_edit = QDateEdit(QDate.fromString(entry.entry_date, "yyyy-MM-dd"))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.hours = QDoubleSpinBox()
        self.hours.setRange(0, 24)
        self.hours.setDecimals(2)
        self.hours.setSingleStep(0.5)
        self.hours.setSuffix(" h")
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
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dayRow")
        self._entry = DailyEntry(date.today().isoformat())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 13, 18, 13)
        layout.setSpacing(16)
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
        date_wrap.setFixedWidth(118)
        date_wrap.setLayout(date_box)
        self.hours_label = QLabel("0 h")
        self.hours_label.setObjectName("hoursValue")
        self.hours_label.setFixedWidth(76)
        self.activity_label = QLabel("Noch keine Tätigkeit eingetragen")
        self.activity_label.setObjectName("activityText")
        self.activity_label.setWordWrap(True)
        self.edit_button = QPushButton("Bearbeiten")
        self.edit_button.setObjectName("iconButton")
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
            window = self.window()
            if hasattr(window, "update_summary"):
                window.update_summary()
            if hasattr(window, "_feedback"):
                window._feedback("Tagesnotiz übernommen")

    def refresh(self) -> None:
        day = QDate.fromString(self._entry.entry_date, "yyyy-MM-dd")
        names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        self.day_label.setText(names[day.dayOfWeek() - 1])
        self.date_label.setText(day.toString("dd.MM.yyyy"))
        self.hours_label.setText(f"{self._entry.hours:g} h")
        text = self._entry.activity_text.strip() or "Noch keine Tätigkeit eingetragen"
        self.activity_label.setText(text)

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
        self.profile = profile
        self.profiles = profiles
        self.reports = reports
        self.template_path = template_path
        self.exporter = PdfExporter(template_path)
        self.current_report: WeeklyReport | None = None
        self.day_rows: list[DayRow] = []
        self._build_ui()
        self.statusBar().showMessage("Bereit")
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
        sidebar.setFixedWidth(280)
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
        section = QLabel("Wochenberichte")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("weekList")
        self.list_widget.currentItemChanged.connect(self.load_selected)
        layout.addWidget(self.list_widget, 1)
        self.company_footer = QLabel(f"{self.profile.company_name}\nPraxisstelle")
        self.company_footer.setObjectName("companyFooter")
        layout.addWidget(self.company_footer)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_toolbar())
        body = QHBoxLayout()
        body.setContentsMargins(22, 22, 22, 18)
        body.setSpacing(22)
        body.addWidget(self._build_editor(), 1)
        body.addWidget(self._build_right_panel())
        layout.addLayout(body, 1)
        layout.addWidget(self._build_action_bar())
        return content

    def _build_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(22, 16, 22, 16)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen...")
        self.search.setFixedWidth(320)
        self.search.textChanged.connect(self.refresh_list)
        new_button = QPushButton("+  Neue Woche")
        new_button.setObjectName("primaryButton")
        new_button.clicked.connect(self.new_week)
        export_all = QPushButton("Export")
        export_all.clicked.connect(self.export_all)
        settings = QPushButton("Einstellungen")
        settings.clicked.connect(self.edit_profile)
        layout.addWidget(self.search)
        layout.addStretch()
        layout.addWidget(new_button)
        layout.addWidget(export_all)
        layout.addWidget(settings)
        return toolbar

    def _build_editor(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("editorScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.number_card = SummaryCard("Bericht Nr.", "01", "Bericht")
        self.period_card = SummaryCard("Zeitraum", "", "Woche")
        self.company_card = SummaryCard("Praxisstelle", self.profile.company_name, "Firma")
        self.field_card = SummaryCard("Fachrichtung", self.profile.internship_field, "Bereich")
        self.hours_card = SummaryCard("Gesamtstunden", "0", "Stunden")
        for card in (self.number_card, self.period_card, self.company_card, self.field_card, self.hours_card):
            cards.addWidget(card)
        layout.addLayout(cards)

        meta = QFrame()
        meta.setObjectName("panel")
        grid = QGridLayout(meta)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setSpacing(12)
        self.number = QSpinBox()
        self.number.setRange(1, 999)
        self.week_start = QDateEdit()
        self.week_end = QDateEdit()
        self.report_date = QDateEdit(QDate.currentDate())
        for widget in (self.week_start, self.week_end, self.report_date):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
            widget.dateChanged.connect(self.update_summary)
        self.number.valueChanged.connect(self.update_summary)
        self.location = QLineEdit()
        self.location.textChanged.connect(self.update_summary)
        self.status = QLabel("Entwurf")
        self.status.setObjectName("statusPill")
        grid.addWidget(QLabel("Nr."), 0, 0)
        grid.addWidget(self.number, 0, 1)
        grid.addWidget(QLabel("Von"), 0, 2)
        grid.addWidget(self.week_start, 0, 3)
        grid.addWidget(QLabel("Bis"), 0, 4)
        grid.addWidget(self.week_end, 0, 5)
        grid.addWidget(QLabel("Ort"), 1, 0)
        grid.addWidget(self.location, 1, 1, 1, 3)
        grid.addWidget(QLabel("Datum"), 1, 4)
        grid.addWidget(self.report_date, 1, 5)
        grid.addWidget(self.status, 0, 6, 2, 1)
        layout.addWidget(meta)

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
        notes_layout.addWidget(label)
        notes_layout.addWidget(self.notes)
        layout.addWidget(notes_panel)
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(270)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        ai = QFrame()
        ai.setObjectName("bluePanel")
        ai_layout = QVBoxLayout(ai)
        ai_layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("KI-Hilfe")
        title.setObjectName("panelTitle")
        text = QLabel("Optionale Textvorschläge kommen später. Offizielle Exporte nutzen nur bestätigte Einträge.")
        text.setObjectName("mutedLabel")
        text.setWordWrap(True)
        ai_layout.addWidget(title)
        ai_layout.addWidget(text)
        for label in ("Tagesnotiz verbessern", "Woche zusammenfassen", "Formeller Text"):
            button = QPushButton(label)
            button.setEnabled(False)
            ai_layout.addWidget(button)
        layout.addWidget(ai)
        preview = QFrame()
        preview.setObjectName("panel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_title = QLabel("Formblatt 9")
        preview_title.setObjectName("panelTitle")
        self.preview_info = QLabel("PDF-Vorschau nach Export")
        self.preview_info.setObjectName("pdfPreview")
        self.preview_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_info.setWordWrap(True)
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.preview_info, 1)
        layout.addWidget(preview, 1)
        return panel

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(22, 16, 22, 16)
        self.total = QLabel("0 Std.")
        self.total.setObjectName("totalLabel")
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        export = QPushButton("PDF erstellen")
        printed = QPushButton("Als gedruckt markieren")
        signed = QPushButton("Als unterschrieben markieren")
        delete = QPushButton("Löschen")
        save.clicked.connect(self.save_current)
        export.clicked.connect(self.export_current)
        printed.clicked.connect(lambda: self.mark_status("Gedruckt"))
        signed.clicked.connect(lambda: self.mark_status("Unterschrieben"))
        delete.clicked.connect(self.delete_current)
        layout.addWidget(self.total)
        layout.addStretch()
        for button in (save, export, printed, signed, delete):
            layout.addWidget(button)
        return bar

    def refresh_list(self, selected_id: int | None = None) -> None:
        selected = selected_id
        if isinstance(selected_id, str):
            selected = self.current_report.id if self.current_report else None
        search = self.search.text().strip().lower() if hasattr(self, "search") else ""
        self.list_widget.clear()
        for report in self.reports.list():
            label = self._report_list_label(report)
            if search and search not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, report.id)
            self.list_widget.addItem(item)
            if selected == report.id:
                self.list_widget.setCurrentItem(item)
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def _report_list_label(self, report: WeeklyReport) -> str:
        week = QDate.fromString(report.week_start, "yyyy-MM-dd").weekNumber()[0]
        return f"KW {week}  |  Nr. {report.report_number}\n{format_date(report.week_start)} - {format_date(report.week_end)}\n{report.status}"

    def load_selected(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        self.current_report = self.reports.get(int(item.data(Qt.ItemDataRole.UserRole)))
        self.show_report(self.current_report)

    def show_report(self, report: WeeklyReport) -> None:
        self.number.setValue(report.report_number)
        self.week_start.setDate(QDate.fromString(report.week_start, "yyyy-MM-dd"))
        self.week_end.setDate(QDate.fromString(report.week_end, "yyyy-MM-dd"))
        self.report_date.setDate(QDate.fromString(report.report_date, "yyyy-MM-dd"))
        self.location.setText(report.location)
        self.notes.setPlainText(report.general_notes)
        self.status.setText(report.status)
        self._set_day_entries(report)
        self.update_summary()

    def _set_day_entries(self, report: WeeklyReport) -> None:
        while self.days_layout.count():
            item = self.days_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.day_rows = []
        entries = report.entries[:7] or self._empty_week_entries(report.week_start)
        for entry in entries[:7]:
            row = DayRow()
            row.set_entry(entry)
            self.days_layout.addWidget(row)
            self.day_rows.append(row)
        self.days_layout.addStretch()

    def _empty_week_entries(self, week_start: str) -> list[DailyEntry]:
        start = date.fromisoformat(week_start)
        return [
            DailyEntry(date.fromordinal(start.toordinal() + offset).isoformat())
            for offset in range(7)
        ]

    def new_week(self) -> None:
        existing = self.reports.list()
        if existing:
            last_end = date.fromisoformat(existing[-1].week_end)
            start = last_end + timedelta(days=1)
        else:
            start = date.today() - timedelta(days=date.today().weekday())
        report = WeeklyReport.new(self.reports.next_number(), start, self.profile.default_location)
        report_id = self.reports.save(report)
        self.refresh_list(report_id)
        self._confirm("Woche erstellt")

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
            entries=entries,
        )

    def validate_report(self, report: WeeklyReport, for_export: bool = False) -> bool:
        if QDate.fromString(report.week_end, "yyyy-MM-dd") < QDate.fromString(report.week_start, "yyyy-MM-dd"):
            QMessageBox.warning(self, "Prüfung", "Das Enddatum darf nicht vor dem Startdatum liegen.")
            return False
        if for_export and not has_exportable_activity(report):
            QMessageBox.warning(self, "Prüfung", "Für den PDF-Export ist mindestens eine Tätigkeit erforderlich.")
            return False
        if report.total_hours == 0:
            QMessageBox.warning(self, "Prüfung", "Die Wochenstunden sind 0.")
        return True

    def save_current(self, notify: bool = True) -> bool:
        if self.current_report is None:
            return False
        try:
            report = self.read_report()
            if not self.validate_report(report):
                return False
            report_id = self.reports.save(report)
            self.current_report = self.reports.get(report_id)
        except Exception as exc:
            self._feedback("Speichern fehlgeschlagen")
            QMessageBox.critical(self, "Fehler", str(exc))
            return False
        self.refresh_list(report_id)
        if notify:
            self._confirm("Gespeichert")
        return True

    def export_current(self) -> None:
        if self.current_report is None or not self.save_current(notify=False):
            return
        report = self.reports.get(self.current_report.id)
        if not self.validate_report(report, for_export=True):
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", f"bericht-{report.report_number}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            self.exporter.export_week(self.profile, report, Path(path))
            self.preview_info.setText(f"Erstellt:\n{Path(path).name}")
            self._feedback("PDF erstellt")
            QMessageBox.information(self, "PDF", "PDF wurde erstellt.")
        except PdfExportError as exc:
            self._feedback("PDF fehlgeschlagen")
            QMessageBox.critical(self, "PDF", str(exc))

    def export_all(self) -> None:
        reports = [report for report in self.reports.list() if has_exportable_activity(report)]
        if not reports:
            QMessageBox.warning(self, "PDF", "Es gibt keine exportierbaren Berichte.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Alle Berichte speichern", "berichte.pdf", "PDF (*.pdf)")
        if path:
            self.exporter.export_many(self.profile, reports, Path(path))
            self.preview_info.setText(f"Gesamtexport:\n{Path(path).name}")
            self._feedback("Export erstellt")
            QMessageBox.information(self, "PDF", "PDF wurde erstellt.")

    def mark_status(self, status: str) -> None:
        if self.current_report is None:
            return
        self.reports.set_status(self.current_report.id, status)
        self.current_report = self.reports.get(self.current_report.id)
        self.refresh_list(self.current_report.id)
        self.show_report(self.current_report)
        self._confirm("Status geändert")

    def delete_current(self) -> None:
        if self.current_report is None:
            return
        result = QMessageBox.question(self, "Löschen", "Diesen Bericht wirklich löschen?")
        if result == QMessageBox.StandardButton.Yes:
            self.reports.delete(self.current_report.id)
            self.current_report = None
            self.refresh_list()
            self._confirm("Gelöscht")

    def edit_profile(self) -> None:
        dialog = SettingsDialog(self.profile, self.template_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.profile = dialog.profile()
            self.profiles.save(self.profile)
            self.company_card.value.setText(self.profile.company_name)
            self.field_card.value.setText(self.profile.internship_field)
            self.company_footer.setText(f"{self.profile.company_name}\nPraxisstelle")
            self.refresh_list(self.current_report.id if self.current_report else None)
            self._confirm("Einstellungen gespeichert")

    def update_summary(self) -> None:
        total = sum(row.entry().hours for row in self.day_rows)
        self.total.setText(f"{total:g} Std.")
        self.hours_card.value.setText(f"{total:g}")
        self.number_card.value.setText(f"{self.number.value():02d}")
        self.period_card.value.setText(
            f"{self.week_start.date().toString('dd.MM.yyyy')} -\n{self.week_end.date().toString('dd.MM.yyyy')}"
        )

    def _feedback(self, message: str) -> None:
        self.statusBar().showMessage(message, 3500)

    def _confirm(self, message: str) -> None:
        self._feedback(message)
        QMessageBox.information(self, "Bestätigung", message)
