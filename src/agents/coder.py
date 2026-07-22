from src.agents.base import BaseAgent
from src.core.agent_middleware import AgentMiddleware
from src.core.prompts import Prompts


class CoderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, "coder")
        self.middleware = AgentMiddleware()

    async def write_code(self, task: str, plan: str, feedback: str = ""):
        tools = self.middleware.get_workflow_tools()
        system = Prompts.CODER_SYSTEM.format(tools=tools)   # prompt sạch, không ChatML
        user = f"TASK: {task}\nPLAN: {plan}"
        if feedback:
            user += f"\nFEEDBACK: {feedback}"
        # generate_chat tự chèn ChatML qua apply_chat_template
        return await self.generate_chat(user=user, system=system,
                                        max_new_tokens=1500, temperature=0.1)