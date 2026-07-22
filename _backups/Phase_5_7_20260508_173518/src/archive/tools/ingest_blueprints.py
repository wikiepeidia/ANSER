import json
import glob
import os

BLUEPRINT_DIR = "/content/drive/MyDrive/ProjectA_Backup/src/Data/blueprints"
REGISTRY_PATH = "/content/drive/MyDrive/ProjectA_Backup/src/Data/schemas/make_modules.json"

def clean_parameters(params):
    """
    Recursively keep keys but sanitize values to types/placeholders.
    This teaches structure without overfitting to your specific data.
    """
    clean = {}
    if not isinstance(params, dict):
        return "VALUE_PLACEHOLDER"
        
    for k, v in params.items():
        if k.startswith("__"): continue # Skip internal Make.com keys
        
        if isinstance(v, dict):
            clean[k] = clean_parameters(v)
        elif isinstance(v, list):
            # For arrays (like headers), keep one example structure if exists
            if len(v) > 0 and isinstance(v[0], dict):
                clean[k] = [clean_parameters(v[0])]
            else:
                clean[k] = []
        elif isinstance(v, bool):
            clean[k] = v
        else:
            # Replace specific strings with generic placeholders
            clean[k] = "REQUIRED_VALUE"
            
    return clean

def main():
    print(f"🚀 Scanning {BLUEPRINT_DIR} for Make.com Blueprints...")
    
    # Load existing registry or start empty
    registry = {}
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except: pass

    blueprint_files = glob.glob(os.path.join(BLUEPRINT_DIR, "*.json"))
    if not blueprint_files:
        print("❌ No JSON files found! Upload them to data/blueprints/ first.")
        return

    new_modules_count = 0
    
    for filepath in blueprint_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if it's a valid blueprint
            if "flow" not in data:
                print(f"⚠️  Skipping {os.path.basename(filepath)}: No 'flow' key found.")
                continue

            # Harvest Modules
            for node in data["flow"]:
                module_name = node.get("module")
                if not module_name: continue
                
                # If we haven't seen this module, or if we want to overwrite to get fresh params
                # We prioritize modules that have parameters over empty ones
                current_entry = registry.get(module_name)
                
                # Create the schema
                schema = {
                    "module": module_name,
                    "version": node.get("version", 1),
                    "parameters": clean_parameters(node.get("parameters", {})),
                    "desc": f"Auto-extracted from {os.path.basename(filepath)}"
                }
                
                # Logic: Update if new, or if the new one has more detailed parameters
                should_update = False
                if module_name not in registry:
                    should_update = True
                    new_modules_count += 1
                elif len(str(schema["parameters"])) > len(str(current_entry.get("parameters", ""))):
                    # We found a richer example of the same module
                    should_update = True
                
                if should_update:
                    registry[module_name] = schema
                    print(f"   [+] Learned Module: {module_name}")

        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")

    # Save Master Registry
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=4)
        
    print(f"\n✅ Done! Registry now contains {len(registry)} modules.")
    print(f"   (Added {new_modules_count} new ones).")

if __name__ == "__main__":
    main()