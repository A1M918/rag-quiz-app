from pathlib import Path
import os

from helpers.helper import extract_pages, chunks_for_embeddings, create_vector_store
BASE_DIR = Path(__file__).resolve().parent


def main():
    # Load the PDF file
    PDF_PATH = BASE_DIR / "files" / "pdf" / "SpanishTrafficLaw.pdf"
    print(f"PDF_PATH= {PDF_PATH}")
    create_vector_store(PDF_PATH)


if __name__ == '__main__':
    main()