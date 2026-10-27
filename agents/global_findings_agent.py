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
        if requested_severities == {"critical"}:
            summary = f"Tüm projelerde {len(findings)} açık critical bulgu var:"
        elif requested_severities == {"high"}:
            summary = f"Tüm projelerde {len(findings)} açık high bulgu var:"
        elif requested_severities == {"critical", "high"}:
            summary = f"Tüm projelerde {len(findings)} açık high veya critical bulgu var:"
        else:
            summary = f"Tüm projelerde toplam {len(findings)} açık bulgu var:"
        state.answer = (
            summary + "\n" +
            "\n".join(lines) +
            ("\n\nRelease değerlendirmesinde high/critical bulgular engel adayıdır; low/medium bulgular tek başına release engeli sayılmaz." if not requested_severities or requested_severities & {"high", "critical"} else "")
        )
        return state
