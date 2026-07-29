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


def test_concurrent_generate_calls_do_not_overlap():
    # Bypass the singleton and _initialize() entirely — construct a bare
    # instance and wire up just what generate_text/generate_chat touch.
    engine = object.__new__(ModelEngine)
    engine.env = "COLAB"  # non-"LOCAL" so the real (non-mock) code path executes
    engine.llm = FakeLLM()

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
