"""LangGraph tabanlı Supervisor ve specialist-agent orchestration."""

from __future__ import annotations

import os
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .finding_projects_agent import FindingProjectsAgent
from .findings_agent import FindingsAgent
from .global_findings_agent import GlobalFindingsAgent
from .global_release_agent import GlobalReleaseAgent
from .global_scorecard_agent import GlobalScorecardAgent
from .global_metrics_agent import GlobalMetricsAgent
from .scanner_projects_agent import ScannerProjectsAgent
from .scan_agent import ScanAgent
from .job_agent import JobDiagnosticAgent
from .knowledge_agent import KnowledgeAgent
from .project_agent import ProjectAgent
from .release_agent import ReleaseRiskAgent
from .scorecard_agent import ScorecardAgent
from .state import AgentState
from ..memory.store import ConversationMemory
from ..tools.mcp_gateway import MCPGateway


AGENT_NAMES = Literal[
    "finding_projects_agent", "global_findings_agent", "findings_agent",
    "global_release_agent", "release_risk_agent", "global_scorecard_agent",
    "scorecard_agent", "job_diagnostic_agent", "project_agent", "knowledge_agent",
    "global_metrics_agent", "scanner_projects_agent", "scan_agent",
]


class Handoff(BaseModel):
    agent: AGENT_NAMES = Field(description="Kullanıcı sorusunu cevaplayacak specialist agent")
    project: str | None = Field(default=None, description="Soruda açıkça geçen proje adı; yoksa null")
    scanner: str | None = Field(default=None, description="Soruda geçen scanner adı")
    scope: Literal["global", "project", "followup"] = Field(description="Sorunun kapsamı")


class GraphState(TypedDict, total=False):
    question: str
    project: str | None
    last_project: str | None
    scanner: str | None
    handoff: str
    answer: str
    history: list[tuple[str, str]]


SUPERVISOR_PROMPT = """
Sen DevSecOps Supervisor Agent'sın. Kullanıcıyı aşağıdaki specialist agent'lardan birine handoff et.

- finding_projects_agent: açık bulgusu olan projelerin listesi
- global_findings_agent: tüm projelerdeki bulgular ve severity analizi
- findings_agent: belirli bir projenin bulguları
- global_release_agent: tüm projelerin release uygunluğu
- release_risk_agent: belirli bir projenin release uygunluğu
- global_scorecard_agent: tüm projelerin karne durumu
- scorecard_agent: belirli bir projenin karne durumu
- job_diagnostic_agent: belirli bir projenin job hatası
- project_agent: proje listesi veya belirli proje özeti
- knowledge_agent: remediation, çözüm önerisi ve güvenlik bilgisi
- global_metrics_agent: sadece istenen aggregate sayı
- scanner_projects_agent: belirli scanner ile taranan projeler
- scan_agent: belirli projenin son başarılı tarama tarihi ve scan geçmişi

Kullanıcı belirli bir proje adı vermediyse global agent seçilmelidir. Sadece kullanıcı açıkça önceki projeye gönderme yapıyorsa follow-up kapsamı kullan.
"critical", "high", "medium" ve "low" severity filtrelerini soruda koru; yalnızca istenen seviyeleri döndüren specialist'i seç.
Scanner sorularında scanner alanını ayrıca doldur.
Önceki proje bağlamı varsa takip sorularında kullan.
Sadece yapılandırılmış handoff çıktısı üret.
"""


class SupervisorAgent:
    """LangGraph workflow'unu çağıran uygulama facade'ı."""

    def __init__(self, *, model: str | None = None):
        self.llm = ChatOllama(
            model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:4b"),
            base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            temperature=0,
            # Supervisor yalnızca handoff seçer; uzun reasoning'i specialist/knowledge akışına bırakır.
            reasoning=os.getenv("OLLAMA_SUPERVISOR_THINK", "false").lower() not in {"0", "false", "no"},
        )
        self.agents = {
            "finding_projects_agent": FindingProjectsAgent(),
            "global_findings_agent": GlobalFindingsAgent(),
            "findings_agent": FindingsAgent(),
            "global_release_agent": GlobalReleaseAgent(),
            "release_risk_agent": ReleaseRiskAgent(),
            "global_scorecard_agent": GlobalScorecardAgent(),
            "scorecard_agent": ScorecardAgent(),
            "job_diagnostic_agent": JobDiagnosticAgent(),
            "project_agent": ProjectAgent(),
            "knowledge_agent": KnowledgeAgent(),
            "global_metrics_agent": GlobalMetricsAgent(),
            "scanner_projects_agent": ScannerProjectsAgent(),
            "scan_agent": ScanAgent(),
        }
        self.graph = self._build_graph()
        self.memory = ConversationMemory()
        self.mcp = MCPGateway()

    def _build_graph(self):
        builder = StateGraph(GraphState)
        builder.add_node("supervisor", self._supervisor_node)
        for name in self.agents:
            builder.add_node(name, self._specialist_node(name))
        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges("supervisor", lambda state: state["handoff"], {name: name for name in self.agents})
        for name in self.agents:
            builder.add_edge(name, END)
        return builder.compile(checkpointer=MemorySaver())

    def _supervisor_node(self, state: GraphState) -> dict:
        known_projects = [str(project) for project in self.mcp.call("list_projects")]
        known_scanners = [str(scanner) for scanner in self.mcp.call("list_scanners")]
        question_lower = state["question"].lower()
        explicit_project = next((project for project in known_projects if project.lower() in question_lower), None)
        explicit_scanner = next((scanner for scanner in known_scanners if scanner.lower() in question_lower), None)
        followup_reference = any(token in question_lower.split() for token in ("bu", "şu", "bunlar", "önceki", "aynı"))
        structured_llm = self.llm.with_structured_output(Handoff)
        response = structured_llm.invoke([
            SystemMessage(content=SUPERVISOR_PROMPT + f"\nGeçerli proje adları: {', '.join(known_projects)}\nGeçerli scanner adları: {', '.join(known_scanners)}\nBu mesajda açık proje: {explicit_project or 'yok'}\nBu mesajda açık scanner: {explicit_scanner or 'yok'}\nAnaforik takip ifadesi: {'var' if followup_reference else 'yok'}"),
            *([HumanMessage(content=f"Önceki proje: {state.get('last_project')}")] if state.get("last_project") else []),
            HumanMessage(content=state["question"]),
        ])
        project = self._normalize_project(response.project, known_projects) if explicit_project else None
        if not explicit_project and response.agent in {"findings_agent", "release_risk_agent", "scorecard_agent", "job_diagnostic_agent"} and not followup_reference:
            response.agent = {"findings_agent": "global_findings_agent", "release_risk_agent": "global_release_agent", "scorecard_agent": "global_scorecard_agent", "job_diagnostic_agent": "project_agent"}[response.agent]
        if not project and response.agent == "knowledge_agent" and state.get("last_project"):
            project = state["last_project"]
        elif not project and response.scope == "followup" and followup_reference:
            project = state.get("last_project")
        scanner = explicit_scanner or response.scanner
        return {"handoff": response.agent, "project": project, "scanner": scanner, "last_project": project or state.get("last_project")}

    @staticmethod
    def _normalize_project(candidate: str | None, known_projects: list[str]) -> str | None:
        if not candidate:
            return None
        value = candidate.strip().lower().replace("_project", "").replace("-project", "")
        return next((project for project in known_projects if project.lower() == value or project.lower() in value), None)

    def _specialist_node(self, name: str):
        def node(state: GraphState) -> dict:
            specialist_state = AgentState(
                question=state["question"],
                project=state.get("project"),
                scanner=state.get("scanner"),
                history=state.get("history", []),
            )
            result = self.agents[name].run(specialist_state)
            return {"answer": result.answer, "history": state.get("history", []) + [(state["question"], result.answer)]}
        return node

    def answer(self, question: str, *, thread_id: str = "default") -> str:
        last_project = self.memory.last_project(thread_id)
        result = self.graph.invoke(
            {"question": question, "history": self.memory.recent(thread_id), "last_project": last_project},
            {"configurable": {"thread_id": thread_id}},
        )
        self.memory.append(thread_id, "user", question, result.get("project"))
        self.memory.append(thread_id, "assistant", result["answer"], result.get("project"))
        return result["answer"]
