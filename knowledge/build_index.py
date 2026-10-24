"""Knowledge documents için FAISS index oluşturur."""

from pathlib import Path
import json


def build() -> None:
    import faiss
    from sentence_transformers import SentenceTransformer

    root = Path(__file__).resolve().parent
    documents = json.loads((root / "documents.json").read_text(encoding="utf-8"))
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vectors = model.encode([item["text"] for item in documents], normalize_embeddings=True)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, str(root / "index.faiss"))
    print(f"FAISS index hazırlandı: {len(documents)} belge")


if __name__ == "__main__":
    build()
