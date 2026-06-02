"""
AgentOps — Log Parser Worker (Tier 3)
=======================================
Stateless single-task worker: parse log lines, extract errors and patterns.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord

log = logging.getLogger("agentops.workers.log_parser")

ERROR_PATTERNS = [
    r"ERROR", r"CRITICAL", r"FATAL", r"Exception", r"Traceback",
    r"\[ERROR\]", r"\[CRITICAL\]", r"500",
]


class LogParserWorker(BaseAgent):
    name = "log_parser_worker"
    role = "Log Analysis Worker"
    goal = "Parse log files, extract error patterns, and return a structured error report."
    backstory = "You are a specialist in log analysis and error pattern recognition."
    tier = "WORKER"
    tools = ["file_reader"]

    async def think(self, task: str, state: AgentState) -> Plan:
        return Plan(steps=["Parse log content for errors", "Format error report"], rationale="Standard log parsing.")

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        start = time.perf_counter()
        log_content = state.get("task", "")
        errors = []
        for i, line in enumerate(log_content.splitlines(), 1):
            if any(re.search(p, line) for p in ERROR_PATTERNS):
                errors.append(f"Line {i}: {line.strip()[:120]}")

        output = (
            f"Found {len(errors)} error(s):\n" + "\n".join(errors[:20])
            if errors else "No errors found in log content."
        )
        record: ToolCallRecord = {
            "tool_name": "log_parser",
            "arguments": {"lines_scanned": len(log_content.splitlines())},
            "result": output,
            "error": None,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }
        return ActionResult(
            success=True, output=output,
            tool_calls_made=[record],
            duration_ms=(time.perf_counter() - start) * 1000,
            step_index=0,
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        return Reflection(
            passed=True, tool_success=True, schema_valid=True, logic_sound=True,
            recommendation="continue", retry_count=0,
            rationale="CONTINUE: Log parsing complete.",
        )
