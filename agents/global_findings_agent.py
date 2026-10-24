"""Tüm projelerdeki bulguları severity bazında analiz eden agent."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class GlobalFindingsAgent:
    name = "global_findings_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        findings = self.mcp.call("get_global_findings")
        question = state.question.lower()
        requested_severities = set()
        if "critical" in question or "kritik" in question:
            requested_severities.add("critical")
        if "high" in question or "yüksek" in question:
            requested_severities.add("high")
        if "medium" in question or "orta" in question:
            requested_severities.add("medium")
        if "low" in question or "düşük" in question:
            requested_severities.add("low")
        if requested_severities:
            findings = [item for item in findings if item["severity"] in requested_severities]
        if not findings:
            state.answer = "İstenen severity seviyelerinde açık bulgu bulunamadı."
            return state
        state.evidence = findings
        lines = [f"- {item['project']}: {item['severity'].upper()} — {item['title']}" for item in findings]
        critical_high = sum(item["severity"] in {"critical", "high"} for item in findings)
        state.answer = (
            f"Tüm projelerde toplam {len(findings)} açık bulgu var; bunların {critical_high} tanesi high veya critical:\n" +
            "\n".join(lines) +
            "\n\nRelease değerlendirmesinde high/critical bulgular engel adayıdır; low/medium bulgular tek başına release engeli sayılmaz."
        )
        return state
