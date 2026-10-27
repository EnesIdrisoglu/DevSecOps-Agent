"""Platform verilerini MCP tools olarak sunar."""

from fastmcp import FastMCP

from ..tools import database
from ..tools.web_search import search_cve
from ..knowledge.vector_store import KnowledgeStore


mcp = FastMCP("DevSecOps Platform MCP Server")
knowledge = KnowledgeStore()


@mcp.tool
def list_projects() -> list[str]:
    return database.list_projects()


@mcp.tool
def get_project_findings(project: str) -> list[dict]:
    summary = database.project_risk_summary(project)
    return (summary or {}).get("findings", [])


@mcp.tool
def get_project_summary(project: str) -> dict:
    return database.project_risk_summary(project) or {}


@mcp.tool
def get_projects_with_findings() -> list[dict]:
    return database.projects_with_open_findings()


@mcp.tool
def get_projects_by_scanner(scanner: str) -> list[dict]:
    return database.projects_by_scanner(scanner)


@mcp.tool
def list_scanners() -> list[str]:
    return database.list_scanners()


@mcp.tool
def get_global_findings() -> list[dict]:
    return database.all_open_findings()


@mcp.tool
def get_release_portfolio() -> list[dict]:
    return database.release_portfolio()


@mcp.tool
def get_project_scorecard(project: str) -> list[dict]:
    return database.scorecard_status(project) or []


@mcp.tool
def get_failed_job(project: str) -> dict | None:
    return database.latest_failed_job(project)


@mcp.tool
def search_knowledge(query: str, limit: int = 3) -> list[dict]:
    return knowledge.search(query, k=limit)


@mcp.tool
def search_cve_web(cve: str) -> dict:
    return search_cve(cve)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8001)
