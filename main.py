import os
import faiss
import PyPDF2
import pickle
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from typing import List
import dotenv
dotenv.load_dotenv()
PDF_PATHS = ["data/data1.pdf", "data/data2.pdf", "data/data3.pdf"]  
INDEX_PATH = "faiss_store/index.faiss"
META_PATH = "faiss_store/meta.pkl"
CHUNK_SIZE = 500
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
def load_pdfs_and_chunk(pdf_paths: List[str], chunk_size: int) -> List[str]:
    all_chunks = []
    for path in pdf_paths:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            full_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        for i in range(0, len(full_text), chunk_size):
            chunk = full_text[i:i + chunk_size]
            if len(chunk.strip()) > 50:
                tagged_chunk = f"[{os.path.basename(path)}]\n{chunk.strip()}"
                all_chunks.append(tagged_chunk)
    return all_chunks
def embed_chunks(chunks: List[str], model_name: str):
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks)
    return embeddings
def save_faiss_index(embeddings, chunks, index_path, meta_path):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(chunks, f)
def load_faiss_index(index_path, meta_path):
    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks
def query_with_gemini(query: str, index, chunks, embedding_model):
    model = SentenceTransformer(embedding_model)
    query_embedding = model.encode([query])
    D, I = index.search(query_embedding, k=3)
    matched_chunks = [chunks[i] for i in I[0]]
    print("\nTop Retrieved Chunks:")
    for i, chunk in enumerate(matched_chunks):
        print(f"\n--- Chunk {i + 1} ---\n{chunk[:500]}...") 
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = (
        "Answer the following question using the provided context:\n\n"
        f"Context:\n{matched_chunks[0]}\n\n{matched_chunks[1]}\n\n{matched_chunks[2]}\n\n"
        f"Question: {query}\n\nAnswer:"
    )
    response = model.generate_content(prompt)
    return response.text
if __name__ == "__main__":
    if not os.path.exists(INDEX_PATH):
        print("Creating FAISS index...")
        chunks = load_pdfs_and_chunk(PDF_PATHS, CHUNK_SIZE)  
        embeddings = embed_chunks(chunks, EMBEDDING_MODEL)
        save_faiss_index(embeddings, chunks, INDEX_PATH, META_PATH)
        print("Indexing complete!")
    else:
        print("Loading existing FAISS index...")
    index, chunks = load_faiss_index(INDEX_PATH, META_PATH)
    while True:
        query = input("\nEnter your query (or type 'exit'): ")
        if query.lower() == 'exit':
            break
        answer = query_with_gemini(query, index, chunks, EMBEDDING_MODEL)
        print(f"\nGemini Answer:\n{answer}")