"""
src/agents/coder.py — sinh workflow n8n dạng JSON Action Block.

Bản Ngày 7. Thay đổi so với bản cũ:
  - `write_code` nhận feedback rõ ràng hơn để chat.py retry khi JSON hỏng.
  - max_new_tokens giảm 1500 -> 1200. Workflow bán lẻ thực tế hiếm khi quá
    8 node; budget dư chỉ tạo thêm không gian cho model sinh rác ở cuối.
  - temperature giữ 0.1 (JSON cần xác định, không cần sáng tạo).
  - Thêm `stop` để model dừng khi bắt đầu viết lời giải thích sau JSON —
    đây là nguồn gốc của đoạn "Giải thích ngắn gọn..." bị dính vào output.
"""

from src.agents.base import BaseAgent
from src.core.agent_middleware import AgentMiddleware
from src.core.prompts import Prompts


class CoderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, "coder")
        self.middleware = AgentMiddleware()

    async def write_code(self, task: str, plan: str, feedback: str = ""):
        """
        Sinh JSON Action Block từ PLAN.

        `feedback` do chat.py truyền vào ở lần retry, chứa lý do lỗi cụ thể
        (ví dụ: 'JSONDecodeError: Expecting , delimiter tại vị trí 412').
        Feedback cụ thể cải thiện tỉ lệ sửa đúng hơn nhiều so với việc chỉ
        bảo model "thử lại".
        """
        tools = self.middleware.get_workflow_tools()
        system = Prompts.CODER_SYSTEM.format(tools=tools)

        user = f"TASK: {task}\nPLAN: {plan}"
        if feedback:
            user += (
                f"\n\nLỖI LẦN TRƯỚC: {feedback}\n"
                "Xuất lại JSON đã sửa. Chỉ JSON, không thêm chữ nào khác."
            )

        return await self.generate_chat(
            system=system,
            user=user,
            max_new_tokens=1200,
            temperature=0.1,
        )