"""Proje kataloğu ve genel proje özeti agent'ı."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class ProjectAgent:
    name = "project_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            projects = self.mcp.call("list_projects")
            state.answer = "Platformdaki projeler: " + ", ".join(projects)
            return state
        summary = self.mcp.call("get_project_summary", project=state.project)
        scorecard = self.mcp.call("get_project_scorecard", project=state.project) or []
        job = self.mcp.call("get_failed_job", project=state.project)
        scan = summary["scan"] if summary else None
        state.answer = (
            f"{state.project} proje özeti:\n"
            f"- Son tarama: {scan['status'] if scan else 'kayıt yok'}\n"
            f"- Açık bulgu: {len(summary['findings']) if summary else 0}\n"
            f"- Karne metriği: {len(scorecard)}\n"
            f"- Başarısız job: {job['job_name'] if job else 'yok'}"
        )
        return state
