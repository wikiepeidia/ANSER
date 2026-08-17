import os
import asyncio
import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path, PurePosixPath, PureWindowsPath

from src.core.config import Config

logger = logging.getLogger("projecta.engine")


def _looks_like_local_model_source(model_source: str) -> bool:
    """Recognize explicit local paths without misclassifying Hub ``owner/repo`` IDs."""
    return (
        PurePosixPath(model_source).is_absolute()
        or PureWindowsPath(model_source).is_absolute()
        or model_source.startswith(("./", "../", ".\\", "..\\", "~"))
    )


def validate_text_model_source(model_source: str) -> str:
    """Fail fast when ``TEXT_MODEL_ID`` names a missing/incomplete local export.

    Hugging Face accepts either a Hub repo ID or a local model directory. When an
    absolute Colab Drive path is missing, its downstream validator interprets the
    string as a repo ID and emits a misleading repository-name error. Validate only
    explicit local-looking paths here; legitimate ``owner/repo`` IDs pass through.
    """
    model_source = model_source.strip()
    if not model_source:
        raise ValueError("TEXT_MODEL_ID is empty; set it to a Hub repo ID or model directory.")
    if not _looks_like_local_model_source(model_source):
        return model_source

    model_dir = Path(model_source).expanduser()
    if not model_dir.is_dir():
        raise FileNotFoundError(
            "TEXT_MODEL_ID points to a local model directory that does not exist: "
            f"{model_source}. Mount the Google Drive account containing ANSER_data "
            "or copy the complete quantized model export to this directory before "
            "starting the server. To load from Hugging Face Hub instead, set "
            "TEXT_MODEL_ID to an owner/repo ID."
        )

    missing_artifacts = []
    if not (model_dir / "config.json").is_file():
        missing_artifacts.append("config.json")
    if not any(
        path.is_file()
        for pattern in ("*.safetensors", "*.bin", "*.pt")
        for path in model_dir.glob(pattern)
    ):
        missing_artifacts.append("model weights (*.safetensors/*.bin/*.pt)")
    if not any(
        (model_dir / filename).is_file()
        for filename in ("tokenizer.json", "tokenizer.model", "spiece.model", "vocab.json")
    ):
        missing_artifacts.append("tokenizer artifact")

    if missing_artifacts:
        raise FileNotFoundError(
            f"TEXT_MODEL_ID local model directory is incomplete: {model_source}. "
            f"Missing: {', '.join(missing_artifacts)}. Re-copy the complete AWQ export; "
            "creating an empty directory is not sufficient."
        )

    return str(model_dir)


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
        # Shared lock around every GPU inference section. vLLM's synchronous
        # LLM.generate() is not thread-safe, and Qwen2-VL runs through the same
        # default ThreadPoolExecutor on the same CUDA device. A chat endpoint can
        # return its task id while vLLM is still generating; an OCR request may
        # then enter Qwen2-VL concurrently. Serializing the device transfer and
        # generation sections prevents the two runtimes from racing for the same
        # CUDA context/allocator while keeping CPU preprocessing, routing, RAG,
        # database work, and the ASGI event loop concurrent.
        self._generate_lock = threading.Lock()

        if self.env == "LOCAL":
            logger.info("Booting LOCAL mock engine (không load model thật)")
            self.llm = None
            self.vision_model = None
            self.vision_processor = None
            logger.info("Mock engine online")
            return

        logger.info("Booting COLAB engine — target GPU L4 22.5GB")

        text_model_source = validate_text_model_source(self.config.text_model_id)

        import torch
        from vllm import LLM
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        # 1) Text brain — vLLM.
        #    gpu_memory_utilization là TỔNG ngân sách vLLM (weights + activation + KV-cache).
        vc = self.config.vllm_config
        logger.info(
            "Loading text model: %s (util=%.2f, max_len=%d, quant=%s)",
            text_model_source,
            vc["gpu_memory_utilization"],
            vc["max_model_len"],
            vc.get("quantization"),
        )
        self.llm = LLM(
            model=text_model_source,
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
            repetition_penalty=1.25,     # Ngày 7: 1.15 chưa đủ, model vẫn lặp nguyên câu
        )

        def _blocking_generate():
            with self._generate_lock:
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
            repetition_penalty=1.25,     # Ngày 7: 1.15 chưa đủ, model vẫn lặp nguyên câu
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
            with self._generate_lock:
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
            )

            # The processor work above is CPU-only. Hold the same lock used by
            # vLLM from the first device transfer through decode so no other
            # Qwen/vLLM call can overlap this request's live CUDA tensors. The
            # context manager releases the lock even when model.generate raises.
            with self._generate_lock:
                device_inputs = inputs.to(self.vision_model.device)
                try:
                    with torch.no_grad():
                        generated = self.vision_model.generate(
                            **device_inputs,
                            max_new_tokens=max_new_tokens,
                        )
                    trimmed = [
                        out[len(inp):]
                        for inp, out in zip(device_inputs.input_ids, generated)
                    ]
                    return self.vision_processor.batch_decode(
                        trimmed,
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=False,
                    )[0].strip()
                finally:
                    # Drop request-local CUDA tensor references before another
                    # inference acquires the lock. Do not call empty_cache():
                    # vLLM owns a persistent KV cache in the same process.
                    del device_inputs

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
