"""Karne hedefleri agent'ı."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class ScorecardAgent:
    name = "scorecard_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            state.answer = "Karne durumunu incelemek için bir proje adı belirtin."
            return state
        rows = self.mcp.call("get_project_scorecard", project=state.project) or []
        if not rows:
            state.answer = f"{state.project} için karne hedefi bulunamadı."
            return state
        details = "; ".join(f"{r['metric']}: hedef {r['target']}, gerçekleşen {r['actual']} ({r['status']})" for r in rows)
        state.answer = f"{state.project} karne durumu: {details}. Eksik hedefleri iyileştirmek için ilgili ekiplerle aksiyon planı oluşturun."
        return state
