import argparse
import asyncio
import json
import os

from sqlalchemy import select

from backend.core.database import async_session_factory
from backend.models.chat import Conversation, Message
from backend.models.document import Chunk, Document

MOCK_FALLBACK_DATASET = [
    {
        "messages": [
            {"role": "user", "content": "What is Hermes AI Workspace?"},
            {
                "role": "assistant",
                "content": (
                    "Hermes AI Workspace is an advanced multi-agent intelligence "
                    "and document search platform designed to ingest, process, "
                    "and query research repositories."
                ),
            },
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "What technologies does Hermes use?"},
            {
                "role": "assistant",
                "content": (
                    "Hermes integrates FastAPI, Next.js, Celery, PostgreSQL, "
                    "Redis, Qdrant vector databases, and LangGraph multi-agent "
                    "orchestrations."
                ),
            },
        ]
    },
    {
        "messages": [
            {
                "role": "user",
                "content": "How does the hybrid search work in Hermes?",
            },
            {
                "role": "assistant",
                "content": (
                    "Hybrid search in Hermes merges keyword-based BM25 relevance "
                    "scores with vector-based Qdrant cosine similarity scores, "
                    "passing the top candidates to a Cross-Encoder reranking model."
                ),
            },
        ]
    },
    {
        "messages": [
            {"role": "user", "content": "Can I export reports from Hermes?"},
            {
                "role": "assistant",
                "content": (
                    "Yes, Hermes provides secure report generator tools that output "
                    "structured PDF files using Flowables via ReportLab and "
                    "PowerPoint slides using python-pptx."
                ),
            },
        ]
    },
]


async def compile_dataset(output_path: str) -> None:
    """Queries the database to compile instruction pairs or falls back

    to mock examples.
    """
    dataset = []

    try:
        async with async_session_factory() as session:
            # 1. Compile dataset from real database chats
            chat_stmt = select(Conversation)
            result = await session.execute(chat_stmt)
            conversations = result.scalars().all()

            for conv in conversations:
                msg_stmt = (
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.created_at)
                )
                msg_res = await session.execute(msg_stmt)
                messages = msg_res.scalars().all()

                if len(messages) >= 2:
                    dialogue = []
                    for m in messages:
                        if m.sender in ["user", "assistant"]:
                            dialogue.append({"role": m.sender, "content": m.content})
                    if dialogue:
                        dataset.append({"messages": dialogue})

            # 2. Compile dataset from document chunks
            chunk_stmt = select(Chunk).limit(50)
            chunk_res = await session.execute(chunk_stmt)
            chunks = chunk_res.scalars().all()

            for chunk in chunks:
                # Query base document to get filename if present
                doc_stmt = select(Document).where(Document.id == chunk.document_id)
                doc_res = await session.execute(doc_stmt)
                doc = doc_res.scalar_one_or_none()
                filename = doc.filename if doc else "the document"

                dataset.append(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    f"Summarize the following research excerpt "
                                    f"from {filename}:\n\n{chunk.content[:200]}..."
                                ),
                            },
                            {"role": "assistant", "content": chunk.content},
                        ]
                    }
                )
    except Exception:
        pass

    # Fallback to mock data if no items were compiled
    if not dataset:
        dataset = MOCK_FALLBACK_DATASET

    # Write output to JSONL
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile Hermes Instruction fine-tuning dataset."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="finetuning/dataset.jsonl",
        help="Target output path for the JSONL dataset.",
    )
    args = parser.parse_args()

    asyncio.run(compile_dataset(args.output))


if __name__ == "__main__":
    main()
