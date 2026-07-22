
from src.agents.base import BaseAgent
from src.core.agent_middleware import AgentMiddleware

class CoderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, "coder")
        self.middleware = AgentMiddleware()

    async def write_code(self, task: str, plan: str, feedback: str = ""):
        tools = self.middleware.get_workflow_tools()
        
        prompt = f'''<|im_start|>system
You are the Automation Engine.
Your job is to translate the PLAN into a JSON Action Block.

AVAILABLE TOOLS:
{tools}

RULES:
1. Output ONLY the JSON object.
2. The JSON MUST start with {{ "action": "create_workflow", ... }}
3. Do not write markdown or explanations.

<|im_end|>
<|im_start|>user
TASK: {task}
PLAN: {plan}
<|im_end|>
<|im_start|>assistant
'''
        return await self.generate(prompt, max_new_tokens=1500, temperature=0.1)
