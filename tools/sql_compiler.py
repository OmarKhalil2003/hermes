import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import async_session_factory


def get_tool_llm() -> ChatOpenAI:
    from pydantic import SecretStr

    api_key = settings.models.openai_api_key or "dummy-key"
    base_url = settings.models.openai_api_base
    return ChatOpenAI(
        model=settings.models.llm_model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0.0,
    )


def is_safe_sql(sql: str) -> bool:
    # Remove single-line comments and block comments
    sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql_clean = re.sub(r"/\*.*?\*/", "", sql_clean, flags=re.DOTALL)
    sql_clean = sql_clean.strip()

    # Must start with SELECT or WITH
    if not re.match(r"^(WITH|SELECT)\b", sql_clean, re.IGNORECASE):
        return False

    # Forbidden DML/DDL operations
    forbidden_patterns = [
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bDROP\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bREPLACE\b",
        r"\bTRUNCATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, sql_clean, re.IGNORECASE):
            return False

    # Check for multiple statements separated by semicolon
    parts = [p.strip() for p in sql_clean.split(";")]
    non_empty_parts = [p for p in parts if p]
    return not len(non_empty_parts) > 1


@tool
async def compile_and_execute_sql(nl_query: str) -> str:
    """Convert a natural language question into an SQL SELECT query, validate

    its safety, execute it against the database, and return formatted results.

    Args:
        nl_query: The natural language question/request about database records.

    Returns:
        JSON string containing the raw executed SQL and result rows, or an error.
    """
    schema_desc = (
        "You are an expert SQL translator. Your job is to convert natural language "
        "queries into read-only PostgreSQL SELECT queries "
        "based on the database schema.\n\n"
        "Schema:\n"
        "1. Table 'users':\n"
        "   - id (UUID, PK)\n"
        "   - email (VARCHAR, unique)\n"
        "   - hashed_password (VARCHAR)\n"
        "   - is_active (BOOLEAN)\n"
        "   - is_superuser (BOOLEAN)\n"
        "   - full_name (VARCHAR)\n"
        "   - created_at (TIMESTAMP)\n"
        "   - updated_at (TIMESTAMP)\n\n"
        "2. Table 'documents':\n"
        "   - id (UUID, PK)\n"
        "   - filename (VARCHAR)\n"
        "   - file_path (VARCHAR)\n"
        "   - status (VARCHAR)\n"
        "   - size_bytes (BIGINT)\n"
        "   - sha256 (VARCHAR)\n"
        "   - user_id (UUID, FK to users.id)\n"
        "   - parsed_metadata (JSONB)\n"
        "   - created_at (TIMESTAMP)\n"
        "   - updated_at (TIMESTAMP)\n\n"
        "3. Table 'chunks':\n"
        "   - id (UUID, PK)\n"
        "   - document_id (UUID, FK to documents.id)\n"
        "   - chunk_index (INTEGER)\n"
        "   - content (TEXT)\n"
        "   - metadata_filters (JSONB)\n"
        "   - created_at (TIMESTAMP)\n\n"
        "4. Table 'conversations':\n"
        "   - id (UUID, PK)\n"
        "   - user_id (UUID, FK to users.id)\n"
        "   - title (VARCHAR)\n"
        "   - created_at (TIMESTAMP)\n"
        "   - updated_at (TIMESTAMP)\n\n"
        "5. Table 'messages':\n"
        "   - id (UUID, PK)\n"
        "   - conversation_id (UUID, FK to conversations.id)\n"
        "   - sender (VARCHAR)\n"
        "   - content (TEXT)\n"
        "   - created_at (TIMESTAMP)\n\n"
        "Output ONLY the raw SQL query. Do not include markdown blocks "
        "or any conversational text."
    )
    llm = get_tool_llm()
    try:
        messages = [SystemMessage(content=schema_desc), HumanMessage(content=nl_query)]
        response = await llm.ainvoke(messages)
        sql_query = str(response.content).strip()

        # Clean markdown code blocks if the model wrapped it
        if sql_query.startswith("```"):
            lines = sql_query.splitlines()
            if lines[0].startswith("```sql") or lines[0].startswith("```"):
                sql_query = "\n".join(lines[1:-1]).strip()

        if not is_safe_sql(sql_query):
            return f"Error: Compiled SQL query is not safe/read-only: {sql_query}"

        # Execute query against database
        async with async_session_factory() as session:
            res = await session.execute(text(sql_query))
            rows = res.mappings().all()

            # Format rows as JSON serialization friendly dicts
            results_list = []
            for row in rows:
                row_dict = {}
                for k, v in row.items():
                    # Handle UUID and datetime serialization
                    if hasattr(v, "hex"):  # UUID
                        row_dict[k] = str(v)
                    elif hasattr(v, "isoformat"):  # datetime
                        row_dict[k] = v.isoformat()
                    else:
                        row_dict[k] = v
                results_list.append(row_dict)

            return json.dumps({"sql": sql_query, "results": results_list}, indent=2)

    except Exception as e:
        return f"Error compiling or executing SQL: {e!s}"
