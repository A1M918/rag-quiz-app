import chromadb
from clients.llm_client import llm
from clients.chroma_client import chroma

# --- CONFIG ---
COLLECTION_NAME = "pdf_docs"
TOP_K = 5

# --- CLIENTS ---
chroma = chroma.client
collection = chroma.get_collection(COLLECTION_NAME)

# --- QUERY ---
def rag_query(question: str):
    # 1. Retrieve
    results = collection.query(
        query_texts=[question],
        n_results=TOP_K
    )

    contexts = results["documents"][0]

    # 2. Build prompt
    context_text = "\n\n".join(contexts)

    prompt = f"""
You are a legal assistant.
Answer ONLY using the context below.
If the answer is not present, say "Not found in the document."

Context:
{context_text}

Question:
{question}
"""

    # 3. Generate
    response = llm.chat(
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# --- RUN ---
if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (or 'exit'): ")
        if q.lower() == "exit":
            break
        answer = rag_query(q)
        print("\nAnswer:\n", answer)