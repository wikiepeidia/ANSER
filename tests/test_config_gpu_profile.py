"""
Wave-0 unit test for AI-OPS-02's GPU_PROFILE parameterization (Phase 9,
09-01-PLAN.md Task 1).

`src.core.config`'s `GPU_PROFILE` and `_VLLM_PROFILES` are module-level
constants resolved once at import time (`os.getenv(...)` executes at module
load, not per-`Config()` construction) -- exactly like `DATABASE_URL`'s
per-instance `os.getenv` inside `Config.__init__` is NOT reused here, since
this value is looked up before the class body. To exercise different
`GPU_PROFILE` values in one pytest session, each test monkeypatches the env
var and then `importlib.reload()`s the module so its module-level constants
are re-derived from the (now-patched) environment, mirroring how a fresh
Colab session process would actually pick up the env var at boot. Each test
reloads the module again in a `finally` block so later tests (and any other
test file that imports `src.core.config` fresh) never see a stale profile
leak across test boundaries.
"""

import importlib

import pytest

import src.core.config as config


def _reload_config():
    return importlib.reload(config)


def test_default_gpu_profile_is_l4_with_real_hardware_proven_values(monkeypatch):
    monkeypatch.delenv("GPU_PROFILE", raising=False)
    mod = _reload_config()
    try:
        cfg = mod.Config()
        assert cfg.gpu_profile == "l4"
        assert cfg.vllm_config == {
            "gpu_memory_utilization": 0.55,
            "max_model_len": 4096,
            "dtype": "half",
            "quantization": "awq",
            "enforce_eager": True,
        }
    finally:
        _reload_config()


def test_gpu_profile_a100_selects_distinct_higher_utilization_profile(monkeypatch):
    monkeypatch.setenv("GPU_PROFILE", "a100")
    mod = _reload_config()
    try:
        cfg = mod.Config()
        assert cfg.gpu_profile == "a100"
        assert cfg.vllm_config["gpu_memory_utilization"] == 0.85
        # Fixed keys are not profile-dependent -- unchanged regardless of tier.
        assert cfg.vllm_config["dtype"] == "half"
        assert cfg.vllm_config["quantization"] == "awq"
        assert cfg.vllm_config["enforce_eager"] is True
        # Proves this is a genuine dict-lookup swap, not the l4 defaults.
        assert cfg.vllm_config["gpu_memory_utilization"] != 0.55
    finally:
        _reload_config()


def test_unrecognized_gpu_profile_falls_back_to_l4_never_raises(monkeypatch):
    monkeypatch.setenv("GPU_PROFILE", "bogus-tier")
    mod = _reload_config()
    try:
        cfg = mod.Config()  # must not raise
        assert cfg.gpu_profile == "l4"
        assert cfg.vllm_config["gpu_memory_utilization"] == 0.55
        assert cfg.vllm_config["max_model_len"] == 4096
    finally:
        _reload_config()


@pytest.mark.parametrize(
    ("gpu_profile", "expected_utilization"),
    (("l4", 0.55), ("a100", 0.85)),
)
def test_text_max_model_len_absent_preserves_profile_defaults(
    monkeypatch, gpu_profile, expected_utilization
):
    monkeypatch.setenv("GPU_PROFILE", gpu_profile)
    monkeypatch.delenv("TEXT_MAX_MODEL_LEN", raising=False)
    mod = _reload_config()
    try:
        cfg = mod.Config()
        assert cfg.gpu_profile == gpu_profile
        assert cfg.vllm_config == {
            "gpu_memory_utilization": expected_utilization,
            "max_model_len": 4096,
            "dtype": "half",
            "quantization": "awq",
            "enforce_eager": True,
        }
    finally:
        monkeypatch.delenv("TEXT_MAX_MODEL_LEN", raising=False)
        monkeypatch.delenv("GPU_PROFILE", raising=False)
        _reload_config()


def test_text_max_model_len_explicit_override_changes_only_context_length(monkeypatch):
    monkeypatch.setenv("GPU_PROFILE", "a100")
    monkeypatch.setenv("TEXT_MAX_MODEL_LEN", "8192")
    mod = _reload_config()
    try:
        cfg = mod.Config()
        assert cfg.gpu_profile == "a100"
        assert cfg.vllm_config == {
            "gpu_memory_utilization": 0.85,
            "max_model_len": 8192,
            "dtype": "half",
            "quantization": "awq",
            "enforce_eager": True,
        }
    finally:
        monkeypatch.delenv("TEXT_MAX_MODEL_LEN", raising=False)
        monkeypatch.delenv("GPU_PROFILE", raising=False)
        _reload_config()


@pytest.mark.parametrize("invalid_value", ("not-an-integer", "0"))
def test_text_max_model_len_rejects_invalid_explicit_values(monkeypatch, invalid_value):
    monkeypatch.delenv("GPU_PROFILE", raising=False)
    monkeypatch.setenv("TEXT_MAX_MODEL_LEN", invalid_value)
    mod = _reload_config()
    try:
        with pytest.raises(ValueError, match="TEXT_MAX_MODEL_LEN"):
            mod.Config()
    finally:
        monkeypatch.delenv("TEXT_MAX_MODEL_LEN", raising=False)
        monkeypatch.delenv("GPU_PROFILE", raising=False)
        _reload_config()
