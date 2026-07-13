from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Global state schema for the multi-agent LangGraph workflow."""

    # History of base messages exchanged
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Name of the next target node to route tasks to
    next: str

    # Context chunks retrieved from search pipelines
    retrieved_context: list[str]

    # Draft compiled by the Research agent
    research_draft: str

    # Review feedback from the Reviewer agent
    review_critique: str

    # Flag indicating whether the Reviewer approved the draft
    review_approved: bool

    # Final compiled markdown output
    report: str

    # Loop count tracking iterations between Research and Reviewer
    loop_count: int

    # Owner ID targeting document scoping
    user_id: str

    # Retrieval parameter limit
    limit: int
