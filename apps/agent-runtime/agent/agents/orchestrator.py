"""
AgentOps — Tier 1 Orchestrator Agent
=======================================
The Orchestrator is the top-level agent. It:
  1. Receives a high-level task from the API Gateway (via Redis/Kafka)
  2. Decomposes it into subtasks
  3. Assigns each subtask to a Tier 2 specialist agent
  4. Monitors sub-runs and aggregates results
  5. Handles failures by retrying or escalating to HITL
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord

log = logging.getLogger("agentops.agents.orchestrator")


@dataclass
class SubTask:
    id: str
    parent_run_id: str
    specialist_type: str
    task_description: str
    status: str = "pending"  # pending | running | completed | failed
    result: Optional[str] = None


class OrchestratorAgent(BaseAgent):
    """
    Tier 1 Orchestrator — Master coordinator of all agent workflows.
    """

    name = "orchestrator"
    role = "Master Orchestrator"
    goal = (
        "Decompose complex tasks into subtasks, assign them to specialist agents, "
        "monitor execution, and deliver a consolidated final result."
    )
    backstory = (
        "You are the director of an elite team of AI agents. "
        "You excel at breaking down ambiguous requests into clear, actionable subtasks "
        "and delegating them to the right specialist."
    )
    tier = "ORCHESTRATOR"
    tools = []  # Orchestrator delegates to specialists rather than using tools directly

    async def think(self, task: str, state: AgentState) -> Plan:
        """Decompose the task into specialist-assignable subtasks."""
        await self.emit_event("agent.think.start", {"task": task[:200]}, run_id=state["run_id"])
        start = time.perf_counter()

        specialist_types = [
            "devops_agent",
            "research_agent",
            "code_agent",
            "data_agent",
            "browser_agent",
            "monitoring_agent",
        ]
        system = (
            "You are a master orchestrator. Given a high-level task, "
            "produce an ordered list of subtasks with the best specialist for each. "
            f"Available specialists: {', '.join(specialist_types)}. "
            'Respond ONLY with JSON: {"steps": ["subtask1", "subtask2"], "rationale": "why"}'
        )

        from agent.nodes import _call_llm

        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            steps = parsed.get("steps", [task])
            rationale = parsed.get("rationale", "")
        except json.JSONDecodeError:
            steps = [task]
            rationale = "Direct execution (plan parse failed)."

        duration_ms = (time.perf_counter() - start) * 1000
        await self.emit_event(
            "agent.think.complete",
            {"steps": steps, "rationale": rationale},
            run_id=state["run_id"],
            duration_ms=duration_ms,
        )
        return Plan(steps=steps, rationale=rationale)

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        """Execute the current step — for the orchestrator this means invoking a specialist."""
        await self.emit_event(
            "agent.act.start", {"step": state.get("current_step")}, run_id=state["run_id"]
        )
        start = time.perf_counter()

        current_step = state.get("current_step", 0)
        if current_step >= len(plan.steps):
            return ActionResult(
                success=True,
                output="All subtasks dispatched.",
                step_index=current_step,
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        step_desc = plan.steps[current_step]

        # In a full implementation: POST to /api/v1/agents/{specialist_id}/run
        # For Phase 2: log the dispatch and return a stub result
        log.info("Orchestrator dispatching subtask: %s", step_desc[:80])

        tool_record: ToolCallRecord = {
            "tool_name": "specialist_dispatch",
            "arguments": {"step": step_desc, "step_index": current_step},
            "result": f"Subtask dispatched: {step_desc[:100]}",
            "error": None,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }

        duration_ms = (time.perf_counter() - start) * 1000
        await self.emit_event(
            "agent.act.complete",
            {"step": current_step, "output": step_desc[:100]},
            run_id=state["run_id"],
            duration_ms=duration_ms,
        )
        return ActionResult(
            success=True,
            output=f"Subtask dispatched to specialist: {step_desc}",
            tool_calls_made=[tool_record],
            duration_ms=duration_ms,
            step_index=current_step,
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        """Evaluate subtask result and decide on routing."""
        await self.emit_event(
            "agent.reflect.start", {"success": result.success}, run_id=state["run_id"]
        )
        start = time.perf_counter()

        retry_count = state.get("retry_count", 0)
        if not result.success and result.error:
            if retry_count < 3:
                recommendation = "retry"
                issues = [f"Subtask failed: {result.error}"]
            else:
                recommendation = "escalate_hitl"
                issues = ["Exceeded retry limit for subtask."]
        else:
            recommendation = "continue"
            issues = []

        reflection = Reflection(
            passed=result.success,
            tool_success=result.success,
            schema_valid=True,
            logic_sound=result.success,
            issues=issues,
            recommendation=recommendation,
            retry_count=retry_count,
            rationale=f"{recommendation.upper()}: {'Success.' if not issues else '; '.join(issues)}",
        )

        await self.emit_event(
            "agent.reflect.complete",
            {"recommendation": recommendation},
            run_id=state["run_id"],
            duration_ms=(time.perf_counter() - start) * 1000,
        )
        return reflection
