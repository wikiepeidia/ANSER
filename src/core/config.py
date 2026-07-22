import os

from src.core.prompts import Prompts


class Config:
    """
    Cấu hình ANSER_AI (Brain) — tối ưu cho Google Colab Pro, GPU L4 22.5GB.
    Mọi con số VRAM dưới đây là ƯỚC TÍNH; phải đo lại bằng nvidia-smi /
    torch.cuda.memory_allocated() trên L4 thật rồi tinh chỉnh.
    """

    def __init__(self):
        # ----------------------------- Paths -----------------------------
        self.PROJECT_ROOT = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.DATA_DIR = os.path.join(self.PROJECT_ROOT, "src", "data")
        self.DOCS_DIR = os.path.join(self.DATA_DIR, "docs")
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.DOCS_DIR, exist_ok=True)

        # --------------------------- Database ----------------------------
        raw_url = os.getenv("DATABASE_URL", "")
        if raw_url.startswith("postgres://"):
            self.DB_URL = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif raw_url.startswith("postgresql://"):
            self.DB_URL = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            self.DB_URL = "sqlite:///:memory:"

        # ------------------------ System context -------------------------
        self.SYSTEM_CONTEXT = Prompts.SYSTEM_CONTEXT

        # =================================================================
        #  NGÂN SÁCH VRAM — GPU L4 22.5GB (Colab Pro)
        #  Đệm an toàn ~19.5GB (chừa ~3GB cho CUDA context/driver/allocator).
        # -----------------------------------------------------------------
        #  Thành phần        Model                      Định dạng    VRAM
        #  Text weights      anser-qwen-distill-awq     AWQ 4-bit    ~5.5GB  ┐ trong vLLM
        #  KV-cache+activ.   —                          —            ~6.5GB  ┘ (~12.0GB)
        #  Vision/VLM        Qwen2-VL-2B-Instruct       FP16(bf16)   ~4.5GB  ┐
        #  Embedding         paraphrase-MiniLM-L12-v2   FP16         ~0.5GB  │ ngoài vLLM
        #  Reranker          ms-marco-MiniLM-L-6-v2     FP16         ~0.3GB  │ (~6.3GB)
        #  ChromaDB (hot)    —                          —            ~1.0GB  ┘
        # -----------------------------------------------------------------
        #  TỔNG ~18.3GB < 19.5GB ✓
        # =================================================================

        # --- Brain: Text reasoning (chạy qua vLLM) ---
        # Dùng env var TEXT_MODEL_ID để linh hoạt mọi môi trường:
        #   Colab : export TEXT_MODEL_ID=/content/drive/MyDrive/ANSER_data/anser-qwen-distill-awq
        #   Server: export TEXT_MODEL_ID=/app/models/anser-qwen-distill-awq
        #   Mặc định fallback về HuggingFace Hub nếu không set.
        self.text_model_id = os.getenv(
            "TEXT_MODEL_ID",
            "/content/drive/MyDrive/ANSER_data/anser-retail-v2-awq"
        )

        # --- Eye: Vision/VLM (load riêng qua transformers, ngoài vLLM) ---
        self.vision_model_id = "Qwen/Qwen2-VL-2B-Instruct"

        # --- RAG: Embedding + Reranker ---
        self.embedding_model_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.reranker_model_id  = "cross-encoder/ms-marco-MiniLM-L-6-v2"

        # =================================================================
        #  vLLM CONFIG
        # -----------------------------------------------------------------
        #  gpu_memory_utilization = PHẦN TỔNG VRAM dành cho vLLM
        #     0.55 × 22.5GB ≈ 12.4GB cho vLLM
        #       ├─ weights 7B-AWQ ........ ~5.5GB
        #       └─ KV-cache + activation . ~6.5GB
        #
        #  enforce_eager=True: tắt CUDA graphs — fix lỗi
        #  "Forward context is not set" của vLLM + Qwen trên Colab.
        # =================================================================
        self.vllm_config = {
            "gpu_memory_utilization": 0.55,
            "max_model_len":          4096,
            "dtype":                  "half",
            "quantization":           "awq",
            "enforce_eager":          True,   # fix vLLM + Qwen CUDA graph bug
        }