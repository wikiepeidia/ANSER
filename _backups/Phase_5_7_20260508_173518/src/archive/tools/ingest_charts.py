import sys
import os

# --- PATH FIXER (CRITICAL) ---
# This ensures we can import 'src' modules regardless of where we run this script from
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../src/tools
src_dir = os.path.dirname(current_dir)                # .../src
project_root = os.path.dirname(src_dir)               # .../ProjectA_Backup

if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------------------

import json
import glob
from pdf2image import convert_from_path
from src.agents.vision import VisionAgent
from tqdm import tqdm

# CONFIG
DOCS_DIR = os.path.join(src_dir, "data", "docs")
OUTPUT_FILE = os.path.join(src_dir, "data", "chart_data.jsonl")

def extract_visual_data():
    print("👁️ Initializing Vision Agent for Chart Reading...")
    
    try:
        vision = VisionAgent()
    except Exception as e:
        print(f"❌ Failed to load Vision Agent: {e}")
        return
    
    pdf_files = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
    if not pdf_files:
        print(f"❌ No PDFs found in {DOCS_DIR}")
        return

    extracted_data = []

    print(f"📂 Found {len(pdf_files)} PDFs. Scanning for charts...")

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"   📄 Processing {filename}...")
        
        try:
            # Convert PDF pages to Images (in memory)
            # We limit to first 10 pages for demo speed. Remove [:10] for full scan.
            pages = convert_from_path(pdf_path)[:10] 
            
            for i, page_image in enumerate(pages):
                # Save temp image for Vision Agent
                temp_img_path = "temp_page.jpg"
                page_image.save(temp_img_path, "JPEG")
                
                # 1. Run Captioning (To understand the graph shape/trend)
                caption = vision.analyze_image(temp_img_path, task_hint="describe caption")
                
                # 2. Run OCR (To read the numbers on the axes)
                text_data = vision.analyze_image(temp_img_path, task_hint="OCR")
                
                # Combine them into a "Visual Context"
                combined_context = f"Page {i+1} Visual Data:\n- Description: {caption}\n- Text Content: {text_data}"
                
                # Check if this page actually has a chart (heuristic)
                # If the description mentions "chart", "graph", "plot", we keep it.
                keywords = ["chart", "graph", "plot", "diagram", "figure", "table", "biểu đồ"]
                if any(k in caption.lower() for k in keywords):
                    print(f"      📊 Found Chart on Page {i+1}")
                    extracted_data.append({
                        "source": filename,
                        "page": i+1,
                        "content": combined_context
                    })
                
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

    # Save raw visual data
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in extracted_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"✅ Extracted {len(extracted_data)} visual insights.")
    print(f"👉 File saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_visual_data()