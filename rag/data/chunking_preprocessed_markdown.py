from langchain_text_splitters import( 
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
    )
import re
import json

# building chunks based on the titles sections
headres_to_split_on=[
   ("##","title_1"),
   ("###","title_2")
]

markdown_splitter=MarkdownHeaderTextSplitter(
    headers_to_split_on=headres_to_split_on,
    strip_headers=False, 
)

with open("./documents/cleaned_markdown_manual_v3.md","r",encoding="utf-8") as file:
    cleaned_markdown=file.read()

markdown_chunks=markdown_splitter.split_text(cleaned_markdown)

markdown_chunks.pop(0)

# for chunk in markdown_chunks:
#     print("--------CHUNK--------")
#     print(f"size {len(chunk.page_content)}")
#     print(f"content : {chunk.page_content[:1024]}")
#     print(f"content : {chunk.metadata}")


final_chunks=[]
MAX_TOKENS=512
OVERLAP=50

recursive_markdown_splitter=RecursiveCharacterTextSplitter(
    chunk_size=MAX_TOKENS,
    chunk_overlap=OVERLAP,
    length_function=len
)

for chunk in markdown_chunks:
    if len(chunk.page_content)>MAX_TOKENS:
        temp_chunks=recursive_markdown_splitter.split_documents([chunk])
        final_chunks.extend(temp_chunks)
    else:
        final_chunks.append(chunk)


# for chunk in final_chunks:
#     print("--------CHUNK--------")
#     print(f"size {len(chunk.page_content)}")
#     print(f"content : {chunk.page_content[:1024]}")
#     print(f"content : {chunk.metadata}")

current_page="8"

pattern=r"\{\"page\":(?P<nb_page>\d+)\}"
for chunk in final_chunks:
    match=re.search(pattern,chunk.page_content)
    if match: 
        current_page=match.group("nb_page")
        chunk.page_content=re.sub(pattern,"",chunk.page_content)
    chunk.metadata["lang"]="english"
    chunk.metadata["embedding_model"]="BGE-M3"
    chunk.metadata["source"]="https://www.scribd.com/document/853727134/Maintenance-Manual-ENG-3-1-Ver-pdf"
    chunk.metadata["format"]="pdf"
    chunk.metadata["page"]=current_page


# for chunk in final_chunks:
#     print("--------CHUNK--------")
#     print(f"size {len(chunk.page_content)}")
#     print(f"content : {chunk.metadata}")


json_ready_chunks = []
for chunk in final_chunks:
    json_ready_chunks.append({
        "page_content": chunk.page_content,
        "metadata": chunk.metadata
    })

with open("./documents/chunks.json", "w", encoding="utf-8") as file:
    json.dump(json_ready_chunks, file, indent=4, ensure_ascii=False)