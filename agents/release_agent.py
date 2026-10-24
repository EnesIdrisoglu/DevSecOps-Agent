"""Release uygunluğu ve güvenlik riski agent'ı."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class ReleaseRiskAgent:
    name = "release_risk_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            state.answer = "Release riskini incelemek için bir proje adı belirtin."
            return state
        data = self.mcp.call("get_project_summary", project=state.project)
        if not data or not data["scan"]:
            state.answer = f"{state.project} için tarama kanıtı bulunamadı."
            return state
        open_high = [f for f in data["findings"] if f["severity"] in ("critical", "high")]
        release = data["release"]
        decision = release["decision"] if release else "kayıt yok"
        titles = "; ".join(f["title"] for f in open_high) or "kritik/yüksek açık bulgu yok"
        state.answer = (
            f"{state.project} release özeti:\n"
            f"- Tarama: {data['scan']['status']} ({data['evidence_time']})\n"
            f"- Kritik/yüksek bulgular: {titles}\n"
            f"- Son release kararı: {decision}\n"
            f"- Gerekçe: {(release or {}).get('reason', 'belirtilmemiş')}\n\n"
            "Bu cevap öneridir; release otomatik olarak değiştirilmedi."
        )
        return state
