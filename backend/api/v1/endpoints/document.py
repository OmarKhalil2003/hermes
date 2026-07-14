import os
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_active_user
from backend.celery_worker.tasks import process_document_task
from backend.core.database import get_db
from backend.core.logging import logger
from backend.models.auth import User
from backend.repositories.document import ChunkRepository, DocumentRepository
from backend.services.search import HybridSearchService

router = APIRouter()

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Any:
    """Accepts document files, persists them to disk, and queues async parsing."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing.",
        )

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".csv", ".txt"]
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {allowed_extensions}",
        )

    # Ensure document directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save uploaded file contents
    file_path = os.path.join(
        UPLOAD_DIR, f"{UUID(int=0)}-{file.filename}"
    )  # Using UUID placeholder to make it unique on disk

    file_size = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):
                f.write(chunk)
                file_size += len(chunk)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File disk storage failed: {e}",
        ) from e

    doc_repo = DocumentRepository(db)

    # Create Document DB record
    try:
        # Generate target path unique name
        import uuid

        unique_id = uuid.uuid4()
        new_file_path = os.path.join(UPLOAD_DIR, f"{unique_id}-{file.filename}")
        os.rename(file_path, new_file_path)

        doc = await doc_repo.create(
            {
                "id": unique_id,
                "user_id": current_user.id,
                "filename": file.filename,
                "file_path": new_file_path,
                "mime_type": file.content_type or "application/octet-stream",
                "file_size": file_size,
                "status": "pending",
            }
        )
        await db.commit()
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        if "new_file_path" in locals() and os.path.exists(new_file_path):
            os.remove(new_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database record creation failed: {e}",
        ) from e

    # Trigger Celery ingestion task
    process_document_task.delay(str(doc.id))

    return {
        "id": doc.id,
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "status": doc.status,
    }


@router.get("/search")
async def search_documents(
    query: str,
    document_id: UUID | None = None,
    limit: int = 5,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Any:
    """Performs a hybrid search query.

    Combines BM25, Qdrant vectors, and Cross-Encoder ranking.
    """
    search_service = HybridSearchService(db)
    try:
        return await search_service.search(
            query=query,
            user_id=current_user.id,
            document_id=document_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {e}",
        ) from e


@router.get("/{document_id}")
async def get_document_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Any:
    """Queries and returns the ingestion status and chunk count of a document."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Check ownership
    if doc.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden access to this resource.",
        )

    chunk_repo = ChunkRepository(db)
    chunks = await chunk_repo.get_chunks_by_document_id(doc.id)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunks_count": len(chunks),
    }


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Any:
    """Deletes a document from the system, removing local file and chunks."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Check ownership
    if doc.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden access to this resource.",
        )

    # Remove file from disk if present
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {doc.file_path}: {e}")

    # DB cascades automatically remove child chunks
    await doc_repo.delete(doc.id)
    await db.commit()

    return {"detail": "Document and extracted chunks deleted successfully."}


@router.get("", response_model=list[dict[str, Any]])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Any:
    """Lists all documents uploaded by the current user."""
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.get_by_user_id(current_user.id)

    result = []
    chunk_repo = ChunkRepository(db)
    for doc in docs:
        chunks = await chunk_repo.get_chunks_by_document_id(doc.id)
        result.append(
            {
                "id": doc.id,
                "filename": doc.filename,
                "mime_type": doc.mime_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at,
                "chunks_count": len(chunks),
            }
        )
    return result


@router.get("/reports", status_code=status.HTTP_200_OK)
async def list_reports(
    current_user: User = Depends(get_active_user),  # noqa: ARG001
) -> list[dict[str, Any]]:
    """List generated PDF and PPTX reports in the uploads directory."""
    if not os.path.exists(UPLOAD_DIR):
        return []

    reports = []
    for entry in os.scandir(UPLOAD_DIR):
        if entry.is_file() and entry.name.lower().endswith((".pdf", ".pptx")):
            stat = entry.stat()
            reports.append(
                {
                    "filename": entry.name,
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
    return reports


@router.get("/reports/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(get_active_user),  # noqa: ARG001
) -> FileResponse:
    """Download a generated PDF or PPTX report securely."""
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename."
        )

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found.",
        )

    return FileResponse(
        file_path, media_type="application/octet-stream", filename=filename
    )
