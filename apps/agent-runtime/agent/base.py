"""
AgentOps — Abstract BaseAgent
==============================
Defines the ReAct (Reason → Act → Observe → Reflect → Repeat) interface
that every agent in the system must implement.

All concrete agents subclass BaseAgent and override:
  - think()   : LLM call — decompose task into a Plan
  - act()     : Execute the next step of the plan (tool call or direct action)
  - reflect() : Evaluate the ActionResult and decide what to do next

Emit semantics:
  Every method emits a structured AgentEvent to:
    1. OpenTelemetry (span + attributes)
    2. Redis pub/sub (agentops.events channel) for live dashboard
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from agent.state import AgentState, ToolCallRecord
from agent.memory import MemoryClient

log = logging.getLogger("agentops.agent")


# ── Data models ───────────────────────────────────────────────────────────────


@dataclass
class Plan:
    """Output of BaseAgent.think()."""

    steps: list[str]
    rationale: str
    estimated_steps: int = 0

    def __post_init__(self) -> None:
        self.estimated_steps = len(self.steps)


@dataclass
class ActionResult:
    """Output of BaseAgent.act()."""

    success: bool
    output: str
    tool_calls_made: list[ToolCallRecord] = field(default_factory=list)
    duration_ms: float = 0.0
    step_index: int = 0
    error: Optional[str] = None


@dataclass
class Reflection:
    """Output of BaseAgent.reflect()."""

    passed: bool
    tool_success: bool
    schema_valid: bool
    logic_sound: bool
    issues: list[str] = field(default_factory=list)
    recommendation: str = "continue"  # 'continue' | 'retry' | 'escalate_hitl' | 'abort'
    retry_count: int = 0
    rationale: str = ""


# ── BaseAgent ─────────────────────────────────────────────────────────────────


class BaseAgent(ABC):
    """
    Abstract base for all AgentOps agents.

    Subclasses must provide:
      - name       : Human-readable agent identifier
      - role       : Short role description (used in LLM system prompt)
      - goal       : What this agent is trying to achieve
      - backstory  : Context / persona for the LLM
      - tools      : List of ToolSpec instances available to this agent
      - tier       : 'ORCHESTRATOR' | 'SPECIALIST' | 'WORKER'

    And must implement:
      - think(task, state) -> Plan
      - act(plan, state) -> ActionResult
      - reflect(result, state) -> Reflection
    """

    # Override in subclasses
    name: str = "base-agent"
    role: str = "Generic Agent"
    goal: str = "Complete the assigned task accurately."
    backstory: str = "You are a helpful AI agent."
    tier: str = "SPECIALIST"
    tools: list[Any] = []

    def __init__(
        self,
        memory_namespace: Optional[str] = None,
        redis: Optional[Any] = None,
        llm: Optional[Any] = None,
    ) -> None:
        self.memory_namespace = memory_namespace or f"agent:{self.name}"
        self._redis = redis
        self._llm = llm
        self._memory: Optional[MemoryClient] = MemoryClient(redis) if redis else None
        log.info(
            "Agent initialised: name=%s tier=%s namespace=%s",
            self.name,
            self.tier,
            self.memory_namespace,
        )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def think(self, task: str, state: AgentState) -> Plan:
        """
        Decompose the high-level task into an ordered list of steps using the LLM.
        Emits: agent.think.start / agent.think.complete
        """
        ...

    @abstractmethod
    async def act(self, plan: Plan, state: AgentState) -> ActionResult:
        """
        Execute the next step from the plan (may invoke a tool).
        Emits: agent.act.start / agent.act.complete
        """
        ...

    @abstractmethod
    async def reflect(self, result: ActionResult, state: AgentState) -> Reflection:
        """
        Evaluate the ActionResult and decide next routing:
          continue | retry | escalate_hitl | abort
        Emits: agent.reflect.start / agent.reflect.complete
        """
        ...

    # ── Concrete helpers ──────────────────────────────────────────────────────

    async def emit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        run_id: str = "",
        duration_ms: Optional[float] = None,
    ) -> None:
        """
        Emit a structured AgentEvent to:
          1. Python logger (always)
          2. Redis pub/sub channel `agentops.events` (if Redis is available)
        """
        event: dict[str, Any] = {
            "event_type": event_type,
            "run_id": run_id,
            "agent_name": self.name,
            "agent_tier": self.tier,
            "timestamp": str(time.time()),
            "payload": payload,
        }
        if duration_ms is not None:
            event["duration_ms"] = duration_ms

        log.info("AgentEvent: type=%s run=%s", event_type, run_id)

        if self._redis:
            try:
                await self._redis.publish("agentops.events", json.dumps(event))
            except Exception as exc:
                log.warning("Failed to publish event to Redis: %s", exc)

    async def get_memory_context(self, query: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant memories from the agent's namespace."""
        if self._memory:
            return await self._memory.retrieve(query, self.memory_namespace, top_k)
        return []

    async def store_memory(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Persist content to the agent's memory namespace."""
        if self._memory:
            return await self._memory.store(content, self.memory_namespace, metadata)
        return None

    def build_system_prompt(self) -> str:
        """Build the LLM system prompt from role/goal/backstory."""
        return (
            f"You are {self.name}, a {self.role}.\n"
            f"Goal: {self.goal}\n"
            f"Backstory: {self.backstory}\n\n"
            "Always respond with structured JSON when asked to plan or reflect."
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} tier={self.tier!r}>"
