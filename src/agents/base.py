from abc import ABC
from src.core.engine import ModelEngine


class BaseAgent(ABC):
    def __init__(self, engine: ModelEngine, role: str):
        self.engine = engine
        self.role = role

    async def generate(self, prompt: str, **kwargs):
        """Raw completion — giữ lại cho tương thích ngược (KHÔNG dùng cho chat ChatML)."""
        max_tokens = kwargs.get('max_new_tokens', 1024)
        temperature = kwargs.get('temperature', 0.1)
        return await self.engine.generate_text(prompt, max_tokens, temperature)

    async def generate_chat(self, system: str, user: str, **kwargs):
        """Chat đúng chuẩn Qwen — để tokenizer.apply_chat_template lo định dạng ChatML."""
        max_tokens = kwargs.get('max_new_tokens', 1024)
        temperature = kwargs.get('temperature', 0.1)
        return await self.engine.generate_chat(system, user, max_tokens, temperature)