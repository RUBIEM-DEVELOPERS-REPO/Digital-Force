"""
Digital Force — LangGraph Agent Graph
Wires all agent nodes into a stateful, cyclical multi-agent workflow.
"""

import logging
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.orchestrator import orchestrator_node
from agent.nodes.researcher import researcher_node
from agent.nodes.strategist import strategist_node
from agent.nodes.content_director import content_director_node
from agent.nodes.publisher import publisher_node
from agent.nodes.skillforge import skillforge_node
from agent.nodes.monitor import monitor_node

logger = logging.getLogger(__name__)


def route_after_orchestrator(state: AgentState) -> str:
    return state.get("next_agent", "researcher")


def route_after_researcher(state: AgentState) -> str:
    return state.get("next_agent", "strategist")


def route_after_strategist(state: AgentState) -> str:
    """After planning, always go to approval gateway (handled externally — pause here)."""
    return END  # Graph pauses; execution resumes after human approval


def route_after_content(state: AgentState) -> str:
    return state.get("next_agent", "publisher")


def route_after_publisher(state: AgentState) -> str:
    next_a = state.get("next_agent", "monitor")
    if next_a == "skillforge":
        return "skillforge"
    return "monitor"


def route_after_skillforge(state: AgentState) -> str:
    return state.get("next_agent", "monitor")


def route_after_monitor(state: AgentState) -> str:
    if state.get("needs_replan") and state.get("replan_count", 0) < 3:
        return "strategist"
    return END


def build_planning_graph() -> StateGraph:
    """
    Phase 1 graph: GOAL → ORCHESTRATOR → RESEARCHER → STRATEGIST → [PAUSE for approval]
    """
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("strategist", strategist_node)

    graph.set_entry_point("orchestrator")
    graph.add_conditional_edges("orchestrator", route_after_orchestrator, {
        "researcher": "researcher",
        "strategist": "strategist",
    })
    graph.add_conditional_edges("researcher", route_after_researcher, {
        "strategist": "strategist",
    })
    graph.add_edge("strategist", END)

    return graph.compile()


def build_execution_graph() -> StateGraph:
    """
    Phase 2 graph: [APPROVED] → CONTENT → PUBLISHER → SKILLFORGE → MONITOR → [loop or END]
    """
    graph = StateGraph(AgentState)

    graph.add_node("content_director", content_director_node)
    graph.add_node("publisher", publisher_node)
    graph.add_node("skillforge", skillforge_node)
    graph.add_node("monitor", monitor_node)
    graph.add_node("strategist", strategist_node)  # For re-planning

    graph.set_entry_point("content_director")
    graph.add_conditional_edges("content_director", route_after_content, {
        "publisher": "publisher",
        "monitor": "monitor",
    })
    graph.add_conditional_edges("publisher", route_after_publisher, {
        "skillforge": "skillforge",
        "monitor": "monitor",
    })
    graph.add_conditional_edges("skillforge", route_after_skillforge, {
        "monitor": "monitor",
        "publisher": "publisher",
        END: END,
    })
    graph.add_conditional_edges("monitor", route_after_monitor, {
        "strategist": "strategist",
        END: END,
    })
    graph.add_edge("strategist", "content_director")  # Re-plan → re-execute

    return graph.compile()


# Compiled graphs (singletons)
planning_graph = build_planning_graph()
execution_graph = build_execution_graph()
