from src.agents.base import BaseAgent
from ddgs import DDGS

class ResearcherAgent(BaseAgent):
    def __init__(self, engine):
        super().__init__(engine, "researcher")

    def search(self, query: str):
        try:
            with DDGS() as ddgs:
                # Max results 4 is usually enough for context
                results = list(ddgs.text(query, max_results=4))
                if not results: return "Search returned no results."
                return str(results)
        except Exception as e:
            return f"Search failed: {e}"

    async def process(self, query: str):
        raw_data = self.search(query)
        
        # Qwen prompt format
        prompt = f'''<|im_start|>system
You are a Research Assistant. Summarize the provided search data concisely in Vietnamese.
Focus on facts relevant to Retail/Business.
<|im_end|>
<|im_start|>user
QUERY: {query}
RAW DATA: {raw_data}
<|im_end|>
<|im_start|>assistant
'''
        return await self.generate(prompt, max_new_tokens=512)