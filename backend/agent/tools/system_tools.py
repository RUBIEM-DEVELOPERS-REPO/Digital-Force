"""
Digital Force — Native System Tools
First-class tools for the Omni-Hub ReAct loop.
"""

from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

def get_agent_tools(state: dict):
    
    @tool
    async def execute_python(code: str) -> str:
        """Executes arbitrary Python code in a local subprocess and returns stdout/stderr. Use exactly when you need to parse data, hit external APIs, or scrape."""
        try:
            from agent.tools.sandbox import run_in_e2b
            res = await run_in_e2b(code)
            if res.get("success"):
                return f"Execution Succeeded:\n{res.get('output')}"
            return f"Execution Failed:\n{res.get('error')}\n{res.get('output')}"
        except Exception as e:
            return f"Sandbox Error: {e}"

    @tool
    async def read_system_context() -> str:
        """Reads live counts of goals, accounts, and tasks from the SQL database to give you system awareness."""
        try:
            from database import async_session, Goal, PlatformConnection, AgentTask
            from sqlalchemy import select, func
            async with async_session() as db:
                g = await db.scalar(select(func.count(Goal.id)))
                p = await db.scalar(select(func.count(PlatformConnection.id)))
                t = await db.scalar(select(func.count(AgentTask.id)))
                return f"Database Context: {g} total goals. {p} platform connections. {t} executed tasks globally."
        except Exception as e:
            return f"Database Error: {e}"

    @tool
    async def query_knowledge(query: str) -> str:
        """Queries the Qdrant Vector database for historic memory, brand guidelines, or training data."""
        try:
            from rag.retriever import retrieve
            docs = await retrieve(query)
            if not docs:
                return "No memories found."
            return "\n\n".join([f"[{d['score']:.2f}] {d['text']}" for d in docs])
        except Exception as e:
            return f"RAG Error: {e}"

    @tool
    async def push_to_chat(message: str) -> str:
        """Pushes a message instantly to the user's UI. VERY IMPORTANT: Use this before running heavy tools to tell the user what you are doing (e.g. 'I am reviewing your database now...')."""
        try:
            from agent.chat_push import chat_push
            user_id = state.get("created_by", "")
            goal_id = state.get("goal_id", "")
            await chat_push(user_id=user_id, content=message, agent_name="digital force - omni", goal_id=goal_id)
            return "Message pushed to user UI."
        except Exception as e:
            return f"Push Error: {e}"

    @tool
    def route_to_agent(target_agent: str) -> str:
        """Routes execution to a specialized worker sub-agent. Valid agents: orchestrator, researcher, strategist, content_director, distribution_manager, publisher, monitor, reflector. DO NOT use if you can solve the task quickly with execute_python."""
        return f"ROUTING_REQUESTED:{target_agent}"
        
    @tool
    def halt_execution() -> str:
        """Stops the loop and halts execution, waiting for the human user to reply."""
        return "ROUTING_REQUESTED:__end__"

    @tool
    async def update_truth_bucket(account_name_match: str, text_to_append: str) -> str:
        """Safely appends authentication credentials, passwords, or recovery codes to a managed account's truth bucket in the SQL Database. Use this whenever the user gives you a password!"""
        try:
            from database import async_session, PlatformConnection
            from sqlalchemy import select, or_
            async with async_session() as session:
                match_str = f"%{account_name_match}%"
                stmt = select(PlatformConnection).where(
                    or_(
                        PlatformConnection.account_label.ilike(match_str),
                        PlatformConnection.display_name.ilike(match_str)
                    )
                )
                conn = (await session.execute(stmt)).scalars().first()
                if conn:
                    current = conn.auth_data or ""
                    conn.auth_data = f"{current}\n[Agent Auto-Saved]: {text_to_append}".strip()
                    await session.commit()
                    return f"Successfully updated Truth Bucket for {conn.account_label}"
                return "Failed: No account found matching that name."
        except Exception as e:
            return f"Database Error: {e}"

    return [execute_python, read_system_context, query_knowledge, push_to_chat, route_to_agent, halt_execution, update_truth_bucket]
