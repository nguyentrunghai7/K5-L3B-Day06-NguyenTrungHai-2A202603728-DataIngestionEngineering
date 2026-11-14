"""Local semantic embeddings shared by all configurations."""
from pathlib import Path

from fastembed import TextEmbedding
from huggingface_hub import snapshot_download


class LocalEmbedder:
    model_name = "BAAI/bge-small-en-v1.5"
    dimensions = 384
    revision = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"

    def __init__(self, cache: Path) -> None:
        snapshot = snapshot_download(
            "Qdrant/bge-small-en-v1.5-onnx-Q", revision=self.revision, cache_dir=cache,
            allow_patterns=["*.json", "model_optimized.onnx", "vocab.txt"],
        )
        self.model = TextEmbedding(
            self.model_name, cache_dir=str(cache), threads=2, specific_model_path=snapshot,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.passage_embed(texts, batch_size=32)]

    def embed_queries(self, questions: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.query_embed(questions, batch_size=32)]
