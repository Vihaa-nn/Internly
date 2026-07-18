from __future__ import annotations

import importlib
from pathlib import Path


def test_database_url_is_resolved_from_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/internly.db")

    import internly.config as config

    importlib.reload(config)

    repo_root = Path(config.__file__).resolve().parent.parent
    expected_db = (repo_root / "data" / "internly.db").resolve()
    assert config.settings.database_url == f"sqlite:///{expected_db.as_posix()}"
