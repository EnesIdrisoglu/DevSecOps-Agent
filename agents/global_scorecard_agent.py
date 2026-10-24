"""Tüm projelerin karne durumunu analiz eden agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class GlobalScorecardAgent:
    name = "global_scorecard_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        lines = []
        for project in self.mcp.call("list_projects"):
            rows = self.mcp.call("get_project_scorecard", project=project) or []
            missing = sum(row["actual"] < row["target"] for row in rows)
            metrics = "; ".join(
                f"{row['metric']}: hedef {row['target']}, gerçekleşen {row['actual']} ({row['status']})"
                for row in rows
            )
            lines.append(f"- {project} projesinde {len(rows)} karne hedefi bulunuyor. Bunların {missing} tanesi karşılanmadı.\n  {metrics}")
        state.answer = "Tüm projelerin karne özeti:\n" + "\n".join(lines)
        return state
