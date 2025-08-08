from langchain.tools import StructuredTool
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.embeddings.base import Embeddings
from pydantic import BaseModel, Field
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np

class KnowledgeSearchInput(BaseModel):
    """Input for the knowledge search tool."""
    query: str = Field(description="The search query to find relevant information in the knowledge base")

class SentenceTransformerEmbeddings(Embeddings):
    """Custom embeddings class for sentence-transformers to work with LangChain"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        embedding = self.model.encode([text])
        return embedding[0].tolist()

class RAGTool:
    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self.faiss_index = None
        self.chunks = None
        self.embeddings_model = None
        self._initialize()
        
    def _initialize(self):
        """Initialize the RAG system with embeddings and vector store"""
        try:
            # Initialize embeddings (matching your creation script)
            self.embeddings_model = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
            
            # Correct path - faiss_store is at same level as tools directory
            current_dir = os.path.dirname(os.path.abspath(__file__))  # tools directory
            parent_dir = os.path.dirname(current_dir)  # parent of tools directory
            
            index_path = os.path.join(parent_dir, "faiss_store", "index.faiss")
            meta_path = os.path.join(parent_dir, "faiss_store", "meta.pkl")
            
            print(f"Looking for FAISS index at: {index_path}")
            print(f"Looking for metadata at: {meta_path}")
            
            if os.path.exists(index_path) and os.path.exists(meta_path):
                # Load the FAISS index and chunks directly (matching your creation method)
                self.faiss_index = faiss.read_index(index_path)
                with open(meta_path, "rb") as f:
                    self.chunks = pickle.load(f)
                
                print(f"Successfully loaded FAISS index with {len(self.chunks)} chunks")
                
                # Create LangChain FAISS vectorstore wrapper
                self._create_langchain_vectorstore()
                
            else:
                print(f"FAISS files not found at expected locations")
                self._create_sample_vectorstore()
            
            # Initialize LLM for QA chain
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                temperature=0
            )
            
            # Create QA chain
            if self.vectorstore:
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 3}
                    ),
                    return_source_documents=True
                )
            
        except Exception as e:
            print(f"Error initializing RAG tool: {e}")
            self.vectorstore = None
            self.qa_chain = None
    
    def _create_langchain_vectorstore(self):
        """Create a LangChain FAISS vectorstore from the loaded index and chunks"""
        try:
            from langchain.schema import Document
            from langchain_community.vectorstores.faiss import FAISS
            
            # Convert chunks to LangChain documents
            documents = []
            for i, chunk in enumerate(self.chunks):
                # Extract source from chunk if tagged
                if chunk.startswith('[') and ']\n' in chunk:
                    source_end = chunk.find(']\n')
                    source = chunk[1:source_end]
                    content = chunk[source_end + 2:]
                else:
                    source = "Agricultural Knowledge Base"
                    content = chunk
                
                doc = Document(
                    page_content=content,
                    metadata={"source": source, "chunk_id": i}
                )
                documents.append(doc)
            
            # Create embeddings for documents
            embeddings = self.embeddings_model.embed_documents([doc.page_content for doc in documents])
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Create FAISS vectorstore
            self.vectorstore = FAISS.from_embeddings(
                text_embeddings=list(zip([doc.page_content for doc in documents], embeddings)),
                embedding=self.embeddings_model,
                metadatas=[doc.metadata for doc in documents]
            )
            
            print("Successfully created LangChain FAISS vectorstore wrapper")
            
        except Exception as e:
            print(f"Error creating LangChain vectorstore: {e}")
            self._create_sample_vectorstore()
    
    def _create_sample_vectorstore(self):
        """Create a sample vectorstore as fallback"""
        from langchain.schema import Document
        from langchain_community.vectorstores import FAISS
        
        sample_docs = [
            Document(
                page_content="PM Kisan Yojana provides financial assistance of ₹6000 per year to eligible farmer families in three installments of ₹2000 each.",
                metadata={"source": "PM_Kisan_Scheme", "topic": "government_schemes"}
            ),
            Document(
                page_content="Organic farming practices include crop rotation, use of compost, biological pest control, and avoiding synthetic fertilizers and pesticides.",
                metadata={"source": "Organic_Farming_Guide", "topic": "farming_practices"}
            ),
            Document(
                page_content="Integrated Pest Management (IPM) combines biological, cultural, physical and chemical tools to manage pests effectively while minimizing environmental impact.",
                metadata={"source": "IPM_Guide", "topic": "pest_management"}
            )
        ]
        
        self.vectorstore = FAISS.from_documents(sample_docs, self.embeddings_model)
        print("Created sample vectorstore with basic agricultural information.")
    
    def search_knowledge_base(self, query: str) -> str:
        """Search the knowledge base and return relevant information"""
        if not self.qa_chain:
            return "Knowledge search system not properly initialized. Please check configuration and ensure Google API key is set."
        
        try:
            # Use LangChain QA chain for consistent response
            result = self.qa_chain.invoke({"query": query})
            answer = result["result"]
            
            # Format sources information
            if "source_documents" in result and result["source_documents"]:
                sources_info = []
                seen_sources = set()
                
                for doc in result["source_documents"][:3]:
                    source = doc.metadata.get("source", "Knowledge Base")
                    if source not in seen_sources:
                        sources_info.append(source)
                        seen_sources.add(source)
                
                if sources_info:
                    answer += f"\n\n📚 Sources: {', '.join(sources_info)}"
            
            return answer
            
        except Exception as e:
            # Fallback to direct FAISS search if LangChain fails
            if self.faiss_index and self.chunks:
                return self._direct_search(query)
            else:
                return f"Error searching knowledge base: {str(e)}. Please ensure your Google API key is properly configured."
    
    def _direct_search(self, query: str) -> str:
        """Direct search using the original FAISS index (fallback method)"""
        try:
            from sentence_transformers import SentenceTransformer
            import google.generativeai as genai
            
            # Get query embedding
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            query_embedding = model.encode([query])
            
            # Search FAISS index
            D, I = self.faiss_index.search(query_embedding, k=3)
            matched_chunks = [self.chunks[i] for i in I[0]]
            
            # Generate response with Gemini
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            genai_model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            prompt = (
                "Answer the following question using the provided context from agricultural documents:\n\n"
                f"Context:\n{matched_chunks[0]}\n\n{matched_chunks[1]}\n\n{matched_chunks[2]}\n\n"
                f"Question: {query}\n\n"
                "Please provide a comprehensive answer based on the context provided."
            )
            
            response = genai_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"Error in direct search: {str(e)}"

# Create the tool instance
rag_instance = RAGTool()

# Define the LangChain tool using StructuredTool
rag_tool = StructuredTool(
    name="knowledge_search",
    description="Search the agricultural knowledge base for information about farming practices, crop management, government schemes like PM Kisan Yojana, fertilizers, pest control, soil management, irrigation, and other agricultural topics. This tool has access to comprehensive agricultural PDF documents and provides expert guidance.",
    func=rag_instance.search_knowledge_base,
    args_schema=KnowledgeSearchInput
)