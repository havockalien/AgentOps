"""
AgentOps — Git Commit Worker (Tier 3)
======================================
Stateless worker: stage, commit, and push changes to a git repository.
"""

from __future__ import annotations

import asyncio
import logging
import time

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState, ToolCallRecord

log = logging.getLogger("agentops.workers.git_commit")


class GitCommitWorker(BaseAgent):
    name = "git_commit_worker"
    role = "Git Operations Worker"
    goal = "Stage, commit, and push code changes to a git repository."
    backstory = "You are a git automation specialist who manages version control operations."
    tier = "WORKER"
    tools = []

    async def think(self, task: str, state: AgentState) -> Plan:
        return Plan(
            steps=["git add -A", f'git commit -m "{task[:60]}"', "git push"],
            rationale="Standard git commit workflow.",
        )

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        step = plan.steps[state.get("current_step", 0)]
        start = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_shell(
                step,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            out = stdout.decode().strip() or stderr.decode().strip()
            success = proc.returncode == 0
        except asyncio.TimeoutError:
            out = "Git operation timed out after 30s."
            success = False
        except Exception as exc:
            out = str(exc)
            success = False

        record: ToolCallRecord = {
            "tool_name": "git",
            "arguments": {"command": step},
            "result": out,
            "error": None if success else out,
            "duration_ms": (time.perf_counter() - start) * 1000,
            "timestamp": str(time.time()),
        }
        return ActionResult(
            success=success,
            output=out,
            tool_calls_made=[record],
            duration_ms=(time.perf_counter() - start) * 1000,
            step_index=state.get("current_step", 0),
            error=None if success else out,
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        passed = result.success
        retry_count = state.get("retry_count", 0)
        rec = "continue" if passed else ("retry" if retry_count < 3 else "escalate_hitl")
        return Reflection(
            passed=passed,
            tool_success=passed,
            schema_valid=True,
            logic_sound=passed,
            recommendation=rec,
            retry_count=retry_count,
            rationale=f"{rec.upper()}: {'Git op succeeded.' if passed else 'Git op failed.'}",
        )
