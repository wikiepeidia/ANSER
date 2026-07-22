import os
import shutil
import subprocess
import datetime
from pathlib import Path

def ignore_patterns(dir, contents):
    """Filter out __pycache__ and virtual environments during copy."""
    return [c for c in contents if c in ("__pycache__", ".venv", "venv", ".git")]

def execute_backup_and_push():
    print("🚀 [@devops] Executing End-of-Phase Backup & Deployment Protocol...")
    
    # 1. Setup paths
    project_root = Path(__file__).parent.absolute()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir_name = f"Phase_5_7_{timestamp}"
    backup_base = project_root / "_backups" / backup_dir_name
    
    src_dir = project_root / "src"
    offline_training_dir = project_root / "offline_training"
    
    # 2. Perform Local Backup
    try:
        print(f"📦 Creating backup directory: {backup_base}")
        os.makedirs(backup_base, exist_ok=True)
        
        if src_dir.exists():
            print("   -> Copying src/ ...")
            shutil.copytree(src_dir, backup_base / "src", ignore=ignore_patterns)
        
        if offline_training_dir.exists():
            print("   -> Copying offline_training/ ...")
            shutil.copytree(offline_training_dir, backup_base / "offline_training", ignore=ignore_patterns)
            
        print("✅ Local backup completed successfully.")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return

    # 3. Perform Git Operations
    print("\n🌐 Executing Remote Push via Git...")
    
    try:
        # Run git add
        subprocess.run(["git", "add", "."], cwd=project_root, check=True)
        print("   -> Staged all changes.")
        
        # Run git commit (may fail if nothing to commit, so we don't check=True)
        commit_res = subprocess.run(
            ["git", "commit", "-m", "feat: complete Phase 5.7 concurrency hardening"], 
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if commit_res.returncode == 0:
            print("   -> Committed changes successfully.")
        else:
            print(f"   -> Commit skipped or failed: {commit_res.stdout.strip()}")

        # Check for remote origin
        remotes_res = subprocess.run(["git", "remote"], cwd=project_root, capture_output=True, text=True)
        if "origin" not in remotes_res.stdout.split():
            print("   -> ⚠️ No remote 'origin' configured. Skipping remote push.")
            print("✅ Backup and local commit completed successfully.")
            return
            
        # Run git push
        print("   -> Pushing to origin (current branch)...")
        push_res = subprocess.run(["git", "push", "origin", "HEAD"], cwd=project_root, capture_output=True, text=True)
        
        if push_res.returncode == 0:
            print("✅ Remote push completed successfully.")
        else:
            print(f"⚠️ Remote push failed:\n{push_res.stderr.strip()}")
            
    except FileNotFoundError:
        print("❌ Git is not installed or not available in PATH.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")

if __name__ == "__main__":
    execute_backup_and_push()
