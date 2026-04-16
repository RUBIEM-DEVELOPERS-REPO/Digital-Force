"""
Digital Force — LangGraph Agent Graph (Neural Supervisor)
Hub-and-spoke architecture where Supervisor evaluates state and routes dynamically.
"""

import logging
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.executive import executive_node
from agent.nodes.manager import manager_node
from agent.nodes.orchestrator import orchestrator_node
from agent.nodes.researcher import researcher_node
from agent.nodes.strategist import strategist_node
from agent.nodes.content_director import content_director_node
from agent.nodes.publisher import publisher_node
from agent.nodes.skillforge import skillforge_node
from agent.nodes.monitor import monitor_node
from agent.nodes.auditor import auditor_node
from agent.nodes.reflector import reflector_node

logger = logging.getLogger(__name__)

def manager_router(state: AgentState):
    """Read the routing decision made by the manager_node or executive_node."""
    nxt = state.get("next_agent")
    
    if nxt == "content_director":
        tasks = state.get("tasks", [])
        completed = state.get("completed_task_ids", [])
        failed = state.get("failed_task_ids", [])
        uncompleted = [t for t in tasks if t.get("task_type") == "generate_content" and t.get("id") not in completed and t.get("id") not in failed]
        
        from langgraph.constants import Send
        if uncompleted:
            return [Send("content_director", {**state, "current_task_id": t["id"]}) for t in uncompleted]
        return "publisher"
        
    if not nxt or nxt == "__end__":
        return END
    return nxt

def build_neural_graph() -> StateGraph:
    """
    Unified Hub-and-Spoke topology starting with the Executive.
    Executive evaluates user input -> Manager delegates tasks -> Workers execute.
    After any agent acts, execution returns to the Manager.
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("executive", executive_node)
    graph.add_node("manager", manager_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("content_director", content_director_node)
    graph.add_node("publisher", publisher_node)
    graph.add_node("skillforge", skillforge_node)
    graph.add_node("monitor", monitor_node)
    graph.add_node("auditor", auditor_node)
    graph.add_node("reflector", reflector_node)

    # Set Entry Point
    graph.set_entry_point("executive")

    # Executive conditional routing
    graph.add_conditional_edges("executive", manager_router, {
        "manager": "manager",
        END: END
    })

    # Manager conditional routing
    graph.add_conditional_edges("manager", manager_router, {
        "orchestrator": "orchestrator",
        "researcher": "researcher",
        "strategist": "strategist",
        "content_director": "content_director",
        "publisher": "publisher",
        "skillforge": "skillforge",
        "monitor": "monitor",
        "auditor": "auditor",
        "reflector": "reflector",
        END: END
    })

    # All action nodes return their output to the Manager to decide what to do next
    graph.add_edge("orchestrator", "manager")
    graph.add_edge("researcher", "manager")
    graph.add_edge("strategist", "manager")
    graph.add_edge("content_director", "manager")
    graph.add_edge("publisher", "manager")
    graph.add_edge("skillforge", "manager")
    graph.add_edge("monitor", "manager")
    graph.add_edge("reflector", "manager")
    
    # Auditor conditional routing: if it passes, it goes to target_agent. If it halts, it ends.
    graph.add_conditional_edges("auditor", manager_router, {
        "publisher": "publisher",
        "skillforge": "skillforge",
        "manager": "manager",
        END: END
    })

    return graph.compile()

# To maintain API backwards compatibility for api/goals.py
# We export the same dynamic neural graph for both phases.
# The manager_node inspects `state["approval_status"]` to route correctly.
planning_graph = build_neural_graph()
execution_graph = build_neural_graph()

