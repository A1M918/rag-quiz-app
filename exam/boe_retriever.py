from pathlib import Path
import re
from clients.chroma_client import chroma

# BASE_DIR = Path(__file__).resolve().parent.parent
# VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma"

client = chroma.client
collection = client.get_collection("pdf_docs")


# Reject numeric tables, annexes, compensation schedules
BAD_PATTERNS = [
    r"€",
    r"\b\d{3,}\b",
    r"ANEXO",
    r"Edad",
    r"Tabla",
    r"Importe",
    r"Cuantía",
]


# def looks_like_noise(text: str) -> bool:
#     for p in BAD_PATTERNS:
#         if re.search(p, text, re.IGNORECASE):
#             return True
#     return False

import re

def looks_like_noise(text: str) -> bool:
    t = text.lower()

    # --- Hard noise keywords (pure metadata / admin) ---
    noise_keywords = [
        "isbn",
        "nipo",
        "depósito legal",
        "catálogo de publicaciones",
        "sumario",
        "índice",
        "boletín oficial del estado",
        "agencia estatal",
        "www.boe.es",
        "avenida de",
        "280",
        "resolución de",
        "dirección general de tráfico",
        "medidas especiales de regulación",
        "punto de acceso nacional",
    ]

    if any(k in t for k in noise_keywords):
        return True

    # --- Index / TOC patterns ---
    # Dot leaders with page numbers
    if re.search(r"\.{5,}\s*\d+", text):
        return True

    # Big numeric tables (compensation charts, annexes)
    digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
    if digit_ratio > 0.45:
        return True

    # Administrative annexes / registries (NOT driving rules)
    if re.search(r"\banexo\b|\bregistro\b|\bconsorcio\b", t):
        return True

    # TOO SHORT to be meaningful
    if len(text) < 120:
        return True

    return False



def get_boe_explanation(question_text: str, n_results: int = 8) -> str:
    print("BOE query:", question_text)

    results = collection.query(
        query_texts=[question_text],
        n_results=n_results,
    )

    docs = results.get("documents", [[]])[0]

    clean_snippets = []

    for d in docs:
        d = d.replace("\n", " ").strip()

        print(len(d), d[:80])
        if looks_like_noise(d):
            continue

        # Keep only meaningful rule text
        clean_snippets.append(d[:800])

        # We only want 1–2 solid references
        if len(clean_snippets) == 2:
            break
    return "\n\n".join(clean_snippets)

# def get_boe_explanation(question_text: str, n_results: int = 2) -> str:
#     """
#     Retrieve relevant BOE legal text for a question.
#     """
#     # results = collection.query(
#     #     query_texts=[question_text],
#     #     n_results=n_results
#     # )

#     results = collection.query(
#         query_texts=[question_text],
#         n_results=n_results,
#         where={
#             "$and": [
#                 {"source": "BOE_Codigo_Trafico"},
#                 {"type": "law"}
#             ]
#         }
#     )

#     docs = results.get("documents", [[]])[0]

#     if not docs:
#         return ""

#     # Clean and shorten output
#     snippets = []
#     for d in docs:
#         clean = d.strip().replace("\n", " ")
#         snippets.append(clean[:600])

#     return "\n\n".join(snippets)


# def get_boe_explanation(question_text: str, n_results: int = 5) -> str:
#     """
#     Retrieve relevant Spanish BOE legal text for a question.
#     Returns raw legal paragraphs only.
#     """

#     results = collection.query(
#         query_texts=[question_text],
#         n_results=n_results,
#         where={"source": "BOE_Codigo_Trafico"}
#     )

#     docs = results.get("documents", [[]])[0]

#     if not docs:
#         return ""

#     for d in docs:
#         text = d.replace("\n", " ").strip()

#         # HARD FILTERS — reject garbage
#         if len(text) < 120:
#             continue
#         if sum(c.isdigit() for c in text) > len(text) * 0.25:
#             continue
#         if "€" in text:
#             continue
#         if "tabla" in text.lower():
#             continue
#         if "anexo" in text.lower() and len(text) > 600:
#             continue

#         # return FIRST clean legal paragraph only
#         return text[:700]

#     return ""



# def retrieve_boe_context(question_text: str, n_results: int = 3) -> str:
    """
    Retrieve raw BOE legal context for a question.
    This function MUST NOT generate explanations.
    """

    # results = collection.query(
    #     query_texts=[question_text],
    #     n_results=n_results,
    # )

    results = collection.query(
        query_texts=[question_text],
        n_results=n_results,
        where={
            "$and": [
                {"source": "BOE_Codigo_Trafico"},
                {"type": "law"}
            ]
        }
    )    


    docs = results.get("documents", [[]])[0]

    if not docs:
        return ""

    # Light cleanup only (NO summarizing here)
    cleaned = []
    for d in docs:
        text = d.replace("\n", " ").strip()
        if len(text) > 1200:
            text = text[:1200]
        cleaned.append(text)

    return "\n\n".join(cleaned)