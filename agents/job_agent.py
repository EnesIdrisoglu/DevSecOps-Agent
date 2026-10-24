"""Scheduled job hata teşhisi agent'ı."""

from ..tools.mcp_gateway import MCPGateway
from .state import AgentState


class JobDiagnosticAgent:
    name = "job_diagnostic_agent"

    def __init__(self):
        self.mcp = MCPGateway()

    def run(self, state: AgentState) -> AgentState:
        if not state.project:
            state.answer = "Job durumunu incelemek için bir proje adı belirtin."
            return state
        job = self.mcp.call("get_failed_job", project=state.project)
        if not job:
            state.answer = f"{state.project} için başarısız job kaydı bulunamadı."
            return state
        state.answer = (
            f"{state.project} son başarısız job analizi:\n"
            f"- Job: {job['job_name']}\n- Zaman: {job['started_at']}\n"
            f"- Hata: {job.get('error') or 'hata ayrıntısı yok'}\n"
            f"- Kaynak: {job.get('source') or 'kaynak belirtilmemiş'}\n\n"
            "Öneri: Kaynak sistem erişimini, kimlik bilgilerini ve ağ timeout ayarlarını kontrol edip job'ı yeniden çalıştırın."
        )
        return state
