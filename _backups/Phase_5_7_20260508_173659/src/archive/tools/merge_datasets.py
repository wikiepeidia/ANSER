import json
import glob
import os
import random

DATA_DIR = "/content/drive/MyDrive/ProjectA_Backup/src/data"
OUTPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/final_finetune_dataset.jsonl"

def merge_data():
    print(f"🔄 Scanning {DATA_DIR} for JSONL files...")
    
    all_files = glob.glob(os.path.join(DATA_DIR, "*.jsonl"))
    # Exclude the output file itself to avoid infinite loops if run twice
    all_files = [f for f in all_files if "final_finetune" not in f]
    
    if not all_files:
        print("❌ No data files found!")
        return

    merged_data = []
    
    for fpath in all_files:
        filename = os.path.basename(fpath)
        print(f"   📄 Reading: {filename}...", end="")
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip():
                        merged_data.append(json.loads(line))
            print(f" ({len(lines)} samples)")
        except Exception as e:
            print(f" ❌ Error: {e}")

    # Shuffle to mix Coding skills with Reasoning skills
    random.shuffle(merged_data)
    
    # Save Master File
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in merged_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print("-" * 40)
    print(f"✅ MERGE COMPLETE.")
    print(f"📊 Total Samples: {len(merged_data)}")
    print(f"💾 Saved to: {OUTPUT_FILE}")
    print("👉 Use this file for the Training Script.")

if __name__ == "__main__":
    merge_data()