# src/agents/vision.py

from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch

class VisionAgent:
    def __init__(self):
        print("👁️ [Vision] Initializing Florence-2...")
        self.model_id = "microsoft/Florence-2-large"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        try:
            # FIX: attn_implementation="eager" fixes the _supports_sdpa crash on newer transformers
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                torch_dtype=self.dtype, 
                trust_remote_code=True,
                attn_implementation="eager"
            ).to(self.device)
            
            self.processor = AutoProcessor.from_pretrained(
                self.model_id, 
                trust_remote_code=True
            )
            print("✅ Vision Ready.")
        except Exception as e:
            print(f"❌ Vision Load Failed: {e}")
            self.model = None

    def analyze_image(self, image_path, task_hint="describe"):
        if not self.model: return "Vision module unavailable."
        
        try:
            image = Image.open(image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")

            prompt = "<MORE_DETAILED_CAPTION>" if "describe" in task_hint else "<OCR>"
            
            inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(self.device, self.dtype)
            
            generated_ids = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                do_sample=False,
                num_beams=3
            )
            
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return text.strip()
            
        except Exception as e:
            return f"Error analyzing image: {e}"
