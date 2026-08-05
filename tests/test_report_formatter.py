from fachabi_diary.models import DailyEntry, WeeklyReport
from fachabi_diary.services.report_formatter import (
    format_activity_bullets,
    format_date,
    format_hours,
    has_exportable_activity,
)


def test_format_date_and_hours() -> None:
    assert format_date("2026-08-04") == "04.08.2026"
    assert format_hours(8) == "8"
    assert format_hours(7.5) == "7,5"


def test_format_activity_bullets_keeps_user_text() -> None:
    entries = [
        DailyEntry("2026-08-03", 8, "Projektstruktur kennengelernt."),
        DailyEntry("2026-08-04", 7.5, "  Git verwendet.  "),
    ]
    assert format_activity_bullets(entries) == (
        "- Montag, 03.08.2026 (8 Std.): Projektstruktur kennengelernt.\n"
        "- Dienstag, 04.08.2026 (7,5 Std.): Git verwendet."
    )


def test_weekend_placeholder_is_not_exportable_activity() -> None:
    report = WeeklyReport(
        1,
        "2026-08-03",
        "2026-08-09",
        "2026-08-07",
        entries=[
            DailyEntry("2026-08-08", 0, "Wochenende"),
            DailyEntry("2026-08-09", 0, " Wochenende "),
        ],
    )

    assert not has_exportable_activity(report)
