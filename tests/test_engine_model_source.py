"""Regression coverage for local-vs-Hub text model source validation."""

from pathlib import Path

import pytest

from src.core.engine import validate_text_model_source


def _write_complete_model(model_dir: Path) -> None:
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "model-00001-of-00001.safetensors").write_bytes(b"weights")


def test_missing_colab_model_path_fails_before_hugging_face_validation() -> None:
    model_path = "/content/drive/MyDrive/ANSER_data/missing-awq-model"

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_text_model_source(model_path)

    message = str(exc_info.value)
    assert model_path in message
    assert "TEXT_MODEL_ID" in message
    assert "Google Drive" in message


def test_colab_engine_checks_model_path_before_importing_vllm(monkeypatch) -> None:
    model_path = "/content/drive/MyDrive/ANSER_data/missing-awq-model"
    monkeypatch.setenv("ENV", "COLAB")
    monkeypatch.setenv("TEXT_MODEL_ID", model_path)
    monkeypatch.setattr("src.core.engine.ModelEngine._instance", None)

    with pytest.raises(FileNotFoundError, match="Google Drive"):
        from src.core.engine import ModelEngine

        ModelEngine()


def test_incomplete_local_model_directory_lists_missing_artifacts(tmp_path: Path) -> None:
    model_dir = tmp_path / "partial-awq-model"
    model_dir.mkdir()

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_text_model_source(str(model_dir))

    message = str(exc_info.value)
    assert "incomplete" in message.lower()
    assert "config.json" in message
    assert "model weights" in message
    assert "tokenizer" in message


def test_complete_local_model_directory_is_accepted(tmp_path: Path) -> None:
    model_dir = tmp_path / "complete-awq-model"
    _write_complete_model(model_dir)

    assert validate_text_model_source(str(model_dir)) == str(model_dir)


def test_hugging_face_repo_id_is_not_treated_as_a_local_path() -> None:
    repo_id = "Qwen/Qwen2.5-7B-Instruct-AWQ"

    assert validate_text_model_source(repo_id) == repo_id


def test_empty_model_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="TEXT_MODEL_ID is empty"):
        validate_text_model_source("   ")
