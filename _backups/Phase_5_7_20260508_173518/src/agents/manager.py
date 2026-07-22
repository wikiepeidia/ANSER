import json
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.agents.base import BaseAgent

class SemanticRouter:
    def __init__(self, model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        print("🚀 Initializing Semantic Router...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder = SentenceTransformer(model_name, device=self.device)

        # Define example queries for each route
        self.routes = {
            "TECHNICAL": [
                "Write a function to find the longest chain",
                "Write a python function to find the first repeated character",
                "Write a function to reverse words in a given string",
                "Write a function to check if the given integer is a prime number",
                "viết một hàm python để xử lý ảnh",
                "tạo quy trình tự động hóa",
                "quy trinh tự hóa mà nó sẽ tự đọc file google sheet",
                "gửi email về kịch bản",
                "viết code python để crawl dữ liệu"
            ],
            "DATA_INTERNAL": [
                "How many heads of the departments are older than 56?",
                "List the name, born state and age of the heads of departments ordered by age",
                "List the creation year, name and budget of each department",
                "What are the maximum and minimum budget of the departments?"
            ],
            "RETRIEVAL": [
                "When did Beyonce start becoming popular?",
                "What areas did Beyonce compete in when she was growing up?",
                "When did Beyonce leave Destiny's Child and become a solo singer?",
                "In what city and state did Beyonce grow up?"
            ],
            "GENERAL": [
                "Say, Jim, how about going for a few beers after we finish here?",
                "Can you do push-ups?",
                "Can you study with the radio on?",
                "Are you all right?"
            ]
        }

        # Pre-compute embeddings for all examples
        self.route_embeddings = {}
        for route, examples in self.routes.items():
            self.route_embeddings[route] = self.embedder.encode(examples)

    def route(self, query: str, threshold: float = 0.4) -> str:
        query_vec = self.embedder.encode([query])
        best_route = "GENERAL"
        highest_sim = -1.0

        for route, embeddings in self.route_embeddings.items():
            # Calculate similarity against all examples in the route
            sims = cosine_similarity(query_vec, embeddings)[0]
            max_sim_for_route = np.max(sims)

            if max_sim_for_route > highest_sim:
                highest_sim = max_sim_for_route
                best_route = route

        # print(f"[Router] Best match: {best_route} (Confidence: {highest_sim:.2f})")

        if highest_sim < threshold:
            return "GENERAL"
        return best_route


class ManagerAgent(BaseAgent):
    def __init__(self, engine, memory, kb=None):
        super().__init__(engine, "manager")
        self.kb = kb # Knowledge Base
        self.router = SemanticRouter()

    async def analyze_task(self, clean_text: str):
        text = clean_text.lower().strip()
        route = self.router.route(text)
        return {"category": route}

    async def plan_or_ask(self, full_context: str):
        prompt = f'''<|im_start|>system
You are a Senior Automation Architect.
1. If request is VAGUE, ask clarifying questions.
2. If request is SPECIFIC, output [PLAN].
<|im_end|>
<|im_start|>user
{full_context}
<|im_end|>
<|im_start|>assistant
'''
        return await self.generate(prompt, max_new_tokens=256, temperature=0.1)

    async def consult(self, task: str, context: str = "", history: str = ""):
        prompt = f'''<|im_start|>system
You are Project A. Answer based on the Context provided.
CONTEXT:
{context}
<|im_end|>
<|im_start|>user
{task}
<|im_end|>
<|im_start|>assistant
'''
        return await self.generate(prompt, max_new_tokens=512)
