import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agents.graph import get_agent_graph
from backend.api.deps import get_active_user
from backend.core.logging import logger
from backend.models.auth import User

router = APIRouter()


class AgentResearchRequest(BaseModel):
    """Payload schema targeting multi-agent supervisor orchestrator queries."""

    query: str = Field(description="The research query or intent.")
    thread_id: str | None = Field(
        default=None, description="Optional thread ID to recover execution state."
    )


@router.post("/research", status_code=status.HTTP_200_OK)
async def run_agent_research(
    request: AgentResearchRequest,
    current_user: User = Depends(get_active_user),
) -> Any:
    """Streams multi-agent orchestrator transitions and report tokens."""
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    async def event_generator() -> AsyncGenerator[str]:
        graph = get_agent_graph()

        # Emit initial session metadata
        yield f"event: connect\ndata: {json.dumps({'thread_id': thread_id})}\n\n"

        try:
            async for event in graph.astream_events(
                {
                    "messages": [HumanMessage(content=request.query)],
                    "user_id": str(current_user.id),
                    "limit": 5,
                    "loop_count": 0,
                },
                config=config,
                version="v2",
            ):
                evt_type = event.get("event")
                meta = event.get("metadata", {})
                node_name = meta.get("langgraph_node")

                # Detect chain transitions matching known agent nodes
                if evt_type == "on_chain_start" and node_name in [
                    "Retriever",
                    "Research",
                    "Reviewer",
                    "Report",
                    "Supervisor",
                ]:
                    payload = json.dumps({"node": node_name})
                    yield f"event: node_start\ndata: {payload}\n\n"
                elif evt_type == "on_chain_end" and node_name in [
                    "Retriever",
                    "Research",
                    "Reviewer",
                    "Report",
                    "Supervisor",
                ]:
                    payload = json.dumps({"node": node_name})
                    yield f"event: node_end\ndata: {payload}\n\n"

                # Detect token chunks emitted during markdown compilation
                elif evt_type == "on_chat_model_stream" and node_name == "Report":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        payload = json.dumps({"token": chunk.content})
                        yield f"event: token\ndata: {payload}\n\n"

            # Emit final termination response
            yield "event: complete\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Agent state execution failed: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
