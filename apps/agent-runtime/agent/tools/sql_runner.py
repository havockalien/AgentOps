"""
AgentOps — Read-Only SQL Runner Tool
======================================
Executes SELECT queries against a configured database.
DML (INSERT/UPDATE/DELETE/DROP) is explicitly blocked.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent.tools.base_tool import BaseTool, get_registry

log = logging.getLogger("agentops.tools.sql_runner")

_BLOCKED_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
}


class SqlRunnerTool(BaseTool):
    name = "sql_runner"
    description = (
        "Execute a read-only SQL SELECT query against the configured database "
        "and return results as a formatted table. Only SELECT statements are allowed."
    )
    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL SELECT query to execute.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows to return.",
                "default": 50,
            },
        },
        "required": ["query"],
    }

    def _validate_query(self, query: str) -> None:
        upper = query.strip().upper()
        for kw in _BLOCKED_KEYWORDS:
            if kw in upper.split():
                raise ValueError(
                    f"SQL keyword '{kw}' is not allowed. Only SELECT queries permitted."
                )
        if not upper.startswith("SELECT"):
            raise ValueError("Only SELECT statements are permitted.")

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        query: str = kwargs["query"]
        limit: int = int(kwargs.get("limit", 50))
        self._validate_query(query)
        db_url = os.getenv("POSTGRES_URL", "")

        if not db_url:
            # Stub response for dev/test without a real database
            log.warning("POSTGRES_URL not set — returning stub SQL results.")
            return {
                "output": f"[STUB] Query: {query}\n| id | name | value |\n|---|---|---|\n| 1 | sample | 42 |",
                "rows": [{"id": 1, "name": "sample", "value": 42}],
                "row_count": 1,
                "stub": True,
            }

        try:
            import asyncpg

            conn = await asyncpg.connect(db_url)
            try:
                rows = await conn.fetch(f"{query} LIMIT {limit}")
                data = [dict(r) for r in rows]
                # Format as table
                if data:
                    headers = list(data[0].keys())
                    header_row = "| " + " | ".join(headers) + " |"
                    sep = "|" + "|".join(["---"] * len(headers)) + "|"
                    body = "\n".join(
                        "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
                        for row in data
                    )
                    output = f"{header_row}\n{sep}\n{body}"
                else:
                    output = "(no rows returned)"
                return {"output": output, "rows": data, "row_count": len(data)}
            finally:
                await conn.close()
        except Exception as exc:
            log.error("SQL execution failed: %s", exc)
            raise


get_registry().register(SqlRunnerTool())
