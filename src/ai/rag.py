# rag index — semantic search over learned messages using chromadb + ollama embeddings
# builds the index from db on startup in bg so the bot doesnt freeze

import logging
from typing import List

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

from src import settings
from src.storage.database import Database

log = logging.getLogger(__name__)

_COLLECTION = 'transcripts'


def _truncate(text: str) -> str:
    # nomic-embed-text has a context limit — chop anything too long before it hits the model
    return text[:settings.RAG_MAX_CHARS]


class RAGIndex:
    # wraps chromadb persistent vector index for pulling relevant style examples

    def __init__(self, db: Database, ollama_url: str) -> None:
        self._db         = db
        self._ollama_url = ollama_url
        self._client     = None
        self._collection = None

    # internal helpers

    def _get_collection(self) -> chromadb.Collection:
        # lazily spin up chromadb client and collection on first use
        if self._collection is not None:
            return self._collection

        ef = OllamaEmbeddingFunction(
            url=f'{self._ollama_url}/api/embeddings',
            model_name=settings.EMBED_MODEL,
        )
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION,
            embedding_function=ef,
            metadata={'hnsw:space': 'cosine'},
        )
        return self._collection

    # public api

    def build_index(self, force: bool = False) -> None:
        # indexes all texts from db — pass force=True to nuke and rebuild from scratch
        col   = self._get_collection()
        texts = self._db.get_transcripts()

        existing = col.count()
        if existing >= len(texts) and not force:
            log.info('RAG -> index already contains %d entries, skipping', existing)
            return

        if force and existing:
            col.delete(where={'source': {'$in': ['transcript', 'learned']}})

        # batches of 100 so we dont spike memory
        batch_size = 100
        added = 0
        for i in range(0, len(texts), batch_size):
            batch = [_truncate(t) for t in texts[i : i + batch_size]]
            ids   = [f'doc_{i + j}' for j in range(len(batch))]
            col.upsert(
                ids=ids,
                documents=batch,
                metadatas=[{'source': 'transcript'}] * len(batch),
            )
            added += len(batch)

        log.info('RAG -> indexed %d texts', added)

    def search(self, query: str, n: int = 20) -> List[str]:
        # returns up to n semantically similar examples — empty list if nothing found so callers can fall back
        try:
            col     = self._get_collection()
            count   = col.count()
            if count == 0:
                return []
            results = col.query(query_texts=[query], n_results=min(n, count))
            docs    = results.get('documents', [[]])[0]
            return docs
        except Exception as e:
            log.warning('RAG -> search error: %s', e)
            return []

    def add_text(self, text: str) -> None:
        # adds a single new text live after channel learning so index stays fresh
        try:
            col = self._get_collection()
            uid = f'learned_{col.count()}'
            col.add(ids=[uid], documents=[_truncate(text)], metadatas=[{'source': 'learned'}])
        except Exception as e:
            log.warning('RAG -> add error: %s', e)
