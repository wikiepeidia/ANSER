import sys
import os
import json

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.insert(0, current_dir)

from src.core.knowledge import KnowledgeBase
from src.agents.coder import CoderAgent
# Mock Engine just for initializing Coder class structure (we won't generate tokens here to save time)
class MockEngine:
    def load_model(self, role): return None
    def config(self): return None

def check_rag_learning():
    print("\n🔍 --- CHECKING RAG (POLICY FILES) ---")
    
    # 1. Initialize Knowledge Base
    # This will trigger ingest_folder() scanning src/data/docs
    kb = KnowledgeBase()
    
    # 2. Check Collection Count
    count = kb.collection.count()
    print(f"📄 Total Document Chunks Indexed: {count}")
    
    if count == 0:
        print("❌ RAG is empty! Did you put .txt/.pdf files in src/data/docs?")
        return

    # 3. Test Retrieval
    # We ask a specific question found in your policy file
    test_query = "Hàng điện tử bảo hành bao lâu?"
    print(f"❓ Test Query: '{test_query}'")
    
    results = kb.search(test_query, top_k=1)
    
    if results:
        print("✅ RAG Retrieval Successful!")
        print(f"📝 Retrieved Text Snippet:\n{results[:200]}...") # Show first 200 chars
        
        # Validation Logic
        if "12 tháng" in results or "bảo hành" in results:
            print("🎯 ACCURACY CHECK: PASS (Found correct policy details)")
        else:
            print("⚠️ ACCURACY CHECK: WEAK (Retrieved text might not be relevant)")
    else:
        print("❌ RAG Search failed to find anything.")

def check_blueprint_learning():
    print("\n🔍 --- CHECKING BLUEPRINTS (JSON SCHEMAS) ---")
    
    registry_path = "src/data/schemas/make_modules.json"
    
    # 1. Check if Schema File Exists
    if not os.path.exists(registry_path):
        print(f"❌ Registry file not found at: {registry_path}")
        print("👉 Run 'python src/tools/ingest_blueprints.py' to parse your JSON files first.")
        return

    # 2. Load Registry
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        
        print(f"✅ Registry Loaded. Found {len(registry)} unique modules.")
        
        # 3. List Learned Modules
        print("🧠 Learned Module Types:")
        for module_name in list(registry.keys())[:5]: # Show top 5
            print(f"   - {module_name}")
            
        if len(registry) > 5:
            print(f"   ... and {len(registry)-5} more.")
            
        # 4. Deep Check: specific Make.com params
        example_mod = "google-email:TriggerNewEmail"
        if example_mod in registry:
            print(f"✅ Found specific module: {example_mod}")
            params = registry[example_mod].get("parameters", {})
            if "xGmRaw" in params:
                print("   - Parameter 'xGmRaw' found (Schema is correct).")
            else:
                print("   ⚠️ Schema seems incomplete (missing parameters).")
        else:
            print(f"⚠️ Specific module '{example_mod}' not found. (Depends on your uploaded blueprints)")

    except Exception as e:
        print(f"❌ Error reading registry: {e}")

if __name__ == "__main__":
    print("🚀 STARTING SYSTEM AUDIT...")
    check_rag_learning()
    check_blueprint_learning()
    print("\n🏁 AUDIT COMPLETE.")