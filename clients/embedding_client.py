# embedding_client.py
import openai
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)
from config import OPENAI_API_BASE, OPENAI_API_KEY, EMBEDDING_MODEL

# TODO: The 'openai.api_base' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(base_url=OPENAI_API_BASE)'
# openai.api_base = OPENAI_API_BASE

class EmbeddingClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def embed(self, texts: list[str]) -> list[list[float]]:
        rsp = client.embeddings.create(model=EMBEDDING_MODEL,
        input=texts)
        return [d["embedding"] for d in rsp.data]

embeddings = EmbeddingClient()
