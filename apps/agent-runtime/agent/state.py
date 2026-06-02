"""
AgentOps — LangGraph AgentState TypedDict
==========================================
Central state bag threaded through every LangGraph node.
All fields are explicitly typed; Optional fields may be absent on first entry.
"""

from __future__ import annotations

from typing import Any, Optional

from typing_extensions import TypedDict


class ToolCallRecord(TypedDict):
    """Serialisable record of one tool invocation."""

    tool_name: str
    arguments: dict[str, Any]
    result: Optional[str]
    error: Optional[str]
    duration_ms: float
    timestamp: str


class AgentState(TypedDict):
    """
    Shared state for the LangGraph workflow.

    Threading model:
      Each field is *replaced* (not merged) on update.
      Accumulating fields (tool_calls, observations, memory_context) use
      Python list concatenation in node functions.
    """

    # ── Run linkage ───────────────────────────────────────────────────────────
    run_id: str  # Phase 1 Run.id — used to update DB/Redis status
    agent_name: str  # Which agent is executing this run

    # ── Task decomposition ────────────────────────────────────────────────────
    task: str  # The original high-level task string
    plan: list[str]  # List of step descriptions (output of planner_node)
    current_step: int  # Zero-based index into plan

    # ── Execution trace ───────────────────────────────────────────────────────
    tool_calls: list[ToolCallRecord]  # Accumulates across all steps
    observations: list[str]  # Tool outputs / intermediate results

    # ── Memory ────────────────────────────────────────────────────────────────
    memory_context: list[str]  # Retrieved relevant memories

    # ── Reflection & control flow ─────────────────────────────────────────────
    reflection: str  # Latest reflection rationale (human-readable)
    retry_count: int  # How many retries have been attempted on current step
    hitl_pending: bool  # True when paused at a human checkpoint
    hitl_request_id: Optional[str]  # Phase 1 HitlRequest.id

    # ── Terminal state ────────────────────────────────────────────────────────
    error: Optional[str]  # Set on abort / unrecoverable failure
    final_output: Optional[str]  # Set by output_node on success
