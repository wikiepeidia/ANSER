import os

from src.core.prompts import Prompts

# GPU_PROFILE selects which vllm_config sizing tier to use (l4/a100), so a
# future GPU tier can be added by extending the _VLLM_PROFILES table below --
# never by adding another if/elif branch. Unset -> "l4" (today's
# real-hardware-proven default). An unrecognized value falls back to "l4"
# rather than raising, since a live Colab session's env var typo should never
# crash boot.
GPU_PROFILE = os.getenv("GPU_PROFILE", "l4").strip().lower()

# Per-tier vLLM sizing. The "l4" entry is unchanged from the values this
# repo's own prior real-L4 execution log proved safe (vLLM's own startup log:
# total_gpu_memory 22.03GiB x gpu_memory_utilization 0.55 = 12.12GiB, model
# weights ~5.20GiB + KV-cache ~5.45GiB -- comfortably fits). The "a100" entry
# is a provisional starting point (more headroom for dev/test-speed
# iteration per AI-OPS-02) pending Plan 02's live confirmation/tuning --
# not a final tuned number.
_VLLM_PROFILES = {
    "l4":   {"gpu_memory_utilization": 0.55, "max_model_len": 4096},
    "a100": {"gpu_memory_utilization": 0.85, "max_model_len": 4096},
}


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
        #  Reranker          bge-reranker-v2-m3         FP16         ~1.6GB  │ (~7.6GB)
        #  ChromaDB (hot)    —                          —            ~1.0GB  ┘
        # -----------------------------------------------------------------
        #  TỔNG ~19.6GB > 19.5GB ✗ (Phase 6 RAG-01: multilingual reranker
        #  swap raised the reranker's footprint from ~0.3GB to ~1.6GB fp16 to
        #  fix an English-only-reranker correctness bug on Vietnamese
        #  queries.) This estimate now sits ABOVE the previously-documented
        #  ~19.5GB safety margin -- it is unverified against a real L4 and
        #  MUST be re-measured live (nvidia-smi / torch.cuda.memory_allocated)
        #  before Phase 8's gpu_memory_utilization/max_model_len tuning work,
        #  which is sequenced after this phase for exactly this reason.
        #
        #  Phase 9 (AI-OPS-02): `GPU_PROFILE` (module-level, above) now
        #  selects between L4 (steady-state, default) and A100 (dev/test
        #  speed) sizing tiers via the `_VLLM_PROFILES` table lookup below --
        #  the l4 numbers are unchanged/real-hardware-proven; the a100
        #  numbers are a provisional starting point pending live
        #  confirmation. `RERANKER_DEVICE` (see knowledge.py) is the other,
        #  independent lever for trimming the non-vLLM VRAM total above.
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
        self.reranker_model_id  = "BAAI/bge-reranker-v2-m3"

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
        #
        #  gpu_memory_utilization/max_model_len are selected from
        #  _VLLM_PROFILES via GPU_PROFILE (l4 default, a100 opt-in). An
        #  explicit positive TEXT_MAX_MODEL_LEN overrides only max_model_len;
        #  when absent, both profiles retain the proven 4096 default. The
        #  remaining keys (dtype/quantization/enforce_eager) are fixed, not
        #  profile-dependent.
        # =================================================================
        self.gpu_profile = GPU_PROFILE if GPU_PROFILE in _VLLM_PROFILES else "l4"
        _profile = _VLLM_PROFILES[self.gpu_profile]
        _max_model_len = _profile["max_model_len"]
        _raw_max_model_len = os.getenv("TEXT_MAX_MODEL_LEN")
        if _raw_max_model_len is not None:
            try:
                _max_model_len = int(_raw_max_model_len.strip())
            except ValueError:
                raise ValueError(
                    "TEXT_MAX_MODEL_LEN must be a positive integer"
                ) from None
            if _max_model_len < 1:
                raise ValueError("TEXT_MAX_MODEL_LEN must be a positive integer")

        self.vllm_config = {
            **_profile,
            "max_model_len":          _max_model_len,
            "dtype":                  "half",
            "quantization":           "awq",
            "enforce_eager":          True,   # fix vLLM + Qwen CUDA graph bug
        }
