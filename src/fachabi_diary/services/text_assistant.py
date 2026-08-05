from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from fachabi_diary.models import WeeklyReport
from fachabi_diary.services.report_formatter import GERMAN_WEEKDAYS


_TERM_REPLACEMENTS = {
    r"\brepo\b": "Repository",
    r"\bgit\b": "Git",
    r"\bgithub\b": "GitHub",
    r"\bui\b": "UI",
    r"\bit\b": "IT",
    r"\bpdf\b": "PDF",
    r"\bfrontend\b": "Frontend",
    r"\bbackend\b": "Backend",
}

_EMPTY_TEXTS = {
    "",
    "wochenende",
    "keine tätigkeit eingetragen",
    "noch keine tätigkeit eingetragen",
}


def _normalize_text(text: str) -> str:
    text = re.sub(r"(^|\n)\s*[-•]\s*", r"\1", text)
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(?=\S)", r"\1 ", text)
    return text.strip()


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[:1].upper() + text[1:]


def _ensure_sentence_end(text: str) -> str:
    if not text or text[-1] in ".!?":
        return text
    return f"{text}."


def _is_real_activity(text: str) -> bool:
    return _normalize_text(text).casefold() not in _EMPTY_TEXTS


def _shorten(text: str, limit: int = 88) -> str:
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else text[:limit].strip()


class LocalTextAssistant:
    """Rule-based text helper that can later be swapped for a real AI provider."""

    def improve_activity(self, text: str) -> str:
        cleaned = _normalize_text(text)
        if not cleaned:
            return ""
        for pattern, replacement in _TERM_REPLACEMENTS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return _ensure_sentence_end(_sentence_case(cleaned))

    def summarize_week(self, report: WeeklyReport) -> str:
        parts: list[str] = []
        for entry in report.entries:
            if not _is_real_activity(entry.activity_text):
                continue
            weekday = GERMAN_WEEKDAYS[date.fromisoformat(entry.entry_date).weekday()]
            activity = self.improve_activity(entry.activity_text).rstrip(".")
            parts.append(f"{weekday}: {_shorten(activity)}")
        if not parts:
            return ""
        if len(parts) == 1:
            return f"In dieser Woche wurde folgende Tätigkeit dokumentiert: {parts[0]}."
        return f"In dieser Woche wurden folgende Tätigkeiten dokumentiert: {'; '.join(parts)}."

    def formalize_report(self, report: WeeklyReport) -> WeeklyReport:
        entries = [
            replace(entry, activity_text=self.improve_activity(entry.activity_text))
            if _is_real_activity(entry.activity_text)
            else entry
            for entry in report.entries
        ]
        notes = self.improve_activity(report.general_notes) if report.general_notes.strip() else report.general_notes
        return replace(report, entries=entries, general_notes=notes)
