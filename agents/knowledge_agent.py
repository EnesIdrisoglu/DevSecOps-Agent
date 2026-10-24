"""FAISS tabanlı remediation ve güvenlik bilgi agent'ı."""

from ..knowledge.vector_store import KnowledgeStore
from ..tools import database
from ..tools.web_search import search_cve
from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class KnowledgeAgent:
    name = "knowledge_agent"

    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store or KnowledgeStore()
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        results = self.mcp.call("search_knowledge", query=state.question, limit=3) or self.store.search(state.question, k=3)
        evidence = []
        if state.project:
            findings = self.mcp.call("get_project_findings", project=state.project)
            evidence = [item for item in findings if item["severity"] in {"critical", "high"}]
        lines = []
        if evidence:
            lines.append(f"{state.project} projesindeki kritik/yüksek bulgu remediation analizi:")
            for finding in evidence:
                line = f"- {finding['severity'].upper()}: {finding['title']}"
                if finding.get("cve"):
                    web = search_cve(finding["cve"])
                    line += f" ({finding['cve']})"
                    if web.get("summary"):
                        line += f" — NVD: {web['summary']}"
                lines.append(line)
        if results:
            lines.append("Bilgi tabanı önerileri:\n" + "\n".join(f"- {item['text']}" for item in results))
        state.answer = "\n".join(lines) if lines else "Bu bulgu için bilgi tabanında yeterli remediation bilgisi bulunamadı."
        return state
