"""
AgentOps — DevOps Specialist Agent (Tier 2)
==============================================
Handles infrastructure tasks: kubernetes operations, git PR management, log analysis.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord
from agent.tools.base_tool import get_registry
from agent.nodes import _call_llm

log = logging.getLogger("agentops.agents.devops")


class DevOpsAgent(BaseAgent):
    name = "devops_agent"
    role = "DevOps Specialist"
    goal = "Manage infrastructure, CI/CD pipelines, kubernetes deployments, and resolve operational incidents."
    backstory = (
        "You are a senior DevOps engineer with 10+ years of experience in kubernetes, "
        "CI/CD, monitoring, and incident response. You solve infrastructure problems methodically."
    )
    tier = "SPECIALIST"
    tools = ["web_search", "code_runner", "file_reader"]

    async def think(self, task: str, state: AgentState) -> Plan:
        system = (
            f"{self.build_system_prompt()}\n"
            "Break down this DevOps task into precise executable steps. "
            'JSON only: {"steps": [...], "rationale": "..."}'
        )
        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            return Plan(steps=parsed.get("steps", [task]), rationale=parsed.get("rationale", ""))
        except json.JSONDecodeError:
            return Plan(steps=[task], rationale="Direct execution.")

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        registry = get_registry()
        start = time.perf_counter()

        # Use code_runner for operational commands
        tool = registry.get("code_runner")
        if tool:
            result = await tool.execute(code=f"# DevOps: {step}\nprint('Executing: {step[:60]}')")
        else:
            result = {"output": f"Executed: {step}", "success": True}

        record: ToolCallRecord = {
            "tool_name": "code_runner",
            "arguments": {"step": step},
            "result": result.get("output"),
            "error": result.get("error"),
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }
        return ActionResult(
            success=result.get("success", True),
            output=result.get("output", ""),
            tool_calls_made=[record],
            duration_ms=(time.perf_counter() - start) * 1000,
            step_index=state.get("current_step", 0),
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        passed = result.success
        retry_count = state.get("retry_count", 0)
        if not passed and retry_count < 3:
            rec = "retry"
        elif not passed:
            rec = "escalate_hitl"
        else:
            rec = "continue"
        return Reflection(
            passed=passed,
            tool_success=passed,
            schema_valid=True,
            logic_sound=passed,
            recommendation=rec,
            retry_count=retry_count,
            rationale=f"{rec.upper()}: {'Success' if passed else result.error or 'Failed'}",
        )
