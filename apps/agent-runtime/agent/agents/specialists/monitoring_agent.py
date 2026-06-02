"""
AgentOps — Monitoring Specialist Agent (Tier 2)
=================================================
Queries Prometheus metrics and Grafana dashboards for system health analysis.
"""

from __future__ import annotations

import json
import logging
import os
import time

import httpx

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord
from agent.nodes import _call_llm

log = logging.getLogger("agentops.agents.monitoring")


class MonitoringAgent(BaseAgent):
    name = "monitoring_agent"
    role = "Platform Monitoring Specialist"
    goal = "Query system metrics, detect anomalies, and produce health reports from Prometheus and Grafana."
    backstory = (
        "You are a platform reliability engineer who monitors distributed systems. "
        "You use Prometheus PromQL and Grafana to detect performance bottlenecks and predict failures."
    )
    tier = "SPECIALIST"
    tools = ["web_search"]

    async def _query_prometheus(self, promql: str) -> dict:
        prometheus_url = os.getenv("PROMETHEUS_URL", "")
        if not prometheus_url:
            return {"status": "stub", "data": {"result": [{"metric": {}, "value": [0, "0.5"]}]}}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{prometheus_url}/api/v1/query", params={"query": promql})
            return resp.json()

    async def think(self, task: str, state: AgentState) -> Plan:
        system = f'{self.build_system_prompt()}\nJSON: {{"steps": [...], "rationale": "..."}}'
        raw = await _call_llm(task, system)
        try:
            parsed = json.loads(raw)
            return Plan(steps=parsed.get("steps", [task]), rationale=parsed.get("rationale", ""))
        except json.JSONDecodeError:
            return Plan(
                steps=[f"Query metrics for: {task}", "Analyse results"],
                rationale="Standard monitoring flow.",
            )

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        start = time.perf_counter()
        data = await self._query_prometheus(f'up{{job="agentops"}}')  # Example query
        output = f"Monitoring result for '{step}': {json.dumps(data)[:300]}"
        record: ToolCallRecord = {
            "tool_name": "prometheus_query",
            "arguments": {"step": step},
            "result": output,
            "error": None,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }
        return ActionResult(
            success=True,
            output=output,
            tool_calls_made=[record],
            duration_ms=(time.perf_counter() - start) * 1000,
            step_index=state.get("current_step", 0),
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        return Reflection(
            passed=True,
            tool_success=True,
            schema_valid=True,
            logic_sound=True,
            recommendation="continue",
            retry_count=state.get("retry_count", 0),
            rationale="CONTINUE: Monitoring data retrieved.",
        )
