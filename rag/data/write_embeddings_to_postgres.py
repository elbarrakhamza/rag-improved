import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

DEFAULT_METADATA: Dict[str, Any] = {
    "brand": "unknown",
    "elevator_model": "unknown",
    "document_type": "unknown",
    "document_version": "unknown",
    "added_at": None,
    "page_number": None,
    "section": "unknown",
    "source_file": "unknown",
    "source_path": "unknown",
    "format": "unknown",
    "language": "unknown",
    "embedding_model": "unknown",
    "chunk_index": None,
    "chunk_total": None,
}

_PAGE_KEYS = ("page_number", "page", "page_num")


def _first_present(metadata: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in metadata and metadata[key] not in (None, ""):
            return metadata[key]
    return None


def normalize_metadata(
    raw_metadata: Optional[Dict[str, Any]],
    default_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = dict(DEFAULT_METADATA)

    if default_metadata:
        metadata.update(default_metadata)
    if raw_metadata:
        metadata.update(raw_metadata)

    page_number = _first_present(metadata, _PAGE_KEYS)
    if page_number is not None:
        try:
            metadata["page_number"] = int(page_number)
        except (TypeError, ValueError):
            metadata["page_number"] = None
    else:
        metadata["page_number"] = None

    metadata["added_at"] = metadata.get("added_at") or datetime.now(timezone.utc).isoformat()
    metadata["brand"] = str(metadata.get("brand") or "unknown")
    metadata["elevator_model"] = str(metadata.get("elevator_model") or "unknown")
    metadata["document_type"] = str(metadata.get("document_type") or "unknown")
    metadata["document_version"] = str(metadata.get("document_version") or "unknown")
    metadata["section"] = str(metadata.get("section") or "unknown")
    metadata["source_file"] = str(metadata.get("source_file") or "unknown")
    metadata["source_path"] = str(metadata.get("source_path") or "unknown")
    metadata["format"] = str(metadata.get("format") or "unknown")
    metadata["language"] = str(metadata.get("language") or "unknown")
    metadata["embedding_model"] = str(metadata.get("embedding_model") or "unknown")

    return metadata


def get_postgres_connection(env_file: Optional[str] = None):
    data_dir = Path(__file__).resolve().parent
    dotenv_file = env_file or str(data_dir / "vecdb.secrets.env")
    load_dotenv(dotenv_file)

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        password=os.getenv("POSTGRES_PASSWORD"),
        user=os.getenv("POSTGRES_USER"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


def _validate_chunk(chunk: Dict[str, Any], index: int) -> None:
    
    if "embedding" not in chunk:
        raise ValueError(f"Chunk {index} is missing 'embedding'.")
    if not isinstance(chunk["embedding"], list):
        raise ValueError(f"Chunk {index} has invalid embedding format (expected list[float]).")


def insert_chunks_with_embeddings(
    conn,
    chunks: List[Dict[str, Any]],
    default_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    if not chunks:
        return 0

    rows = []
    for index, chunk in enumerate(chunks):
        _validate_chunk(chunk, index)
        metadata = normalize_metadata(chunk.get("metadata", {}), default_metadata=default_metadata)
        rows.append((chunk["page_content"], json.dumps(metadata), chunk["embedding"]))

    query = """
        INSERT INTO documents (content, metadata, embedding)
        VALUES %s
    """

    with conn.cursor() as cursor:
        execute_values(cursor, query, rows, template="(%s, %s::jsonb, %s)")
    conn.commit()
    return len(rows)


def _load_chunks(json_path: Path) -> List[Dict[str, Any]]:
    with json_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list of chunk objects.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insert embedded chunks into PostgreSQL/pgvector with normalized metadata."
    )
    parser.add_argument(
        "--input-json",
        default=str(Path(__file__).resolve().parent / "documents" / "chunks_with_embeddings.json"),
        help="Path to JSON file containing chunks with embeddings.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to env file containing PostgreSQL credentials (default: data/vecdb.secrets.env).",
    )
    args = parser.parse_args()

    input_json_path = Path(args.input_json).resolve()
    chunks = _load_chunks(input_json_path)

    conn = get_postgres_connection(args.env_file)
    try:
        inserted = insert_chunks_with_embeddings(conn, chunks)
    finally:
        conn.close()

    print(f"Inserted {inserted} chunks from {input_json_path}.")


if __name__ == "__main__":
    main()
