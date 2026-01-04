from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import re
import time
import json
import os
import sys
import time
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from chroma_client import chroma
from embedding_client import embeddings as embeding
from config import METADATA, SLEEP_SECONDS, CHUNK_SIZE, CHUNK_OVERLAP, BATCH_SIZE
from generate.boe_topics import BOE_TOPICS
import hashlib 

# ------------------ Noise filters ------------------
NOISE_KEYWORDS = [
    "isbn", "nipo", "depósito legal", "sumario", "índice",
    "boletín oficial", "agencia estatal", "www.boe.es",
    "anexo", "tabla", "indemnización", "euros"
]

def looks_like_noise(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in NOISE_KEYWORDS):
        return True
    digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
    return digit_ratio > 0.30

def chunk_text(text: str):
    splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )
    print(f"==>{text}")
    chunks = splitter.split_text(text)
    return chunks
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk and len(chunk) > 200 and not looks_like_noise(chunk):
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
    return chunks

def embed_batch(texts):
    return embeding.embed(texts)

def safe_json_load(text: str):
    """
    Safely extract and parse JSON from LLM output.
    Supports:
    - Raw JSON
    - JSON wrapped in text
    - Objects or arrays
    """
    if not text or not isinstance(text, str):
        raise ValueError("Empty LLM response")

    # Remove markdown fences if present
    text = text.strip()
    text = re.sub(r"^```json|```$", "", text, flags=re.I | re.M).strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract first JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not match:
        raise ValueError("LLM did not return valid JSON")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed after extraction: {e}")


# ------------------ Main ------------------
def perform_embeddings(PDF_PATH = "", ARTICLE_RE = None, lang = "en", collection_name = None):
    if not collection_name:
        print(f"""Collection name not defined...""")
        return
    reader = PdfReader(str(PDF_PATH))
    buffer = ""
    doc_counter = 0
    print(f"""Using Collection: {collection_name}""")
    collection = chroma.get_collection(collection_name)
    print("Starting BOE ingestion (memory-safe)...")

    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue

        buffer += "\n" + page_text

        # Plain-text ingestion (no article structure)
        if ARTICLE_RE is None:
            if len(buffer) >= 1500:
                chunks = chunk_text(buffer)
                buffer = ""

                idx = 0
                while idx < len(chunks):
                    batch = chunks[idx : idx + BATCH_SIZE]
                    embeddings = embed_batch(batch)

                    ids = [f"generic_{doc_counter + i}" for i in range(len(batch))]
                    metadatas = [{"source": "PDF-en", "lang": lang}] * len(batch)

                    collection.add(
                        documents=batch,
                        embeddings=embeddings,
                        ids=ids,
                        metadatas=METADATA,
                    )

                    doc_counter += len(batch)
                    idx += len(batch)

                    print(f"  added {doc_counter} generic chunks")
                    time.sleep(SLEEP_SECONDS)

            continue  # skip article logic entirely
        
        # Process complete articles only
        matches = list(ARTICLE_RE.finditer(buffer))
        if not matches:
            continue


        for m in matches[:-1]:
            article_text = m.group(2).strip()
            if len(article_text) < 400:
                continue

            chunks = chunk_text(article_text)

            idx = 0
            total = len(chunks)

            while idx < total:
                batch = chunks[idx : idx + BATCH_SIZE]
                embeddings = embed_batch(batch)

                ids = [f"boe_es_{doc_counter + i}" for i in range(len(batch))]
                metadatas = [{
                    "source": "BOE",
                    "lang": "es"
                }] * len(batch)
                
                collection.add(
                    documents=batch,
                    embeddings=embeddings,
                    ids=ids,
                    metadatas=metadatas
                )

                doc_counter += len(batch)
                idx += len(batch)

                print(f"  added {doc_counter} chunks")
                time.sleep(SLEEP_SECONDS)

        if not matches and len(buffer) > 1500:
            chunks = chunk_text(buffer)
            buffer = ""

            idx = 0
            while idx < len(chunks):
                batch = chunks[idx : idx + BATCH_SIZE]
                embeddings = embed_batch(batch)

                ids = [f"boe_es_fallback_{doc_counter + i}" for i in range(len(batch))]
                metadatas = [{"source": "BOE", "lang": "es"}] * len(batch)

                collection.add(
                    documents=batch,
                    embeddings=embeddings,
                    ids=ids,
                    metadatas=metadatas,
                )

                doc_counter += len(batch)
                idx += len(batch)

                print(f"  added {doc_counter} fallback chunks")
                time.sleep(SLEEP_SECONDS)

        # keep unfinished article in buffer
        buffer = matches[-1].group(1) + matches[-1].group(2)

    print(f"ingestion completed. Total chunks stored: {doc_counter}")

def normalize_boe_mcqs(raw):
    if not raw:
        raise ValueError("Empty LLM response")

    # Case 1: Already a list → return as-is
    if isinstance(raw, list):
        return raw

    # Case 2: Wrapped dict → unwrap
    if isinstance(raw, dict):
        if "preguntas" in raw and isinstance(raw["preguntas"], list):
            return raw["preguntas"]

        if "questions" in raw and isinstance(raw["questions"], list):
            return raw["questions"]

        raise ValueError("Dict response does not contain MCQ list")

    raise ValueError(f"Unexpected MCQ format: {type(raw)}")

def parse_llm_json(text: str):
    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid LLM response")

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}")
    
def validate_mcq(q):
    required = {"question", "options", "correct_answer"}
    if not required.issubset(q):
        return False
    if set(q["options"].keys()) != {"A", "B", "C", "D"}:
        return False
    if q["correct_answer"] not in {"A","B","C","D"}:
        return False
    return True

def jsonl_to_json_array(src, dst):
    with open(src, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
def infer_topics_from_context(context: str) -> list[str]:
    context_lower = context.lower()
    topics = []

    for t in BOE_TOPICS:
        if any(k in context_lower for k in t["keywords"]):
            topics.append(t["topic"])

    return topics or ["general"]

def translate_file(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout:

        for line_no, line in enumerate(fin, start=1):
            if not line.strip():
                continue

            mcq = json.loads(line)
            translated = translate_mcq(mcq)

            translated["lang"] = "en"
            translated["translated_from"] = "es"

            fout.write(json.dumps(translated, ensure_ascii=False) + "\n")

            if line_no % 50 == 0:
                print(f"Translated {line_no} MCQs")
                
def translate_mcq(mcq):
    prompt = f"""
        Translate this Spanish MCQ to English.

        Return ONLY JSON.

        {json.dumps(mcq, ensure_ascii=False)}
        """

    rsp = llm.chat([
        {"role": "user", "content": prompt}
    ])

    return json.loads(rsp.choices.message.content.strip())

def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
        if i % 25 == 0:
            print(f"  extracted page {i}")
    return "\n".join(pages)

def make_document_id(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]

def is_noise(text: str) -> bool:
    noise_markers = [
        "thank you for downloading",
        "disclaimer",
        "introduction",
        "email",
        "www.",
        "http",
        "copyright",
    ]
    t = text.lower()
    return any(m in t for m in noise_markers)