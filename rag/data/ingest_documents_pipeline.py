import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Vérification de la disponibilité de torch
try:
    import torch
    from FlagEmbedding import BGEM3FlagModel
    TORCH_AVAILABLE = True
    print("✅ Torch disponible - embeddings locaux possibles")
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ Torch non disponible - utilisation du mode sans embeddings")
    print("   Pour les embeddings, utilisez l'API NVIDIA configurée dans .env")
    
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from write_embeddings_to_postgres import (
    get_postgres_connection,
    insert_chunks_with_embeddings,
    normalize_metadata,
)

# Import du smart PDF processor (SANS torch)
from smart_pdf_processor import process_pdf_smart

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
        chunk["metadata"]["chunk_index"] = 0  # Sera mis à jour plus tard
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


def read_pdf_pages(path: Path) -> List[Dict[str, Any]]:
    extracted_pages: List[Dict[str, Any]] = []
    with fitz.open(path) as pdf:
        for page_index, page in enumerate(pdf, start=1):
            page_text = page.get_text("text").strip()
            if not page_text:
                continue
            extracted_pages.append({"text": page_text, "metadata": {"page_number": page_index}})
    return extracted_pages


def read_markdown_sections(path: Path) -> List[Dict[str, Any]]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "title_1"), ("###", "title_2")],
        strip_headers=False,
    )
    docs = splitter.split_text(content)

    if not docs:
        return [{"text": content, "metadata": {}}]

    sections: List[Dict[str, Any]] = []
    for doc in docs:
        section_name = " > ".join(
            [value for key, value in doc.metadata.items() if key in ("title_1", "title_2") and value]
        )
        sections.append(
            {
                "text": doc.page_content.strip(),
                "metadata": {"section": section_name or "unknown"},
            }
        )
    return sections


def read_plain_text(path: Path) -> List[Dict[str, Any]]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    return [{"text": content, "metadata": {}}]


def extract_document_units(job: IngestionJob) -> List[Dict[str, Any]]:
    extension = job.path.suffix.lower()
    if extension == ".pdf":
        return read_pdf_pages(job.path)
    if extension in {".md", ".markdown"}:
        return read_markdown_sections(job.path)
    if extension == ".txt":
        return read_plain_text(job.path)
    return []


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
    """
    # Si c'est un PDF et qu'on utilise le smart processing
    if use_smart_pdf and job.path.suffix.lower() == ".pdf":
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
        return chunks
    
    # Sinon, traitement standard
    units = extract_document_units(job)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    raw_chunks: List[Dict[str, Any]] = []
    for unit in units:
        text = unit["text"].strip()
        if not text:
            continue
        split_texts = splitter.split_text(text)
        for split in split_texts:
            metadata = dict(job.metadata)
            metadata.update(unit.get("metadata", {}))
            metadata["source_file"] = job.path.name
            metadata["source_path"] = str(job.path)
            metadata["format"] = job.path.suffix.lstrip(".").lower()
            metadata["language"] = language
            metadata["embedding_model"] = embedding_model
            raw_chunks.append({"page_content": split, "metadata": metadata})

    chunk_total = len(raw_chunks)
    for index, chunk in enumerate(raw_chunks):
        chunk["metadata"]["chunk_index"] = index
        chunk["metadata"]["chunk_total"] = chunk_total
        chunk["metadata"] = normalize_metadata(chunk["metadata"])

    return raw_chunks


def enrich_chunks_with_embeddings(
    chunks: List[Dict[str, Any]],
    embedding_model: str,
    max_tokens: int,
    batch_size: int,
    skip_embedding: bool = False,
) -> None:
    """Génère des embeddings via API NVIDIA (1024 dimensions)"""
    if not chunks:
        return
    
    if skip_embedding:
        for chunk in chunks:
            chunk["embedding"] = [0.0] * 1024
        return

    print(f"🔄 Génération des embeddings via API NVIDIA...")
    
    import requests, os, math
    
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("⚠️ NVIDIA_API_KEY non trouvée")
        for chunk in chunks:
            chunk["embedding"] = [0.0] * 1024
        return
    
    url = "https://integrate.api.nvidia.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    all_embeddings = []
    batch_size = 10
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [chunk["page_content"] for chunk in batch]
        
        payload = {"input": texts, "model": embedding_model, "encoding_format": "float"}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                full_embeddings = [item["embedding"] for item in data["data"]]
                
                for emb in full_embeddings:
                    sliced = emb[:1024]
                    norm = math.sqrt(sum(x * x for x in sliced))
                    if norm > 0:
                        sliced = [x / norm for x in sliced]
                    all_embeddings.append(sliced)
                print(f"   ✅ Batch {i//batch_size + 1}: {len(full_embeddings)} embeddings (1024 dims)")
            else:
                print(f"   ❌ API error: {response.status_code}")
                for _ in batch:
                    all_embeddings.append([0.0] * 1024)
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            for _ in batch:
                all_embeddings.append([0.0] * 1024)
    
    for i, embedding in enumerate(all_embeddings):
        chunks[i]["embedding"] = embedding
    
    print(f"✅ {len(all_embeddings)} embeddings générés (1024 dims)")


def save_chunks_to_json(chunks: List[Dict[str, Any]], output_path: str) -> None:
    """Sauvegarde les chunks au format JSON pour inspection"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Créer une copie sans les embeddings pour un affichage plus lisible
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


def print_chunk_summary(chunks: List[Dict[str, Any]], skip_embedding: bool = False) -> None:
    """Affiche un résumé des chunks générés"""
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES CHUNKS GÉNÉRÉS")
    print("=" * 80)
    print(f"Nombre total de chunks: {len(chunks)}")
    
    if chunks:
        # Statistiques
        total_chars = sum(len(c["page_content"]) for c in chunks)
        avg_chars = total_chars / len(chunks) if chunks else 0
        print(f"Total caractères: {total_chars}")
        print(f"Moyenne caractères par chunk: {avg_chars:.0f}")
        
        # Métadonnées uniques
        sources = set()
        pages = set()
        brands = set()
        models = set()
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            if meta.get("source_file"):
                sources.add(meta["source_file"])
            if meta.get("page_number"):
                pages.add(str(meta["page_number"]))
            if meta.get("brand"):
                brands.add(meta["brand"])
            if meta.get("elevator_model"):
                models.add(meta["elevator_model"])
        
        print(f"Fichiers sources: {', '.join(sources) if sources else 'N/A'}")
        print(f"Pages: {', '.join(sorted(pages, key=int)[:5])}{'...' if len(pages) > 5 else ''}")
        print(f"Marques: {', '.join(brands) if brands else 'N/A'}")
        print(f"Modèles: {', '.join(models) if models else 'N/A'}")
        
        # Aperçu du premier chunk
        if chunks:
            print("\n" + "-" * 40)
            print("📝 APERÇU DU PREMIER CHUNK:")
            print("-" * 40)
            print(f"Contenu: {chunks[0]['page_content'][:300]}...")
            print(f"Métadonnées: {json.dumps(chunks[0]['metadata'], indent=2, ensure_ascii=False)}")
            if "embedding" in chunks[0]:
                emb = chunks[0]["embedding"]
                if skip_embedding or not TORCH_AVAILABLE:
                    print(f"Embedding: [FACTICE] taille={len(emb)} (mode sans torch)")
                else:
                    print(f"Embedding: taille={len(emb)}, premiers éléments={emb[:5]}...")
    
    print("=" * 80 + "\n")


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
    parser.add_argument("--embedding-model", default="BAAI/bge-m3", help="Embedding model name.")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Max characters per chunk.")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap in characters.")
    parser.add_argument("--max-tokens", type=int, default=512, help="Embedding model max sequence length.")
    parser.add_argument("--batch-size", type=int, default=8, help="Embedding batch size.")
    parser.add_argument("--use-smart-pdf", action="store_true", help="Use smart PDF processing (OCR, tables, images).")
    parser.add_argument("--use-vision-llm", action="store_true", default=True, help="Use vision LLM for image descriptions.")
    parser.add_argument("--no-vision-llm", dest="use_vision_llm", action="store_false", help="Disable vision LLM.")
    
    # NOUVEAU: Option pour sauter l'embedding (mode test)
    parser.add_argument(
        "--skip-embedding", 
        action="store_true", 
        help="Skip embedding generation and database insertion (test mode)."
    )
    parser.add_argument(
        "--no-db-insert", 
        action="store_true", 
        help="Skip database insertion (only generate chunks)."
    )
    
    parser.set_defaults(use_vision_llm=True)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if not args.inputs and not args.manifest:
        raise ValueError("Provide --inputs and/or --manifest.")
    
    # Avertissement si mode test
    if args.skip_embedding:
        print("\n" + "⚠️" * 20)
        print("  MODE TEST ACTIVÉ (--skip-embedding)")
        print("  - Aucun embedding ne sera généré")
        print("  - Aucune insertion en base de données")
        print("  - Les chunks seront sauvegardés en JSON si --output-json est fourni")
        print("⚠️" * 20 + "\n")
    
    if not TORCH_AVAILABLE and not args.skip_embedding:
        print("\n" + "⚠️" * 20)
        print("  TORCH NON DISPONIBLE")
        print("  - Les embeddings ne peuvent pas être générés localement")
        print("  - Utilisez --skip-embedding pour le mode test")
        print("  - Ou installez torch: pip install torch FlagEmbedding")
        print("⚠️" * 20 + "\n")
        args.skip_embedding = True  # Forcer le mode skip

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

    # Afficher le résumé
    print_chunk_summary(chunks, skip_embedding=args.skip_embedding)

    # Sauvegarder en JSON si demandé
    if args.output_json:
        save_chunks_to_json(chunks, args.output_json)

    # Générer les embeddings (sauf si skip)
    enrich_chunks_with_embeddings(
        chunks=chunks,
        embedding_model=args.embedding_model,
        max_tokens=args.max_tokens,
        batch_size=args.batch_size,
        skip_embedding=args.skip_embedding,
    )

    # Insertion en base de données (sauf si skip ou no-db-insert)
    if args.skip_embedding or args.no_db_insert:
        print(f"\n⏭️  Insertion en base de données SKIPPÉE (mode test)")
        print(f"✅ Traitement terminé - {len(chunks)} chunks générés")
        if args.output_json:
            print(f"📄 Les chunks sont disponibles dans: {args.output_json}")
    else:
        print(f"\n💾 Insertion dans PostgreSQL...")
        conn = get_postgres_connection(args.env_file)
        try:
            inserted = insert_chunks_with_embeddings(conn, chunks)
            print(f"✅ Inserted {inserted} chunks into vector database.")
        finally:
            conn.close()

    # Résumé final
    print("\n" + "=" * 80)
    print("✅ INGESTION TERMINÉE")
    print("=" * 80)
    print(f"📊 Chunks générés: {len(chunks)}")
    if args.skip_embedding or args.no_db_insert:
        print("💾 Base de données: NON INSÉRÉ (mode test)")
    else:
        print("💾 Base de données: INSÉRÉ")
    if args.output_json:
        print(f"📄 Fichier JSON: {args.output_json}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()