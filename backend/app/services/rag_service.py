import os
import faiss
import pickle
import google.generativeai as genai
from typing import List
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_PATH = "faiss_store/index.faiss"
META_PATH = "faiss_store/meta.pkl"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class RAGService:
    def __init__(self):
        self.index, self.chunks = self.load_faiss_index()
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        genai.configure(api_key=GOOGLE_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    def load_faiss_index(self):
        if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
            raise FileNotFoundError("FAISS index or metadata not found. Please generate it first.")
        index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            chunks = pickle.load(f)
        return index, chunks

    def retrieve_relevant_chunks(self, query: str, k: int = 10) -> List[str]:
        query_embedding = self.embedding_model.encode([query])
        D, I = self.index.search(query_embedding, k)
        return [self.chunks[i] for i in I[0]]

    def generate_response(self, query: str, context_chunks: List[str]) -> str:
        prompt = (
            "Answer the following farming-related question using the provided context:\n\n"
            f"Context:\n{context_chunks[0]}\n\n{context_chunks[1]}\n\n{context_chunks[2]}\n\n"
            f"Question: {query}\n\nAnswer:"
        )
        response = self.gemini_model.generate_content(prompt)
        return response.text

