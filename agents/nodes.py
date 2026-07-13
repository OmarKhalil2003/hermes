import contextlib
import uuid
from typing import Any, Literal, cast

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from agents.state import AgentState
from backend.core.config import settings
from backend.core.database import async_session_factory
from backend.services.search import HybridSearchService


class RouteResponse(BaseModel):
    """Routing schema output for the Supervisor agent."""

    next: Literal["Retriever", "Research", "Reviewer", "Report", "FINISH"] = Field(
        description="The next node to transition to, or FINISH if complete."
    )


class ReviewResponse(BaseModel):
    """Evaluation output schema for the Reviewer agent."""

    approved: bool = Field(
        description=(
            "True if the draft is fully accurate, coherent and complete. "
            "False if revisions are needed."
        )
    )
    critique: str = Field(
        description="Constructive critique listing missing details or corrections."
    )


def get_llm() -> ChatOpenAI:
    """Helper to instantiate the ChatOpenAI client with environment parameters."""
    api_key = settings.models.openai_api_key or "dummy-key"
    base_url = settings.models.openai_api_base
    return ChatOpenAI(
        model=settings.models.llm_model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0.0,
    )


async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """Supervisor agent that routes query tasks to specific workspace nodes."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(RouteResponse)

    # Compile routing system prompt instructions
    system_prompt = (
        "You are the Research Supervisor directing a multi-agent system.\n"
        "Your team consists of the following agents:\n"
        "- Retriever: Fetches document context chunks from the database.\n"
        "- Research: Drafts detailed answers using retrieved context.\n"
        "- Reviewer: Checks research draft accuracy/completeness against context.\n"
        "- Report: Compiles approved draft into a polished markdown report.\n\n"
        "Routing guidelines:\n"
        "1. If no document context is retrieved yet, route to Retriever.\n"
        "2. If context is available but no draft is compiled, route to Research.\n"
        "3. If a draft is compiled but not reviewed, route to Reviewer.\n"
        "4. If Reviewer approved, route to Report.\n"
        "5. If Reviewer rejected and loop_count < 3, route back to Research.\n"
        "6. If loop_count >= 3 or report is compiled, route to FINISH.\n"
    )

    messages = [SystemMessage(content=system_prompt), *list(state["messages"])]
    try:
        route = cast(RouteResponse, structured_llm.invoke(messages))
        next_step = route.next
    except Exception:
        # Fallback routing logic if LLM parsing errors occur
        if not state.get("retrieved_context"):
            next_step = "Retriever"
        elif not state.get("research_draft"):
            next_step = "Research"
        elif not state.get("review_approved") and state.get("loop_count", 0) < 3:
            next_step = "Reviewer"
        else:
            next_step = "Report"

    return {"next": next_step}


async def retriever_node(state: AgentState) -> dict[str, Any]:
    """Retriever agent that queries hybrid vector database collections."""
    # Find user query from message history
    user_query = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            user_query = str(msg.content)
            break

    if not user_query:
        return {
            "messages": [AIMessage(content="No query provided. Skipping retrieval.")]
        }

    user_uuid = None
    if state.get("user_id"):
        with contextlib.suppress(ValueError):
            user_uuid = uuid.UUID(state["user_id"])

    if not user_uuid:
        return {"messages": [AIMessage(content="User ID missing. Skipping retrieval.")]}

    limit = state.get("limit") or 5
    retrieved_chunks = []

    async with async_session_factory() as db:
        search_service = HybridSearchService(db)
        try:
            results = await search_service.search(
                query=user_query,
                user_id=user_uuid,
                limit=limit,
            )
            for res in results:
                retrieved_chunks.append(res["content"])
        except Exception as e:
            retrieved_chunks.append(f"Retrieval error occurred: {e}")

    context_summary = f"Retrieved {len(retrieved_chunks)} relevant source passages."
    return {
        "retrieved_context": retrieved_chunks,
        "messages": [AIMessage(content=context_summary)],
    }


async def research_node(state: AgentState) -> dict[str, Any]:
    """Research agent that synthesizes context to draft structured analyses."""
    llm = get_llm()

    context_str = "\n---\n".join(state.get("retrieved_context", []))
    system_prompt = (
        "You are the Research Specialist agent.\n"
        "Draft a detailed, comprehensive synthesis answering the user's query.\n"
        "Rely strictly on the provided context. If it lacks info, "
        "synthesize the facts present without making assumptions.\n\n"
        f"Retrieved Context:\n{context_str}\n"
    )

    if state.get("review_critique"):
        system_prompt += (
            f"\nPrevious Review Critique:\n{state['review_critique']}\n"
            "Please address all of the above points in this revised draft."
        )

    messages = [SystemMessage(content=system_prompt), *list(state["messages"])]
    response = await llm.ainvoke(messages)
    draft = str(response.content)

    return {
        "research_draft": draft,
        "messages": [AIMessage(content="Research draft compiled successfully.")],
    }


async def reviewer_node(state: AgentState) -> dict[str, Any]:
    """Reviewer agent that evaluates research draft quality and coherence."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ReviewResponse)

    context_str = "\n---\n".join(state.get("retrieved_context", []))
    system_prompt = (
        "You are the Peer Reviewer agent.\n"
        "Compare the compiled research draft against the retrieved source context.\n"
        "Validate if the draft is accurate, coherent, and has no hallucinations.\n\n"
        f"Source Context:\n{context_str}\n\n"
        f"Research Draft:\n{state.get('research_draft', '')}\n"
    )

    messages = [SystemMessage(content=system_prompt), *list(state["messages"])]

    try:
        review = cast(ReviewResponse, await structured_llm.ainvoke(messages))
        approved = review.approved
        critique = review.critique
    except Exception as e:
        # Fallback review decision on parsing exceptions
        approved = True
        critique = f"Review parsed with exception fallback: {e}"

    loop_count = state.get("loop_count", 0)
    if not approved:
        loop_count += 1

    return {
        "review_approved": approved,
        "review_critique": critique,
        "loop_count": loop_count,
        "messages": [
            AIMessage(
                content=(
                    f"Review evaluation: "
                    f"{'Approved' if approved else 'Changes requested'}.\n"
                    f"Critique: {critique}"
                )
            )
        ],
    }


async def report_node(state: AgentState) -> dict[str, Any]:
    """Report agent that compiles research draft into professional markdown."""
    llm = get_llm()

    system_prompt = (
        "You are the Report Compiler agent.\n"
        "Format the research draft into a beautiful, publication-ready report.\n"
        "Use markdown (headings, bullets) to make it professional.\n"
        "Do not alter the facts, only format the text structure.\n\n"
        f"Approved Research Draft:\n{state.get('research_draft', '')}\n"
    )

    messages = [SystemMessage(content=system_prompt), *list(state["messages"])]
    response = await llm.ainvoke(messages)
    report_content = str(response.content)

    return {
        "report": report_content,
        "messages": [AIMessage(content=report_content)],
    }
