from __future__ import annotations

import sqlite3

from .models import DailyEntry, Profile, WeeklyReport


class ProfileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self) -> Profile | None:
        row = self.connection.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
        return Profile(**dict(row)) if row else None

    def save(self, profile: Profile) -> None:
        self.connection.execute(
            """
            INSERT INTO profiles
            (id, surname, first_name, company_name, company_address, internship_field,
             contract_start, contract_end, default_location, working_days)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              surname=excluded.surname,
              first_name=excluded.first_name,
              company_name=excluded.company_name,
              company_address=excluded.company_address,
              internship_field=excluded.internship_field,
              contract_start=excluded.contract_start,
              contract_end=excluded.contract_end,
              default_location=excluded.default_location,
              working_days=excluded.working_days
            """,
            (
                profile.surname,
                profile.first_name,
                profile.company_name,
                profile.company_address,
                profile.internship_field,
                profile.contract_start,
                profile.contract_end,
                profile.default_location,
                profile.working_days,
            ),
        )
        self.connection.commit()


class WeeklyReportRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list(self) -> list[WeeklyReport]:
        rows = self.connection.execute(
            "SELECT * FROM weekly_reports ORDER BY report_number"
        ).fetchall()
        return [self.get(row["id"]) for row in rows]

    def get(self, report_id: int) -> WeeklyReport:
        row = self.connection.execute("SELECT * FROM weekly_reports WHERE id = ?", (report_id,)).fetchone()
        if row is None:
            raise ValueError("Bericht wurde nicht gefunden.")
        report = WeeklyReport(
            id=row["id"],
            report_number=row["report_number"],
            week_start=row["week_start"],
            week_end=row["week_end"],
            report_date=row["report_date"],
            location=row["location"],
            general_notes=row["general_notes"],
            status=row["status"],
        )
        entry_rows = self.connection.execute(
            "SELECT * FROM daily_entries WHERE weekly_report_id = ? ORDER BY entry_date, id",
            (report.id,),
        ).fetchall()
        report.entries = [
            DailyEntry(
                id=entry["id"],
                weekly_report_id=entry["weekly_report_id"],
                entry_date=entry["entry_date"],
                hours=entry["hours"],
                activity_text=entry["activity_text"],
            )
            for entry in entry_rows
        ]
        return report

    def next_number(self) -> int:
        row = self.connection.execute("SELECT COALESCE(MAX(report_number), 0) + 1 AS n FROM weekly_reports").fetchone()
        return int(row["n"])

    def save(self, report: WeeklyReport) -> int:
        if report.id is None:
            cursor = self.connection.execute(
                """
                INSERT INTO weekly_reports
                (report_number, week_start, week_end, report_date, location, general_notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_number,
                    report.week_start,
                    report.week_end,
                    report.report_date,
                    report.location,
                    report.general_notes,
                    report.status,
                ),
            )
            report.id = int(cursor.lastrowid)
        else:
            self.connection.execute(
                """
                UPDATE weekly_reports
                SET report_number=?, week_start=?, week_end=?, report_date=?, location=?,
                    general_notes=?, status=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    report.report_number,
                    report.week_start,
                    report.week_end,
                    report.report_date,
                    report.location,
                    report.general_notes,
                    report.status,
                    report.id,
                ),
            )
            self.connection.execute("DELETE FROM daily_entries WHERE weekly_report_id=?", (report.id,))
        for entry in report.entries:
            self.connection.execute(
                """
                INSERT INTO daily_entries (weekly_report_id, entry_date, hours, activity_text)
                VALUES (?, ?, ?, ?)
                """,
                (report.id, entry.entry_date, entry.hours, entry.activity_text),
            )
        self.connection.commit()
        return report.id

    def delete(self, report_id: int) -> None:
        self.connection.execute("DELETE FROM weekly_reports WHERE id=?", (report_id,))
        self.connection.commit()

    def set_status(self, report_id: int, status: str) -> None:
        self.connection.execute(
            "UPDATE weekly_reports SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, report_id),
        )
        self.connection.commit()
