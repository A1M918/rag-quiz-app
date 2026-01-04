# llm_client.py
# import openai
from openai import OpenAI
from config import (
    OPENAI_API_BASE,
    OPENAI_API_KEY,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

class LLMClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def chat(self, messages):
        return client.chat.completions.create(model=LLM_MODEL,
        messages=messages,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        stream=False,
        timeout=120)

# Global singleton
llm = LLMClient()
