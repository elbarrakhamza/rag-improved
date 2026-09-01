#!/usr/bin/env python3
"""
ingest_documents_pipeline.py - Version simplifiée pour l'API
Utilise smart_pdf_processor.py pour tous les PDFs
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import du smart PDF processor (SANS torch)
from smart_pdf_processor import process_pdf_smart

from write_embeddings_to_postgres import (
    get_postgres_connection,
    insert_chunks_with_embeddings,
    normalize_metadata,
)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


@dataclass
class IngestionJob:
    path: Path
    metadata: Dict[str, Any]


def process_file_with_smart_pdf(
    file_path: str,
    metadata: Dict[str, Any],
    ocr_lang: str = "fra+ara",
    use_vision_llm: bool = True,
    output_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Traite un fichier PDF avec le smart processor
    """
    chunks = process_pdf_smart(
        pdf_path=file_path,
        ocr_lang=ocr_lang,
        use_vision_llm=use_vision_llm,
        output_dir=output_dir
    )
    
    # Ajouter les métadonnées supplémentaires
    for chunk in chunks:
        chunk["metadata"].update(metadata)
        chunk["metadata"]["chunk_index"] = 0
        chunk["metadata"]["chunk_total"] = 0
        chunk["metadata"] = normalize_metadata(chunk["metadata"])
    
    return chunks


def collect_jobs_from_inputs(input_paths: List[str], base_metadata: Dict[str, Any]) -> List[IngestionJob]:
    jobs: List[IngestionJob] = []
    for input_path in input_paths:
        path = Path(input_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")

        if path.is_dir():
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    jobs.append(IngestionJob(path=file_path, metadata=dict(base_metadata)))
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            jobs.append(IngestionJob(path=path, metadata=dict(base_metadata)))

    if not jobs:
        raise ValueError(
            "No compatible documents found. Supported formats: .pdf, .txt, .md, .markdown."
        )
    return jobs


def collect_jobs_from_manifest(manifest_path: str) -> List[IngestionJob]:
    path = Path(manifest_path).resolve()
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError("Manifest must be a JSON list of objects.")

    jobs: List[IngestionJob] = []
    for item in payload:
        file_path = Path(item["path"]).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Manifest file does not exist: {file_path}")
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        jobs.append(IngestionJob(path=file_path, metadata=dict(item.get("metadata", {}))))

    if not jobs:
        raise ValueError("Manifest does not contain any supported documents.")
    return jobs


def build_chunks(
    job: IngestionJob,
    chunk_size: int,
    chunk_overlap: int,
    language: str,
    embedding_model: str,
    use_smart_pdf: bool = False,
    use_vision_llm: bool = True,
) -> List[Dict[str, Any]]:
    """
    Construit les chunks à partir d'un job d'ingestion
    Utilise toujours le smart PDF pour les PDFs
    """
    # Si c'est un PDF, utiliser le smart processing
    if job.path.suffix.lower() == ".pdf":
        chunks = process_file_with_smart_pdf(
            file_path=str(job.path),
            metadata=job.metadata,
            ocr_lang="fra+ara",
            use_vision_llm=use_vision_llm
        )
        # Ajouter les métadonnées de chunk
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk["metadata"]["chunk_index"] = i
            chunk["metadata"]["chunk_total"] = total
            chunk["metadata"]["language"] = language
            chunk["metadata"]["embedding_model"] = embedding_model
        return chunks
    
    # Pour les fichiers TXT et MD, lire simplement le contenu
    if job.path.suffix.lower() in {".txt", ".md", ".markdown"}:
        content = job.path.read_text(encoding="utf-8", errors="ignore")
        metadata = dict(job.metadata)
        metadata["source_file"] = job.path.name
        metadata["source_path"] = str(job.path)
        metadata["format"] = job.path.suffix.lstrip(".").lower()
        metadata["language"] = language
        metadata["embedding_model"] = embedding_model
        metadata["chunk_index"] = 0
        metadata["chunk_total"] = 1
        metadata = normalize_metadata(metadata)
        
        return [{
            "page_content": content,
            "metadata": metadata
        }]
    
    return []


def enrich_chunks_with_embeddings(
    chunks: List[Dict[str, Any]],
    embedding_model: str,
    max_tokens: int,
    batch_size: int,
    skip_embedding: bool = False,
) -> None:
    """
    Enrichit les chunks avec des embeddings factices (car on utilise NVIDIA API)
    """
    if not chunks:
        return
    
    print(f"ℹ️  Utilisation de l'API NVIDIA pour les embeddings")
    for chunk in chunks:
        chunk["embedding"] = [0.0] * 1024  # Embedding factice
    print(f"✅ {len(chunks)} chunks prêts pour l'API NVIDIA")


def save_chunks_to_json(chunks: List[Dict[str, Any]], output_path: str) -> None:
    """Sauvegarde les chunks au format JSON pour inspection"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    chunks_display = []
    for chunk in chunks:
        chunk_copy = {
            "page_content": chunk["page_content"],
            "metadata": chunk["metadata"]
        }
        if "embedding" in chunk:
            chunk_copy["embedding_size"] = len(chunk["embedding"])
        chunks_display.append(chunk_copy)
    
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(chunks_display, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Chunks sauvegardés dans: {output_file}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generic RAG ingestion pipeline for elevator maintenance documents."
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        help="Document files or folders to ingest."
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Optional JSON manifest for per-document metadata."
    )
    parser.add_argument("--env-file", default=None, help="Path to vecdb env file.")
    parser.add_argument("--output-json", default=None, help="Optional output JSON path for chunks.")
    parser.add_argument("--brand", default="unknown", help="Elevator brand metadata.")
    parser.add_argument("--elevator-model", default="unknown", help="Elevator model/type metadata.")
    parser.add_argument("--document-type", default="maintenance_manual", help="Document type metadata.")
    parser.add_argument("--document-version", default="unknown", help="Document version metadata.")
    parser.add_argument("--language", default="english", help="Document language metadata.")
    parser.add_argument("--embedding-model", default="nvidia/nemotron-3-embed-1b", help="Embedding model name.")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Max characters per chunk.")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap in characters.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Embedding model max sequence length.")
    parser.add_argument("--batch-size", type=int, default=8, help="Embedding batch size.")
    parser.add_argument("--use-smart-pdf", action="store_true", default=True, help="Use smart PDF processing.")
    parser.add_argument("--no-smart-pdf", dest="use_smart_pdf", action="store_false", help="Disable smart PDF.")
    parser.add_argument("--use-vision-llm", action="store_true", default=True, help="Use vision LLM.")
    parser.add_argument("--no-vision-llm", dest="use_vision_llm", action="store_false", help="Disable vision LLM.")
    parser.add_argument("--skip-embedding", action="store_true", help="Skip embedding generation.")
    parser.add_argument("--no-db-insert", action="store_true", help="Skip database insertion.")
    
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if not args.inputs and not args.manifest:
        raise ValueError("Provide --inputs and/or --manifest.")

    base_metadata = {
        "brand": args.brand,
        "elevator_model": args.elevator_model,
        "document_type": args.document_type,
        "document_version": args.document_version,
    }

    jobs: List[IngestionJob] = []
    if args.inputs:
        jobs.extend(collect_jobs_from_inputs(args.inputs, base_metadata))
    if args.manifest:
        jobs.extend(collect_jobs_from_manifest(args.manifest))

    chunks: List[Dict[str, Any]] = []
    for job in jobs:
        print(f"\n📄 Traitement de: {job.path.name}")
        job_chunks = build_chunks(
            job=job,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            language=args.language,
            embedding_model=args.embedding_model,
            use_smart_pdf=args.use_smart_pdf,
            use_vision_llm=args.use_vision_llm,
        )
        chunks.extend(job_chunks)
        print(f"   ✅ {len(job_chunks)} chunks générés")

    if not chunks:
        raise ValueError("No chunks were generated from input documents.")

    # Enrichir avec des embeddings (via API NVIDIA)
    enrich_chunks_with_embeddings(
        chunks=chunks,
        embedding_model=args.embedding_model,
        max_tokens=args.max_tokens,
        batch_size=args.batch_size,
        skip_embedding=args.skip_embedding,
    )

    # Sauvegarder en JSON si demandé
    if args.output_json:
        save_chunks_to_json(chunks, args.output_json)

    # Insertion en base de données
    if not args.skip_embedding and not args.no_db_insert:
        print(f"\n💾 Insertion dans PostgreSQL...")
        conn = get_postgres_connection(args.env_file)
        try:
            inserted = insert_chunks_with_embeddings(conn, chunks)
            print(f"✅ Inserted {inserted} chunks into vector database.")
        finally:
            conn.close()
    else:
        print(f"\n⏭️  Insertion en base de données SKIPPÉE")

    print("\n" + "=" * 80)
    print("✅ INGESTION TERMINÉE")
    print("=" * 80)
    print(f"📊 Chunks générés: {len(chunks)}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()