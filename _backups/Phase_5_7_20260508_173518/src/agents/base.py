
from abc import ABC
from src.core.engine import ModelEngine

class BaseAgent(ABC):
    def __init__(self, engine: ModelEngine, role: str):
        self.engine = engine
        self.role = role

    async def generate(self, prompt: str, **kwargs):
        """Async generation — delegates to the async ModelEngine."""
        max_tokens = kwargs.get('max_new_tokens', 1024)
        temperature = kwargs.get('temperature', 0.1)
        
        return await self.engine.generate_text(prompt, max_tokens, temperature)
