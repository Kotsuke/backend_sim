import json
import faiss
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from groq import Groq

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class RAGPipeline:
    def __init__(self):
        # ===== EMBEDDING (Tetap Local - Ringan) =====
        self.embedder = SentenceTransformer(
            "all-MiniLM-L6-v2",
            cache_folder=str(BASE_DIR / "models" / "embedding")
        )

        # ===== FAISS + CHUNKS =====
        self.index = faiss.read_index(
            str(BASE_DIR / "data" / "processed" / "faiss.index")
        )

        with open(
            BASE_DIR / "data" / "processed" / "chunks.json",
            "r",
            encoding="utf-8"
        ) as f:
            self.chunks = json.load(f)

        # ===== LLM : GROQ API =====
        # Ambil dari environment variable (aman untuk di-push)
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("⚠️ WARNING: GROQ_API_KEY belum diset di file .env!") 
        self.client = Groq(api_key=api_key)

    # ===== RETRIEVE =====
    def retrieve(self, query, k=3):
        query_vec = self.embedder.encode([query])
        distances, indices = self.index.search(query_vec, k)
        return [self.chunks[i] for i in indices[0]]

    # ===== GENERATE =====
    def generate(self, prompt):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=300,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Maaf, terjadi kesalahan koneksi ke AI: {str(e)}"
