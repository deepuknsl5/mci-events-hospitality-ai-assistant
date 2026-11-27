
import json
import re
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.config import (
    CHROMA_DIR,
    DATA_DIR,
    EMBEDDING_MODEL,
    SIMILARITY_THRESHOLD,
)


class EventRetriever:
    """Hybrid retriever using vector search, BM25 and RRF."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        threshold: float = SIMILARITY_THRESHOLD,
    ):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        self.collection = self.client.get_or_create_collection(
            name="mci_event_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        # Each event gets its own independent BM25 index.
        self.bm25_indexes: dict[str, dict[str, Any]] = {}

        self._build_bm25_indexes()

  
    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text and remove common English stopwords."""

        stopwords = {
            "a", "an", "the", "is", "are", "was", "were",
            "where", "what", "when", "which", "who", "how",
            "do", "does", "did", "in", "on", "at", "to",
            "of", "for", "and", "or", "with", "from",
            "it", "this", "that", "my", "your", "me"
        }

        tokens = re.findall(r"\b\w+\b", text.lower())

        return [
            token for token in tokens
            if token not in stopwords
        ]

    def _build_bm25_indexes(self) -> None:
        """Dynamically build separate BM25 indexes for all events."""
        self.bm25_indexes.clear()

        result = self.collection.get(
            include=["documents", "metadatas"],
        )

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        # Group documents by event_id without hardcoding event names.
        event_documents: dict[str, list] = {}

        for doc_id, document, metadata in zip(
            ids, documents, metadatas
        ):
            event_id = metadata.get("event_id")

            if not event_id:
                continue

            event_documents.setdefault(
                event_id, []
            ).append({
                "id": doc_id,
                "document": document,
                "metadata": metadata,
            })

        # Build one BM25 index per event.
        for event_id, records in event_documents.items():
            tokenized_docs = [
                self.tokenize(record["document"])
                for record in records
            ]

            if not tokenized_docs:
                continue

            self.bm25_indexes[event_id] = {
                "bm25": BM25Okapi(tokenized_docs),
                "ids": [record["id"] for record in records],
                "documents": [
                    record["document"] for record in records
                ],
                "metadatas": [
                    record["metadata"] for record in records
                ],
            }

    def ingest(self, reset: bool = False) -> int:
        """Load event knowledge and rebuild vector and BM25 indexes."""

        if reset:
            try:
                self.client.delete_collection(
                    "mci_event_knowledge"
                )
            except Exception:
                pass

            self.collection = self.client.get_or_create_collection(
                name="mci_event_knowledge",
                metadata={"hnsw:space": "cosine"},
            )

        source = DATA_DIR / "events.json"

        records = json.loads(
            source.read_text(encoding="utf-8")
        )

        ids, docs, metas = [], [], []

        for index, record in enumerate(records):
            ids.append(
                f'{record["event_id"]}_{record["topic"]}_{index}'
            )

            enriched_text = (
                f"Event: {record['event_name']}. "
                f"Topic: {record['topic']}. "
                f"Information: {record['content']}"
            )

            docs.append(enriched_text)

            metas.append({
                "event_id": record["event_id"],
                "event_name": record["event_name"],
                "topic": record["topic"],
                "content": record["content"],
            })

        if ids:
            embeddings = self.model.encode(
                docs,
                normalize_embeddings=True,
            ).tolist()

            self.collection.upsert(
                ids=ids,
                documents=docs,
                metadatas=metas,
                embeddings=embeddings,
            )

        # Refresh event-specific lexical indexes.
        self._build_bm25_indexes()

        return len(ids)

    def retrieve(
        self,
        question: str,
        event_id: str,
        top_k: int = 3,
        candidate_k: int = 10,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:

        # Retrieve only from the requested event's corpus.
        event_index = self.bm25_indexes.get(event_id)

        if not event_index:
            return []

        event_doc_count = len(event_index["ids"])
        vector_limit = min(candidate_k, event_doc_count)

        if vector_limit == 0:
            return []

        # Candidate documents are keyed by unique Chroma IDs.
        candidates: dict[str, dict[str, Any]] = {}

        # 1. Semantic vector retrieval.
        query_embedding = self.model.encode(
            [question],
            normalize_embeddings=True,
        ).tolist()

        vector_result = self.collection.query(
            query_embeddings=query_embedding,
            n_results=vector_limit,
            where={"event_id": event_id},
            include=["documents", "metadatas", "distances"],
        )

        vector_ranked = []

        vector_ids = vector_result["ids"][0]
        vector_metas = vector_result["metadatas"][0]
        vector_distances = vector_result["distances"][0]

        for doc_id, metadata, distance in zip(
            vector_ids, vector_metas, vector_distances
        ):
            similarity = 1.0 - float(distance)

            candidates[doc_id] = {
                "content": metadata["content"],
                "metadata": metadata,
                "similarity": round(similarity, 4),
                "bm25_score": 0.0,
            }

            vector_ranked.append(doc_id)

        # 2. BM25 lexical retrieval.
        query_tokens = self.tokenize(question)

        bm25_ranked = []

        if query_tokens:
            scores = event_index["bm25"].get_scores(
                query_tokens
            )

            bm25_order = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True,
            )

            for index in bm25_order[:candidate_k]:
                bm25_score = float(scores[index])

                # Ignore documents with no keyword match.
                if bm25_score <= 0:
                    continue

                doc_id = event_index["ids"][index]
                metadata = event_index["metadatas"][index]

                if doc_id not in candidates:
                    candidates[doc_id] = {
                        "content": metadata["content"],
                        "metadata": metadata,
                        "similarity": None,
                        "bm25_score": bm25_score,
                    }
                else:
                    candidates[doc_id]["bm25_score"] = (
                        bm25_score
                    )

                bm25_ranked.append(doc_id)

        # 3. Reciprocal Rank Fusion.
        rrf_scores: dict[str, float] = {}

        for ranking in (vector_ranked, bm25_ranked):
            for rank, doc_id in enumerate(ranking, start=1):
                rrf_scores[doc_id] = (
                    rrf_scores.get(doc_id, 0.0)
                    + 1.0 / (rrf_k + rank)
                )

        # 4. Sort by combined ranking score.
        ranked_documents = sorted(
            rrf_scores,
            key=lambda doc_id: rrf_scores[doc_id],
            reverse=True,
        )

        # 5. Apply threshold while allowing genuine BM25 matches.
        results = []

        for doc_id in ranked_documents:
            item = candidates[doc_id]

            similarity = item["similarity"]
            bm25_score = item["bm25_score"]

            vector_match = (
                similarity is not None
                and similarity >= self.threshold
            )

            lexical_match = bm25_score > 0

            if not vector_match and not lexical_match:
                continue

            item["rrf_score"] = round(
                rrf_scores[doc_id], 6
            )

            results.append(item)

            if len(results) >= top_k:
                break

        return results
