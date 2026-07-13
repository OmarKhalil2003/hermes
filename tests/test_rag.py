from unittest.mock import MagicMock, patch
from uuid import UUID

import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.celery_worker.tasks import process_document_task
from backend.repositories.document import ChunkRepository, DocumentRepository
from rag.chunking import RecursiveTextSplitter


def test_recursive_text_splitter() -> None:
    """Verifies that RecursiveTextSplitter chunk sizes and overlaps are respected."""
    splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=10)
    text = "This is a sentence. And another one. Here is some text to split."
    chunks = splitter.split_text(text)

    assert len(chunks) > 1
    # Check that chunks respect sizing
    for chunk in chunks:
        assert len(chunk) <= 50


@pytest.mark.asyncio
async def test_document_upload_flow(client: AsyncClient) -> None:
    # 1. Unauthenticated -> 401 Unauthorized
    files = {"file": ("test.txt", b"Dummy document content here.", "text/plain")}
    response = await client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 401

    # Register & Login user
    reg_data = {"email": "rag@example.com", "password": "mypassword123"}
    await client.post("/api/v1/auth/register", json=reg_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "rag@example.com", "password": "mypassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Authenticated Upload (with mock Celery delay)
    with patch(
        "backend.api.v1.endpoints.document.process_document_task.delay"
    ) as mock_delay:
        response = await client.post(
            "/api/v1/documents/upload", files=files, headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["status"] == "pending"
        mock_delay.assert_called_once()
        doc_id = data["id"]

    # 3. Query Document Status
    response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # 4. Try upload unsupported format -> 400 Bad Request
    unsupported_files = {"file": ("test.exe", b"binary", "application/octet-stream")}
    response = await client.post(
        "/api/v1/documents/upload", files=unsupported_files, headers=headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_check_and_processing_task(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Setup authenticated headers
    reg_data = {"email": "rag2@example.com", "password": "mypassword123"}
    await client.post("/api/v1/auth/register", json=reg_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "rag2@example.com", "password": "mypassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create dummy files
    file_content = b"This is unique file content to test ingestion tasks."
    files = {"file": ("ingest.txt", file_content, "text/plain")}

    doc_ids = []
    with patch("backend.api.v1.endpoints.document.process_document_task.delay"):
        # Upload first doc
        r1 = await client.post("/api/v1/documents/upload", files=files, headers=headers)
        doc_ids.append(r1.json()["id"])

        # Upload second doc (duplicate content)
        r2 = await client.post("/api/v1/documents/upload", files=files, headers=headers)
        doc_ids.append(r2.json()["id"])

    doc_repo = DocumentRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    # Mock embedding model to return numpy arrays
    mock_embed = MagicMock()
    mock_embed.encode.return_value = np.array([[0.1] * 384])  # batch of 1 vector

    # Resolve session to ensure local SQLite session is shared in task run
    # Execute celery task synchronously for the first document
    with (
        patch("backend.celery_worker.tasks.async_session_factory") as mock_sf,
        patch("backend.celery_worker.tasks.init_qdrant_collection"),
        patch("backend.celery_worker.tasks.qdrant_client"),
        patch(
            "backend.celery_worker.tasks.get_embedding_model",
            return_value=mock_embed,
        ),
    ):
        mock_sf.return_value.__aenter__.return_value = db_session

        res1 = process_document_task(doc_ids[0])
        assert "Ingested" in res1

        # Assert database updates
        doc1 = await doc_repo.get(UUID(doc_ids[0]))
        assert doc1 is not None
        assert doc1.status == "processed"
        assert doc1.checksum is not None

        chunks = await chunk_repo.get_chunks_by_document_id(UUID(doc_ids[0]))
        assert len(chunks) > 0

        # Execute celery task synchronously for the duplicate document
        res2 = process_document_task(doc_ids[1])
        assert "Duplicate document detected" in res2

        doc2 = await doc_repo.get(UUID(doc_ids[1]))
        assert doc2 is not None
        assert doc2.status == "duplicate"


@pytest.mark.asyncio
async def test_document_deletion(client: AsyncClient, db_session: AsyncSession) -> None:
    # Setup authenticated headers
    reg_data = {"email": "rag3@example.com", "password": "mypassword123"}
    await client.post("/api/v1/auth/register", json=reg_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "rag3@example.com", "password": "mypassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Upload document
    files = {"file": ("delete_me.txt", b"Delete content.", "text/plain")}
    with patch("backend.api.v1.endpoints.document.process_document_task.delay"):
        response = await client.post(
            "/api/v1/documents/upload", files=files, headers=headers
        )
        doc_id = response.json()["id"]

    # Delete Document
    response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["detail"]

    # Verify deleted from DB
    doc_repo = DocumentRepository(db_session)
    doc = await doc_repo.get(UUID(doc_id))
    assert doc is None


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient) -> None:
    # 1. Register & Login user
    reg_data = {"email": "rag_list@example.com", "password": "mypassword123"}
    await client.post("/api/v1/auth/register", json=reg_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "rag_list@example.com", "password": "mypassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Initially listing should return empty list
    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

    # 3. Upload a file (mocked Celery delay)
    files = {"file": ("list_test.txt", b"Content for listing.", "text/plain")}
    with patch("backend.api.v1.endpoints.document.process_document_task.delay"):
        await client.post("/api/v1/documents/upload", files=files, headers=headers)

    # 4. Listing should now contain the uploaded file
    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "list_test.txt"
    assert docs[0]["status"] == "pending"
    assert docs[0]["chunks_count"] == 0
