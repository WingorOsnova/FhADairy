from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    migrate(connection)
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            surname TEXT NOT NULL,
            first_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            company_address TEXT NOT NULL,
            internship_field TEXT NOT NULL,
            contract_start TEXT NOT NULL,
            contract_end TEXT NOT NULL,
            default_location TEXT NOT NULL,
            working_days TEXT NOT NULL DEFAULT '0,1,2,3,4'
        );

        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number INTEGER NOT NULL UNIQUE,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            report_date TEXT NOT NULL,
            location TEXT NOT NULL,
            general_notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weekly_report_id INTEGER NOT NULL REFERENCES weekly_reports(id) ON DELETE CASCADE,
            entry_date TEXT NOT NULL,
            hours REAL NOT NULL DEFAULT 0,
            activity_text TEXT NOT NULL DEFAULT ''
        );
        """
    )
    profile_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(profiles)").fetchall()
    }
    if "working_days" not in profile_columns:
        connection.execute(
            "ALTER TABLE profiles ADD COLUMN working_days TEXT NOT NULL DEFAULT '0,1,2,3,4'"
        )
    row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
    elif int(row["version"]) < SCHEMA_VERSION:
        connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
    connection.commit()
