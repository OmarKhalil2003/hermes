from typing import Any

from langgraph.graph import END, StateGraph

from agents.nodes import (
    report_node,
    research_node,
    retriever_node,
    reviewer_node,
    supervisor_node,
)
from agents.state import AgentState
from backend.core.checkpointer import SQLAlchemyCheckpointSaver
from backend.core.database import async_session_factory

# 1. Initialize State Graph
workflow = StateGraph(AgentState)

# 2. Add Nodes
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Retriever", retriever_node)
workflow.add_node("Research", research_node)
workflow.add_node("Reviewer", reviewer_node)
workflow.add_node("Report", report_node)

# 3. Add Edges pointing back to Supervisor
workflow.add_edge("Retriever", "Supervisor")
workflow.add_edge("Research", "Supervisor")
workflow.add_edge("Reviewer", "Supervisor")
workflow.add_edge("Report", "Supervisor")

# 4. Set entry point
workflow.set_entry_point("Supervisor")


# 5. Routing conditional transition function
def route_next(state: AgentState) -> str:
    """Evaluates the next target node computed by the Supervisor."""
    next_node = state.get("next") or "FINISH"
    if next_node == "FINISH":
        return END
    return next_node


# 6. Add conditional edges from Supervisor
workflow.add_conditional_edges(
    "Supervisor",
    route_next,
    {
        "Retriever": "Retriever",
        "Research": "Research",
        "Reviewer": "Reviewer",
        "Report": "Report",
        END: END,
    },
)


def get_agent_graph() -> Any:
    """Compiles the LangGraph state workflow with the PostgreSQL checkpointer."""
    checkpointer = SQLAlchemyCheckpointSaver(async_session_factory)
    return workflow.compile(checkpointer=checkpointer)
