from __future__ import annotations

from datetime import date

from fachabi_diary.models import DailyEntry, WeeklyReport

GERMAN_WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%d.%m.%Y")


def format_hours(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def format_activity_bullets(entries: list[DailyEntry], general_notes: str = "") -> str:
    lines: list[str] = []
    for entry in entries:
        text = " ".join(entry.activity_text.split())
        if not text:
            continue
        weekday = GERMAN_WEEKDAYS[date.fromisoformat(entry.entry_date).weekday()]
        hours = f" ({format_hours(entry.hours)} Std.)" if entry.hours else ""
        lines.append(f"- {weekday}, {format_date(entry.entry_date)}{hours}: {text}")
    notes = " ".join(general_notes.split())
    if notes:
        lines.append(f"- Wochennotiz: {notes}")
    return "\n".join(lines)


def has_exportable_activity(report: WeeklyReport) -> bool:
    return any(entry.activity_text.strip() for entry in report.entries)
