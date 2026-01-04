# config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "0.5"))

# ------------------ Safety parameters ------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))

# ----------------- Quiz Parameters -----------------
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "2"))
MCQS_PER_WINDOW = int(os.getenv("MCQS_PER_WINDOW", "5"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "0.2"))

METADATA = {
    "lang": "en",          # or "es"
    "source": "N332",
    "topic": "Speed",      # one of your 17
    "type": "law_rule"
}

# SYSTEM_PROMPT = """
# You are a high-quality exam question generator for Spanish traffic theory.
# Rules:
# - Generate exactly {n} *distinct* multiple-choice questions language should be English untill explicitly asked for another language.
# - Provide 4 options labeled A, B, C, D.
# - Only one correct answer.
# - Response should be a valid JSON include keys: question, options, correct_answer, explanation, topic_name, source.
# - Use the *context* below.
# - Make questions varied and not trivial duplicates.


# context:
# {context_text}
# """

SYSTEM_PROMPT = """
You are a high-quality exam question generator for Spanish traffic theory.

Rules:
- Generate exactly {n} *distinct* multiple-choice questions on *varied topics* from the context.
- Avoid generating questions that are very similar in theme.
- Provide 4 options labeled A, B, C, D.
- Only one correct answer.
- Output MUST be valid JSON.
- Each question MUST include keys:
  question, options, correct_answer, explanation, topic_name, source
- Use the context below to generate questions across multiple subtopics.

Context:
{context_text}
"""