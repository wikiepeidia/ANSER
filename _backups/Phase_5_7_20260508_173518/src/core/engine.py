
import os
import asyncio
import logging
import threading
import time
from collections import OrderedDict
from src.core.config import Config

logger = logging.getLogger("projecta.engine")


class TaskRegistry:
    """Thread-safe, bounded task registry with FIFO eviction."""

    def __init__(self, max_size: int = 1000):
        self._store: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size

    def get(self, task_id: str):
        with self._lock:
            entry = self._store.get(task_id)
            if entry is None:
                return None
            return dict(entry)  # return a copy

    def set(self, task_id: str, data: dict):
        with self._lock:
            data["_created_at"] = data.get("_created_at", time.time())
            self._store[task_id] = data
            # FIFO eviction when over capacity
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def __contains__(self, task_id: str):
        with self._lock:
            return task_id in self._store


TASK_REGISTRY = TaskRegistry(max_size=1000)


class ModelEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.env = os.getenv("ENV", "LOCAL").upper()
        if self.env == "LOCAL":
            print("🚀 [Engine] Booting LOCAL Mock Architecture...")
            self.llm = None
            self.vision_model = None
            self.vision_processor = None
            print("✅ Mock Engine Online.")
            return

        print("🚀 [Engine] Booting Heavyweight Architecture (A100)...")
        self.config = Config()
        
        # 1. Load Text Brain (vLLM)
        # vLLM manages its own memory pool. We give it 50% of the A100.
        from vllm import LLM, SamplingParams
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        import torch

        print(f"🧠 Loading Brain: {self.config.text_model_id}...")
        self.llm = LLM(
            model=self.config.text_model_id,
            gpu_memory_utilization=self.config.vllm_config['gpu_memory_utilization'],
            max_model_len=self.config.vllm_config['max_model_len'],
            dtype=self.config.vllm_config['dtype'],
            trust_remote_code=True
        )
        
        # 2. Load Vision Eye (Transformers)
        # We load this into the REMAINING GPU memory.
        print(f"👁️ Loading Eye: {self.config.vision_model_id}...")
        self.vision_model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.config.vision_model_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
        )
        self.vision_processor = AutoProcessor.from_pretrained(self.config.vision_model_id)
        
        print("✅ Unified Engine Online.")

    async def generate_text(self, prompt, max_tokens=1024, temperature=0.1):
        """Async text generation. LOCAL mock uses non-blocking sleep."""
        if self.env == "LOCAL":
            # Non-blocking delay to simulate inference without freezing the ASGI loop
            await asyncio.sleep(0.05)
            return '{"mock_response": "This is a mock response respecting the 6GB VRAM limit."}'
            
        # vLLM generation is CPU-bound — offload to thread pool to avoid blocking
        from vllm import SamplingParams
        loop = asyncio.get_running_loop()
        params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
        
        def _blocking_generate():
            outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()
        
        return await loop.run_in_executor(None, _blocking_generate)

    async def background_worker(self, task_id: str, handler_func, *args, **kwargs):
        """
        Async background worker. handler_func MUST be an async coroutine.
        Updates TASK_REGISTRY on completion or failure.
        """
        try:
            TASK_REGISTRY.set(task_id, {"status": "running"})
            result = await handler_func(*args, **kwargs)
            TASK_REGISTRY.set(task_id, {"status": "completed", "result": result})
        except Exception as e:
            logger.exception(f"Error in background worker for task {task_id}: {e}")
            TASK_REGISTRY.set(task_id, {"status": "failed", "error": str(e)})
