from pypdf import PdfReader
from pathlib import Path
from langchain_text_splitters import TokenTextSplitter
from collections import defaultdict
import os
import sys
import time
import re
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from clients.chroma_client import chroma
from config import BATCH_SIZE
CHAPTER_REGEX = re.compile(
    r"(chapter\s+\d+|cap[ií]tulo\s+\d+)",
    re.IGNORECASE
)

# Extraction chapter vise
def build_text_with_metadata(pages):
    full_text = []
    page_map = []

    current_chapter = None

    for page in pages:
        text = page["text"]

        match = CHAPTER_REGEX.search(text)
        if match:
            current_chapter = match.group(0)

        start_idx = sum(len(t) for t in full_text)
        full_text.append(text + "\n")
        end_idx = start_idx + len(text)

        page_map.append({
            "start": start_idx,
            "end": end_idx,
            "page_number": page["page_number"],
            "chapter": current_chapter
        })

    return "".join(full_text), page_map


# Step 1: Extract pages's text from PDF
def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            print(f"Page {i + 1} extracted")
            pages.append({
                "page_number": i + 1,
                "text": text.strip()
            })
    return pages

# Step 2: Create chunks from text chunks
def chunks_for_embeddings(PDF_PATH):
    # PDF_PATH = BASE_DIR / "files" / "pdf" / "SpanishTrafficLaw.pdf"

    splitter = TokenTextSplitter(
        chunk_size=256,
        chunk_overlap=32
    )

    chunks = []
    buffer_text = ""
    buffer_pages = []
    pages = extract_pages(PDF_PATH)

    for page in pages:
        buffer_text += page["text"] + "\n"
        buffer_pages.append(page["page_number"])

        # chunk when buffer grows
        if len(buffer_text) > 2000:  # character guard
            sub_chunks = splitter.split_text(buffer_text)

            for chunk in sub_chunks:
                chunks.append({
                    "text": chunk,
                    "metadata": {
                        "pages": buffer_pages.copy(),
                        "chapters": []  # or detect inline if needed
                    }
                })

            buffer_text = ""
            buffer_pages = []

    # flush remainder
    if buffer_text.strip():
        sub_chunks = splitter.split_text(buffer_text)
        for chunk in sub_chunks:
            chunks.append({
                "text": chunk,
                "metadata": {
                    "pages": buffer_pages.copy(),
                    "chapters": []
                }
            })

    # for page in pages:
    #     sub_chunks = splitter.split_text(page["text"])
    #     for idx, chunk in enumerate(sub_chunks):
    #         print(f"===>{chunk}")
    #         chunks.append({
    #             "page_number": page["page_number"],
    #             "chunk_index": idx,
    #             "text": chunk
    #         })
    # full_text, page_map = build_text_with_metadata(pages)
    # chunks = splitter.split_text(full_text)
    # chunks = attach_metadata_to_chunks(chunks, page_map);
    return chunks

# Step 3: Create vector store from chunks
def create_vector_store(PDF_PATH):
    chunks = chunks_for_embeddings(PDF_PATH)
    collection = chroma.get_collection("pdf_docs")
    print(f"Collection =======> {collection}"); 
    file_name = os.path.basename(PDF_PATH)
    if collection.count() > 0:
        print("collection already populated, skipping ingestion")
        return
    page_groups = defaultdict(list)
    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        print(f"[INFO] Progressing -- {i+1}/{len(chunks)}")
        documents.append(chunk["text"])
        metadatas.append({
            "source": file_name,
            "pages": ",".join(map(str, chunk["metadata"]["pages"])),
            "chapters": ",".join(chunk["metadata"]["chapters"]) or "unknown"
        })
        ids.append(f"doc_{i}")
        print(f"len(documents): {len(documents)}")
        if len(documents) == BATCH_SIZE:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            # Cleaing the batch
            documents.clear()
            metadatas.clear()
            ids.clear()

    # flush remainder
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    # for i in range(0, len(documents), BATCH_SIZE):
    #     collection.add(
    #         documents=documents[i:i + BATCH_SIZE],
    #         metadatas=metadatas[i:i + BATCH_SIZE],
    #         ids=ids[i:i + BATCH_SIZE]
    #     )

    # for doc, meta, id_ in zip(documents, metadatas, ids):
    #     for p in meta["pages"].split(","):
    #         page_groups[p].append((doc, meta, id_))

    # for page, items in page_groups.items():
    #     collection.add(
    #         documents=[x[0] for x in items],
    #         metadatas=[x[1] for x in items],
    #         ids=[x[2] for x in items]
    #     )
    # collection.add(
    #     documents=documents,
    #     metadatas=metadatas,
    #     ids=ids
    # )
    
def normalize_mcqs_output(raw_output):
    """
    Ensure mcqs is a list of dicts.
    Accepts:
      - single dict
      - list of dicts
    """
    if isinstance(raw_output, dict):
        return [raw_output]
    if isinstance(raw_output, list):
        return raw_output
    raise ValueError("Unexpected MCQ output format")


def attach_metadata_to_chunks(chunks, page_map):
    enriched_chunks = []
    cursor = 0

    for chunk in chunks:
        chunk_len = len(chunk)
        chunk_start = cursor
        chunk_end = cursor + chunk_len

        pages = {
            entry["page_number"]
            for entry in page_map
            if not (chunk_end < entry["start"] or chunk_start > entry["end"])
        }

        chapters = {
            entry["chapter"]
            for entry in page_map
            if not (chunk_end < entry["start"] or chunk_start > entry["end"])
            and entry["chapter"] is not None
        }

        enriched_chunks.append({
            "text": chunk,
            "metadata": {
                "pages": sorted(pages),
                "chapters": sorted(chapters)
            }
        })

        cursor += chunk_len

    return enriched_chunks
