"""Persistent Chroma collections with cosine search and explicit embeddings."""
import hashlib
import json
from pathlib import Path

import chromadb

from .models import Chunk


class ChromaStore:
    def __init__(self, directory: Path) -> None:
        self.client = chromadb.PersistentClient(path=str(directory))

    def prepare(self, strategy: str, chunks: list[Chunk], embedder):
        digest = hashlib.sha256()
        digest.update(embedder.model_name.encode())
        for chunk in chunks:
            digest.update(json.dumps(vars(chunk), sort_keys=True).encode())
        name = f"lab06-{strategy.lower()}-{digest.hexdigest()[:24]}"
        collection = self.client.get_or_create_collection(
            name, embedding_function=None, configuration={"hnsw": {"space": "cosine", "num_threads": 2}}
        )
        expected = {chunk.chunk_id for chunk in chunks}
        existing = set(collection.get(include=[])["ids"])
        if existing != expected:
            missing = [chunk for chunk in chunks if chunk.chunk_id not in existing]
            for start in range(0, len(missing), 128):
                batch = missing[start:start + 128]
                documents = [chunk.text for chunk in batch]
                vectors = embedder.embed_documents(documents)
                if len(vectors) != len(batch) or any(len(v) != embedder.dimensions for v in vectors):
                    raise ValueError("Unexpected embedding dimensions or batch length")
                collection.upsert(
                    ids=[chunk.chunk_id for chunk in batch], documents=documents, embeddings=vectors,
                    metadatas=[
                        {"document_id": c.document_id, "source": c.source, "page": c.page, **c.metadata}
                        for c in batch
                    ],
                )
            if existing - expected:
                collection.delete(ids=sorted(existing - expected))
        if set(collection.get(include=[])["ids"]) != expected:
            raise RuntimeError(f"Incomplete collection: {name}")
        return collection, existing == expected

    @staticmethod
    def search(collection, query_vector: list[float], filters: dict | None) -> list[dict]:
        result = collection.query(query_embeddings=[query_vector], n_results=3, where=filters)
        return [
            {"chunk_id": key, "text": text, "score": 1 - distance, "metadata": metadata}
            for key, text, distance, metadata in zip(
                result["ids"][0], result["documents"][0], result["distances"][0],
                result["metadatas"][0], strict=True,
            )
        ]
