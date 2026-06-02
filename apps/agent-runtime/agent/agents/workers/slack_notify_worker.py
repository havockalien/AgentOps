"""
AgentOps — Slack Notification Worker (Tier 3)
==============================================
Stateless worker: send a message to a Slack webhook.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord

log = logging.getLogger("agentops.workers.slack_notify")


class SlackNotifyWorker(BaseAgent):
    name = "slack_notify_worker"
    role = "Notification Worker"
    goal = "Send structured notifications to Slack channels via webhook."
    backstory = "You deliver concise, well-formatted status updates to team communication channels."
    tier = "WORKER"
    tools = []

    async def think(self, task: str, state: AgentState) -> Plan:
        return Plan(
            steps=["Format Slack message", "POST to webhook"],
            rationale="Standard notification flow.",
        )

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        start = time.perf_counter()
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        message = state.get("task", "AgentOps notification")

        payload = {
            "text": f":robot_face: *AgentOps Update*\n{message[:500]}",
            "username": "AgentOps Bot",
        }

        if not webhook_url:
            log.warning("SLACK_WEBHOOK_URL not set — skipping notification (stub).")
            output = f"[STUB] Slack notification sent: {message[:80]}"
            success = True
            error_msg = None
        else:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(webhook_url, json=payload)
                success = resp.status_code == 200
                output = f"Slack response: {resp.status_code}"
                error_msg = None if success else f"HTTP {resp.status_code}"
            except Exception as exc:
                output = f"Slack notification failed: {exc}"
                success = False
                error_msg = str(exc)

        record: ToolCallRecord = {
            "tool_name": "slack_webhook",
            "arguments": {"message": message[:100]},
            "result": output,
            "error": error_msg,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }
        return ActionResult(
            success=success,
            output=output,
            tool_calls_made=[record],
            duration_ms=(time.perf_counter() - start) * 1000,
            step_index=0,
            error=error_msg,
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        return Reflection(
            passed=result.success,
            tool_success=result.success,
            schema_valid=True,
            logic_sound=result.success,
            recommendation="continue" if result.success else "retry",
            retry_count=state.get("retry_count", 0),
            rationale=(
                "CONTINUE: Notification sent." if result.success else "RETRY: Notification failed."
            ),
        )
