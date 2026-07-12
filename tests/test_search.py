from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.main import app
from backend.repositories.auth import UserRepository
from backend.repositories.document import ChunkRepository, DocumentRepository
from backend.services.search import HybridSearchService


@pytest.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Test client fixture that overrides get_db dependency."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_hybrid_search_service(db_session: AsyncSession) -> None:
    # 1. Create a dummy user, document, and chunk in SQL db
    doc_repo = DocumentRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    user_id = uuid4()
    doc = await doc_repo.create(
        {
            "id": uuid4(),
            "user_id": user_id,
            "filename": "search_test.txt",
            "file_path": "/fake/path/search_test.txt",
            "mime_type": "text/plain",
            "file_size": 100,
            "status": "processed",
        }
    )

    c1 = await chunk_repo.create(
        {
            "document_id": doc.id,
            "content": "This is a document about machine learning systems.",
            "index": 0,
            "metadata_json": {"filename": doc.filename},
        }
    )
    c2 = await chunk_repo.create(
        {
            "document_id": doc.id,
            "content": "We study artificial intelligence and search pipelines.",
            "index": 1,
            "metadata_json": {"filename": doc.filename},
        }
    )
    await db_session.commit()

    # 2. Setup mock embedding model
    mock_embed = MagicMock()
    # Mock all-MiniLM-L6-v2 vector dimension
    mock_embed.encode.return_value = np.array([0.1] * 384)

    # 3. Setup mock reranker model
    mock_rerank = MagicMock()
    mock_rerank.predict.return_value = [0.95, 0.45]

    # 4. Setup mock Qdrant client search response
    mock_qdrant_res1 = MagicMock()
    mock_qdrant_res1.score = 0.85
    mock_qdrant_res1.payload = {
        "chunk_id": str(c1.id),
        "document_id": str(doc.id),
        "content": c1.content,
        "filename": doc.filename,
        "ingested_at": datetime.now(UTC).isoformat(),
        "user_id": str(user_id),
    }

    mock_qdrant_res2 = MagicMock()
    mock_qdrant_res2.score = 0.70
    mock_qdrant_res2.payload = {
        "chunk_id": str(c2.id),
        "document_id": str(doc.id),
        "content": c2.content,
        "filename": doc.filename,
        "ingested_at": datetime.now(UTC).isoformat(),
        "user_id": str(user_id),
    }

    # Build a mock QueryResponse with .points
    mock_query_response = MagicMock()
    mock_query_response.points = [mock_qdrant_res1, mock_qdrant_res2]

    # Patch modules
    with (
        patch("backend.services.search.get_embedding_model", return_value=mock_embed),
        patch("backend.services.search.get_rerank_model", return_value=mock_rerank),
        patch(
            "backend.services.search.qdrant_client.query_points",
            return_value=mock_query_response,
        ),
    ):
        search_service = HybridSearchService(db_session)
        results = await search_service.search(
            query="machine learning",
            user_id=user_id,
            limit=5,
        )

        assert len(results) == 2
        # Check sorted by CrossEncoder score descending
        assert results[0]["score"] == 0.95
        assert results[0]["chunk_id"] == c1.id
        assert results[1]["score"] == 0.45
        assert results[1]["chunk_id"] == c2.id


@pytest.mark.asyncio
async def test_search_endpoint(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register & Login user
    reg_data = {"email": "searcher@example.com", "password": "mypassword123"}
    await client.post("/api/v1/auth/register", json=reg_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "searcher@example.com", "password": "mypassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Add document record
    doc_repo = DocumentRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("searcher@example.com")
    assert user is not None

    doc = await doc_repo.create(
        {
            "id": uuid4(),
            "user_id": user.id,
            "filename": "api_search.txt",
            "file_path": "/fake/api_search.txt",
            "mime_type": "text/plain",
            "file_size": 50,
            "status": "processed",
        }
    )
    chunk_repo = ChunkRepository(db_session)
    c1 = await chunk_repo.create(
        {
            "document_id": doc.id,
            "content": "Deep learning models are neural networks.",
            "index": 0,
            "metadata_json": {"filename": doc.filename},
        }
    )
    await db_session.commit()

    # 3. Setup mocks
    mock_embed = MagicMock()
    mock_embed.encode.return_value = np.array([0.2] * 384)

    mock_rerank = MagicMock()
    mock_rerank.predict.return_value = [0.88]

    mock_qdrant_res = MagicMock()
    mock_qdrant_res.score = 0.90
    mock_qdrant_res.payload = {
        "chunk_id": str(c1.id),
        "document_id": str(doc.id),
        "content": c1.content,
        "filename": doc.filename,
        "ingested_at": datetime.now(UTC).isoformat(),
        "user_id": str(user.id),
    }

    # Build a mock QueryResponse with .points
    mock_query_response = MagicMock()
    mock_query_response.points = [mock_qdrant_res]

    with (
        patch("backend.services.search.get_embedding_model", return_value=mock_embed),
        patch("backend.services.search.get_rerank_model", return_value=mock_rerank),
        patch(
            "backend.services.search.qdrant_client.query_points",
            return_value=mock_query_response,
        ),
    ):
        # 4. Search query API request
        response = await client.get(
            "/api/v1/documents/search",
            params={"query": "neural networks", "limit": 3},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == c1.content
        assert data[0]["score"] == 0.88
        assert data[0]["filename"] == "api_search.txt"
