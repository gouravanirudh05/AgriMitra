import json
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

def build_vectorstore(chunk_path):
    with open(chunk_path) as f:
        chunks = json.load(f)

    docs = [
        Document(page_content=chunk['content'], metadata=chunk['metadata'])
        for chunk in chunks
    ]

    embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    vectorstore = FAISS.from_documents(docs, embed_model)
    vectorstore.save_local("kcc_faiss_index")

if __name__ == "__main__":
    build_vectorstore("chunked.json")
