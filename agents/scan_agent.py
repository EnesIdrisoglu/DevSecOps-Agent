"""Proje scan geçmişi ve son başarılı tarama agent'ı."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class ScanAgent:
    name = "scan_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            state.answer = "Tarama tarihini öğrenmek için bir proje adı belirtin."
            return state
        summary = self.mcp.call("get_project_summary", project=state.project)
        scan = summary.get("scan") if isinstance(summary, dict) else None
        if not scan:
            state.answer = f"{state.project} için başarılı tarama kaydı bulunamadı."
            return state
        state.answer = f"{state.project} projesinin son başarılı tarama tarihi: {scan['scanned_at']}"
        return state
