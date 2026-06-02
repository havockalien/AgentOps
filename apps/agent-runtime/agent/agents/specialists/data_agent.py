"""
AgentOps — Data Specialist Agent (Tier 2)
==========================================
Handles SQL queries, data analysis, and report generation.
"""

from __future__ import annotations

import json
import logging
import time

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord
from agent.tools.base_tool import get_registry
from agent.nodes import _call_llm

log = logging.getLogger("agentops.agents.data")


class DataAgent(BaseAgent):
    name = "data_agent"
    role = "Data Analysis Specialist"
    goal = "Query databases, analyse datasets, and produce actionable insights and reports."
    backstory = (
        "You are a data engineer and analyst with expertise in SQL, pandas, and statistical analysis. "
        "You translate business questions into precise queries and clear visualisations."
    )
    tier = "SPECIALIST"
    tools = ["sql_runner", "code_runner", "file_reader"]

    async def think(self, task: str, state: AgentState) -> Plan:
        system = f'{self.build_system_prompt()}\nJSON: {{"steps": [...], "rationale": "..."}}'
        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            return Plan(steps=parsed.get("steps", [task]), rationale=parsed.get("rationale", ""))
        except json.JSONDecodeError:
            return Plan(
                steps=[f"Query data for: {task}", "Analyse results"],
                rationale="Standard data flow.",
            )

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        registry = get_registry()
        start = time.perf_counter()
        tool = registry.get("sql_runner")
        query = f"SELECT * FROM information_schema.tables LIMIT 5  -- {step}"
        if tool:
            result = await tool.execute(query=query)
        else:
            result = {"output": f"Data result for: {step}", "success": True}
        record: ToolCallRecord = {
            "tool_name": "sql_runner",
            "arguments": {"query": query},
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
            rationale=f"{rec.upper()}: {'Query succeeded.' if passed else 'Query failed.'}",
        )
