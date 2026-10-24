"""Tüm projelerin release uygunluğunu analiz eden agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class GlobalReleaseAgent:
    name = "global_release_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        portfolio = self.mcp.call("get_release_portfolio")
        blocked = [row for row in portfolio if not row["suitable"]]
        suitable = [row for row in portfolio if row["suitable"]]
        blocked_text = ", ".join(f"{row['project']} ({row['blocking_findings']} high/critical)" for row in blocked) or "yok"
        suitable_text = ", ".join(row["project"] for row in suitable) or "yok"
        state.answer = (
            "Release değerlendirmesi (high/critical bulgular engel kabul edilmiştir):\n"
            f"- Uygun olmayan projeler: {blocked_text}\n"
            f"- Uygun görünen projeler: {suitable_text}\n"
            "Low/medium bulgular tek başına release engeli olarak değerlendirilmemiştir."
        )
        return state
