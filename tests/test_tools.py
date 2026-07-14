import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.models import Base
from tools.chart_generator import generate_chart
from tools.python_executor import execute_python_code
from tools.report_generator import generate_pdf_report, generate_pptx_report
from tools.sql_compiler import compile_and_execute_sql, is_safe_sql


def test_python_executor_success() -> None:
    """Verifies that execute_python_code runs code and captures stdout."""
    code = 'print("Hello Sandbox World")'
    result = execute_python_code.invoke({"code": code})
    assert "Hello Sandbox World" in result


def test_python_executor_timeout() -> None:
    """Verifies that execute_python_code terminates after exceeding timeout limit."""
    code = "import time\ntime.sleep(10)"
    result = execute_python_code.invoke({"code": code, "timeout": 1})
    assert "Error: Execution timed out" in result


def test_python_executor_memory_limit() -> None:
    """Verifies that execute_python_code terminates when memory threshold is crossed."""
    # Attempt to allocate ~100MB of bytes
    code = 'x = b"a" * 100 * 1024 * 1024\nprint(len(x))'
    result = execute_python_code.invoke({"code": code, "memory_limit_mb": 10})
    assert "Error: Memory limit of 10" in result or "MemoryError" in result


def test_is_safe_sql() -> None:
    """Verifies SQL query string safety validation checks."""
    assert is_safe_sql("SELECT * FROM users") is True
    assert is_safe_sql("WITH sample AS (SELECT 1) SELECT * FROM sample") is True
    assert is_safe_sql("SELECT * FROM users; DROP TABLE users") is False
    assert is_safe_sql("DROP TABLE users") is False
    assert is_safe_sql("INSERT INTO users (email) VALUES ('a@b.com')") is False
    assert is_safe_sql("UPDATE users SET is_active=True") is False
    assert is_safe_sql("DELETE FROM users") is False
    assert is_safe_sql("ALTER TABLE users ADD COLUMN age INT") is False


@pytest.mark.asyncio
async def test_compile_and_execute_sql() -> None:
    """Verifies Natural Language translation to SQL and safe mock execution."""
    from sqlalchemy.ext.asyncio import create_async_engine

    # 1. Create temporary SQLite in-memory database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    # 2. Mock ChatOpenAI compiler response
    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(
        return_value=AIMessage(content="SELECT * FROM users")
    )

    with (
        patch("tools.sql_compiler.get_tool_llm", return_value=mock_llm_instance),
        patch("tools.sql_compiler.async_session_factory", async_session_maker),
    ):
        result = await compile_and_execute_sql.ainvoke(
            {"nl_query": "Show me all users"}
        )
        assert "SELECT * FROM users" in result
        assert "results" in result

    await engine.dispose()


def test_generate_chart() -> None:
    """Verifies chart generation outputting a base64 PNG."""
    data = [
        {"item": "Apples", "qty": 10},
        {"item": "Bananas", "qty": 15},
        {"item": "Oranges", "qty": 8},
    ]

    result = generate_chart.invoke(
        {
            "chart_type": "bar",
            "data": data,
            "title": "Fruits Quantity",
            "x_label": "Fruits",
            "y_label": "Quantity",
            "x_key": "item",
            "y_key": "qty",
        }
    )

    assert result.startswith("data:image/png;base64,")


def test_generate_pdf_report() -> None:
    """Verifies PDF report creation and page styling layout checks."""
    title = "Test Executive Summary"
    content = (
        "# Executive Summary\n\n"
        "This is a paragraph detailing results.\n\n"
        "## Section 1\n\n"
        "Detail metrics."
    )
    filename = "test_pdf_report.pdf"

    pdf_path = generate_pdf_report.invoke(
        {"title": title, "content": content, "filename": filename}
    )

    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")
    assert os.path.getsize(pdf_path) > 0

    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_generate_pptx_report() -> None:
    """Verifies slide layout presentation compilation."""
    title = "Test Pitch Deck"
    slides = [
        {"title": "Overview", "bullets": ["First point of data", "Second point"]},
        {"title": "Conclusion", "bullets": ["We achieved success"]},
    ]
    filename = "test_deck.pptx"

    pptx_path = generate_pptx_report.invoke(
        {"title": title, "slides_content": slides, "filename": filename}
    )

    assert os.path.exists(pptx_path)
    assert pptx_path.endswith(".pptx")
    assert os.path.getsize(pptx_path) > 0

    # Cleanup
    if os.path.exists(pptx_path):
        os.remove(pptx_path)
