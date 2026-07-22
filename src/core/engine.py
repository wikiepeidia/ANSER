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
    """
    Singleton quản lý 2 model trên 1 GPU L4 22.5GB:
      - Text reasoning: Qwen2.5-7B-Instruct-AWQ qua vLLM.
      - Vision/VLM:    Qwen2-VL-2B-Instruct qua transformers (NẰM NGOÀI pool vLLM).

    LƯU Ý KIẾN TRÚC: đây là NGUỒN VISION DUY NHẤT. VisionAgent (vision.py) PHẢI
    gọi engine.generate_vision(...) thay vì tự load Florence-2 riêng — nếu không sẽ
    nạp 2 model vision song song và lãng phí ~4.5GB VRAM.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            inst = super(ModelEngine, cls).__new__(cls)
            try:
                inst._initialize()
            except Exception:
                # Không giữ instance hỏng — lần gọi sau sẽ thử khởi tạo lại
                cls._instance = None
                raise
            cls._instance = inst
        return cls._instance

    def _initialize(self):
        self.env = os.getenv("ENV", "LOCAL").upper()
        self.config = Config()

        if self.env == "LOCAL":
            logger.info("Booting LOCAL mock engine (không load model thật)")
            self.llm = None
            self.vision_model = None
            self.vision_processor = None
            logger.info("Mock engine online")
            return

        logger.info("Booting COLAB engine — target GPU L4 22.5GB")

        import torch
        from vllm import LLM
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        # 1) Text brain — vLLM.
        #    gpu_memory_utilization là TỔNG ngân sách vLLM (weights + activation + KV-cache).
        vc = self.config.vllm_config
        logger.info(
            "Loading text model: %s (util=%.2f, max_len=%d, quant=%s)",
            self.config.text_model_id,
            vc["gpu_memory_utilization"],
            vc["max_model_len"],
            vc.get("quantization"),
        )
        self.llm = LLM(
            model=self.config.text_model_id,
            gpu_memory_utilization=vc["gpu_memory_utilization"],
            max_model_len=vc["max_model_len"],
            dtype=vc["dtype"],
            quantization=vc.get("quantization"),   # AWQ phải khai báo rõ
            enforce_eager=vc.get("enforce_eager", False),  # fix CUDA graph bug với Qwen
            trust_remote_code=True,
        )

        # 2) Vision eye — transformers, load vào phần VRAM CÒN LẠI ngoài pool vLLM.
        #    FP bf16 ~4.5GB (khớp config.vision_model_id mặc định).
        #    Nếu đổi config sang bản -AWQ thì bỏ torch_dtype và để model tự dùng quant config.
        logger.info("Loading vision model: %s", self.config.vision_model_id)
        self.vision_model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.config.vision_model_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
        )
        self.vision_model.eval()
        self.vision_processor = AutoProcessor.from_pretrained(self.config.vision_model_id)

        logger.info("Unified engine online (text + vision)")

    # ------------------------------------------------------------------
    # TEXT
    # ------------------------------------------------------------------
    async def generate_text(self, prompt, max_tokens=1024, temperature=0.1):
        """Sinh text bất đồng bộ. LOCAL trả mock không block ASGI loop."""
        if self.env == "LOCAL":
            await asyncio.sleep(0.05)
            return '{"mock_response": "LOCAL mock text response."}'

        from vllm import SamplingParams

        loop = asyncio.get_running_loop()
        params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            repetition_penalty=1.15,   # ngăn model lặp câu
        )

        def _blocking_generate():
            outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()

        # vLLM generate là blocking -> đẩy ra thread pool để không nghẽn event loop
        return await loop.run_in_executor(None, _blocking_generate)

    async def generate_chat(self, system: str, user: str, max_tokens=1024, temperature=0.1):
        """
        Sinh text theo ĐÚNG định dạng chat của Qwen.
        Tự dựng messages [system, user] rồi để tokenizer.apply_chat_template chèn
        token ChatML chuẩn — KHÔNG nhúng tay <|im_start|> trong prompt nữa.
        """
        if self.env == "LOCAL":
            await asyncio.sleep(0.05)
            return '{"mock_response": "LOCAL mock chat response."}'

        from vllm import SamplingParams

        loop = asyncio.get_running_loop()
        params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            repetition_penalty=1.15,   # ngăn model lặp câu
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        def _blocking_generate():
            tokenizer = self.llm.get_tokenizer()
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            outputs = self.llm.generate([prompt], params)
            return outputs[0].outputs[0].text.strip()

        return await loop.run_in_executor(None, _blocking_generate)

    # ------------------------------------------------------------------
    # VISION  (method MỚI — để vision_model không còn là "dead load")
    # ------------------------------------------------------------------
    async def generate_vision(self, image_path: str, prompt: str, max_new_tokens: int = 512):
        """
        Chạy Qwen2-VL trên 1 ảnh + prompt, trả về text.
        Bất đồng bộ: inference nặng được đẩy ra thread pool (không block event loop).
        """
        if self.env == "LOCAL":
            await asyncio.sleep(0.05)
            return '{"mock_vision": "LOCAL mock OCR/caption result."}'

        loop = asyncio.get_running_loop()

        def _blocking_vision():
            import torch
            from qwen_vl_utils import process_vision_info

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt},
                ],
            }]
            text = self.vision_processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.vision_processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(self.vision_model.device)

            with torch.no_grad():
                generated = self.vision_model.generate(**inputs, max_new_tokens=max_new_tokens)
            trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
            return self.vision_processor.batch_decode(
                trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0].strip()

        return await loop.run_in_executor(None, _blocking_vision)

    # ------------------------------------------------------------------
    # BACKGROUND
    # ------------------------------------------------------------------
    async def background_worker(self, task_id: str, handler_func, *args, **kwargs):
        """Worker nền. handler_func PHẢI là async coroutine. Cập nhật TASK_REGISTRY."""
        try:
            TASK_REGISTRY.set(task_id, {"status": "running"})
            result = await handler_func(*args, **kwargs)
            TASK_REGISTRY.set(task_id, {"status": "completed", "result": result})
        except Exception as e:
            logger.exception("Error in background worker for task %s: %s", task_id, e)
            TASK_REGISTRY.set(task_id, {"status": "failed", "error": str(e)})