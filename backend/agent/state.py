"""
Digital Force Agent State
Shared TypedDict state flowing through the LangGraph agent graph.
"""

import operator
from typing import TypedDict, Annotated, Optional, Any
from langgraph.graph.message import add_messages
from datetime import datetime

def reduce_list(left: list, right: list) -> list:
    """Safely merge lists for map-reduce parallel swarms."""
    if not left: left = []
    if not right: right = []
    return left + right


class AgentState(TypedDict):
    # ── Identity ────────────────────────────────────────
    goal_id: str
    goal_description: str
    created_by: str           # User ID — so agents can push to chat
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
    completed_task_ids: Annotated[list[str], reduce_list]
    failed_task_ids: Annotated[list[str], reduce_list]
    content_swarm_results: Annotated[list[dict], reduce_list] # Stores generated content from parallel nodes

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
    target_agent: Optional[str]   # Where the manager wanted to go before Auditor intercepted
    risk_score: Optional[int]     # 0-100 risk grading
    error: Optional[str]
    iteration_count: int
