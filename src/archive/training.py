import torch
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset
import os
import psutil
import builtins

# --- PATCH FOR UNSLOTH BUG ---
builtins.psutil = psutil

# --- CONFIG ---
PROJECT_ROOT = "/content/drive/MyDrive/ProjectA_Backup"
DATASET_PATH = os.path.join(PROJECT_ROOT, "src/data/final_finetune_dataset.jsonl")
SAVE_PATH = os.path.join(PROJECT_ROOT, "models/project_a_14b_finetuned")
OUTPUT_DIR = "outputs"

max_seq_length = 2048
load_in_4bit = True

def train_model():
    print(f"🚀 Initializing Training...")
    print(f"📂 Data: {DATASET_PATH}")
    
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError("❌ Dataset not found! Run 'src/tools/merge_datasets.py' first.")

    # 1. Load Base Model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "Qwen/Qwen2.5-Coder-14B-Instruct",
        max_seq_length = max_seq_length,
        dtype = None,
        load_in_4bit = load_in_4bit,
    )

    # 2. Add LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16, 
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 16,
        lora_dropout = 0,
        bias = "none",
        use_gradient_checkpointing = "unsloth", 
        random_state = 3407,
        use_rslora = False,
        loftq_config = None,
    )

    # 3. Load & Clean Data
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    def formatting_prompts_func(examples):
        conversations = examples["messages"]
        texts = []
        for conv in conversations:
            if not conv or not isinstance(conv, list):
                texts.append("") 
                continue
            try:
                # Apply Chat Template
                text = tokenizer.apply_chat_template(conv, tokenize=False, add_generation_prompt=False)
                texts.append(text)
            except:
                texts.append("")
        return { "text" : texts }

    dataset = dataset.map(formatting_prompts_func, batched = True)
    dataset = dataset.filter(lambda x: x["text"] != "")

    print(f"📊 Training on {len(dataset)} samples.")

    # 4. Train
    print("🏋️‍♂️ Starting Training Cycle...")
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "text",
        max_seq_length = max_seq_length,
        dataset_num_proc = 2,
        packing = False,
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 5,
            num_train_epochs = 3, # Train for 3 full loops
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 1,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = OUTPUT_DIR,
            report_to = "none", 
        ),
    )

    trainer.train()

    # 5. Save Adapters Locally
    print(f"💾 Saving to local folder 'lora_model'...")
    model.save_pretrained("lora_model")
    tokenizer.save_pretrained("lora_model")
    print("✅ Training Complete.")

if __name__ == "__main__":
    train_model()