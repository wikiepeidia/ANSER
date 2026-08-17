"""
Regression test for ENGINE-03 ("AI replies to itself").

Root cause: ModelEngine.generate_text/generate_chat dispatch vLLM's synchronous,
non-thread-safe self.llm.generate() via loop.run_in_executor()'s default
multi-threaded ThreadPoolExecutor. Two concurrent chat requests (e.g. two
different store_id tenants) can call self.llm.generate() on the same shared
engine instance from two different OS threads simultaneously — a documented
-unsafe vLLM usage pattern and the most plausible mechanism for one request
receiving another's output.

This test proves two concurrent generate_text/generate_chat calls never let
their underlying self.llm.generate() calls overlap in wall-clock time.

Uses a bare ModelEngine instance built via object.__new__() to bypass the
singleton and _initialize() entirely, since the real vLLM/transformers stack
is not installed on this Windows dev machine. A stub `vllm` module is
registered in sys.modules before importing src.core.engine, since
generate_text/generate_chat's inline `from vllm import SamplingParams` must
resolve against something importable outside Colab.
"""

import os
import sys
import time
import asyncio
import threading
import types
from pathlib import Path

# Force LOCAL env var (mirrors tests/test_server.py's existing setup pattern) —
# not actually relied on for this test's engine instance (we set engine.env
# directly to a non-"LOCAL" value below so the real, non-mock code path runs),
# but kept for consistency with the rest of the test suite's import-time setup.
os.environ["ENV"] = "LOCAL"

# Add project root to sys.path using pathlib (mirrors tests/test_server.py)
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Register a stub `vllm` module in sys.modules BEFORE importing src.core.engine.
# The real vllm package has no Windows wheel and is not importable outside
# Colab, so generate_text/generate_chat's inline `from vllm import SamplingParams`
# must resolve against this stub instead of raising ImportError.
if "vllm" not in sys.modules:
    _vllm_stub = types.ModuleType("vllm")

    class _StubSamplingParams:
        """No-op stand-in for vllm.SamplingParams — accepts any kwargs."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    _vllm_stub.SamplingParams = _StubSamplingParams
    sys.modules["vllm"] = _vllm_stub

from src.core.engine import ModelEngine  # noqa: E402


def _intervals_overlap(a, b):
    """True if half-open wall-clock intervals a=(start,end), b=(start,end) overlap."""
    return a[0] < b[1] and b[0] < a[1]


class _FakeOutputItem:
    def __init__(self, text):
        self.outputs = [types.SimpleNamespace(text=text)]


class _FakeTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "FAKE_CHAT_TEMPLATE_PROMPT"


class FakeLLM:
    """
    Stand-in for vLLM's LLM instance. generate() sleeps 0.2s and records
    (start, end) time.monotonic() timestamps into a shared list before
    returning a vLLM-shaped output object — the sleep forces a genuine
    overlap window across the real OS threads the default ThreadPoolExecutor
    uses, so a missing/broken lock is caught deterministically rather than
    depending on timing luck.
    """

    def __init__(self):
        self.calls = []  # shared list of (start, end) monotonic timestamps

    def generate(self, prompts, params):
        start = time.monotonic()
        time.sleep(0.2)
        end = time.monotonic()
        self.calls.append((start, end))
        return [_FakeOutputItem(f"generated:{prompts[0]}")]

    def get_tokenizer(self):
        return _FakeTokenizer()


class _FakeVisionInputs(dict):
    """Mapping-shaped processor result; never allocates a real tensor/GPU."""

    def __init__(self):
        super().__init__(input_ids=[[1, 2]])
        self.input_ids = self["input_ids"]

    def to(self, device):
        self.device = device
        return self


class _FakeVisionProcessor:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "FAKE_VISION_PROMPT"

    def __call__(self, **kwargs):
        return _FakeVisionInputs()

    def batch_decode(self, outputs, **kwargs):
        return ["generated:vision"]


class _FakeVisionModel:
    device = "fake-cuda"

    def __init__(self, *, fail=False):
        self.calls = []
        self.fail = fail

    def generate(self, **kwargs):
        start = time.monotonic()
        time.sleep(0.2)
        end = time.monotonic()
        self.calls.append((start, end))
        if self.fail:
            raise RuntimeError("fake vision failure")
        return [[1, 2, 3]]


class _NoGrad:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _install_vision_stubs(monkeypatch):
    torch_stub = types.ModuleType("torch")
    torch_stub.no_grad = _NoGrad
    monkeypatch.setitem(sys.modules, "torch", torch_stub)

    qwen_utils_stub = types.ModuleType("qwen_vl_utils")
    qwen_utils_stub.process_vision_info = lambda messages: (["fake-image"], None)
    monkeypatch.setitem(sys.modules, "qwen_vl_utils", qwen_utils_stub)


def test_concurrent_generate_calls_do_not_overlap():
    # Bypass the singleton and _initialize() entirely — construct a bare
    # instance and wire up just what generate_text/generate_chat touch.
    engine = object.__new__(ModelEngine)
    engine.env = "COLAB"  # non-"LOCAL" so the real (non-mock) code path executes
    engine.llm = FakeLLM()
    # _initialize() is bypassed by construction (see module docstring), so
    # replicate the one other instance attribute generate_text/generate_chat's
    # _blocking_generate closures depend on: the shared _generate_lock. Before
    # the ENGINE-03 fix lands, _blocking_generate() never references this
    # attribute at all, so its presence here does not mask the race — the
    # overlap assertion below still fails against unfixed code exactly as it
    # did before this attribute existed.
    engine._generate_lock = threading.Lock()

    async def _run_concurrent():
        return await asyncio.gather(
            engine.generate_text("hello text prompt"),
            engine.generate_chat("system prompt", "user prompt"),
        )

    text_result, chat_result = asyncio.run(_run_concurrent())

    assert text_result == "generated:hello text prompt"
    assert chat_result == "generated:FAKE_CHAT_TEMPLATE_PROMPT"

    calls = engine.llm.calls
    assert len(calls) == 2, (
        f"Expected exactly 2 recorded self.llm.generate() calls, got {len(calls)}: {calls}"
    )

    a, b = calls
    assert not _intervals_overlap(a, b), (
        "ModelEngine.generate_text and ModelEngine.generate_chat's underlying "
        "self.llm.generate() calls overlapped in wall-clock time "
        f"(interval {a} overlaps interval {b}). This means "
        "ModelEngine._generate_lock is missing or not shared by both "
        "generate_text's and generate_chat's _blocking_generate closures — "
        "the exact 'AI replies to itself' race (ENGINE-03)."
    )


def test_text_and_vision_gpu_calls_do_not_overlap(monkeypatch):
    """vLLM and Qwen2-VL must never execute concurrently on the shared GPU."""
    _install_vision_stubs(monkeypatch)

    engine = object.__new__(ModelEngine)
    engine.env = "COLAB"
    engine.llm = FakeLLM()
    engine.vision_model = _FakeVisionModel()
    engine.vision_processor = _FakeVisionProcessor()
    engine._generate_lock = threading.Lock()

    async def _run_concurrent():
        return await asyncio.gather(
            engine.generate_text("hello text prompt"),
            engine.generate_vision("fake.png", "read image"),
        )

    text_result, vision_result = asyncio.run(_run_concurrent())

    assert text_result == "generated:hello text prompt"
    assert vision_result == "generated:vision"
    assert len(engine.llm.calls) == 1
    assert len(engine.vision_model.calls) == 1
    assert not _intervals_overlap(engine.llm.calls[0], engine.vision_model.calls[0]), (
        "vLLM text generation overlapped Qwen2-VL generation on the same GPU. "
        "All GPU inference paths must share ModelEngine._generate_lock."
    )


def test_vision_failure_releases_shared_gpu_lock(monkeypatch):
    """An exception in Qwen2-VL must not permanently block later text work."""
    _install_vision_stubs(monkeypatch)

    engine = object.__new__(ModelEngine)
    engine.env = "COLAB"
    engine.llm = FakeLLM()
    engine.vision_model = _FakeVisionModel(fail=True)
    engine.vision_processor = _FakeVisionProcessor()
    engine._generate_lock = threading.Lock()

    async def _run_after_failure():
        try:
            await engine.generate_vision("fake.png", "read image")
        except RuntimeError as exc:
            assert str(exc) == "fake vision failure"
        else:
            raise AssertionError("fake vision call should fail")

        return await asyncio.wait_for(
            engine.generate_text("text after vision failure"),
            timeout=2.0,
        )

    assert asyncio.run(_run_after_failure()) == "generated:text after vision failure"
