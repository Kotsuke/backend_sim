import json
import faiss
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from groq import Groq

BASE_DIR = Path(__file__).resolve().parent.parent


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
        # Pastikan API KEY sudah diset di environment variable atau hardcode sementara
        api_key = os.environ.get("GROQ_API_KEY", "gsk_...") 
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
                model="llama3-8b-8192",
                temperature=0.5,
                max_tokens=300,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Maaf, terjadi kesalahan koneksi ke AI: {str(e)}"
