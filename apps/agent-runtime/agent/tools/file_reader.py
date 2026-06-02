"""
AgentOps — File Reader/Writer Tool
====================================
Read and write files within the allowed workspace directory only.
Prevents path traversal attacks.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from agent.tools.base_tool import BaseTool, get_registry

log = logging.getLogger("agentops.tools.file_reader")

WORKSPACE_ROOT = Path(os.getenv("AGENT_WORKSPACE", "/tmp/agentops_workspace"))


class FileReaderTool(BaseTool):
    name = "file_reader"
    description = (
        "Read or write files within the agent workspace. "
        "Use for reading configuration, source code, or writing output reports."
    )
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list"],
                "description": "Operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "Relative file path within the workspace.",
            },
            "content": {
                "type": "string",
                "description": "Content to write (required for write action).",
            },
        },
        "required": ["action", "path"],
    }

    def _safe_path(self, relative: str) -> Path:
        """Resolve and validate path stays within workspace."""
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        resolved = (WORKSPACE_ROOT / relative).resolve()
        if not str(resolved).startswith(str(WORKSPACE_ROOT.resolve())):
            raise PermissionError(f"Path '{relative}' is outside the workspace.")
        return resolved

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        action: str = kwargs["action"]
        path: str = kwargs["path"]
        content: Optional[str] = kwargs.get("content")
        safe = self._safe_path(path)

        if action == "read":
            if not safe.exists():
                return {"output": f"File not found: {path}", "error": "not_found"}
            text = safe.read_text(encoding="utf-8")
            return {"output": text[:8000], "path": str(safe), "size": len(text)}

        elif action == "write":
            if content is None:
                return {"output": "No content provided for write.", "error": "missing_content"}
            safe.parent.mkdir(parents=True, exist_ok=True)
            safe.write_text(content, encoding="utf-8")
            return {"output": f"Written {len(content)} chars to {path}.", "path": str(safe)}

        elif action == "list":
            if not safe.is_dir():
                return {"output": f"Not a directory: {path}", "error": "not_a_dir"}
            entries = [str(p.relative_to(WORKSPACE_ROOT)) for p in safe.iterdir()]
            return {"output": "\n".join(entries), "entries": entries}

        return {"output": f"Unknown action: {action}", "error": "unknown_action"}


get_registry().register(FileReaderTool())
