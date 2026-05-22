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
    retrieved_at: str = "",
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
            "retrieved_at": retrieved_at,
            "chunk_index": len(chunks),
        })

        if start_index + chunk_size >= len(words):
            break

    return chunks


def build_unreachable_chunk(page: dict[str, Any]) -> dict[str, Any]:
    """Represent a relevant search result whose page content could not be read."""
    reason = page.get("fetch_error") or "fetch failed"
    status = page.get("http_status")
    status_text = f" HTTP status: {status}." if status else ""
    snippet = str(page.get("snippet", "")).strip()
    snippet_text = f"\nSearch snippet: {snippet}" if snippet else ""

    return {
        "text": (
            "[Content unreachable] This relevant search result was selected, but the page content "
            f"could not be read. Reason: {reason}.{status_text}{snippet_text}"
        ),
        "url": page.get("url", ""),
        "domain": page.get("domain", ""),
        "title": page.get("title", "Unknown Title"),
        "query": page.get("query", ""),
        "rank": page.get("rank"),
        "retrieved_at": page.get("retrieved_at", ""),
        "chunk_index": 0,
        "content_unreachable": True,
        "fetch_error": reason,
        "http_status": status,
    }


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate simple lexical overlap between two strings."""
    set1 = set(tokenize_text(text1))
    set2 = set(tokenize_text(text2))
    if not set1 or not set2:
        return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))


def mmr_filter_chunks(
    queries: list[str] | str,
    chunks: list[dict[str, Any]],
    top_k: int = 15,
    lambda_param: float = 0.6,
    per_domain_limit: int = 3,
) -> list[dict[str, Any]]:
    """Select relevant and diverse chunks using BM25 plus MMR redundancy penalties.

    ``queries`` may be a single string or a list of strings.  When multiple
    queries are provided (e.g. the original user question plus sub-queries
    generated during multi-hop reasoning), the BM25 score for each chunk is
    the *maximum* score across all queries.  This prevents chunks retrieved
    for a hop sub-question from being penalised because they don't match
    the original wording.
    """
    if not chunks:
        return []

    # Normalise queries to a list
    if isinstance(queries, str):
        query_list = [queries]
    else:
        query_list = [q for q in queries if q.strip()] or [""]

    tokenized_corpus = [tokenize_text(chunk["text"]) for chunk in chunks]
    if not any(tokenized_corpus):
        return chunks[:top_k]

    bm25 = BM25Okapi(tokenized_corpus)

    # Compute per-chunk scores as the max across all queries
    combined_scores = [0.0] * len(chunks)
    for q in query_list:
        tokenized_q = tokenize_text(q)
        if not tokenized_q:
            continue
        scores = bm25.get_scores(tokenized_q)
        for idx, score in enumerate(scores):
            if score > combined_scores[idx]:
                combined_scores[idx] = score

    max_score = max(combined_scores) if combined_scores and max(combined_scores) > 0 else 1
    normalized_scores = [score / max_score for score in combined_scores]

    # Dynamic per-domain limit: allow more chunks when source diversity is low
    unique_domains = {chunk.get("domain", "") for chunk in chunks if chunk.get("domain")}
    if len(unique_domains) <= 3:
        effective_domain_limit = max(per_domain_limit, 5)
    else:
        effective_domain_limit = per_domain_limit

    unselected = list(range(len(chunks)))
    selected_indices = []
    selected_domain_counts: dict[str, int] = {}

    while len(selected_indices) < top_k and unselected:
        best_score = -float("inf")
        best_idx = -1

        for idx in unselected:
            domain = chunks[idx].get("domain", "")
            if selected_domain_counts.get(domain, 0) >= effective_domain_limit:
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
    max_context_chars: int = 24000,
    additional_queries: list[str] | None = None,
    deep_research: bool = False,
) -> dict[str, Any]:
    """Build a compact, diverse research context from scraped pages.

    Parameters
    ----------
    additional_queries:
        Extra queries (e.g. multi-hop sub-queries) to include when scoring
        chunk relevance.  Chunks matching *any* of these queries will receive
        a high BM25 score, preventing hop-specific content from being dropped.
    deep_research:
        When True, selects more chunks (``top_k`` bumped to 20 unless the
        caller already set a higher value) and allows a larger context window.
    """
    effective_top_k = max(top_k, 20) if deep_research else top_k
    effective_max_chars = max(max_context_chars, 32000) if deep_research else max_context_chars

    all_chunks = []
    unreachable_chunks = []
    for page in pages:
        if page.get("content_unreachable"):
            unreachable_chunks.append(build_unreachable_chunk(page))
            continue

        all_chunks.extend(
            get_overlapping_chunks(
                text=page.get("content", ""),
                source_url=page.get("url", ""),
                domain=page.get("domain", ""),
                title=page.get("title", "Unknown Title"),
                query=page.get("query", ""),
                rank=page.get("rank"),
                retrieved_at=page.get("retrieved_at", ""),
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    # Build composite query list for BM25 scoring
    scoring_queries: list[str] = [query]
    if additional_queries:
        scoring_queries.extend(q for q in additional_queries if q.strip())

    filtered_chunks = mmr_filter_chunks(
        queries=scoring_queries,
        chunks=all_chunks,
        top_k=effective_top_k,
        lambda_param=lambda_param,
    )
    selected_chunks = filtered_chunks + unreachable_chunks[: max(0, effective_top_k - len(filtered_chunks))]

    capped_chunks = []
    used_chars = 0
    for chunk in selected_chunks:
        next_size = len(chunk.get("text", "")) + len(chunk.get("title", "")) + len(chunk.get("url", "")) + 80
        if capped_chunks and used_chars + next_size > effective_max_chars:
            break
        capped_chunks.append(chunk)
        used_chars += next_size

    return {
        "chunks": capped_chunks,
        "context": assemble_context_string(capped_chunks),
        "chunk_count": len(all_chunks) + len(unreachable_chunks),
        "selected_count": len(capped_chunks),
        "unreachable_count": len(unreachable_chunks),
        "max_context_chars": effective_max_chars,
    }


def assemble_context_string(selected_chunks: list[dict[str, Any]]) -> str:
    """Format selected chunks for the synthesis LLM."""
    assembled_parts = []

    for index, chunk in enumerate(selected_chunks, start=1):
        formatted_chunk = (
            f"[Source ID: {index} | Title: {chunk['title']} | Domain: {chunk['domain']} | Retrieved: {chunk.get('retrieved_at', '')}]\n"
            f"{chunk['text']}\n"
            f"URL: {chunk['url']}"
        )
        assembled_parts.append(formatted_chunk)

    return "\n\n---\n\n".join(assembled_parts)
