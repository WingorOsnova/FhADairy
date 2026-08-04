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
    window = MainWindow(profile, profiles, reports, Path.cwd() / "assets" / "formblatt9.pdf")
    window.resize(1180, 760)
    window.show()
    return app.exec()


STYLE = """
QWidget {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
  font-size: 14px;
  color: #1d1d1f;
  background: #f5f5f7;
}
QLineEdit, QTextEdit, QDateEdit, QDoubleSpinBox, QSpinBox, QTableWidget {
  background: white;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px;
  selection-background-color: #0071e3;
}
QPushButton {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 8px 12px;
}
QPushButton:hover { background: #f0f0f2; }
QPushButton#primaryButton {
  background: #0071e3;
  color: white;
  border-color: #0071e3;
}
QListWidget {
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 10px;
  padding: 6px;
}
QGroupBox {
  border: 1px solid #d2d2d7;
  border-radius: 10px;
  margin-top: 12px;
  padding: 12px;
  background: #fbfbfd;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
"""
