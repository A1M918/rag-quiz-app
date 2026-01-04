import json
import random
from pathlib import Path
from exam.boe_retriever import get_boe_explanation

MCQ_FILE = Path(__file__).resolve().parent.parent / "data" / "mcqs" / "eng_big_mcqs.json"
mcqs = json.loads(MCQ_FILE.read_text(encoding="utf-8"))

def bucket_by_difficulty():
    buckets = {"easy": [], "medium": [], "hard": []}
    for q in mcqs:
        buckets[q.get("difficulty", "medium")].append(q)
    return buckets

def generate_exam(level="medium", n=30):
    buckets = bucket_by_difficulty()

    if level == "easy":
        weights = {"easy": 0.7, "medium": 0.3, "hard": 0.0}
    elif level == "hard":
        weights = {"easy": 0.1, "medium": 0.4, "hard": 0.5}
    else:  # medium
        weights = {"easy": 0.3, "medium": 0.5, "hard": 0.2}

    exam = []
    for diff, w in weights.items():
        count = int(n * w)
        exam.extend(random.sample(buckets[diff], min(count, len(buckets[diff]))))

    while len(exam) < n:
        exam.append(random.choice(mcqs))

    random.shuffle(exam)
    return exam[:n]

def generate_boe_explanation(
    question_text: str,
    user_answer: str,
    correct_answer: str,
) -> str:
    """
    Generate a short, exam-style explanation grounded in BOE law.
    """

    boe_context = retrieve_boe_context(question_text)

    if not boe_context:
        return "According to traffic regulations, the selected answer does not comply with the correct rule."

    prompt = f"""
You are a Spanish driving theory instructor.

Using ONLY the legal reference below, explain why the user's answer is wrong
and what the correct rule is.

Legal reference (BOE):
{boe_context}

Question:
{question_text}

User's answer:
{user_answer}

Correct answer:
{correct_answer}

Rules:
- Write 3 to 5 short sentences
- Do NOT quote legal text verbatim
- Do NOT mention article numbers
- Do NOT include administrative or procedural law
- Explain in clear, exam-oriented language
"""

    response = client.chat.completions.create(
        model="Mistral-7B-Instruct-v0.3-GGUF",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()

def grade_exam(exam, answers):
    score = 0
    results = []

    for q, a in zip(exam, answers):
        correct = q.get("correct_answer")
        if correct is None:
            raise ValueError("Question missing correct answer")

        ok = a == correct

        if ok:
            score += 1
            explanation = ""
        else:
            # Build a richer retrieval query
            retrieval_text = (
                q.get("question_es")
                or f"{q.get('question')} Correct answer: {correct}"
            )

            explanation = get_boe_explanation(retrieval_text)

        results.append({
            "correct": ok,
            "difficulty": q.get("difficulty", "medium"),
            "explanation": explanation
        })

    return score, results


def next_level(score, current):
    if score >= 26:
        return "hard"
    if score <= 18:
        return "easy"
    return "medium"
