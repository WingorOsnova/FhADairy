from fachabi_diary.db import connect
from fachabi_diary.models import DailyEntry, Profile, WeeklyReport
from fachabi_diary.repositories import ProfileRepository, WeeklyReportRepository


def test_profile_and_report_persistence(tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)
    reports = WeeklyReportRepository(connection)
    profiles.save(Profile())
    report = WeeklyReport(
        report_number=1,
        week_start="2026-08-03",
        week_end="2026-08-09",
        report_date="2026-08-07",
        location="Berlin",
        entries=[DailyEntry("2026-08-03", 8, "Entwicklungsumgebung eingerichtet.")],
    )
    report_id = reports.save(report)

    saved_profile = profiles.get()
    saved_report = reports.get(report_id)

    assert saved_profile is not None
    assert saved_profile.company_name == "Garamantis GmbH"
    assert saved_report.report_number == 1
    assert saved_report.total_hours == 8
    assert saved_report.entries[0].activity_text == "Entwicklungsumgebung eingerichtet."


def test_delete_report_removes_entries(tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    reports = WeeklyReportRepository(connection)
    report_id = reports.save(
        WeeklyReport(
            report_number=1,
            week_start="2026-08-03",
            week_end="2026-08-09",
            report_date="2026-08-07",
            entries=[DailyEntry("2026-08-03", 8, "Test")],
        )
    )
    reports.delete(report_id)
    count = connection.execute("SELECT COUNT(*) FROM daily_entries").fetchone()[0]
    assert count == 0
