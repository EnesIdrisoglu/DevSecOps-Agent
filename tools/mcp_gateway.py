"""Specialist agent'ların MCP tool çağrı sınırı."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any


class MCPGateway:
    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("DEVSECOPS_MCP_URL", "http://127.0.0.1:8001/mcp")
        self.timeout = float(os.getenv("MCP_TIMEOUT", "8"))
        self.strict = os.getenv("MCP_STRICT", "true").lower() not in {"0", "false", "no"}

    def call(self, tool: str, **arguments: Any) -> Any:
        """MCP server'a çağrı yapar; MCP kapalıysa yerel geliştirme fallback'i kullanır."""
        try:
            return asyncio.run(asyncio.wait_for(self._call(tool, arguments), timeout=self.timeout))
        except Exception:
            if self.strict:
                raise
            return self._local(tool, arguments)

    async def _call(self, tool: str, arguments: dict[str, Any]) -> Any:
        from langchain.mcp import MCPAdapter

        config = {"mcpServers": {"devsecops": {"url": self.url}}}
        async with MCPAdapter(config) as adapter:
            tools = await adapter.list_tools()
        selected = next((item for item in tools if item.name.endswith(tool) or item.name == tool), None)
        if selected is None:
            raise LookupError(f"MCP tool bulunamadı: {tool}")
        result = await selected.ainvoke(arguments)
        result = self._unwrap_content(result)
        if tool == "list_projects":
            return self._project_names(result)
        return result

    @staticmethod
    def _unwrap_content(result: Any) -> Any:
        """LangChain MCPAdapter'ın content bloklarını gerçek JSON değerine çevirir."""
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict) and "text" in result[0]:
            try:
                return json.loads(result[0]["text"])
            except (TypeError, json.JSONDecodeError):
                return result[0]["text"]
        return result

    @staticmethod
    def _project_names(result: Any) -> list[str]:
        if isinstance(result, dict):
            result = result.get("projects", result.get("data", result.get("result", [])))
        if isinstance(result, str):
            return [result]
        if not isinstance(result, list):
            return []
        names = []
        for item in result:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("project")
                if name:
                    names.append(str(name))
        return names

    @staticmethod
    def _local(tool: str, arguments: dict[str, Any]) -> Any:
        from . import database
        local = {
            "list_projects": lambda: database.list_projects(),
            "get_project_findings": lambda: (database.project_risk_summary(arguments["project"]) or {}).get("findings", []),
            "get_project_summary": lambda: database.project_risk_summary(arguments["project"]) or {},
            "get_projects_with_findings": lambda: database.projects_with_open_findings(),
            "get_projects_by_scanner": lambda: database.projects_by_scanner(arguments["scanner"]),
            "get_global_findings": lambda: database.all_open_findings(),
            "get_release_portfolio": lambda: database.release_portfolio(),
            "get_project_scorecard": lambda: database.scorecard_status(arguments["project"]) or [],
            "get_failed_job": lambda: database.latest_failed_job(arguments["project"]),
        }
        if tool not in local:
            return []
        return local[tool]()
