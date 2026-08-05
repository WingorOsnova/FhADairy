from pathlib import Path

from PySide6.QtWidgets import QApplication, QPushButton

from fachabi_diary.db import connect
from fachabi_diary.main_window import MainWindow, ReportListItem
from fachabi_diary.models import DailyEntry, Profile, WeeklyReport
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
    assert saved[0].week_start == "2026-08-03"
    assert saved[0].week_end == "2026-08-09"
    assert saved[1].report_number == 2
    assert saved[1].week_start == "2026-08-10"
    assert "KW" not in window._report_list_label(saved[0])
    assert "Bericht Nr. 1" in window._report_list_label(saved[0])


def test_weekend_defaults_keep_existing_weekend_work(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.new_week()
    saturday = window.day_rows[5].entry()
    window.day_rows[5].set_entry(
        DailyEntry(
            entry_date=saturday.entry_date,
            hours=2,
            activity_text="Samstagsarbeit",
        )
    )
    window.fill_weekend_defaults()

    assert window.day_rows[5].entry().activity_text == "Samstagsarbeit"
    assert window.day_rows[5].entry().hours == 2
    assert window.day_rows[6].entry().activity_text == "Wochenende"
    assert window.day_rows[6].entry().hours == 0


def test_summary_period_and_action_bar_stay_compact(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.new_week()
    window.show()
    qt_app.processEvents()

    assert "\n" not in window.period_card.value.text()
    button_texts = {button.text() for button in window.findChildren(QPushButton)}
    assert {"Speichern", "PDF erstellen", "Löschen", "Weitere"} <= button_texts
    assert "Gedruckt markieren" not in button_texts
    assert "Als unterschrieben markieren" not in button_texts
    menu_actions = [action.text() for action in window.more_menu.actions()]
    assert "Gedruckt markieren" in menu_actions
    assert "Unterschrieben markieren" in menu_actions
    expected_sizes = {
        "Speichern": (150, 42),
        "PDF erstellen": (150, 42),
        "Löschen": (128, 42),
        "Weitere": (132, 42),
    }
    for button in window.findChildren(QPushButton):
        if button.text() in expected_sizes:
            assert (button.width(), button.height()) == expected_sizes[button.text()]


def test_empty_state_when_no_weekly_reports(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    assert window.current_report is None
    assert window.editor_stack.currentWidget() is window.empty_state
    assert not window.action_bar.isVisible()
    assert window.empty_state.findChildren(QPushButton) == []


def test_ai_helper_updates_current_week_text(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.new_week()
    first_entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry_date=first_entry.entry_date,
            hours=6,
            activity_text=" repo geklont und ui getestet ",
        )
    )

    window.improve_selected_day_note()
    window.summarize_week_note()

    assert window.day_rows[0].entry().activity_text == "Repository geklont und UI getestet."
    assert "Montag: Repository geklont und UI getestet" in window.notes.toPlainText()


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
