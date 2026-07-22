from src.agents.base import BaseAgent
from ddgs import DDGS


class ResearcherAgent(BaseAgent):
    # System prompt THUẦN (không ChatML) — apply_chat_template lo định dạng qua generate_chat.
    SYSTEM = (
        "You are a Research Assistant. Summarize the provided search data concisely "
        "in Vietnamese. Focus on facts relevant to Retail/Business."
    )

    def __init__(self, engine):
        super().__init__(engine, "researcher")

    def search(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=4))
                if not results:
                    return "Search returned no results."
                return str(results)
        except Exception as e:
            return f"Search failed: {e}"

    async def process(self, query: str):
        raw_data = self.search(query)
        user = f"QUERY: {query}\nRAW DATA: {raw_data}"
        # generate_chat tự chèn ChatML chuẩn Qwen — hết nhúng tay <|im_start|>
        return await self.generate_chat(system=self.SYSTEM, user=user, max_new_tokens=512)