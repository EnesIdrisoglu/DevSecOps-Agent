"""Açık bulgusu bulunan projeleri listeleyen specialist agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class FindingProjectsAgent:
    name = "finding_projects_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        projects = self.mcp.call("get_projects_with_findings")
        if not projects:
            state.answer = "Açık bulgusu olan proje bulunamadı."
            return state
        state.evidence = projects
        state.answer = "Açık bulgusu olan projeler:\n" + "\n".join(
            f"- {row['project']}: {row['finding_count']} açık bulgu" for row in projects
        )
        return state
