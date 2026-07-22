import os
import subprocess
import shutil

# CONFIG
LEARNING_FILE = "src/data/learning_queue.jsonl"
MASTER_DATASET = "src/data/final_finetune_dataset.jsonl"

def run_night_school():
    print("🌙 Welcome to Night School. Checking for new lessons...")
    
    if not os.path.exists(LEARNING_FILE):
        print("💤 No new corrections found. Skipping training.")
        return

    # 1. Count new samples
    with open(LEARNING_FILE, 'r') as f:
        new_lessons = f.readlines()
    
    if len(new_lessons) < 5:
        print(f"⚠️ Only {len(new_lessons)} new lessons. Waiting for at least 5 to train.")
        return

    print(f"📚 Found {len(new_lessons)} user corrections. Merging into Brain...")

    # 2. Append new lessons to Master Dataset
    with open(MASTER_DATASET, "a", encoding="utf-8") as f:
        for line in new_lessons:
            f.write(line)
            
    # 3. Archive the queue (Clear it so we don't re-add next time)
    # In prod, move to an archive folder
    os.remove(LEARNING_FILE)

    # 4. Trigger Training
    print("🏋️‍♂️ Starting Fine-Tuning Process...")
    try:
        # Run the existing training script
        subprocess.run(["python", "src/training.py"], check=True)
        print("✅ Training Complete. New Brain created.")
        print("👉 Restart the Server to load the new intelligence.")
    except Exception as e:
        print(f"❌ Training Failed: {e}")

if __name__ == "__main__":
    run_night_school()