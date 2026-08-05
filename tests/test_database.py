import sqlite3

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
    assert saved_profile.working_days == "0,1,2,3,4"
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


def test_profile_working_days_persistence(tmp_path) -> None:
    connection = connect(tmp_path / "app.sqlite3")
    profiles = ProfileRepository(connection)

    profiles.save(Profile(working_days="0,1,2,3,4,5"))

    saved = profiles.get()
    assert saved is not None
    assert saved.working_days == "0,1,2,3,4,5"
    assert saved.is_working_day(5)
    assert not saved.is_working_day(6)


def test_migrates_old_profile_schema_to_working_days(tmp_path) -> None:
    path = tmp_path / "old.sqlite3"
    old_connection = sqlite3.connect(path)
    old_connection.executescript(
        """
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version(version) VALUES (1);

        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            surname TEXT NOT NULL,
            first_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            company_address TEXT NOT NULL,
            internship_field TEXT NOT NULL,
            contract_start TEXT NOT NULL,
            contract_end TEXT NOT NULL,
            default_location TEXT NOT NULL
        );
        INSERT INTO profiles
        (id, surname, first_name, company_name, company_address, internship_field,
         contract_start, contract_end, default_location)
        VALUES
        (1, 'Lysenko', 'Kostiantyn', 'Garamantis GmbH', 'Berlin', 'IT',
         '2026-08-04', '2027-07-31', 'Berlin');
        """
    )
    old_connection.commit()
    old_connection.close()

    connection = connect(path)
    profile = ProfileRepository(connection).get()
    version = connection.execute("SELECT version FROM schema_version").fetchone()["version"]

    assert profile is not None
    assert profile.working_days == "0,1,2,3,4"
    assert version == 2
