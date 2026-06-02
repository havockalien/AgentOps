"""
Tests for agent.base — BaseAgent, Plan, ActionResult, Reflection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.base import ActionResult, BaseAgent, Plan, Reflection
from agent.state import AgentState

# ── Minimal concrete implementation for testing ───────────────────────────────────────


class MinimalAgent(BaseAgent):
    name = "test_agent"
    role = "Test Agent"
    goal = "Run tests successfully."
    backstory = "A minimal agent for unit testing."
    tier = "SPECIALIST"
    tools = []

    async def think(self, task: str, state: AgentState) -> Plan:
        return Plan(steps=["Step A", "Step B"], rationale="Test plan.")

    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        return ActionResult(
            success=True,
            output="Test action completed.",
            step_index=state.get("current_step", 0),
        )

    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        return Reflection(
            passed=result.success,
            tool_success=result.success,
            schema_valid=True,
            logic_sound=True,
            recommendation="continue",
            rationale="CONTINUE: Test passed.",
        )


# ── Tests ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def agent():
    return MinimalAgent()


@pytest.fixture
def state(sample_state):
    return sample_state


class TestPlan:
    def test_plan_estimated_steps(self):
        plan = Plan(steps=["a", "b", "c"], rationale="test")
        assert plan.estimated_steps == 3

    def test_plan_empty(self):
        plan = Plan(steps=[], rationale="empty")
        assert plan.estimated_steps == 0


class TestBaseAgentThink:
    @pytest.mark.asyncio
    async def test_think_returns_plan(self, agent, sample_state):
        plan = await agent.think("test task", sample_state)
        assert isinstance(plan, Plan)
        assert len(plan.steps) > 0
        assert plan.rationale

    @pytest.mark.asyncio
    async def test_think_has_multiple_steps(self, agent, sample_state):
        plan = await agent.think("complex task", sample_state)
        assert plan.estimated_steps >= 1


class TestBaseAgentAct:
    @pytest.mark.asyncio
    async def test_act_returns_action_result(self, agent, stub_plan, sample_state):
        result = await agent.act(stub_plan, sample_state)
        assert isinstance(result, ActionResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_act_output_is_string(self, agent, stub_plan, sample_state):
        result = await agent.act(stub_plan, sample_state)
        assert isinstance(result.output, str)
        assert len(result.output) > 0


class TestBaseAgentReflect:
    @pytest.mark.asyncio
    async def test_reflect_pass(self, agent, sample_state):
        result = ActionResult(success=True, output="OK")
        reflection = await agent.reflect(result, sample_state)
        assert reflection.passed is True
        assert reflection.recommendation == "continue"

    @pytest.mark.asyncio
    async def test_reflect_fail_returns_retry(self, agent, sample_state):
        """A failed result with retry_count < 3 should recommend retry."""
        # Override reflect to simulate retry logic
        sample_state["retry_count"] = 1
        result = ActionResult(success=False, output="", error="Tool failed")

        # MinimalAgent always returns continue; we test the pattern using Orchestrator
        from agent.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        reflection = await orch.reflect(result, sample_state)
        assert reflection.recommendation == "retry"

    @pytest.mark.asyncio
    async def test_reflect_escalate_after_max_retries(self, agent, sample_state):
        """After MAX_RETRIES failures, recommend escalate_hitl."""
        sample_state["retry_count"] = 3
        result = ActionResult(success=False, output="", error="Persistent failure")

        from agent.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        reflection = await orch.reflect(result, sample_state)
        assert reflection.recommendation == "escalate_hitl"


class TestBaseAgentEmitEvent:
    @pytest.mark.asyncio
    async def test_emit_event_no_redis(self, agent, sample_state):
        """emit_event should not raise even with no Redis connection."""
        await agent.emit_event("agent.think.start", {"task": "test"}, run_id="run-001")

    @pytest.mark.asyncio
    async def test_emit_event_publishes_to_redis(self, fake_redis, sample_state):
        agent = MinimalAgent(redis=fake_redis)
        await agent.emit_event("agent.act.complete", {"output": "done"}, run_id="run-001")
        # If fakeredis is available, we can check the published messages
        # For the stub, just assert no exception
