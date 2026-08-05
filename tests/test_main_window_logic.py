from pathlib import Path

from PySide6.QtWidgets import QApplication

from fachabi_diary.db import connect
from fachabi_diary.main_window import MainWindow, ReportListItem
from fachabi_diary.models import Profile, WeeklyReport
from fachabi_diary.repositories import ProfileRepository, WeeklyReportRepository


def test_new_reports_start_from_internship_start(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.new_week()
    window.new_week()

    saved = reports.list()
    assert saved[0].report_number == 1
    assert saved[0].week_start == "2026-08-04"
    assert saved[0].week_end == "2026-08-10"
    assert saved[1].report_number == 2
    assert saved[1].week_start == "2026-08-11"
    assert "KW" not in window._report_list_label(saved[0])
    assert "Bericht Nr. 1" in window._report_list_label(saved[0])


def test_qt_app_fixture_smoke(qt_app) -> None:
    assert QApplication.instance() is qt_app


def test_sidebar_active_state_moves_as_one(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    first_id = reports.save(WeeklyReport(1, "2026-08-04", "2026-08-10", "2026-08-05", "Berlin"))
    second_id = reports.save(WeeklyReport(2, "2026-08-11", "2026-08-17", "2026-08-12", "Berlin"))
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.refresh_list(first_id)
    window.load_report_by_id(second_id)

    states = [
        (item.report.report_number, item.property("active"), item.stripe.property("active"), item.title.property("active"))
        for item in window.findChildren(ReportListItem)
        if item.parent() is not None
    ]
    assert states == [(1, False, False, False), (2, True, True, True)]
