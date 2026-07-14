import contextlib
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import async_sessionmaker

from agents.graph import get_agent_graph
from agents.nodes import ReviewResponse, RouteResponse
from backend.core.checkpointer import SQLAlchemyCheckpointSaver


@pytest.mark.asyncio
async def test_sqlalchemy_checkpointer(db_session: Any) -> None:
    """Verifies that checkpointer saves and loads state."""
    async_session_maker = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    saver = SQLAlchemyCheckpointSaver(async_session_maker)

    config: RunnableConfig = {
        "configurable": {
            "thread_id": "thread-test-1",
            "checkpoint_ns": "ns-1",
            "checkpoint_id": "cp-1",
        }
    }

    checkpoint = {
        "id": "cp-1",
        "v": 1,
        "ts": "2026-07-13T12:00:00Z",
        "channel_values": {"messages": [HumanMessage(content="Hello World")]},
        "channel_versions": {"messages": "v1"},
        "versions_seen": {},
        "pending_sends": [],
    }

    metadata = {"source": "input"}
    new_versions = {"messages": "v1"}

    # Save state
    await saver.aput(
        config,
        cast(Any, checkpoint),
        cast(Any, metadata),
        cast(Any, new_versions),
    )

    # Read state back
    loaded_tuple = await saver.aget_tuple(config)
    assert loaded_tuple is not None
    assert loaded_tuple.checkpoint["id"] == "cp-1"
    assert (
        loaded_tuple.checkpoint["channel_values"]["messages"][0].content
        == "Hello World"
    )
    assert loaded_tuple.metadata["source"] == "input"

    # List states
    items = []
    async for item in saver.alist(config):
        items.append(item)
    assert len(items) == 1
    assert items[0].config["configurable"]["checkpoint_id"] == "cp-1"

    # Delete thread
    await saver.adelete_thread("thread-test-1")
    loaded_tuple_deleted = await saver.aget_tuple(config)
    assert loaded_tuple_deleted is None


@pytest.mark.asyncio
@patch("agents.nodes.ChatOpenAI")
@patch("agents.nodes.HybridSearchService")
async def test_multi_agent_graph_workflow(
    mock_search_class: Any, mock_chat_openai_class: Any, db_session: Any  # noqa: ARG001
) -> None:
    """Verifies sequential LangGraph execution and state transitions."""
    # 1. Mock Hybrid Search Service
    mock_search_service = MagicMock()

    async def mock_search(*_args: Any, **_kwargs: Any) -> Any:
        return [{"content": "Document database chunk content."}]

    mock_search_service.search = mock_search
    mock_search_class.return_value = mock_search_service

    # 2. Mock ChatOpenAI and Structured Outputs
    mock_llm_instance = MagicMock()

    supervisor_calls = 0

    def supervisor_structured_output_mock(
        _messages: Any, *_args: Any, **_kwargs: Any
    ) -> RouteResponse:
        nonlocal supervisor_calls
        supervisor_calls += 1
        if supervisor_calls == 1:
            return RouteResponse(next="Retriever")
        if supervisor_calls == 2:
            return RouteResponse(next="Research")
        if supervisor_calls == 3:
            return RouteResponse(next="Reviewer")
        if supervisor_calls == 4:
            return RouteResponse(next="Research")
        if supervisor_calls == 5:
            return RouteResponse(next="Reviewer")
        if supervisor_calls == 6:
            return RouteResponse(next="Report")
        return RouteResponse(next="FINISH")

    reviewer_calls = 0

    def reviewer_structured_output_mock(
        _messages: Any, *_args: Any, **_kwargs: Any
    ) -> ReviewResponse:
        nonlocal reviewer_calls
        reviewer_calls += 1
        # Loop once for test coverage of critique pathway
        if reviewer_calls == 1:
            return ReviewResponse(approved=False, critique="Missing details.")
        return ReviewResponse(approved=True, critique="Excellent.")

    def with_structured_output_mock(schema: Any, *_args: Any, **_kwargs: Any) -> Any:
        mock_structured = MagicMock()
        if schema == RouteResponse:
            mock_structured.invoke = supervisor_structured_output_mock
        elif schema == ReviewResponse:
            mock_structured.ainvoke = AsyncMock(
                side_effect=reviewer_structured_output_mock
            )
        return mock_structured

    mock_llm_instance.with_structured_output = with_structured_output_mock

    async def ainvoke_mock(messages: Any, *_args: Any, **_kwargs: Any) -> AIMessage:
        prompt_text = str(messages[0].content)
        if "Research Specialist" in prompt_text:
            return AIMessage(content="Generated research draft answer.")
        if "Report Compiler" in prompt_text:
            return AIMessage(content="Finalized formatted report.")
        return AIMessage(content="Generic mock message.")

    mock_llm_instance.ainvoke = ainvoke_mock
    mock_chat_openai_class.return_value = mock_llm_instance

    # 3. Compile Graph with Test DB session maker
    import os

    from sqlalchemy.ext.asyncio import create_async_engine

    from backend.models import Base

    db_file = os.path.join(os.getcwd(), "test_workflow.db")
    if os.path.exists(db_file):
        with contextlib.suppress(OSError):
            os.remove(db_file)

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session_maker = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

        with (
            patch("agents.graph.async_session_factory", async_session_maker),
            patch("agents.nodes.async_session_factory", async_session_maker),
        ):

            graph = get_agent_graph()
            config = {"configurable": {"thread_id": "workflow-test-1"}}

            result = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content="Query about testing.")],
                    "user_id": "00000000-0000-0000-0000-000000000000",
                    "limit": 5,
                    "loop_count": 0,
                },
                config=config,
            )

        assert result["next"] == "FINISH"
        assert len(result["retrieved_context"]) == 1
        assert "Document database chunk content." in result["retrieved_context"][0]
        assert result["research_draft"] == "Generated research draft answer."
        assert result["review_approved"] is True
        assert result["report"] == "Finalized formatted report."
        assert result["loop_count"] == 1  # 1 iteration due to rejection first loop
    finally:
        await engine.dispose()
        if os.path.exists(db_file):
            with contextlib.suppress(OSError):
                os.remove(db_file)


@pytest.mark.asyncio
@patch("backend.api.v1.endpoints.agent.get_agent_graph")
async def test_agent_research_api_endpoint(
    mock_get_graph: Any, client: AsyncClient
) -> None:
    """Verifies that endpoint streams SSE events."""
    # 2. Mock state stream events sequence
    mock_graph = MagicMock()

    async def mock_astream_events(*_args: Any, **_kwargs: Any) -> Any:
        # Yield mock agent node start/end events and token output chunk
        yield {
            "event": "on_chain_start",
            "name": "Retriever",
            "metadata": {"langgraph_node": "Retriever"},
        }
        yield {
            "event": "on_chain_end",
            "name": "Retriever",
            "metadata": {"langgraph_node": "Retriever"},
        }
        yield {
            "event": "on_chain_start",
            "name": "Report",
            "metadata": {"langgraph_node": "Report"},
        }

        # Mock AIMessageChunk for chat model stream
        class MockChunk:
            content = "Final report token chunk."

        yield {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "metadata": {"langgraph_node": "Report"},
            "data": {"chunk": MockChunk()},
        }
        yield {
            "event": "on_chain_end",
            "name": "Report",
            "metadata": {"langgraph_node": "Report"},
        }

    mock_graph.astream_events = mock_astream_events
    mock_get_graph.return_value = mock_graph

    # 3. Invoke endpoint and parse streamed events (auth is bypassed in backend)
    response = await client.post(
        "/api/v1/agents/research",
        json={"query": "Test query string.", "thread_id": "thread-sse-1"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    body_bytes = await response.aread()
    body_str = body_bytes.decode("utf-8")

    assert "event: connect" in body_str
    assert "event: node_start" in body_str
    assert "Retriever" in body_str
    assert "event: token" in body_str
    assert "Final report token chunk." in body_str
    assert "event: complete" in body_str
