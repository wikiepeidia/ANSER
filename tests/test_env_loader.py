"""Unit tests for core.env_loader's branch-aware `.env` resolution.

Uses `tmp_path` to build isolated fake root directories for every resolution
case — never touches the real repo root `.env`. Branch-dependent cases
monkeypatch `core.env_loader._current_branch` directly (a plain function
reference swap); only the `_current_branch()` git-missing test monkeypatches
`subprocess.run` itself.
"""
import subprocess

import core.env_loader as env_loader
from core.env_loader import _current_branch, _resolve_env_path, load_project_env


def test_resolve_env_path_root_env_is_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar")

    result = _resolve_env_path(str(tmp_path))

    assert result == str(env_file)


def test_resolve_env_path_dir_matches_current_branch(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    branch_file = env_dir / ".env.sanxuat"
    branch_file.write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: "anser-san-xuat")

    result = _resolve_env_path(str(tmp_path))

    assert result == str(branch_file)


def test_resolve_env_path_dir_git_unavailable_returns_none(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    (env_dir / ".env.sanxuat").write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: None)

    result = _resolve_env_path(str(tmp_path))

    assert result is None


def test_resolve_env_path_dir_unmapped_branch_returns_none(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    (env_dir / ".env.sanxuat").write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: "some-other-branch")

    result = _resolve_env_path(str(tmp_path))

    assert result is None


def test_resolve_env_path_dir_mapped_branch_file_missing_returns_none(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    # No .env.sanxuat file created inside env_dir.

    monkeypatch.setattr(env_loader, "_current_branch", lambda: "anser-san-xuat")

    result = _resolve_env_path(str(tmp_path))

    assert result is None


def test_resolve_env_path_dir_unmapped_branch_uses_generic_fallback_file(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    fallback_file = env_dir / ".env"
    fallback_file.write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: "some-other-branch")

    result = _resolve_env_path(str(tmp_path))

    assert result == str(fallback_file)


def test_resolve_env_path_dir_mapped_branch_file_missing_uses_generic_fallback_file(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    # No .env.sanxuat file created inside env_dir, but a generic fallback is.
    fallback_file = env_dir / ".env"
    fallback_file.write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: "anser-san-xuat")

    result = _resolve_env_path(str(tmp_path))

    assert result == str(fallback_file)


def test_resolve_env_path_dir_git_unavailable_uses_generic_fallback_file(tmp_path, monkeypatch):
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    fallback_file = env_dir / ".env"
    fallback_file.write_text("FOO=bar")

    monkeypatch.setattr(env_loader, "_current_branch", lambda: None)

    result = _resolve_env_path(str(tmp_path))

    assert result == str(fallback_file)


def test_resolve_env_path_neither_file_nor_dir_returns_none(tmp_path):
    # tmp_path/.env does not exist at all.
    result = _resolve_env_path(str(tmp_path))

    assert result is None


def test_current_branch_git_missing_returns_none(monkeypatch):
    def _raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError("git binary not found")

    monkeypatch.setattr(subprocess, "run", _raise_file_not_found)

    result = _current_branch()

    assert result is None


def test_load_project_env_with_resolved_path_calls_load_dotenv_with_path(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar")

    calls = []
    monkeypatch.setattr(env_loader, "load_dotenv", lambda *a, **kw: calls.append((a, kw)))

    load_project_env(str(tmp_path))

    assert calls == [((str(env_file),), {})]


def test_load_project_env_with_no_resolved_path_calls_bare_load_dotenv(tmp_path, monkeypatch):
    # tmp_path/.env does not exist -> _resolve_env_path returns None.
    calls = []
    monkeypatch.setattr(env_loader, "load_dotenv", lambda *a, **kw: calls.append((a, kw)))

    load_project_env(str(tmp_path))

    assert calls == [((), {})]
