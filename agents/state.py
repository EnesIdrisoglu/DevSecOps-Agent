"""Multi-agent akışında paylaşılan konuşma durumu."""

from dataclasses import dataclass, field


@dataclass
class AgentState:
    question: str
    project: str | None = None
    scanner: str | None = None
    handoff: str | None = None
    evidence: list[dict] = field(default_factory=list)
    answer: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)
