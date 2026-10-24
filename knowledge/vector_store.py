"""FAISS semantic retrieval katmanı."""

from __future__ import annotations

import json
from pathlib import Path


class KnowledgeStore:
    def __init__(self, documents_path: str | Path | None = None, index_path: str | Path | None = None):
        root = Path(__file__).resolve().parent
        self.documents_path = Path(documents_path or root / "documents.json")
        self.index_path = Path(index_path or root / "index.faiss")
        self.documents = json.loads(self.documents_path.read_text(encoding="utf-8")) if self.documents_path.exists() else []
        self._index = None
        self._model = None
        self._load_faiss()

    def _load_faiss(self) -> None:
        if not self.index_path.exists() or not self.documents:
            return
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._index = faiss.read_index(str(self.index_path))
        except ImportError:
            self._index = None

    def search(self, query: str, k: int = 3) -> list[dict]:
        if self._index is None or self._model is None:
            return []
        vector = self._model.encode([query], normalize_embeddings=True)
        _, indexes = self._index.search(vector, k)
        return [self.documents[i] for i in indexes[0] if i >= 0 and i < len(self.documents)]
