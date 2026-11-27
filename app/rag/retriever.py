import json
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import CHROMA_DIR, DATA_DIR, EMBEDDING_MODEL, SIMILARITY_THRESHOLD


class EventRetriever:
    """Persistent ChromaDB RAG retriever with mandatory event metadata filtering."""

    def __init__(self, model_name: str = EMBEDDING_MODEL, threshold: float = SIMILARITY_THRESHOLD):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name="mci_event_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    def ingest(self, reset: bool = False) -> int:
        if reset:
            try:
                self.client.delete_collection("mci_event_knowledge")
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name="mci_event_knowledge", metadata={"hnsw:space": "cosine"}
            )

        source = DATA_DIR / "events.json"
        records = json.loads(source.read_text(encoding="utf-8"))
        ids, docs, metas = [], [], []
        for index, record in enumerate(records):
            ids.append(f'{record["event_id"]}_{record["topic"]}_{index}')
            docs.append(record["content"])
            metas.append({
                "event_id": record["event_id"],
                "event_name": record["event_name"],
                "topic": record["topic"],
            })

        if ids:
            self.collection.upsert(
                ids=ids,
                documents=docs,
                metadatas=metas,
                embeddings=self.model.encode(docs, normalize_embeddings=True).tolist(),
            )
        return len(ids)

    def retrieve(self, question: str, event_id: str, top_k: int = 3) -> list[dict[str, Any]]:
        # Event ID filter is applied inside the vector database query.
        query_embedding = self.model.encode(
            [question], normalize_embeddings=True
        ).tolist()
        result = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"event_id": event_id},
            include=["documents", "metadatas", "distances"],
        )
        items = []
        for doc, metadata, distance in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            similarity = 1.0 - float(distance)
            if similarity >= self.threshold:
                items.append({
                    "content": doc,
                    "metadata": metadata,
                    "similarity": round(similarity, 4),
                })
        return items
