from pathlib import Path
import json
import sys
import time
import hashlib

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from clients.chroma_client import chroma
from clients.llm_client import llm
from config import MCQS_PER_WINDOW

OUTPUT_FILE = BASE_DIR / "data" / "mcqs" / "large_mcq_bank.json"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = """
You are a high-quality exam question generator for Spanish traffic theory.

Rules:
- Generate exactly {n} distinct multiple-choice questions.
- Provide 4 options labeled A, B, C, D.
- Only one correct answer.
- Output MUST be valid JSON.
- Each item MUST include keys:
  question, options, correct_answer, explanation, topic_name, source.

Return a JSON object with the key "questions" whose value is the list of questions.

Context:
{context_text}
"""

def safe_load_json(text: str):
    """
    Safely parse JSON — returns [] on failure.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
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

def generate_mcqs(context, count):
    prompt = SYSTEM_PROMPT.format(n=count, context_text=context)
    messages = [{"role":"user", "content": prompt}]
    rsp = llm.chat(messages)
    raw = rsp.choices[0].message.content.strip()
    parsed = safe_load_json(raw)
    return extract_list(parsed)

def hash_question(question_text: str) -> str:
    """
    Consistent hash for deduplication.
    """
    return hashlib.sha256(question_text.encode("utf-8")).hexdigest()

def main():
    collection = chroma.get_collection("pdf_docs")

    # Load all chunk texts safely
    result = collection.get(include=["documents"])
    chunk_texts = []
    for page_chunks in result["documents"]:
        chunk_texts.extend(page_chunks)

    print(f"[INFO] Total chunks found: {len(chunk_texts)}")

    large_bank = []
    seen = set()

    # Load existing bank if it exists
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            large_bank = json.load(f)
            for q in large_bank:
                seen.add(hash_question(q["question"]))

    for i, chunk in enumerate(chunk_texts):
        if i % 50 == 0:
            print(f"[PROGRESS] Processing chunk {i}/{len(chunk_texts)}")

        mcqs = generate_mcqs(chunk, MCQS_PER_WINDOW * 2)

        for q in mcqs:
            # Check required fields
            question_text = q.get("question")
            if not question_text:
                continue

            q_hash = hash_question(question_text)
            if q_hash in seen:
                continue

            seen.add(q_hash)
            large_bank.append(q)

        # Save periodically to avoid memory spikes
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(large_bank, f, ensure_ascii=False, indent=2)

        time.sleep(1.5)

    print(f"[DONE] Generated {len(large_bank)} MCQs")
    print("Saved to:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
