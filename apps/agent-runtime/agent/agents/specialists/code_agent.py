"""
AgentOps — Code Specialist Agent (Tier 2)
==========================================
Writes, reviews, and executes code.
"""

from __future__ import annotations

import json
import logging
import time

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord
from agent.tools.base_tool import get_registry
from agent.nodes import _call_llm

log = logging.getLogger("agentops.agents.code")


class CodeAgent(BaseAgent):
    name = "code_agent"
    role = "Software Engineering Specialist"
    goal = "Write correct, efficient, and well-tested code to solve programming tasks."
    backstory = (
        "You are a senior software engineer with expertise in Python, TypeScript, and system design. "
        "You write clean code, add tests, and validate your solutions."
    )
    tier = "SPECIALIST"
    tools = ["code_runner", "file_reader", "web_search"]

    async def think(self, task: str, state: AgentState) -> Plan:
        system = (
            f"{self.build_system_prompt()}\n"
            "Plan the code solution step by step. "
            'JSON: {"steps": ["write function X", "test it", ...], "rationale": "..."}'
        )
        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            return Plan(steps=parsed.get("steps", [task]), rationale=parsed.get("rationale", ""))
        except json.JSONDecodeError:
            return Plan(
                steps=[f"Write code for: {task}", "Test the solution"],
                rationale="Standard coding flow.",
            )

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        registry = get_registry()
        start = time.perf_counter()

        # Generate code via LLM then execute it
        code_prompt = f"Write Python code for this task (executable, no imports that aren't standard):\n{step}\nOutput ONLY the code."
        code = await _call_llm(code_prompt)

        tool = registry.get("code_runner")
        if tool:
            result = await tool.execute(code=code)
        else:
            result = {"output": f"Code generated: {code[:100]}", "success": True}

        record: ToolCallRecord = {
            "tool_name": "code_runner",
            "arguments": {"code": code[:200]},
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
        rec = (
            "continue"
            if passed
            else ("retry" if state.get("retry_count", 0) < 3 else "escalate_hitl")
        )
        return Reflection(
            passed=passed,
            tool_success=passed,
            schema_valid=True,
            logic_sound=passed,
            recommendation=rec,
            retry_count=state.get("retry_count", 0),
            rationale=f"{rec.upper()}: {'Code executed successfully.' if passed else result.error or 'Execution failed.'}",
        )
