"""Tests for harness.core.model_selection — Cursor state DB integration."""

from __future__ import annotations

import sqlite3

from harness.core.model_selection import (
    detect_cursor_recent_models,
    validate_model_name,
)


class TestValidateModelName:
    def test_inherit_is_valid(self):
        assert validate_model_name("inherit") is True

    def test_simple_id(self):
        assert validate_model_name("gpt-4.1") is True

    def test_empty_string(self):
        assert validate_model_name("") is False

    def test_starts_with_digit(self):
        assert validate_model_name("4gpt") is False


class TestDetectCursorRecentModels:
    def test_returns_empty_when_no_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "harness.core.model_selection._cursor_state_db_path",
            lambda: tmp_path / "nonexistent.vscdb",
        )
        assert detect_cursor_recent_models() == []

    def test_last_single_preference(self, tmp_path, monkeypatch):
        db = tmp_path / "state.vscdb"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("cursor/lastSingleModelPreference", '{"composer":"from-last"}'),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(
            "harness.core.model_selection._cursor_state_db_path",
            lambda: db,
        )
        models = detect_cursor_recent_models()
        assert "from-last" in models

    def test_best_of_n_fallback(self, tmp_path, monkeypatch):
        db = tmp_path / "state.vscdb"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("cursor/bestOfNEnsemblePreferences", '{"3":["bon-first","bon-second"]}'),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(
            "harness.core.model_selection._cursor_state_db_path",
            lambda: db,
        )
        models = detect_cursor_recent_models()
        assert "bon-first" in models
        assert "bon-second" in models

    def test_both_keys_dedup(self, tmp_path, monkeypatch):
        db = tmp_path / "state.vscdb"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("cursor/lastSingleModelPreference", '{"composer":"shared-model"}'),
        )
        conn.execute(
            "INSERT INTO ItemTable VALUES (?, ?)",
            ("cursor/bestOfNEnsemblePreferences", '{"3":["shared-model","unique-bon"]}'),
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(
            "harness.core.model_selection._cursor_state_db_path",
            lambda: db,
        )
        models = detect_cursor_recent_models()
        assert models.count("shared-model") == 1
        assert "unique-bon" in models
