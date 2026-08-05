from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QDialog

from .db import connect
from .main_window import MainWindow, ProfileDialog
from .repositories import ProfileRepository, WeeklyReportRepository


def data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base or Path.home() / ".fachabi-diary")


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Fachabi Diary")
    app.setStyleSheet(STYLE)
    connection = connect(data_dir() / "fachabi_diary.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = profiles.get()
    if profile is None:
        dialog = ProfileDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
        profile = dialog.profile()
        profiles.save(profile)
    elif profile.contract_start == "2026-08-01":
        profile.contract_start = "2026-08-04"
        profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path.cwd() / "assets" / "formblatt9.pdf")
    window.resize(1420, 900)
    window.show()
    return app.exec()


STYLE = """
QWidget {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
  font-size: 14px;
  color: #1d1d1f;
  background: #f6f7fb;
}
QLabel {
  background: transparent;
}
QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox, QSpinBox {
  background: white;
  border: 1px solid #d9dde7;
  border-radius: 8px;
  padding: 6px;
  selection-background-color: #0071e3;
}
QTextEdit {
  padding: 8px;
}
QPushButton {
  background: #ffffff;
  border: 1px solid #d9dde7;
  border-radius: 8px;
  padding: 9px 14px;
}
QPushButton:hover { background: #f0f0f2; }
QPushButton:pressed {
  background: #e6e9ef;
  border-color: #b8c0cc;
}
QPushButton#primaryButton {
  background: #0a66ff;
  color: white;
  border-color: #0a66ff;
  font-weight: 600;
}
QPushButton#primaryButton:pressed {
  background: #0057d8;
}
QPushButton:disabled {
  color: #8a8f98;
  background: #f8f9fb;
}
QPushButton#iconButton {
  padding: 7px 10px;
  min-width: 88px;
}
QListWidget#weekList {
  background: #ffffff;
  border: 1px solid #dde2ec;
  border-radius: 10px;
  padding: 6px;
}
QListWidget#weekList::item {
  min-height: 76px;
  border-radius: 10px;
  padding: 11px 12px;
  margin: 4px 0;
}
QListWidget#weekList::item:selected {
  background: #edf4ff;
  color: #111827;
  border-left: 4px solid #0a66ff;
}
QListWidget#weekList QScrollBar:vertical,
QScrollArea QScrollBar:vertical {
  width: 0;
}
QFrame#sidebar {
  background: #f8f9fc;
  border-right: 1px solid #dde2ec;
}
QFrame#sidebarDivider {
  background: #e8ecf2;
  border: none;
  max-height: 1px;
}
QFrame#reportListItem {
  background: #ffffff;
  border: 1px solid transparent;
  border-radius: 12px;
}
QFrame#reportListItem:hover {
  background: #f8fbff;
  border-color: #dbeafe;
}
QFrame#reportListItem[active="true"] {
  background: #eaf2ff;
  border-color: #c7ddff;
}
QFrame#selectedStripe {
  background: transparent;
  border-radius: 2px;
}
QFrame#selectedStripe[active="true"] {
  background: #0a6cff;
}
QLabel#reportItemTitle {
  color: #0f172a;
  font-size: 14px;
  font-weight: 720;
}
QLabel#reportItemTitle[active="true"] {
  color: #075bd8;
}
QLabel#statusChip {
  border-radius: 9px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 650;
}
QLabel#statusChip[status="Entwurf"] {
  color: #0a6cff;
  background: #dbeafe;
}
QLabel#statusChip[status="Bereit"] {
  color: #b45309;
  background: #fef3c7;
}
QLabel#statusChip[status="Gedruckt"] {
  color: #475569;
  background: #e2e8f0;
}
QLabel#statusChip[status="Unterschrieben"] {
  color: #15803d;
  background: #dcfce7;
}
QFrame#toolbar {
  background: #ffffff;
  border-bottom: 1px solid #dde2ec;
}
QFrame#actionBar {
  background: #ffffff;
  border-top: 1px solid #dde2ec;
}
QFrame#summaryCard, QFrame#panel, QFrame#bluePanel {
  background: #ffffff;
  border: 1px solid #dde2ec;
  border-radius: 10px;
}
QFrame#summaryCard {
  min-height: 112px;
  max-height: 126px;
}
QFrame#bluePanel {
  background: #f4f8ff;
  border-color: #bcd4ff;
}
QFrame#dayRow {
  background: #ffffff;
  border-bottom: 1px solid #e7eaf0;
}
QWidget#dayDateCell {
  background: transparent;
}
QLabel#brandTitle {
  color: #0a4dbf;
  font-size: 21px;
  font-weight: 750;
}
QLabel#logoBox {
  background: #0a66ff;
  color: white;
  border-radius: 10px;
  padding: 12px 9px;
  font-size: 17px;
  font-weight: 800;
}
QLabel#sectionLabel {
  color: #4b5563;
  font-weight: 650;
}
QLabel#mutedLabel {
  color: #667085;
}
QLabel#cardMarker {
  color: #0a66ff;
  background: #f4f8ff;
  border-radius: 7px;
  padding: 5px 8px;
  font-size: 12px;
  font-weight: 700;
}
QLabel#cardValue {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
QLabel#dayName {
  font-size: 16px;
  font-weight: 700;
}
QLabel#hoursValue {
  font-size: 18px;
  font-weight: 650;
  color: #111827;
  min-width: 64px;
}
QLabel#activityText {
  font-size: 15px;
  color: #253044;
}
QLabel#panelTitle {
  font-size: 16px;
  font-weight: 750;
}
QLabel#dialogTitle {
  font-size: 24px;
  font-weight: 760;
}
QLabel#statusPill {
  background: #eaf2ff;
  color: #0a66ff;
  border-radius: 10px;
  padding: 6px 12px;
  font-weight: 650;
}
QLabel#totalLabel {
  font-size: 18px;
  font-weight: 750;
}
QFrame#companyFooter {
  background: #ffffff;
  border: 1px solid #dde2ec;
  border-radius: 10px;
}
QLabel#companyName {
  background: transparent;
  color: #344054;
  font-weight: 650;
}
QLabel#companyRole {
  background: transparent;
  color: #64748b;
  font-size: 12px;
}
QLabel#companyIcon {
  background: transparent;
}
QLabel#pdfPreview {
  background: #f8fafc;
  border: 1px dashed #c8d1df;
  border-radius: 8px;
  color: #667085;
  min-height: 220px;
}
QLabel#toast {
  background: #111827;
  color: #ffffff;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 650;
}
"""
