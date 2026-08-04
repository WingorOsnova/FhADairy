from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import DailyEntry, Profile, STATUSES, WeeklyReport
from .repositories import ProfileRepository, WeeklyReportRepository
from .services.pdf_exporter import PdfExporter, PdfExportError
from .services.report_formatter import has_exportable_activity


class ProfileDialog(QDialog):
    def __init__(self, profile: Profile | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Profil einrichten")
        self._profile = profile or Profile()
        layout = QFormLayout(self)
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
            surname=self.surname.text().strip(),
            first_name=self.first_name.text().strip(),
            company_name=self.company_name.text().strip(),
            company_address=self.company_address.text().strip(),
            internship_field=self.internship_field.text().strip(),
            contract_start=self.contract_start.date().toString("yyyy-MM-dd"),
            contract_end=self.contract_end.date().toString("yyyy-MM-dd"),
            default_location=self.default_location.text().strip() or "Berlin",
        )


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
        self.exporter = PdfExporter(template_path)
        self.current_report: WeeklyReport | None = None
        self._build_ui()
        self.refresh_list()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        sidebar = QVBoxLayout()
        title = QLabel("Berichte")
        title.setStyleSheet("font-size: 22px; font-weight: 650;")
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentItemChanged.connect(self.load_selected)
        new_button = QPushButton("Neue Woche")
        new_button.setObjectName("primaryButton")
        new_button.clicked.connect(self.new_week)
        sidebar.addWidget(title)
        sidebar.addWidget(self.list_widget, 1)
        sidebar.addWidget(new_button)
        layout.addLayout(sidebar, 1)

        editor = QVBoxLayout()
        top = QGroupBox("Wochenbericht")
        grid = QGridLayout(top)
        self.number = QSpinBox()
        self.number.setRange(1, 999)
        self.week_start = QDateEdit()
        self.week_end = QDateEdit()
        self.report_date = QDateEdit(QDate.currentDate())
        for widget in (self.week_start, self.week_end, self.report_date):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("dd.MM.yyyy")
        self.location = QLineEdit()
        self.status = QLabel("Entwurf")
        grid.addWidget(QLabel("Nr."), 0, 0)
        grid.addWidget(self.number, 0, 1)
        grid.addWidget(QLabel("Von"), 0, 2)
        grid.addWidget(self.week_start, 0, 3)
        grid.addWidget(QLabel("Bis"), 0, 4)
        grid.addWidget(self.week_end, 0, 5)
        grid.addWidget(QLabel("Ort"), 1, 0)
        grid.addWidget(self.location, 1, 1, 1, 2)
        grid.addWidget(QLabel("Datum"), 1, 3)
        grid.addWidget(self.report_date, 1, 4)
        grid.addWidget(self.status, 1, 5)
        editor.addWidget(top)

        self.table = QTableWidget(7, 3)
        self.table.setHorizontalHeaderLabels(["Datum", "Stunden", "Tätigkeiten"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.update_total)
        editor.addWidget(self.table, 1)
        notes_box = QGroupBox("Wochennotiz")
        notes_layout = QVBoxLayout(notes_box)
        self.notes = QTextEdit()
        self.notes.setFixedHeight(70)
        notes_layout.addWidget(self.notes)
        editor.addWidget(notes_box)
        bottom = QHBoxLayout()
        self.total = QLabel("0 Std.")
        save = QPushButton("Speichern")
        save.setObjectName("primaryButton")
        export = QPushButton("PDF erstellen")
        export_all = QPushButton("Alle als PDF")
        printed = QPushButton("Als gedruckt markieren")
        signed = QPushButton("Als unterschrieben markieren")
        delete = QPushButton("Löschen")
        save.clicked.connect(self.save_current)
        export.clicked.connect(self.export_current)
        export_all.clicked.connect(self.export_all)
        printed.clicked.connect(lambda: self.mark_status("Gedruckt"))
        signed.clicked.connect(lambda: self.mark_status("Unterschrieben"))
        delete.clicked.connect(self.delete_current)
        bottom.addWidget(self.total)
        bottom.addStretch()
        for button in (save, export, export_all, printed, signed, delete):
            bottom.addWidget(button)
        editor.addLayout(bottom)
        layout.addLayout(editor, 4)
        self.setCentralWidget(root)

    def refresh_list(self, selected_id: int | None = None) -> None:
        self.list_widget.clear()
        for report in self.reports.list():
            item = QListWidgetItem(f"Nr. {report.report_number} | {report.week_start} | {report.status}")
            item.setData(Qt.ItemDataRole.UserRole, report.id)
            self.list_widget.addItem(item)
            if selected_id == report.id:
                self.list_widget.setCurrentItem(item)
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

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
        self.table.blockSignals(True)
        self.table.setRowCount(7)
        for row, entry in enumerate(report.entries[:7]):
            self.table.setItem(row, 0, QTableWidgetItem(entry.entry_date))
            hours = QTableWidgetItem(str(entry.hours).rstrip("0").rstrip("."))
            self.table.setItem(row, 1, hours)
            self.table.setItem(row, 2, QTableWidgetItem(entry.activity_text))
        self.table.blockSignals(False)
        self.update_total()

    def new_week(self) -> None:
        start = date.today() - timedelta(days=date.today().weekday())
        report = WeeklyReport.new(self.reports.next_number(), start, self.profile.default_location)
        report_id = self.reports.save(report)
        self.refresh_list(report_id)

    def read_report(self) -> WeeklyReport:
        entries = []
        for row in range(self.table.rowCount()):
            date_item = self.table.item(row, 0)
            hours_item = self.table.item(row, 1)
            text_item = self.table.item(row, 2)
            entry_date = (date_item.text() if date_item else "").strip()
            hours_text = (hours_item.text() if hours_item else "0").strip().replace(",", ".")
            entries.append(DailyEntry(entry_date=entry_date, hours=float(hours_text or 0), activity_text=(text_item.text() if text_item else "")))
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

    def save_current(self) -> bool:
        if self.current_report is None:
            return False
        try:
            report = self.read_report()
            if not self.validate_report(report):
                return False
            report_id = self.reports.save(report)
        except ValueError:
            QMessageBox.warning(self, "Fehler", "Bitte Stunden als Zahl eingeben.")
            return False
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))
            return False
        self.refresh_list(report_id)
        return True

    def export_current(self) -> None:
        if self.current_report is None or not self.save_current():
            return
        report = self.reports.get(self.current_report.id)
        if not self.validate_report(report, for_export=True):
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", f"bericht-{report.report_number}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            self.exporter.export_week(self.profile, report, Path(path))
            QMessageBox.information(self, "PDF", "PDF wurde erstellt.")
        except PdfExportError as exc:
            QMessageBox.critical(self, "PDF", str(exc))

    def export_all(self) -> None:
        reports = [r for r in self.reports.list() if has_exportable_activity(r)]
        if not reports:
            QMessageBox.warning(self, "PDF", "Es gibt keine exportierbaren Berichte.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Alle Berichte speichern", "berichte.pdf", "PDF (*.pdf)")
        if path:
            self.exporter.export_many(self.profile, reports, Path(path))
            QMessageBox.information(self, "PDF", "PDF wurde erstellt.")

    def mark_status(self, status: str) -> None:
        if self.current_report is None:
            return
        self.reports.set_status(self.current_report.id, status)
        self.refresh_list(self.current_report.id)

    def delete_current(self) -> None:
        if self.current_report is None:
            return
        result = QMessageBox.question(self, "Löschen", "Diesen Bericht wirklich löschen?")
        if result == QMessageBox.StandardButton.Yes:
            self.reports.delete(self.current_report.id)
            self.current_report = None
            self.refresh_list()

    def update_total(self) -> None:
        total = 0.0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                try:
                    total += float(item.text().replace(",", ".") or 0)
                except ValueError:
                    pass
        self.total.setText(f"{total:g} Std.")
