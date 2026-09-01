#!/usr/bin/env python3
"""
tokenizer.py - Version avec fallback si torch n'est pas disponible
Ce fichier est un script autonome, pas utilisé par l'API principale
"""

import json
import os
import sys

# Vérifier si torch est disponible
try:
    import torch
    from FlagEmbedding import BGEM3FlagModel
    TORCH_AVAILABLE = True
    print("✅ Torch disponible - génération des embeddings en cours...")
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ Torch non disponible - ce script nécessite torch")
    print("   Pour l'API, utilisez NVIDIA API pour les embeddings")
    print("   Pour exécuter ce script, installez: pip install torch FlagEmbedding")
    sys.exit(1)

def main():
    """Génère les embeddings à partir des chunks"""
    
    # Vérifier que le fichier chunks.json existe
    chunks_path = "./documents/chunks.json"
    if not os.path.exists(chunks_path):
        print(f"❌ Erreur: {chunks_path} n'existe pas")
        print("   Exécutez d'abord chunking_preprocessed_markdown.py")
        sys.exit(1)
    
    print("📂 Chargement des chunks...")
    with open(chunks_path, "r", encoding="utf-8") as file:
        json_chunks = json.load(file)
    
    print(f"✅ {len(json_chunks)} chunks chargés")
    
    if not json_chunks:
        print("❌ Aucun chunk trouvé")
        sys.exit(1)
    
    # Charger le modèle
    print("🔄 Chargement du modèle BGE-M3...")
    try:
        model = BGEM3FlagModel(
            'BAAI/bge-m3',
            use_bf16=True,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        device = "GPU" if torch.cuda.is_available() else "CPU"
        print(f"✅ Modèle chargé sur {device}")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du modèle: {e}")
        sys.exit(1)
    
    # Extraire les textes
    chunks = [chunk["page_content"] for chunk in json_chunks]
    print(f"📝 {len(chunks)} textes à embedder")
    
    # Générer les embeddings
    print("🔄 Génération des embeddings...")
    try:
        embeddings = model.encode(
            chunks,
            max_length=512,
            batch_size=8,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False  
        )
        dense_embeddings = embeddings["dense_vecs"]
        print(f"✅ {len(dense_embeddings)} embeddings générés")
    except Exception as e:
        print(f"❌ Erreur lors de la génération des embeddings: {e}")
        sys.exit(1)
    
    # Ajouter les embeddings aux chunks
    print("🔄 Ajout des embeddings aux chunks...")
    for i in range(len(dense_embeddings)):
        json_chunks[i]["embedding"] = dense_embeddings[i].tolist()
    
    # Sauvegarder
    output_path = "./documents/chunks_with_embeddings.json"
    print(f"💾 Sauvegarde dans {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_chunks, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Terminé! {len(json_chunks)} chunks avec embeddings sauvegardés")
    print(f"📄 Fichier: {output_path}")

if __name__ == "__main__":
    main()