"""
Digital Force Agent State
Shared TypedDict state flowing through the LangGraph agent graph.
"""

from typing import TypedDict, Annotated, Optional, Any
from langgraph.graph.message import add_messages
from datetime import datetime


class AgentState(TypedDict):
    # ── Identity ────────────────────────────────────────
    goal_id: str
    goal_description: str
    platforms: list[str]
    deadline: Optional[str]
    success_metrics: dict
    constraints: dict
    asset_ids: list[str]          # Media library asset IDs provided

    # ── Conversation / Messages ──────────────────────────
    messages: Annotated[list, add_messages]

    # ── Research outputs ─────────────────────────────────
    research_findings: dict       # trends, competitor intel, audience data

    # ── Strategy / Plan ─────────────────────────────────
    campaign_plan: dict           # Full structured plan from Strategist
    tasks: list[dict]             # List of AgentTask dicts to create

    # ── Execution state ──────────────────────────────────
    current_task_id: Optional[str]
    completed_task_ids: list[str]
    failed_task_ids: list[str]

    # ── Monitor ──────────────────────────────────────────
    kpi_snapshot: dict            # Latest analytics vs targets
    needs_replan: bool

    # ── Human approval ───────────────────────────────────
    approval_status: str          # pending | approved | rejected | modified
    human_feedback: Optional[str]

    # ── Skills ───────────────────────────────────────────
    new_skills_created: list[str]  # Names of skills forged this run

    # ── Control flow ─────────────────────────────────────
    next_agent: Optional[str]     # Which agent to route to next
    error: Optional[str]
    iteration_count: int
