import httpx
import json
from clients.llm_client import llm
from config import LLM_MODEL, OPENAI_API_BASE
from httpx_sse import connect_sse
LOCALAI_URL = f"{OPENAI_API_BASE}/chat/completions"

def stream_localai_chat():
    body = {
        "model": LLM_MODEL,  # your LocalAI model
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me a joke about Python."}
        ],
        "stream": True
    }

    # Use httpx.Client as normal
    with httpx.Client(timeout=None) as client:
        # Connect via SSE; LocalAI uses POST with streaming
        with connect_sse(client, "POST", LOCALAI_URL, json=body) as event_source:
            print("Streaming from LocalAI:")

            # Iterate events until stream ends
            for event in event_source.iter_sse():
                if event.data is None:
                    continue

                data = event.data.strip()
                # LocalAI might send “[DONE]” at the end
                if data == "[DONE]":
                    print("\n<< STREAM COMPLETE >>")
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    print("Unparseable chunk:", data)
                    continue

                # Print incremental text
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta", {})
                    text = delta.get("content")
                    if text:
                        print(text, end="", flush=True)

            print("\nStream closed.")

if __name__ == "__main__":
    stream_localai_chat()
