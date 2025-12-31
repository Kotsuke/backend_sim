import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama

BASE_DIR = Path(__file__).resolve().parent.parent


class RAGPipeline:
    def __init__(self):
        # ===== EMBEDDING =====
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

        # ===== LLM : MISTRAL =====
        self.llm = Llama(
            model_path=str(
                BASE_DIR / "models" / "llm" / "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
            ),
            n_ctx=4096,
            n_threads=8,
            verbose=False
        )

    # ===== RETRIEVE =====
    def retrieve(self, query, k=3):
        query_vec = self.embedder.encode([query])
        distances, indices = self.index.search(query_vec, k)
        return [self.chunks[i] for i in indices[0]]

    # ===== GENERATE =====
    def generate(self, prompt):
        output = self.llm(
            prompt,
            max_tokens=200,
            temperature=0.2,
            top_p=0.9,
            repeat_penalty=1.1
        )

        text = output["choices"][0]["text"].strip()
        if not text:
            return "Maaf, sistem tidak menghasilkan jawaban."
        return text
