# llm_client.py
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from config import EMBEDDING_MODEL, OPENAI_API_BASE,OPENAI_API_KEY

BASE_DIR = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma"
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


class ChromaClient:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_base=OPENAI_API_BASE,
                api_key=OPENAI_API_KEY,
                model_name=EMBEDDING_MODEL
            )

            cls._client = chromadb.PersistentClient(
                path=str(VECTORSTORE_DIR)
            )

            cls._embedding_fn = embedding_fn

        return cls._instance

    @property
    def client(self):
        return self._client

    def get_collection(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embedding_fn
        )

    def list_collections(self):
        return self._client.list_collections()


# -------- Global singleton --------
chroma = ChromaClient()
