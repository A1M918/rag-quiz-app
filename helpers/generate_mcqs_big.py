from pathlib import Path
import json
import sys
import time
import hashlib

# ------------------ Paths ------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from clients.chroma_client import chroma
from clients.llm_client import llm
from config import MCQS_PER_WINDOW
from helpers.helper import normalize_mcqs_output

# ------------------ Config ------------------
COLLECTION_NAME = "pdf_docs"
OUTPUT_FILE = BASE_DIR / "data" / "mcqs" / "eng_big_mcqs.json"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

MAX_CONTEXT_CHUNKS = 5
SLEEP_BETWEEN_CALLS = 1.5  # seconds (rate safety)

collection = chroma.get_collection(COLLECTION_NAME)

TOPIC_SEEDS = [
    "speed limits",
    "road signs",
    "overtaking",
    "alcohol and driving",
    "minimum distance",
    "seat belt",
    "right of way",
    "signalling",
    "useage of Airbags",
    "Useage of Baby Car Seat",
    "Vehicle breakdown or emergency situation"
    "I.T.V / M.O.T "
]


topic_array = [
        "speed limits",
        "road signs",
        "minimum distance",
        "overtaking rules",
        "alcohol and driving",
        "seat belt regulations",
        "right of way",
        "signalling"
    ]

# ------------------ Prompt ------------------
# SYSTEM_PROMPT = """
# You are a high-quality exam question generator for Spanish traffic theory.

# Rules:
# - Generate exactly {n} distinct multiple-choice questions.
# - Language must be English.
# - Provide 4 options labeled A, B, C, D.
# - Only one correct answer from one of the options.
# - Output MUST be valid JSON.
# - Each item MUST include keys:
#   question, options, correct_answer, explanation, topic_name, source
# - Do not include markdown.
# - Do not include commentary.
# - Base answers ONLY on the provided context.

# Context:
# {context_text}
# """

SYSTEM_PROMPT = """
You are a high-quality exam question generator for Spanish traffic theory.

Rules:
- Generate upto {n} *distinct* multiple-choice questions on *varied topics* from the provided context.
- Avoid generating questions that are very similar in theme.
- Provide 4 options labeled A, B, C, D.
- Only one correct answer from one of the options.
- Output MUST be valid JSON.
- Ignore any context that is not related to traffic law, for example, a website, a copyright claim etc.
- Each question MUST include keys:
  question, options, correct_answer, explanation, topic_name, source
- Use the context below to generate questions across multiple subtopics.


Context:
{context_text}
"""

# ------------------ Helpers ------------------
def retrieve_context(query: str, k: int = MAX_CONTEXT_CHUNKS) -> str:
    extended_query = query
    # print(extended_query)
    results = collection.query(
        query_texts= extended_query,
        n_results=MAX_CONTEXT_CHUNKS,
    )
    # print(results)
    return (results["documents"][0])


def safe_json_load(text: str, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"Failed to load JSON: {text}")
            if attempt == retries:
                continue
            time.sleep(0.5)
    return []

def extract_list(parsed):
    """
    Unwraps common output shapes:
    - {"questions":[...]} -> returns list
    - list[...] -> returns list
    - otherwise -> []
    """
    if isinstance(parsed, dict):
        if "questions" in parsed and isinstance(parsed["questions"], list):
            return parsed["questions"]
        return []
    if isinstance(parsed, list):
        return parsed
    return []


def generate_mcqs(context_text: str, count: int):
    prompt = SYSTEM_PROMPT.format(
        n=count,
        context_text=context_text
    )

    messages = [{"role": "user", "content": prompt}]
    response = llm.chat(messages)
    raw = response.choices[0].message.content.strip()
    # print(f"{raw}\n======================")
    parsed = safe_json_load(raw)
    # print(f"parsed['question'] ================= \n{parsed['questions'][0]['question']}\n======================")
    return extract_list(parsed)


def hash_question(q: str) -> str:
    return hashlib.sha256(q.encode("utf-8")).hexdigest()

def retrieve_context_from_chunk(chunk):
    return chunk

def main():
    chunk_texts = []

    # Retrieve all chunk texts in memory-safe manner
    result = collection.get(include=["documents"])
    for page_chunks in result["documents"]:
        chunk_texts.extend(page_chunks)    
        chunk_texts = ''.join(chunk_texts).strip()
        chunk_texts = chunk_texts.split(" \n\n") #splitting if paragraph is changed
    chunk_texts = ''.join(chunk_texts).split(" \n") #splitting if paragraph is changed
    
    print(f"[INFO] Total chunks found: {len(chunk_texts)}")
    large_bank = []
    seen = set()
    # print(chunk_texts)
    # exit()
    # Load existing bank if it exists
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            large_bank = json.load(f)
            for q in large_bank:
                seen.add(hash_question(q["question"]))
    
    # print(f"====>{chunk_texts[0]}<=====")
    # exit()

    for i, chunk in enumerate(chunk_texts):
        if i % 50 == 0:
            print(f"[PROGRESS] Processing chunk {i}/{len(chunk_texts)}")

        context = retrieve_context(chunk, 5)
        if not context: 
            print(f"  |  Skipping because the context is None")
            print(f"[DEBUG]| [CONTEXT]: {context}")
            continue
        mcqs = generate_mcqs(context, 3)
        # print(f"=================================================\nC:{''.join(context)}")
        print(f"=================================================\nQ:{mcqs}")

        for q in mcqs:
            # Check required fields
            # q_hash = hash_question(q["question"])
            question_text = q.get("question")
            if not question_text:
                continue
            q_hash = hash_question(question_text)
            if q_hash in seen:
                continue
            # if q_hash in seen:
            #     continue
            seen.add(q_hash)
            large_bank.append(q)

        # Save periodically to avoid memory spikes
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(large_bank, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    print(f"[DONE] Generated {len(large_bank)} MCQs")
    print("Saved to:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
