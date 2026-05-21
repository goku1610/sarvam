import re
from typing import Any

from rank_bm25 import BM25Okapi


def tokenize_text(text: str) -> list[str]:
    """Tokenize text for BM25/MMR without adding a heavy NLP dependency."""
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def get_overlapping_chunks(
    text: str,
    source_url: str,
    domain: str,
    title: str,
    query: str = "",
    rank: int | None = None,
    chunk_size: int = 250,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Split text into overlapping word chunks while preserving source metadata."""
    words = text.split()
    if not words:
        return []

    step = max(1, chunk_size - overlap)
    chunks = []
    for start_index in range(0, len(words), step):
        chunk_words = words[start_index:start_index + chunk_size]
        if len(chunk_words) < 40:
            break

        chunks.append({
            "text": " ".join(chunk_words),
            "url": source_url,
            "domain": domain,
            "title": title,
            "query": query,
            "rank": rank,
            "chunk_index": len(chunks),
        })

        if start_index + chunk_size >= len(words):
            break

    return chunks


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate simple lexical overlap between two strings."""
    set1 = set(tokenize_text(text1))
    set2 = set(tokenize_text(text2))
    if not set1 or not set2:
        return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))


def mmr_filter_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 15,
    lambda_param: float = 0.6,
    per_domain_limit: int = 3,
) -> list[dict[str, Any]]:
    """Select relevant and diverse chunks using BM25 plus MMR redundancy penalties."""
    if not chunks:
        return []

    tokenized_query = tokenize_text(query)
    tokenized_corpus = [tokenize_text(chunk["text"]) for chunk in chunks]
    if not tokenized_query or not any(tokenized_corpus):
        return chunks[:top_k]

    bm25 = BM25Okapi(tokenized_corpus)
    base_scores = bm25.get_scores(tokenized_query)
    max_score = max(base_scores) if len(base_scores) and max(base_scores) > 0 else 1
    normalized_scores = [score / max_score for score in base_scores]

    unselected = list(range(len(chunks)))
    selected_indices = []
    selected_domain_counts: dict[str, int] = {}

    while len(selected_indices) < top_k and unselected:
        best_score = -float("inf")
        best_idx = -1

        for idx in unselected:
            domain = chunks[idx].get("domain", "")
            if selected_domain_counts.get(domain, 0) >= per_domain_limit:
                continue

            relevance = normalized_scores[idx]
            penalty = 0.0
            if selected_indices:
                penalty = max(
                    calculate_jaccard_similarity(chunks[idx]["text"], chunks[selected_idx]["text"])
                    for selected_idx in selected_indices
                )

            mmr_score = (lambda_param * relevance) - ((1 - lambda_param) * penalty)
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx == -1:
            break

        selected_indices.append(best_idx)
        unselected.remove(best_idx)
        selected_domain = chunks[best_idx].get("domain", "")
        selected_domain_counts[selected_domain] = selected_domain_counts.get(selected_domain, 0) + 1

    return [
        {
            **chunks[index],
            "bm25_score": float(normalized_scores[index]),
            "source_id": selected_position + 1,
        }
        for selected_position, index in enumerate(selected_indices)
    ]


def build_context_from_pages(
    query: str,
    pages: list[dict[str, Any]],
    top_k: int = 15,
    chunk_size: int = 250,
    overlap: int = 50,
    lambda_param: float = 0.6,
) -> dict[str, Any]:
    """Build a compact, diverse research context from scraped pages."""
    all_chunks = []
    for page in pages:
        all_chunks.extend(
            get_overlapping_chunks(
                text=page.get("content", ""),
                source_url=page.get("url", ""),
                domain=page.get("domain", ""),
                title=page.get("title", "Unknown Title"),
                query=page.get("query", ""),
                rank=page.get("rank"),
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    filtered_chunks = mmr_filter_chunks(
        query=query,
        chunks=all_chunks,
        top_k=top_k,
        lambda_param=lambda_param,
    )

    return {
        "chunks": filtered_chunks,
        "context": assemble_context_string(filtered_chunks),
        "chunk_count": len(all_chunks),
        "selected_count": len(filtered_chunks),
    }


def assemble_context_string(selected_chunks: list[dict[str, Any]]) -> str:
    """Format selected chunks for the synthesis LLM."""
    assembled_parts = []

    for index, chunk in enumerate(selected_chunks, start=1):
        formatted_chunk = (
            f"[Source ID: {index} | Title: {chunk['title']} | Domain: {chunk['domain']}]\n"
            f"{chunk['text']}\n"
            f"URL: {chunk['url']}"
        )
        assembled_parts.append(formatted_chunk)

    return "\n\n---\n\n".join(assembled_parts)
