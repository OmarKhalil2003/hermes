from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from backend.core.config import settings
from backend.core.logging import logger

qdrant_client = QdrantClient(
    host=settings.qdrant.host,
    port=settings.qdrant.port,
    api_key=settings.qdrant.api_key,
)

COLLECTION_NAME = "research_chunks"


def init_qdrant_collection() -> None:
    """Initializes the research_chunks Qdrant vector database collection if missing."""
    try:
        if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=384,  # Dimension size for all-MiniLM-L6-v2 embeddings
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                f"Successfully initialized Qdrant collection '{COLLECTION_NAME}'."
            )
    except Exception as e:
        logger.error(
            f"Failed to check/create Qdrant collection '{COLLECTION_NAME}': {e}",
            exc_info=True,
        )
