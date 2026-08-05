from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


STATUSES = ("Entwurf", "Bereit", "Gedruckt", "Unterschrieben")


@dataclass
class Profile:
    surname: str = "Lysenko"
    first_name: str = "Kostiantyn"
    company_name: str = "Garamantis GmbH"
    company_address: str = "EUREF-Campus 7, 10829 Berlin"
    internship_field: str = "Softwareentwicklung / Informationstechnik"
    contract_start: str = "2026-08-04"
    contract_end: str = "2027-07-31"
    default_location: str = "Berlin"
    id: int | None = None


@dataclass
class DailyEntry:
    entry_date: str
    hours: float = 0.0
    activity_text: str = ""
    id: int | None = None
    weekly_report_id: int | None = None


@dataclass
class WeeklyReport:
    report_number: int
    week_start: str
    week_end: str
    report_date: str
    location: str = "Berlin"
    general_notes: str = ""
    status: str = "Entwurf"
    id: int | None = None
    entries: list[DailyEntry] = field(default_factory=list)

    @property
    def total_hours(self) -> float:
        return sum(entry.hours for entry in self.entries)

    @classmethod
    def new(cls, report_number: int, week_start: date, location: str) -> "WeeklyReport":
        week_end = date.fromordinal(week_start.toordinal() + 6)
        entries = [
            DailyEntry(date.fromordinal(week_start.toordinal() + offset).isoformat())
            for offset in range(7)
        ]
        return cls(
            report_number=report_number,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            report_date=date.today().isoformat(),
            location=location,
            entries=entries,
        )
