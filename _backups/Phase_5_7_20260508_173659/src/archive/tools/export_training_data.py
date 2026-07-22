import json
import glob
import os
import random
import re

# CONFIG
# Locations to look for your valid blueprints
BLUEPRINT_DIRS = ["/content/drive/MyDrive/ProjectA_Backup/src/data/blueprints", "my_workflows"]
DB_PATH = "/content/drive/MyDrive/ProjectA_Backup/src/data/project_a.db"
OUTPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/training_dataset.jsonl"

# Identity
SYSTEM_PROMPT = "You are Project A, the Lead Automation Engineer. You generate strict Make.com JSON blueprints."

def clean_json_string(data):
    """Minifies JSON slightly but keeps structure for training."""
    return json.dumps(data, indent=2, ensure_ascii=False)

def generate_prompts_for_blueprint(filename, data):
    """
    Generates synthetic user prompts based on the modules found in the JSON.
    This is 'Reverse Engineering' the prompt from the answer.
    """
    prompts = []
    
    # 1. Analyze the Flow
    modules = []
    if "flow" in data:
        for node in data["flow"]:
            if "module" in node:
                modules.append(node["module"])
    
    if not modules: return []
    
    # Simplify module names for natural language (e.g. google-sheets:addRow -> Google Sheets)
    human_modules = [m.split(':')[0].replace('-', ' ').title() for m in modules]
    flow_summary = " -> ".join(human_modules)
    
    # 2. Create Variations (English & Vietnamese)
    
    # Variation A: Direct Request (English)
    prompts.append(f"Create a Make.com automation that connects {flow_summary}.")
    
    # Variation B: "Build" Intent (English)
    prompts.append(f"Build a workflow: {flow_summary}.")
    
    # Variation C: Vietnamese Intent
    prompts.append(f"Tạo quy trình tự động hóa: {flow_summary}.")
    
    # Variation D: Specific Filename Context (if filename is descriptive)
    clean_name = filename.replace("WF_", "").replace(".json", "").replace("_", " ")
    prompts.append(f"Design an automation for: {clean_name}")

    return prompts

def export_blueprints():
    print(f"🔍 Scanning for blueprints in {BLUEPRINT_DIRS}...")
    samples = []
    
    found_files = []
    for d in BLUEPRINT_DIRS:
        found_files.extend(glob.glob(os.path.join(d, "*.json")))
    
    print(f"   Found {len(found_files)} files.")

    for fpath in found_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate it's a real blueprint
            if "flow" not in data and "scenarios" not in data:
                continue

            # Generate synthetic user inputs
            user_prompts = generate_prompts_for_blueprint(os.path.basename(fpath), data)
            
            # The Target Output (The JSON)
            assistant_response = f"```json\n{clean_json_string(data)}\n```"
            
            # Create training pairs
            for p in user_prompts:
                sample = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": p},
                        {"role": "assistant", "content": assistant_response}
                    ]
                }
                samples.append(sample)
        except Exception as e:
            print(f"   ⚠️ Error reading {fpath}: {e}")
            
    print(f"✅ Generated {len(samples)} training samples from blueprints.")
    return samples

def main():
    print("🏭 Starting Data Factory...")
    
    dataset = export_blueprints()
    
    # Shuffle to prevent overfitting to one type of task sequence
    random.shuffle(dataset)
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"🎉 SUCCESS: Dataset saved to {OUTPUT_FILE}")
    print(f"📊 Total Training Rows: {len(dataset)}")
    print("👉 Next Step: Use this file to fine-tune Qwen using LoRA.")

if __name__ == "__main__":
    main()