from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


STATUSES = ("Entwurf", "Bereit", "Gedruckt", "Unterschrieben")
DEFAULT_WORKING_DAYS = "0,1,2,3,4"


def parse_working_days(value: str) -> set[int]:
    days: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part.isdigit():
            continue
        day = int(part)
        if 0 <= day <= 6:
            days.add(day)
    return days or {0, 1, 2, 3, 4}


def serialize_working_days(days: set[int]) -> str:
    valid_days = sorted(day for day in days if 0 <= day <= 6)
    if not valid_days:
        valid_days = [0, 1, 2, 3, 4]
    return ",".join(str(day) for day in valid_days)


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
    working_days: str = DEFAULT_WORKING_DAYS
    id: int | None = None

    @property
    def working_day_indexes(self) -> set[int]:
        return parse_working_days(self.working_days)

    def is_working_day(self, weekday_index: int) -> bool:
        return weekday_index in self.working_day_indexes


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
