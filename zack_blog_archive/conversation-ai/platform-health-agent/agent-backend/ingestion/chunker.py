"""Document chunker — split documents into overlapping chunks for embedding.

Why chunking?
- LLMs have limited context windows (and cost per token)
- Embedding models work best on focused, paragraph-sized text
- Smaller chunks = more precise search results
- Overlap ensures no information is lost at chunk boundaries

Strategy:
- Target ~500 tokens per chunk (~2000 characters)
- 200 character overlap between chunks
- Split on paragraph boundaries when possible
"""


CHUNK_SIZE = 2000       # Target characters per chunk (~500 tokens)
CHUNK_OVERLAP = 200     # Characters of overlap between chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into overlapping chunks.
    
    Args:
        documents: List of {"title", "content", "source", "url", "source_type"}
    
    Returns:
        List of chunk dicts, each containing:
        - content: The chunk text
        - title: Parent document title
        - source: Parent document source ID
        - url: Parent document URL
        - source_type: blog/confluence/file
        - chunk_index: Position within the document (0, 1, 2, ...)
    """
    all_chunks = []

    for doc in documents:
        text = doc["content"]
        chunks = split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "content": chunk_text,
                "title": doc["title"],
                "source": doc["source"],
                "url": doc["url"],
                "source_type": doc["source_type"],
                "chunk_index": i,
            })

    return all_chunks


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.
    
    Algorithm:
    1. Start at position 0
    2. Look ahead chunk_size characters
    3. Find the nearest paragraph break (double newline) before that point
    4. If no paragraph break, find the nearest sentence end (period + space)
    5. If neither, just cut at chunk_size
    6. Move forward by (cut_point - overlap) to create overlap
    7. Repeat until end of text
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        # Take a window of chunk_size characters
        end = start + chunk_size

        if end >= len(text):
            # Last chunk — take everything remaining
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Try to find a natural break point
        window = text[start:end]

        # Prefer paragraph break (double newline)
        para_break = window.rfind("\n\n")
        if para_break > chunk_size // 2:  # Only if it's in the second half
            end = start + para_break + 2
        else:
            # Try sentence break (period followed by space/newline)
            sentence_break = window.rfind(". ")
            if sentence_break > chunk_size // 2:
                end = start + sentence_break + 2
            # Otherwise just cut at chunk_size (end stays as is)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward with overlap
        start = end - overlap

    return chunks
