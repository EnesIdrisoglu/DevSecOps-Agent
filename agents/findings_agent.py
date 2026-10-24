"""Güvenlik bulguları konusunda uzman agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class FindingsAgent:
    name = "findings_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            state.answer = "Bulguları incelemek için bir proje adı belirtin."
            return state
        findings = self.mcp.call("get_project_findings", project=state.project)
        if not findings:
            state.answer = f"{state.project} için açık bulgu bulunamadı."
            return state
        state.evidence = findings
        lines = []
        for finding in findings:
            cve = f" / {finding['cve']}" if finding.get("cve") else ""
            lines.append(f"- {finding['severity'].upper()}: {finding['title']}{cve} ({finding['component']})")
        state.answer = (
            f"{state.project} projesinde {len(findings)} açık bulgu var:\n" + "\n".join(lines) +
            "\n\nÖneri: Etkilenen bileşenleri güncelleyin, düzeltmeyi yeniden tarayın ve bulguları doğrulama sonrası kapatın."
        )
        return state
