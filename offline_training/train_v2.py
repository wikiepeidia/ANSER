"""
train_v2.py — NGÀY 5, bước 2
Huấn luyện lại Qwen2.5-7B từ MÔ HÌNH GỐC với train_retail_v2.jsonl

Vì sao train từ gốc thay vì tiếp tục checkpoint cũ:
  Model v1 đã hình thành thói quen trả lời như trợ lý tổng quát.
  Train tiếp lên đó sẽ mang theo thói quen này.

CHẠY TRONG COLAB (không chạy bằng !python vì cần GPU trong cùng process):
  exec(open('/content/ANSER_AI_FIX/offline_training/train_v2.py').read())
"""
import json, os, torch, gc
from pathlib import Path

ROOT = Path("/content/ANSER_AI_FIX")
DATA_FILE = ROOT / "src" / "data" / "train_retail_v2.jsonl"
OUT_DIR   = "/content/checkpoints/anser-retail-v2"
LORA_DIR  = "/content/checkpoints/anser-retail-v2-lora"

# ── 1. Kiểm tra môi trường ──────────────────────────────────────────────
assert torch.cuda.is_available(), "Không thấy GPU"
gpu = torch.cuda.get_device_name(0)
vram = torch.cuda.get_device_properties(0).total_memory / 1e9
print(f"GPU  : {gpu}")
print(f"VRAM : {vram:.1f} GB")

assert DATA_FILE.exists(), f"Thiếu {DATA_FILE} — chạy merge_all.py trước"
n_samples = sum(1 for l in DATA_FILE.read_text(encoding="utf-8").splitlines() if l.strip())
print(f"Data : {n_samples} mẫu\n")

# ── 2. Tải mô hình gốc ──────────────────────────────────────────────────
from modelscope import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from trl import SFTTrainer, SFTConfig

print("Tải Qwen2.5-7B-Instruct...")
model_path = snapshot_download('qwen/Qwen2.5-7B-Instruct', cache_dir='/content/models')
print(f"✓ {model_path}\n")

tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    ),
    device_map="auto",
    trust_remote_code=True,
)
print(f"✓ Model loaded | VRAM dùng: {torch.cuda.memory_allocated()/1e9:.1f} GB\n")

# ── 3. Gắn LoRA ─────────────────────────────────────────────────────────
model = get_peft_model(model, LoraConfig(
    r=64,
    lora_alpha=128,
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
))
model.enable_input_require_grads()
model.print_trainable_parameters()
print()

# ── 4. Chuẩn bị dataset ─────────────────────────────────────────────────
data = [json.loads(l) for l in
        DATA_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]

texts = [tokenizer.apply_chat_template(
             d["messages"], tokenize=False, add_generation_prompt=False)
         for d in data]

# Thống kê độ dài để chọn max_seq_length hợp lý
lengths = [len(tokenizer(t)["input_ids"]) for t in texts[:200]]
p95 = sorted(lengths)[int(len(lengths) * 0.95)]
print(f"Độ dài token (mẫu 200):")
print(f"  Trung bình : {sum(lengths)//len(lengths):,}")
print(f"  Phân vị 95 : {p95:,}")
print(f"  Tối đa     : {max(lengths):,}")

MAX_LEN = 4096
n_truncated = sum(1 for l in lengths if l > MAX_LEN)
if n_truncated:
    print(f"  ⚠ {n_truncated/len(lengths)*100:.0f}% mẫu vượt {MAX_LEN} token, sẽ bị cắt")
print()

dataset = Dataset.from_dict({"text": texts})
print(f"✓ Dataset: {len(dataset)} mẫu\n")

# ── 5. Trainer ──────────────────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        dataset_text_field          = "text",
        max_seq_length              = MAX_LEN,
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 8,      # lô hiệu dụng 16
        num_train_epochs            = 3,
        learning_rate               = 2e-4,
        lr_scheduler_type           = "cosine",
        warmup_ratio                = 0.05,
        bf16                        = True,
        logging_steps               = 10,
        save_steps                  = 100,
        save_total_limit            = 2,
        output_dir                  = OUT_DIR,
        optim                       = "paged_adamw_8bit",
        report_to                   = "none",
    ),
)

steps = len(dataset) * 3 // 16
print(f"Số bước dự kiến: ~{steps}")
print(f"Thời gian ước tính: ~{steps * 3 / 60:.0f} phút\n")
print("🚀 Bắt đầu huấn luyện...\n")

trainer.train()

# ── 6. Lưu ──────────────────────────────────────────────────────────────
model.save_pretrained(LORA_DIR)
tokenizer.save_pretrained(LORA_DIR)

size = sum(f.stat().st_size for f in Path(LORA_DIR).rglob('*') if f.is_file()) / 1e6
print(f"\n{'='*54}")
print(f"  HUẤN LUYỆN XONG")
print(f"{'='*54}")
print(f"  LoRA lưu tại : {LORA_DIR}")
print(f"  Kích thước   : {size:.0f} MB")
print(f"\n  Bước tiếp: gộp LoRA + lượng tử hóa AWQ")
print(f"{'='*54}\n")
