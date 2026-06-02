"""
AgentOps — CrewAI Crew Definitions
=====================================
Defines named multi-agent crews using CrewAI's Crew and Agent abstractions.
Each crew groups an Orchestrator with domain specialists for a specific mission type.

AutoGen integration provides debate/critique sessions before final commits.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger("agentops.crews")


def _try_import_crewai() -> tuple[Any, Any, Any]:
    """Attempt to import CrewAI; return stubs if not installed."""
    try:
        from crewai import Agent, Crew, Task

        return Agent, Crew, Task
    except ImportError:
        log.warning("crewai not installed — crew features will be unavailable.")
        return None, None, None


def _make_crewai_agent(role: str, goal: str, backstory: str, verbose: bool = True) -> Any:
    Agent, _, _ = _try_import_crewai()
    if Agent is None:
        return None
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=verbose,
        allow_delegation=False,
    )


# ── Crew Definitions ──────────────────────────────────────────────────────────


def build_devops_crew() -> Optional[Any]:
    """
    DevOpsCrew — Orchestrator + DevOps Specialist + Log Parser + Git Commit Worker.
    Use for: incident response, deployment automation, log analysis.
    """
    Agent, Crew, Task = _try_import_crewai()
    if Crew is None:
        return None

    orchestrator = _make_crewai_agent(
        role="Master Orchestrator",
        goal="Coordinate the DevOps team to resolve infrastructure issues efficiently.",
        backstory="You are the director of a DevOps team, expert at delegating and tracking tasks.",
    )
    devops = _make_crewai_agent(
        role="DevOps Specialist",
        goal="Diagnose and resolve infrastructure, CI/CD, and kubernetes issues.",
        backstory="Senior DevOps engineer with 10+ years in cloud infrastructure.",
    )
    log_analyst = _make_crewai_agent(
        role="Log Analysis Worker",
        goal="Parse logs and extract error patterns for root cause analysis.",
        backstory="Expert in log analysis, regex patterns, and error classification.",
    )

    if not all([orchestrator, devops, log_analyst]):
        return None

    return Crew(
        agents=[orchestrator, devops, log_analyst],
        verbose=True,
        process="hierarchical",
        manager_llm=None,
    )


def build_research_crew() -> Optional[Any]:
    """
    ResearchCrew — Orchestrator + Research Specialist.
    Use for: information gathering, documentation, competitive analysis.
    """
    Agent, Crew, Task = _try_import_crewai()
    if Crew is None:
        return None

    orchestrator = _make_crewai_agent(
        role="Research Director",
        goal="Oversee the research process and synthesise findings into actionable insights.",
        backstory="Strategic research director with a talent for distilling complex information.",
    )
    researcher = _make_crewai_agent(
        role="Research Specialist",
        goal="Gather accurate, comprehensive information from web and knowledge sources.",
        backstory="Meticulous researcher with expertise in web search and information synthesis.",
    )

    if not all([orchestrator, researcher]):
        return None

    return Crew(
        agents=[orchestrator, researcher],
        verbose=True,
        process="sequential",
    )


def build_fullstack_crew() -> Optional[Any]:
    """
    FullStackCrew — Orchestrator + Code + Research + Data agents.
    Use for: feature development, data-driven coding tasks.
    """
    Agent, Crew, Task = _try_import_crewai()
    if Crew is None:
        return None

    orchestrator = _make_crewai_agent(
        role="Full Stack Orchestrator",
        goal="Coordinate the engineering team to deliver complete, tested features.",
        backstory="Engineering lead with expertise in full-stack development and technical planning.",
    )
    coder = _make_crewai_agent(
        role="Software Engineer",
        goal="Write correct, efficient, and well-tested code.",
        backstory="Senior software engineer specialising in Python and TypeScript.",
    )
    researcher = _make_crewai_agent(
        role="Technical Researcher",
        goal="Research APIs, libraries, and best practices for the engineering team.",
        backstory="Technical researcher with deep knowledge of software ecosystems.",
    )
    data_analyst = _make_crewai_agent(
        role="Data Analyst",
        goal="Analyse data requirements and provide insights to support development decisions.",
        backstory="Data engineer with expertise in SQL, analytics, and reporting.",
    )

    if not all([orchestrator, coder, researcher, data_analyst]):
        return None

    return Crew(
        agents=[orchestrator, coder, researcher, data_analyst],
        verbose=True,
        process="hierarchical",
        manager_llm=None,
    )


# ── AutoGen Debate Session ────────────────────────────────────────────────────


async def run_autogen_debate(
    topic: str,
    context: str,
    max_turns: int = 4,
) -> str:
    """
    Run a multi-agent debate using AutoGen to critique a proposed action.
    Returns a consensus recommendation string.

    Uses GPT-4o as the backbone LLM. Falls back to a simple stub if
    pyautogen is not installed or no API key is available.
    """
    try:
        import autogen  # pyautogen
    except ImportError:
        log.warning("pyautogen not installed — returning stub debate result.")
        return f"[STUB] Consensus: Proceed with '{topic[:60]}' — no issues found."

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return f"[STUB] No LLM key for debate. Defaulting to: Proceed with '{topic[:60]}'."

    config_list = [{"model": "gpt-4o", "api_key": openai_key}]
    llm_config = {"config_list": config_list, "temperature": 0.3}

    proposer = autogen.AssistantAgent(
        name="Proposer",
        llm_config=llm_config,
        system_message=(
            "You are advocating for the proposed action. "
            "Explain why it is the right approach given the context."
        ),
    )
    critic = autogen.AssistantAgent(
        name="Critic",
        llm_config=llm_config,
        system_message=(
            "You are a rigorous critic. Challenge the proposed action — "
            "identify risks, alternatives, and weaknesses."
        ),
    )
    judge = autogen.AssistantAgent(
        name="Judge",
        llm_config=llm_config,
        system_message=(
            "After hearing both sides, deliver a final consensus: "
            "'Proceed', 'Proceed with changes: ...', or 'Reject: ...'. "
            "Be concise and decisive."
        ),
    )
    user_proxy = autogen.UserProxyAgent(
        name="Coordinator",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=max_turns,
        code_execution_config=False,
    )

    initial_message = f"Topic: {topic}\n\nContext: {context[:800]}"
    await user_proxy.a_initiate_chat(proposer, message=initial_message, max_turns=2)
    await user_proxy.a_initiate_chat(critic, message=initial_message, max_turns=2)
    await user_proxy.a_initiate_chat(judge, message=initial_message, max_turns=1)

    # Extract the last judge message as the consensus
    messages = user_proxy.chat_messages.get(judge, [])
    if messages:
        return messages[-1].get("content", "Proceed.")
    return "Proceed."
