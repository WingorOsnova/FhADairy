from fachabi_diary.models import DailyEntry, WeeklyReport
from fachabi_diary.services.text_assistant import LocalTextAssistant


def test_improve_activity_normalizes_common_terms() -> None:
    assistant = LocalTextAssistant()

    result = assistant.improve_activity("  repo geklont und ui getestet ")

    assert result == "Repository geklont und UI getestet."


def test_summarize_week_uses_filled_workdays_only() -> None:
    assistant = LocalTextAssistant()
    report = WeeklyReport(
        1,
        "2026-08-03",
        "2026-08-09",
        "2026-08-08",
        entries=[
            DailyEntry("2026-08-03", 6, "repo geklont"),
            DailyEntry("2026-08-04", 0, ""),
            DailyEntry("2026-08-08", 0, "Wochenende"),
        ],
    )

    result = assistant.summarize_week(report)

    assert result.startswith("In dieser Woche wurde")
    assert "Montag: Repository geklont" in result
    assert "Samstag" not in result
