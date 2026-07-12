import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from qdrant_client.http import models as qdrant_models
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.logging import logger
from backend.core.qdrant import COLLECTION_NAME, qdrant_client
from backend.models.document import Chunk, Document
from backend.repositories.document import ChunkRepository

# Lazy loaded neural models
_embed_model: SentenceTransformer | None = None
_rerank_model: CrossEncoder | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy loader for SentenceTransformer embedding model."""
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def get_rerank_model() -> CrossEncoder:
    """Lazy loader for CrossEncoder reranker model."""
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _rerank_model


def tokenize(text: str) -> list[str]:
    """Helper to tokenize text into lowercase word tokens."""
    return re.findall(r"\w+", text.lower())


class HybridSearchService:
    """Hybrid Search Service combining dense vectors and BM25 keyword matching.

    Results are re-ranked using neural Cross-Encoder models.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        self.chunk_repo = ChunkRepository(db_session)

    async def search(
        self,
        query: str,
        user_id: UUID,
        document_id: UUID | None = None,
        limit: int = 5,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Executes a hybrid search query over RAG chunks.

        Merges results using Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.
        """
        # Return empty list for empty queries
        if not query.strip():
            return []

        # 1. Fetch dense candidates from Qdrant
        dense_candidates = []
        try:
            # Build Qdrant filters
            filter_conditions: list[Any] = [
                qdrant_models.FieldCondition(
                    key="user_id",
                    match=qdrant_models.MatchValue(value=str(user_id)),
                )
            ]
            if document_id:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="document_id",
                        match=qdrant_models.MatchValue(value=str(document_id)),
                    )
                )

            # Compute query vector
            embed_model = get_embedding_model()
            query_vector = embed_model.encode(query).tolist()

            # Search Qdrant
            response = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=qdrant_models.Filter(must=filter_conditions),
                limit=50,  # candidate pool size
            )

            # Collect dense candidate mappings
            for point in response.points:
                payload = point.payload or {}
                # Apply Python-side date filtering if specified
                if payload.get("ingested_at") and (start_date or end_date):
                    try:
                        ingested_dt = datetime.fromisoformat(payload["ingested_at"])
                        if start_date and ingested_dt < start_date:
                            continue
                        if end_date and ingested_dt > end_date:
                            continue
                    except ValueError:
                        pass

                dense_candidates.append(
                    {
                        "chunk_id": UUID(payload["chunk_id"]),
                        "score": point.score,
                        "content": payload["content"],
                        "document_id": UUID(payload["document_id"]),
                        "filename": payload.get("filename", ""),
                    }
                )
        except Exception as e:
            # Vector DB query failure fallback gracefully
            logger.warning(f"Qdrant dense search failed: {e}")

        # 2. Fetch sparse candidates from PostgreSQL and score with BM25
        sparse_candidates = []
        try:
            # Query candidate chunks matching metadata filters
            stmt = (
                select(Chunk)
                .join(Document)
                .where(Document.user_id == user_id)
                .options(selectinload(Chunk.document))
            )
            if document_id:
                stmt = stmt.where(Chunk.document_id == document_id)
            if start_date:
                stmt = stmt.where(Document.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Document.created_at <= end_date)

            res = await self.db_session.execute(stmt)
            chunks = res.scalars().all()

            if chunks:
                # Tokenize corpus for BM25
                tokenized_corpus = [tokenize(c.content) for c in chunks]
                bm25 = BM25Okapi(tokenized_corpus)

                # Score corpus
                tokenized_query = tokenize(query)
                scores = bm25.get_scores(tokenized_query)

                # Compile sparse candidates
                scored_chunks = []
                for idx, score in enumerate(scores):
                    if score > 0:  # Only count positive keyword overlaps
                        chunk = chunks[idx]
                        scored_chunks.append(
                            {
                                "chunk_id": chunk.id,
                                "score": float(score),
                                "content": chunk.content,
                                "document_id": chunk.document_id,
                                "filename": chunk.document.filename,
                            }
                        )

                # Sort and take top 50
                scored_chunks.sort(key=lambda x: cast(float, x["score"]), reverse=True)
                sparse_candidates = scored_chunks[:50]

        except Exception as e:
            logger.warning(f"BM25 sparse search failed: {e}")

        # 3. Reciprocal Rank Fusion (RRF)
        # Compute ranks
        dense_ranks = {
            item["chunk_id"]: idx for idx, item in enumerate(dense_candidates)
        }
        sparse_ranks = {
            item["chunk_id"]: idx for idx, item in enumerate(sparse_candidates)
        }

        # Combine candidates
        all_candidates = {}
        for item in dense_candidates:
            all_candidates[item["chunk_id"]] = item
        for item in sparse_candidates:
            if item["chunk_id"] not in all_candidates:
                all_candidates[item["chunk_id"]] = item

        # Calculate RRF score (k=60 constant)
        rrf_scores = []
        for chunk_id, item in all_candidates.items():
            r_dense = dense_ranks.get(chunk_id)
            r_sparse = sparse_ranks.get(chunk_id)

            rrf_score = 0.0
            if r_dense is not None:
                rrf_score += 1.0 / (60.0 + r_dense)
            if r_sparse is not None:
                rrf_score += 1.0 / (60.0 + r_sparse)

            rrf_scores.append((rrf_score, item))

        # Sort by RRF score descending
        rrf_scores.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [item for _, item in rrf_scores[:20]]  # Top 20 for reranking

        if not top_candidates:
            return []

        # 4. Neural Re-ranking with CrossEncoder
        try:
            rerank_model = get_rerank_model()
            # Construct query-passage pairs
            pairs = [(query, cast(str, item["content"])) for item in top_candidates]

            # Predict similarity scores
            cross_scores = rerank_model.predict(pairs)  # type: ignore[arg-type]

            # Assign neural scores
            final_results = []
            for idx, score in enumerate(cross_scores):
                item = top_candidates[idx]
                final_results.append(
                    {
                        "chunk_id": item["chunk_id"],
                        "document_id": item["document_id"],
                        "filename": item["filename"],
                        "content": item["content"],
                        "score": float(score),
                    }
                )

            # Sort by CrossEncoder score descending
            final_results.sort(key=lambda x: x["score"], reverse=True)
            return final_results[:limit]

        except Exception as e:
            # Fallback to RRF order if reranker fails
            logger.warning(f"Cross-Encoder reranking failed: {e}")
            return [
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "filename": item["filename"],
                    "content": item["content"],
                    "score": 0.0,
                }
                for item in top_candidates[:limit]
            ]
