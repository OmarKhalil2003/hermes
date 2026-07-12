import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.auth import Role
from backend.repositories.audit import AuditLogRepository
from backend.repositories.auth import (
    PermissionRepository,
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from backend.repositories.chat import ConversationRepository, MessageRepository
from backend.repositories.document import ChunkRepository, DocumentRepository
from backend.repositories.jobs import EvaluationRepository, TrainingJobRepository


@pytest.mark.asyncio
async def test_user_repository(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    # Test Create
    user_data = {
        "email": "test@example.com",
        "hashed_password": "hashed_password_123",
        "is_active": True,
        "is_superuser": False,
    }
    user = await repo.create(user_data)
    assert user.id is not None
    assert user.email == "test@example.com"

    # Test Get by ID
    fetched_user = await repo.get(user.id)
    assert fetched_user is not None
    assert fetched_user.email == "test@example.com"

    # Test Get by Email
    fetched_by_email = await repo.get_by_email("test@example.com")
    assert fetched_by_email is not None
    assert fetched_by_email.id == user.id

    # Test Get non-existent user by email
    assert await repo.get_by_email("nonexistent@example.com") is None

    # Test Get All
    users = await repo.get_all()
    assert len(users) >= 1

    # Test Update using dict
    updated_user = await repo.update(user, {"is_superuser": True})
    assert updated_user.is_superuser is True

    # Test Update using object
    user.is_active = False
    updated_user_obj = await repo.update(user, user)
    assert updated_user_obj.is_active is False

    # Test Delete
    deleted_user = await repo.delete(user.id)
    assert deleted_user is not None
    assert deleted_user.id == user.id

    # Verify Deleted
    assert await repo.get(user.id) is None
    assert await repo.delete(uuid4()) is None


@pytest.mark.asyncio
async def test_role_and_permission_repositories(db_session: AsyncSession) -> None:
    role_repo = RoleRepository(db_session)
    perm_repo = PermissionRepository(db_session)

    # Test Create Permission
    perm = await perm_repo.create({"name": "document:read", "description": "Read docs"})
    assert perm.id is not None
    assert perm.name == "document:read"

    # Test Create Role
    role = await role_repo.create(
        {"name": "researcher", "description": "Researcher role"}
    )
    assert role.id is not None
    assert role.name == "researcher"

    # Test Get by Name
    fetched_perm = await perm_repo.get_by_name("document:read")
    assert fetched_perm is not None
    assert fetched_perm.id == perm.id

    fetched_role = await role_repo.get_by_name("researcher")
    assert fetched_role is not None
    assert fetched_role.id == role.id

    # Test Non-existent lookup
    assert await perm_repo.get_by_name("nonexistent:permission") is None
    assert await role_repo.get_by_name("nonexistent_role") is None

    # Test Relationship linkage
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Role).where(Role.id == role.id).options(selectinload(Role.permissions))
    )
    result = await db_session.execute(stmt)
    role_loaded = result.scalars().one()

    role_loaded.permissions.append(perm)
    updated_role = await role_repo.update(role_loaded, role_loaded)
    assert len(updated_role.permissions) == 1
    assert updated_role.permissions[0].name == "document:read"


@pytest.mark.asyncio
async def test_session_repository(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    session_repo = SessionRepository(db_session)

    # Create User for Session
    user = await user_repo.create(
        {"email": "session@example.com", "hashed_password": "pw"}
    )

    # Create Session
    session_token = "some_random_session_token_123"
    sess = await session_repo.create(
        {
            "user_id": user.id,
            "token": session_token,
            "expires_at": datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=1),
            "is_revoked": False,
        }
    )
    assert sess.id is not None
    assert sess.token == session_token

    # Get by Token
    fetched_sess = await session_repo.get_by_token(session_token)
    assert fetched_sess is not None
    assert fetched_sess.id == sess.id

    # Get by non-existent token
    assert await session_repo.get_by_token("fake_token") is None


@pytest.mark.asyncio
async def test_document_and_chunk_repositories(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    doc_repo = DocumentRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    # Create User
    user = await user_repo.create({"email": "doc@example.com", "hashed_password": "pw"})

    # Create Document
    doc = await doc_repo.create(
        {
            "user_id": user.id,
            "filename": "research.pdf",
            "file_path": "/var/data/research.pdf",
            "mime_type": "application/pdf",
            "file_size": 102456,
            "status": "pending",
        }
    )
    assert doc.id is not None

    # Get by User ID
    user_docs = await doc_repo.get_by_user_id(user.id)
    assert len(user_docs) == 1
    assert user_docs[0].filename == "research.pdf"

    # Create Chunks
    chunk1 = await chunk_repo.create(
        {
            "document_id": doc.id,
            "content": "First chunk content.",
            "index": 0,
            "metadata_json": {"source": "header"},
        }
    )
    chunk2 = await chunk_repo.create(
        {
            "document_id": doc.id,
            "content": "Second chunk content.",
            "index": 1,
            "metadata_json": {"source": "footer"},
        }
    )
    assert chunk1.id is not None
    assert chunk2.id is not None

    # Get Chunks by Doc ID
    chunks = await chunk_repo.get_chunks_by_document_id(doc.id)
    assert len(chunks) == 2
    assert chunks[0].index == 0
    assert chunks[1].index == 1


@pytest.mark.asyncio
async def test_conversation_and_message_repositories(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    conv_repo = ConversationRepository(db_session)
    msg_repo = MessageRepository(db_session)

    # Create User
    user = await user_repo.create(
        {"email": "chat@example.com", "hashed_password": "pw"}
    )

    # Create Conversation
    conv = await conv_repo.create({"user_id": user.id, "title": "AI Assistant Chat"})
    assert conv.id is not None

    # Get by User ID
    user_convs = await conv_repo.get_by_user_id(user.id)
    assert len(user_convs) == 1
    assert user_convs[0].title == "AI Assistant Chat"

    # Create Messages
    msg_user = await msg_repo.create(
        {
            "conversation_id": conv.id,
            "sender": "user",
            "content": "Hello AI!",
        }
    )
    msg_ai = await msg_repo.create(
        {
            "conversation_id": conv.id,
            "sender": "assistant",
            "content": "Hello User!",
        }
    )
    assert msg_user.id is not None
    assert msg_ai.id is not None

    # Get Messages by Conversation ID
    msgs = await msg_repo.get_messages_by_conversation_id(conv.id)
    assert len(msgs) == 2
    assert msgs[0].sender == "user"
    assert msgs[1].sender == "assistant"


@pytest.mark.asyncio
async def test_jobs_and_evaluations_repositories(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    job_repo = TrainingJobRepository(db_session)
    eval_repo = EvaluationRepository(db_session)

    # Create User
    user = await user_repo.create({"email": "job@example.com", "hashed_password": "pw"})

    # Create Training Job
    job = await job_repo.create(
        {
            "user_id": user.id,
            "model_name": "fine-tuned-qwen-v1",
            "base_model": "Qwen2.5-3B",
            "dataset_path": "/var/datasets/legal.jsonl",
            "hyperparameters": {"lr": 2e-5, "epochs": 3},
            "status": "pending",
        }
    )
    assert job.id is not None

    # Retrieve Jobs by Status
    pending_jobs = await job_repo.get_jobs_by_status("pending")
    assert len(pending_jobs) == 1
    assert pending_jobs[0].id == job.id

    # Update Job Status
    job.status = "running"
    await job_repo.update(job, job)

    running_jobs = await job_repo.get_jobs_by_status("running")
    assert len(running_jobs) == 1
    assert running_jobs[0].id == job.id

    # Create Evaluation
    evaluation = await eval_repo.create(
        {
            "training_job_id": job.id,
            "model_name": "fine-tuned-qwen-v1",
            "dataset_name": "legal_eval",
            "metrics": {"rouge1": 0.82, "rougeL": 0.79},
        }
    )
    assert evaluation.id is not None

    # Retrieve Evaluations by Job ID
    evals = await eval_repo.get_by_training_job_id(job.id)
    assert len(evals) == 1
    assert evals[0].id == evaluation.id


@pytest.mark.asyncio
async def test_audit_log_repository(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    audit_repo = AuditLogRepository(db_session)

    # Create User
    user = await user_repo.create(
        {"email": "audit@example.com", "hashed_password": "pw"}
    )

    # Create Audit Log
    log = await audit_repo.create(
        {
            "user_id": user.id,
            "action": "document_upload",
            "ip_address": "127.0.0.1",
            "details": {"filename": "research.pdf"},
        }
    )
    assert log.id is not None

    # Retrieve Audit Logs by User ID
    logs = await audit_repo.get_logs_by_user_id(user.id)
    assert len(logs) == 1
    assert logs[0].action == "document_upload"
