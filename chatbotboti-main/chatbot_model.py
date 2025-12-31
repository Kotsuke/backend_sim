from rag.rag_pipeline import RAGPipeline


class SIMChatbot:
    def __init__(self):
        self.rag = RAGPipeline()

    def chat(self, question):
        contexts = self.rag.retrieve(question, k=3)

        if not contexts:
            return "Maaf, data SIM belum tersedia."

        context_text = "\n".join(contexts)

        prompt = f"""
Kamu adalah asisten AI untuk aplikasi Smart Infrastructure Monitoring System (SIM).

Gunakan konteks berikut untuk menjawab pertanyaan secara singkat,
jelas, dan bersifat akademik.

Konteks:
{context_text}

Pertanyaan:
{question}

Jawaban:
"""

        return self.rag.generate(prompt)


# ===== CLI =====
if __name__ == "__main__":
    bot = SIMChatbot()
    print("✅ SIM Chatbot siap. Ketik 'exit' untuk keluar.\n")

    while True:
        q = input("Kamu: ")
        if q.lower() in ["exit", "quit"]:
            break

        answer = bot.chat(q)
        print("\nBot:", answer, "\n")
