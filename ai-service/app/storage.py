from typing import List, Dict, Callable
import uuid
import heapq


class InMemoryDocStore:
    """
    Very simple in-memory document chunk store for hackathon demo.

    Each chunk is stored as:
    {
        "id": str,
        "text": str,
        "embedding": List[float]
    }
    """

    def __init__(self) -> None:
        self.chunks: List[Dict] = []

    def add_chunk(self, text: str, embedding: List[float]) -> str:
        """
        Add a single text chunk with its embedding.
        Returns generated chunk id.
        """
        chunk_id = str(uuid.uuid4())
        self.chunks.append(
            {
                "id": chunk_id,
                "text": text,
                "embedding": embedding,
            }
        )
        return chunk_id

    def add_document(self, chunks_text: List[str], embeddings: List[List[float]]) -> List[str]:
        """
        Add a whole document, given a list of text chunks and matching embeddings.
        Returns list of chunk ids.
        """
        if len(chunks_text) != len(embeddings):
            raise ValueError("chunks_text and embeddings must have same length")

        ids: List[str] = []
        for text, emb in zip(chunks_text, embeddings):
            ids.append(self.add_chunk(text, emb))
        return ids

    def get_top_k(
        self,
        query_embedding: List[float],
        k: int,
        metric: Callable[[List[float], List[float]], float],
    ) -> List[Dict]:
        """
        Return top-k chunks by similarity between query_embedding and each stored embedding,
        using the provided metric (e.g., cosine similarity).
        """
        if not self.chunks:
            return []

        # Use a heap for efficiency if there are many chunks
        heap: List = []

        for chunk in self.chunks:
            score = metric(query_embedding, chunk["embedding"])
            # Python heaps are min-heaps; we push negative score to simulate max-heap
            heapq.heappush(heap, (-score, chunk))

            if len(heap) > k:
                heapq.heappop(heap)

        # Extract from heap and sort by highest score
        top_chunks: List[Dict] = []
        while heap:
            score, chunk = heapq.heappop(heap)
            chunk_with_score = dict(chunk)
            chunk_with_score["similarity"] = -score
            top_chunks.append(chunk_with_score)

        top_chunks.reverse()  # highest similarity first
        return top_chunks


# Create a single global instance that you import in main.py
doc_store = InMemoryDocStore()
