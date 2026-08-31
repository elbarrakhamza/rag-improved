import textwrap

def build_prompt(question: str, documents: list) -> str:
    context_blocks = []
    
    for i, chunk in enumerate(documents):
        meta = chunk.get("metadata", {})
        block = f"[Source {i+1} | Page {meta.get('page', 'N/A')} | Fichier: {meta.get('source', 'N/A')}]\n{chunk.get('content', '')}"
        context_blocks.append(block)

    context_str = "\n\n".join(context_blocks)

    prompt = f"""
    You are an expert elevator maintenance technician and diagnostic assistant.
    Your task is to answer the user's question using ONLY the information provided in the <context> block below.

    Strict Guidelines:
    1. Accuracy: Base your answer strictly on the provided context. Do not use outside knowledge or hallucinate.
    2. Unknowns: If the context does not contain the answer, reply exactly with: "I could not find this information in the manual." Do not guess.
    3. Citations: Explicitly cite the File name and page number for your claims (e.g., "According to [Manual name, Page 12]...").
    4. Formatting: Be precise and technical. Use bullet points for step-by-step procedures.

    <context>
    {context_str}
    </context>

    Question: {question}

    Answer:
    """
    
    return textwrap.dedent(prompt).strip()