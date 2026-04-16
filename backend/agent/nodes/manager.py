"""
Digital Force — Supervisor Node (Omniscient ReAct Hub)
"""
import logging
from agent.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage

logger = logging.getLogger(__name__)

async def manager_node(state: AgentState) -> dict:
    from agent.tools.system_tools import get_agent_tools
    from agent.llm import get_tool_llm
    
    logger.info(f"[Supervisor] Waking up Omni-Hub for goal: {state['goal_id'][:8]}...")
    
    tools = get_agent_tools(state)
    llm = get_tool_llm(temperature=0.2).bind_tools(tools)
    
    # ── Map-Reduce Results Stitching ──
    tasks = state.get("tasks", [])
    swarm_res = state.get("content_swarm_results", [])
    state_updates = {}
    if swarm_res:
        new_tasks = []
        has_new = False
        for t in tasks:
            t_copy = dict(t)
            for res in swarm_res:
                if res.get("task_id") == t.get("id") and "result" not in t_copy:
                    t_copy["result"] = res["result"]
                    t_copy["task_type"] = "post_content"
                    has_new = True
            new_tasks.append(t_copy)
        if has_new:
            state_updates["tasks"] = new_tasks

    messages = list(state.get("messages", []))
    if not messages:
        messages.append(HumanMessage(content="Trigger autonomous cycle."))
        
    system_prompt = """You are the Omniscient Manager of the Digital Force AI Agency.
You have native ability to write code, read the database, query memory, or delegate to specific sub-agents.
Always use `push_to_chat` BEFORE delegating to a sub-agent or writing heavy code so the human knows what you are doing natively in the chat UI.

Sub-Agent Routing Guide (Use route_to_agent ONLY when these specialized pipelines are absolutely required):
- orchestrator: Extracts intent and platforms from human goals.
- researcher: Scrapes web data.
- strategist: Builds campaigns.
- content_director: Writes social media copy.
- distribution_manager: Assigns proxy environments.
- publisher: Executes the final post.
- skillforge: Re-writes existing system tool schemas specifically.
- monitor: Pulls analytics.

If the user asks you to do something simple or something unrelated to standard social media (like parsing a CSV, fetching web text, scanning the web, API integrations), DO NOT use regular agents! Instead, use `execute_python` and write a robust python script to do it directly in the local sandbox!

If the user gives you a password, auth token, or credential, immediately use `update_truth_bucket` to save it and tell them it's saved!

If you are done processing the user's intent or you need to reply directly to their chat message, push a message via `push_to_chat` then use `halt_execution`."""

    messages.insert(0, SystemMessage(content=system_prompt))
    
    max_loops = 5
    loops = 0
    target_next_agent = "__end__"
    
    while loops < max_loops:
        loops += 1
        response = await llm.ainvoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            # Reached a conclusion without halting explicitly
            break
            
        exit_loop = False
        
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            
            # Find tool
            tool_func = next((t for t in tools if t.name == tool_name), None)
            if tool_func:
                try:
                    res = await tool_func.ainvoke(tool_args)
                    res_str = str(res)
                    # Check if it was a routing command
                    if "ROUTING_REQUESTED:" in res_str:
                        target_next_agent = res_str.split(":")[1].strip()
                        exit_loop = True
                        break
                    else:
                        messages.append(ToolMessage(content=res_str, tool_call_id=tc["id"]))
                except Exception as e:
                    messages.append(ToolMessage(content=f"Error: {e}", tool_call_id=tc["id"]))
            else:
                messages.append(ToolMessage(content="Tool not found.", tool_call_id=tc["id"]))
                
        if exit_loop:
            break
            
    # Clean up message list (remove SystemMessages before returning to exact state requirements)
    final_messages = [m for m in messages if getattr(m, "type", "") != "system"]
    state_updates["messages"] = final_messages
    
    # Intercept high-risk execution nodes for Auditing
    if target_next_agent in ["publisher", "skillforge"]:
        state_updates.update({
            "next_agent": "auditor",
            "target_agent": target_next_agent
        })
        return state_updates

    state_updates["next_agent"] = target_next_agent
    logger.info(f"[Supervisor] Routing done. Handoff to: {target_next_agent}")
    return state_updates
