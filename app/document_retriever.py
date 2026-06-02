import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ollama


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERAL_DATA_DIR = PROJECT_ROOT / "data" / "general"
INDEX_FILE = PROJECT_ROOT / "data" / "general_embeddings_index.json"

EMBEDDING_MODEL = "mxbai-embed-large"

CHUNK_SIZE = 700
CHUNK_OVERLAP = 150

INDEX_VERSION = "similarity_retriever_v2_mxbai_structured_heading"

DEBUG_RETRIEVAL = False


@dataclass
class HeadingDetectionResult:
    is_heading: bool
    reason: str
    confidence: float


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_general_documents() -> list[dict]:
    documents = []

    for file_path in GENERAL_DATA_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")

        documents.append({
            "source": file_path.name,
            "text": text,
        })

    return documents


def detect_section_heading(
    line: str,
    next_line: str | None = None,
) -> HeadingDetectionResult:
    """
    Generic structured heading detector.

    It detects headings using document structure, not specific words.
    """

    line = line.strip()

    if not line:
        return HeadingDetectionResult(False, "empty_line", 0.0)

    words = line.split()
    word_count = len(words)

    # Bullet/list items are usually content, not headings.
    if re.match(r"^[-*•]\s+", line):
        return HeadingDetectionResult(False, "bullet_item", 0.0)

    # Long lines are usually paragraphs, not headings.
    if word_count > 14:
        return HeadingDetectionResult(False, "too_many_words", 0.1)

    # Numbered headings, for example:
    # 1. Product Summary
    # 8. Required Documents for Motor Claims
    if re.match(r"^\d+\.\s+[A-Z]", line):
        return HeadingDetectionResult(True, "numbered_heading_or_list_item", 0.9)

    # Decimal headings, for example:
    # 1.1 Coverage Details
    # 2.3 Refund Rules
    if re.match(r"^\d+(\.\d+)+\s+[A-Z]", line):
        return HeadingDetectionResult(True, "decimal_numbered_heading", 0.95)

    # Label-style headings, for example:
    # Supported Products:
    # Customer Support Hours:
    # Required Documents:
    if line.endswith(":") and word_count <= 10:
        return HeadingDetectionResult(True, "short_colon_heading", 0.9)

    # Uppercase headings, for example:
    # SUPPORTED PRODUCTS
    # CLAIM REQUIREMENTS
    if line.isupper() and word_count <= 10:
        return HeadingDetectionResult(True, "uppercase_heading", 0.85)

    # Short title followed by a list.
    if next_line:
        next_line = next_line.strip()

        next_line_is_list = bool(
            re.match(r"^[-*•]\s+", next_line)
            or re.match(r"^\d+[\.\)]\s+", next_line)
        )

        looks_like_title = (
            word_count <= 10
            and line[0].isupper()
            and not line.endswith(".")
            and not line.endswith(",")
        )

        if looks_like_title and next_line_is_list:
            return HeadingDetectionResult(True, "short_title_followed_by_list", 0.8)

    return HeadingDetectionResult(False, "not_heading", 0.0)


def current_section_started_with_label_heading(current_section: str) -> bool:
    """
    Checks whether the current section started with a label-style heading.

    Example:
    Supported Products:
    1. Motor Comprehensive Insurance
    2. Health Gold Insurance

    In this case, the numbered lines should stay inside the same section,
    not become separate chunks.
    """

    lines = [line.strip() for line in current_section.splitlines() if line.strip()]

    if not lines:
        return False

    first_line = lines[0]

    return first_line.endswith(":") and len(first_line.split()) <= 10


def is_numbered_list_item(line: str) -> bool:
    """
    Detects numbered list items like:
    1. Motor Comprehensive Insurance
    2. Health Gold Insurance
    """

    return bool(re.match(r"^\d+[\.\)]\s+", line.strip()))


def split_long_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Splits a long section into overlapping chunks.
    Used only when a detected section is too large.
    """

    text = clean_text(text)

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        split_at = text.rfind(" ", start, end)

        if split_at == -1 or split_at <= start:
            split_at = end

        chunk = text[start:split_at].strip()

        if chunk:
            chunks.append(chunk)

        start = max(split_at - overlap, start + 1)

    return chunks


def split_into_chunks(text: str) -> list[str]:
    """
    Section-aware chunking with section packing.

    Step 1:
    Split the document into logical sections using the heading detector.

    Step 2:
    Merge nearby small sections into one chunk until CHUNK_SIZE is reached.

    Why:
    Some useful answers are spread across nearby sections.
    Example:
    - company overview
    - supported products
    - required documents
    - support hours

    We do not want each small section to become a separate chunk.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    sections = []
    current_section = ""

    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else None

        heading_result = detect_section_heading(line, next_line)

        is_list_item_inside_label_section = (
            current_section_started_with_label_heading(current_section)
            and is_numbered_list_item(line)
        )

        if (
            heading_result.is_heading
            and not is_list_item_inside_label_section
            and current_section.strip()
        ):
            sections.append(current_section.strip())
            current_section = line
        else:
            current_section += "\n" + line

    if current_section.strip():
        sections.append(current_section.strip())

    chunks = []
    current_chunk = ""

    for section in sections:
        cleaned_section = clean_text(section)

        if not cleaned_section:
            continue

        # If one section alone is too long, split it with overlap.
        if len(cleaned_section) > CHUNK_SIZE:
            if current_chunk.strip():
                chunks.append(clean_text(current_chunk))
                current_chunk = ""

            chunks.extend(
                split_long_text(
                    cleaned_section,
                    chunk_size=CHUNK_SIZE,
                    overlap=CHUNK_OVERLAP,
                )
            )

            continue

        # Try to merge nearby sections into the same chunk.
        candidate_chunk = (
            cleaned_section
            if not current_chunk
            else current_chunk + "\n" + cleaned_section
        )

        if len(clean_text(candidate_chunk)) <= CHUNK_SIZE:
            current_chunk = candidate_chunk
        else:
            if current_chunk.strip():
                chunks.append(clean_text(current_chunk))

            current_chunk = cleaned_section

    if current_chunk.strip():
        chunks.append(clean_text(current_chunk))

    return chunks


def build_chunk_index() -> list[dict]:
    documents = load_general_documents()
    indexed_chunks = []

    for document in documents:
        chunks = split_into_chunks(document["text"])

        for chunk_index, chunk in enumerate(chunks):
            heading = chunk[:120]

            indexed_chunks.append({
                "index_version": INDEX_VERSION,
                "embedding_model": EMBEDDING_MODEL,
                "source": document["source"],
                "chunk_index": chunk_index,
                "heading": clean_text(heading),
                "text": clean_text(chunk),
                "search_text": clean_text(chunk),
            })

    return indexed_chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return response["embeddings"]


def is_valid_saved_index(index_data: list[dict]) -> bool:
    if not index_data:
        return False

    required_keys = {
        "index_version",
        "embedding_model",
        "source",
        "chunk_index",
        "heading",
        "text",
        "search_text",
        "embedding",
    }

    first_item = index_data[0]

    if not required_keys.issubset(first_item.keys()):
        return False

    if first_item["index_version"] != INDEX_VERSION:
        return False

    if first_item["embedding_model"] != EMBEDDING_MODEL:
        return False

    return True


def build_or_load_embedding_index(force_rebuild: bool = False) -> list[dict]:
    if INDEX_FILE.exists() and not force_rebuild:
        with open(INDEX_FILE, "r", encoding="utf-8") as file:
            index_data = json.load(file)

        if is_valid_saved_index(index_data):
            return index_data

    chunks = build_chunk_index()

    if not chunks:
        return []

    texts_to_embed = [chunk["search_text"] for chunk in chunks]
    embeddings = embed_texts(texts_to_embed)

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(INDEX_FILE, "w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=2)

    return chunks


def cosine_similarity(
    query_embedding: list[float],
    chunk_embedding: list[float],
) -> float:
    query_vector = np.array(query_embedding, dtype=float)
    chunk_vector = np.array(chunk_embedding, dtype=float)

    query_norm = np.linalg.norm(query_vector)
    chunk_norm = np.linalg.norm(chunk_vector)

    if query_norm == 0 or chunk_norm == 0:
        return 0.0

    return float(np.dot(query_vector, chunk_vector) / (query_norm * chunk_norm))


def retrieve_relevant_chunks(
    question: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve the most relevant chunks using embedding similarity.

    Flow:
    1. Load or build document embeddings.
    2. Embed the customer question.
    3. Compare the question embedding with every chunk embedding.
    4. Return the chunks with the highest similarity scores.
    """

    indexed_chunks = build_or_load_embedding_index()

    if not indexed_chunks:
        return []

    question_embedding = embed_texts([question])[0]

    scored_chunks = []

    for chunk in indexed_chunks:
        score = cosine_similarity(
            query_embedding=question_embedding,
            chunk_embedding=chunk["embedding"],
        )

        scored_chunks.append({
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
            "heading": chunk["heading"],
            "text": chunk["text"],
            "score": round(score, 4),
        })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    selected_chunks = scored_chunks[:top_k]

    if DEBUG_RETRIEVAL:
        print("\n========== RETRIEVED CHUNKS BY SIMILARITY ==========")

        for index, chunk in enumerate(selected_chunks, start=1):
            print(f"\n--- Chunk {index} ---")
            print("Source:", chunk["source"])
            print("Chunk index:", chunk["chunk_index"])
            print("Score:", chunk["score"])
            print("Text:")
            print(chunk["text"])
            print("-" * 80)

        print("====================================================\n")

    return selected_chunks