"""Sadece aggregate sayı isteyen global sorular için agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class GlobalMetricsAgent:
    name = "global_metrics_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        state.answer = str(len(self.mcp.call("get_global_findings")))
        return state
