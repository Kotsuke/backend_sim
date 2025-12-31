from pathlib import Path
from docx import Document
from sentence_transformers import SentenceTransformer
import faiss
import json
import os
from pypdf import PdfReader
import numpy as np

# ========= PATH =========
BASE_DIR = Path(__file__).parent
OUT_DIR = "data/processed"
CHUNK_PATH = f"{OUT_DIR}/chunks.json"
INDEX_PATH = f"{OUT_DIR}/faiss.index"

os.makedirs(OUT_DIR, exist_ok=True)

# ========= LOAD PDF =========
def load_pdf(path):
    reader = PdfReader(path)
    text = ""

    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"

    return text

PDF_PATH = BASE_DIR / "data" / "raw" / "SIM.pdf"
text = load_pdf(PDF_PATH)

# ========= CHUNKING =========
words = text.split()
chunks = []
chunk_size = 400
overlap = 50

for i in range(0, len(words), chunk_size - overlap):
    chunks.append(" ".join(words[i:i + chunk_size]))

# ========= EMBEDDING =========
embedder = SentenceTransformer(
    "all-MiniLM-L6-v2",
    cache_folder="models/embedding"
)

embeddings = embedder.encode(chunks, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

# ========= FAISS =========
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, INDEX_PATH)

with open(CHUNK_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print("✅ Knowledge base berhasil dibuat")
