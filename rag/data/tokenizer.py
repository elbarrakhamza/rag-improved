import torch
import json 
from FlagEmbedding import BGEM3FlagModel


with open("./documents/chunks.json","r",encoding="utf-8") as file:
    json_chunks=json.load(file)

model = BGEM3FlagModel(
    'BAAI/bge-m3',
    use_bf16=True,
    device="cuda" if torch.cuda.is_available() else "cpu"
    )

chunks=[chunck["page_content"] for chunck in json_chunks]

embeddings=model.encode(
    chunks,
    max_length=512,
    batch_size=8,
    return_dense=True,
    return_sparse=False,
    return_colbert_vecs=False  
)

dense_embeddings=embeddings["dense_vecs"]

for i in range(len(dense_embeddings)):
    json_chunks[i]["embedding"]=dense_embeddings[i].tolist()

with open("./documents/chunks_with_embeddings.json", "w", encoding="utf-8") as f:
    json.dump(json_chunks, f, ensure_ascii=False, indent=4)