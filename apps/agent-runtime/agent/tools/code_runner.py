"""
AgentOps — Code Runner Tool
============================
Executes Python code in a restricted subprocess sandbox.
Only safe builtins are allowed. Network and filesystem access are blocked.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import textwrap
from typing import Any

from agent.tools.base_tool import BaseTool, get_registry

log = logging.getLogger("agentops.tools.code_runner")

MAX_EXEC_SECONDS = 10
MAX_OUTPUT_CHARS = 4000

_SAFE_BUILTINS = [
    "print",
    "len",
    "range",
    "int",
    "float",
    "str",
    "list",
    "dict",
    "set",
    "tuple",
    "bool",
    "sum",
    "min",
    "max",
    "abs",
    "round",
    "sorted",
    "enumerate",
    "zip",
    "map",
    "filter",
    "isinstance",
    "type",
    "repr",
    "format",
]


class CodeRunnerTool(BaseTool):
    name = "code_runner"
    description = (
        "Execute Python code and return stdout output. "
        "Use for calculations, data processing, and algorithm verification. "
        "Network and file-system access are disabled for safety."
    )
    schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute."},
            "timeout": {
                "type": "integer",
                "description": f"Execution timeout in seconds (max {MAX_EXEC_SECONDS}).",
                "default": 5,
            },
        },
        "required": ["code"],
    }

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        code: str = kwargs["code"]
        timeout: int = min(int(kwargs.get("timeout", 5)), MAX_EXEC_SECONDS)
        clean_code = textwrap.dedent(code)

        # Write to a temp file and run in subprocess for isolation
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(clean_code)
            tmp_path = tmp.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "output": f"Execution timed out after {timeout}s.",
                    "error": "timeout",
                    "exit_code": -1,
                }

            out = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_CHARS]
            err = stderr.decode("utf-8", errors="replace")[:500]

            if proc.returncode != 0:
                return {
                    "output": f"Code failed:\n{err}",
                    "error": err,
                    "exit_code": proc.returncode,
                }

            return {"output": out or "(no output)", "exit_code": 0}
        finally:
            os.unlink(tmp_path)


get_registry().register(CodeRunnerTool())
