from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QPushButton, QSizePolicy

import fachabi_diary.main_window as main_window_module
from fachabi_diary.db import connect
from fachabi_diary.main_window import (
    ExportResultDialog,
    MainWindow,
    ProfileDialog,
    ReportListItem,
    SettingsDialog,
    _profile_validation_error,
)
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


def test_new_week_prefills_non_working_days_from_profile(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04", working_days="0,1,2,3,4,5")
    profiles.save(profile)
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.new_week()

    saved = reports.list()[0]
    assert saved.entries[5].activity_text == ""
    assert saved.entries[6].activity_text == "Wochenende"


def test_settings_dialog_saves_working_days(qt_app) -> None:
    dialog = SettingsDialog(Profile(working_days="0,2,4"), Path("assets/formblatt9.pdf"))

    assert dialog.minimumWidth() >= 820
    assert dialog.surname.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert all(
        check.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        for check in dialog.working_day_checks
    )
    assert [check.isChecked() for check in dialog.working_day_checks] == [
        True,
        False,
        True,
        False,
        True,
        False,
        False,
    ]
    dialog.working_day_checks[1].setChecked(True)
    dialog.working_day_checks[4].setChecked(False)

    assert dialog.profile().working_days == "0,1,2"


def test_profile_dialog_starts_empty_and_saves_working_days(qt_app) -> None:
    dialog = ProfileDialog()

    assert dialog.surname.text() == ""
    assert dialog.first_name.text() == ""
    assert [check.isChecked() for check in dialog.working_day_checks] == [
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    ]
    dialog.surname.setText("Muster")
    dialog.first_name.setText("Max")
    dialog.company_name.setText("Praxis GmbH")
    dialog.company_address.setText("Berlin")
    dialog.internship_field.setText("Informationstechnik")
    dialog.default_location.setText("Berlin")
    dialog.working_day_checks[5].setChecked(True)

    profile = dialog.profile()

    assert profile.surname == "Muster"
    assert profile.working_days == "0,1,2,3,4,5"
    assert _profile_validation_error(profile) is None


def test_profile_validation_requires_core_fields(qt_app) -> None:
    dialog = ProfileDialog()

    error = _profile_validation_error(dialog.profile())

    assert error is not None
    assert "Nachname" in error
    assert "Praxisstelle" in error


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
    assert not window.open_last_pdf_action.isVisible()
    assert not window.reveal_last_pdf_action.isVisible()
    assert window.pdf_status_file.text() == "Noch kein PDF erstellt"
    assert not window.open_pdf_button.isEnabled()
    assert not window.reveal_pdf_button.isEnabled()
    expected_sizes = {
        "Speichern": (150, 42),
        "PDF erstellen": (150, 42),
        "Löschen": (128, 42),
        "Weitere": (132, 42),
    }
    for button in window.findChildren(QPushButton):
        if button.text() in expected_sizes:
            assert (button.width(), button.height()) == expected_sizes[button.text()]


def test_summary_card_shows_total_practice_hours(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile(contract_start="2026-08-04")
    profiles.save(profile)
    reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            entries=[DailyEntry("2026-08-03", 4, "Erste Woche.")],
        )
    )
    second_id = reports.save(
        WeeklyReport(
            2,
            "2026-08-10",
            "2026-08-16",
            "2026-08-14",
            "Berlin",
            entries=[DailyEntry("2026-08-10", 2, "Zweite Woche.")],
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.refresh_list(second_id)

    assert window.total.text() == "2 Std."
    assert window.hours_card.value.text() == "6 Std."

    entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry.entry_date,
            5,
            entry.activity_text,
            id=entry.id,
            weekly_report_id=entry.weekly_report_id,
        )
    )
    window._handle_day_row_changed()

    assert window.total.text() == "5 Std."
    assert window.hours_card.value.text() == "9 Std."


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


def test_export_result_dialog_shows_file_actions(qt_app, tmp_path) -> None:
    output = tmp_path / "bericht-1.pdf"
    dialog = ExportResultDialog(output)

    button_texts = {button.text() for button in dialog.findChildren(QPushButton)}

    assert dialog.output_path == output
    assert "Öffnen" in button_texts
    assert "Schließen" in button_texts
    assert any("anzeigen" in text for text in button_texts)


def test_more_menu_shows_last_pdf_actions_for_exported_report(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    output = tmp_path / "bericht-1.pdf"
    output.write_bytes(b"%PDF-1.4\n")
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            last_pdf_path=str(output),
            last_pdf_exported_at="2026-08-10T12:05:00",
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))

    window.refresh_list(report_id)

    assert window.open_last_pdf_action.isVisible()
    assert window.reveal_last_pdf_action.isVisible()
    assert window._last_pdf_path() == output
    assert window.pdf_status_file.text() == "bericht-1.pdf"
    assert "10.08.2026, 12:05" in window.pdf_status_meta.text()
    assert window.open_pdf_button.isEnabled()
    assert window.reveal_pdf_button.isEnabled()


def test_export_current_marks_draft_report_ready(qt_app, tmp_path, monkeypatch) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            status="Entwurf",
            entries=[DailyEntry("2026-08-03", 6, "Test exportieren.")],
        )
    )
    output = tmp_path / "bericht-1.pdf"
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(report_id)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(output), "PDF (*.pdf)"))
    monkeypatch.setattr(ExportResultDialog, "exec", lambda self: 0)

    window.export_current()

    saved = reports.get(report_id)
    assert saved.status == "Bereit"
    assert saved.last_pdf_path == str(output)
    assert saved.last_pdf_exported_at
    assert window.current_report.status == "Bereit"
    assert window.open_last_pdf_action.isVisible()
    assert window.pdf_status_file.text() == "bericht-1.pdf"
    assert window.open_pdf_button.isEnabled()


def test_export_current_keeps_printed_status(qt_app, tmp_path, monkeypatch) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            status="Gedruckt",
            entries=[DailyEntry("2026-08-03", 6, "Test exportieren.")],
        )
    )
    output = tmp_path / "bericht-gedruckt.pdf"
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(report_id)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(output), "PDF (*.pdf)"))
    monkeypatch.setattr(ExportResultDialog, "exec", lambda self: 0)

    window.export_current()

    assert reports.get(report_id).status == "Gedruckt"


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


def test_settings_save_preserves_unsaved_current_report(qt_app, tmp_path, monkeypatch) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            entries=[DailyEntry("2026-08-03", 0, "")],
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(report_id)
    entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry.entry_date,
            6,
            "Nicht gespeicherte Tätigkeit bleibt erhalten.",
            id=entry.id,
            weekly_report_id=entry.weekly_report_id,
        )
    )

    class FakeSettingsDialog:
        def __init__(self, profile: Profile, template_path: Path, parent=None) -> None:
            self._profile = profile

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def profile(self) -> Profile:
            return Profile(
                id=self._profile.id,
                surname=self._profile.surname,
                first_name=self._profile.first_name,
                company_name="Neue Praxisstelle GmbH",
                company_address=self._profile.company_address,
                internship_field=self._profile.internship_field,
                contract_start=self._profile.contract_start,
                contract_end=self._profile.contract_end,
                default_location=self._profile.default_location,
                working_days=self._profile.working_days,
            )

    monkeypatch.setattr(main_window_module, "SettingsDialog", FakeSettingsDialog)

    window.edit_profile()

    saved = reports.get(report_id)
    assert saved.entries[0].activity_text == "Nicht gespeicherte Tätigkeit bleibt erhalten."
    assert saved.entries[0].hours == 6
    assert profiles.get().company_name == "Neue Praxisstelle GmbH"
    assert window.day_rows[0].entry().activity_text == "Nicht gespeicherte Tätigkeit bleibt erhalten."


def test_autosave_persists_dirty_report(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            entries=[DailyEntry("2026-08-03", 0, "")],
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(report_id)
    entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry.entry_date,
            5,
            "Autosave speichert diese Tätigkeit.",
            id=entry.id,
            weekly_report_id=entry.weekly_report_id,
        )
    )

    window._handle_day_row_changed()
    window._autosave_current()

    saved = reports.get(report_id)
    assert not window._report_dirty
    assert saved.entries[0].hours == 5
    assert saved.entries[0].activity_text == "Autosave speichert diese Tätigkeit."


def test_switching_report_saves_pending_current_report(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    first_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            entries=[DailyEntry("2026-08-03", 0, "")],
        )
    )
    second_id = reports.save(
        WeeklyReport(
            2,
            "2026-08-10",
            "2026-08-16",
            "2026-08-14",
            "Berlin",
            entries=[DailyEntry("2026-08-10", 0, "")],
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(first_id)
    entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry.entry_date,
            4,
            "Vor dem Wechsel gespeichert.",
            id=entry.id,
            weekly_report_id=entry.weekly_report_id,
        )
    )
    window._handle_day_row_changed()

    window.load_report_by_id(second_id)

    saved_first = reports.get(first_id)
    assert saved_first.entries[0].activity_text == "Vor dem Wechsel gespeichert."
    assert saved_first.entries[0].hours == 4
    assert window.current_report.id == second_id


def test_status_change_saves_pending_report_text(qt_app, tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profile = Profile()
    profiles.save(profile)
    report_id = reports.save(
        WeeklyReport(
            1,
            "2026-08-03",
            "2026-08-09",
            "2026-08-07",
            "Berlin",
            entries=[DailyEntry("2026-08-03", 0, "")],
        )
    )
    window = MainWindow(profile, profiles, reports, Path("assets/formblatt9.pdf"))
    window.refresh_list(report_id)
    entry = window.day_rows[0].entry()
    window.day_rows[0].set_entry(
        DailyEntry(
            entry.entry_date,
            6,
            "Statuswechsel darf den Text nicht verlieren.",
            id=entry.id,
            weekly_report_id=entry.weekly_report_id,
        )
    )
    window._handle_day_row_changed()

    window.mark_status("Gedruckt")

    saved = reports.get(report_id)
    assert saved.status == "Gedruckt"
    assert saved.entries[0].activity_text == "Statuswechsel darf den Text nicht verlieren."
