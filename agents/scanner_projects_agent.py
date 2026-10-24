"""Scanner bazında taranan projeleri listeleyen agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class ScannerProjectsAgent:
    name = "scanner_projects_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        rows = self.mcp.call("get_projects_by_scanner", scanner=state.scanner or "")
        if not rows:
            state.answer = f"{state.scanner or 'Bu scanner'} ile taranan proje bulunamadı."
            return state
        state.answer = f"{state.scanner} ile taranan projeler:\n" + "\n".join(f"- {row['project']} ({row['status']}, {row['scanned_at']})" for row in rows)
        return state
