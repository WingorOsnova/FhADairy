import sys
from pathlib import Path

from fachabi_diary.app import resource_path


def test_resource_path_finds_repo_assets() -> None:
    assert resource_path("assets/formblatt9.pdf").exists()


def test_resource_path_uses_pyinstaller_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert resource_path("assets/formblatt9.pdf") == tmp_path / "assets/formblatt9.pdf"
