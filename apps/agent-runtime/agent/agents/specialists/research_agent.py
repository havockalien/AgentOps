"""
AgentOps — Research Specialist Agent (Tier 2)
===============================================
Handles information gathering, documentation synthesis, and web research.
"""

from __future__ import annotations

import json
import logging
import time

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord
from agent.tools.base_tool import get_registry
from agent.nodes import _call_llm

log = logging.getLogger("agentops.agents.research")


class ResearchAgent(BaseAgent):
    name = "research_agent"
    role = "Research Specialist"
    goal = "Gather accurate, up-to-date information from the web and internal knowledge base."
    backstory = (
        "You are a meticulous researcher who synthesises information from multiple sources, "
        "verifies facts, and delivers concise, well-structured summaries."
    )
    tier = "SPECIALIST"
    tools = ["web_search", "file_reader"]

    async def think(self, task: str, state: AgentState) -> Plan:
        system = (
            f"{self.build_system_prompt()}\n"
            'JSON: {"steps": ["search for X", "synthesise", ...], "rationale": "..."}'
        )
        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            return Plan(steps=parsed.get("steps", [task]), rationale=parsed.get("rationale", ""))
        except json.JSONDecodeError:
            return Plan(steps=[f"Search for: {task}", "Summarise findings"], rationale="Standard research flow.")

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        registry = get_registry()
        start = time.perf_counter()
        tool = registry.get("web_search")
        if tool:
            result = await tool.execute(query=step)
        else:
            result = {"output": f"Research result for: {step}", "success": True}
        record: ToolCallRecord = {
            "tool_name": "web_search",
            "arguments": {"query": step},
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
        passed = result.success and bool(result.output.strip())
        rec = "continue" if passed else ("retry" if state.get("retry_count", 0) < 3 else "escalate_hitl")
        return Reflection(
            passed=passed, tool_success=result.success, schema_valid=passed,
            logic_sound=passed, recommendation=rec, retry_count=state.get("retry_count", 0),
            rationale=f"{rec.upper()}: {'Good results found.' if passed else 'No results.'}",
        )
