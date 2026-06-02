"""
Shared pytest fixtures for agent-runtime tests.

Provides:
  - fake_redis        : fakeredis async Redis stub
  - mock_llm_response : patches _call_llm to return canned JSON
  - sample_state      : a minimal AgentState for node testing
  - stub_plan         : a simple 2-step Plan for act/reflect testing
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


# ── Fake Redis ────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def fake_redis():
    """In-memory Redis stub using fakeredis."""
    try:
        # fakeredis >= 2.x: FakeRedis() constructor, no .create() needed
        try:
            import fakeredis.aioredis as fakeredis_async
            r = fakeredis_async.FakeRedis()
        except (ImportError, AttributeError):
            import fakeredis
            r = fakeredis.FakeRedis()
        yield r
        if hasattr(r, "aclose"):
            await r.aclose()
        elif hasattr(r, "close"):
            r.close()
    except ImportError:
        # Fallback: minimal async dict-based stub
        class SimpleRedisStub:
            def __init__(self):
                self._store = {}
                self._published = []

            async def setex(self, key, ttl, value):
                self._store[key] = value

            async def set(self, key, value, ex=None):
                self._store[key] = value

            async def get(self, key):
                return self._store.get(key)

            async def keys(self, pattern):
                import fnmatch
                return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

            async def publish(self, channel, message):
                self._published.append((channel, message))

            async def aclose(self):
                pass

        yield SimpleRedisStub()



# ── Sample state factory ───────────────────────────────────────────────────────


@pytest.fixture
def sample_state():
    """Minimal AgentState for testing individual nodes."""
    return {
        "run_id": "test-run-001",
        "agent_name": "test_agent",
        "task": "Write a Python function that returns the sum of two numbers.",
        "plan": ["Define the function", "Write the body", "Test the function"],
        "current_step": 0,
        "tool_calls": [],
        "observations": [],
        "memory_context": [],
        "reflection": "",
        "retry_count": 0,
        "hitl_pending": False,
        "hitl_request_id": None,
        "error": None,
        "final_output": None,
    }


@pytest.fixture
def stub_plan():
    """A minimal Plan for act/reflect testing."""
    from agent.base import Plan
    return Plan(
        steps=["Analyse requirements", "Implement solution"],
        rationale="Standard two-step approach.",
    )


# ── LLM mock context manager ─────────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """Patch agent.nodes._call_llm to return a canned plan JSON."""
    plan_json = json.dumps({
        "steps": ["Step 1: analyse task", "Step 2: execute solution"],
        "rationale": "Standard two-step approach from mock LLM.",
    })
    with patch("agent.nodes._call_llm", new_callable=AsyncMock, return_value=plan_json) as m:
        yield m
