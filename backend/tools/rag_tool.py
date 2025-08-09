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
import logging

logger = logging.getLogger(__name__)

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

class EnhancedRAGTool:
    """Enhanced RAG tool with better error handling and fallback responses"""
    
    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self.faiss_index = None
        self.chunks = None
        self.embeddings_model = None
        self.llm = None
        self.is_initialized = False
        self._initialize()
        
    def _initialize(self):
        """Initialize the RAG system with embeddings and vector store"""
        try:
            logger.info("Initializing Enhanced RAG Tool...")
            
            # Initialize embeddings (matching your creation script)
            self.embeddings_model = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
            
            # Initialize LLM early for fallback purposes
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                temperature=0.1,
                convert_system_message_to_human=True,
                safety_settings={
                    7: 0, 8: 0, 9: 0, 10: 0
                }
            )
            
            # Correct path - faiss_store is at same level as tools directory
            current_dir = os.path.dirname(os.path.abspath(__file__))  # tools directory
            parent_dir = os.path.dirname(current_dir)  # parent of tools directory
            
            index_path = os.path.join(parent_dir, "faiss_store", "index.faiss")
            meta_path = os.path.join(parent_dir, "faiss_store", "meta.pkl")
            
            logger.info(f"Looking for FAISS index at: {index_path}")
            logger.info(f"Looking for metadata at: {meta_path}")
            
            if os.path.exists(index_path) and os.path.exists(meta_path):
                # Load the FAISS index and chunks directly
                self.faiss_index = faiss.read_index(index_path)
                with open(meta_path, "rb") as f:
                    self.chunks = pickle.load(f)
                
                logger.info(f"Successfully loaded FAISS index with {len(self.chunks)} chunks")
                
                # Create LangChain FAISS vectorstore wrapper
                self._create_langchain_vectorstore()
                
            else:
                logger.warning(f"FAISS files not found at expected locations")
                self._create_sample_vectorstore()
            
            # Create QA chain if vectorstore is available
            if self.vectorstore:
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 4}  # Increased for better coverage
                    ),
                    return_source_documents=True
                )
                self.is_initialized = True
                logger.info("RAG Tool initialized successfully with QA chain")
            else:
                logger.warning("RAG Tool initialized without QA chain (vectorstore unavailable)")
            
        except Exception as e:
            logger.error(f"Error initializing RAG tool: {e}")
            self.vectorstore = None
            self.qa_chain = None
            # Still mark as initialized so we can use LLM fallback
            self.is_initialized = True
    
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
            
            # Create FAISS vectorstore
            self.vectorstore = FAISS.from_embeddings(
                text_embeddings=list(zip([doc.page_content for doc in documents], embeddings)),
                embedding=self.embeddings_model,
                metadatas=[doc.metadata for doc in documents]
            )
            
            logger.info("Successfully created LangChain FAISS vectorstore wrapper")
            
        except Exception as e:
            logger.error(f"Error creating LangChain vectorstore: {e}")
            self._create_sample_vectorstore()
    
    def _create_sample_vectorstore(self):
        """Create a comprehensive sample vectorstore as fallback"""
        try:
            from langchain.schema import Document
            from langchain_community.vectorstores import FAISS
            
            sample_docs = [
                Document(
                    page_content="PM Kisan Yojana (Pradhan Mantri Kisan Samman Nidhi) provides direct income support of ₹6000 per year to eligible farmer families in three equal installments of ₹2000 each. Eligible farmers are those who own cultivable land. The scheme was launched in 2019 to supplement financial needs of farmers and ensure proper crop health and production. Benefits are transferred directly to bank accounts through Direct Benefit Transfer (DBT).",
                    metadata={"source": "PM_Kisan_Scheme", "topic": "government_schemes"}
                ),
                Document(
                    page_content="Pradhan Mantri Fasal Bima Yojana (PMFBY) is a comprehensive crop insurance scheme providing financial support to farmers in case of crop loss due to natural calamities, pests, and diseases. The scheme covers all food crops, oilseeds, and annual commercial crops. Premium rates are: 2% for Kharif crops, 1.5% for Rabi crops, and 5% for annual commercial and horticultural crops. The government subsidizes the remaining premium.",
                    metadata={"source": "PMFBY_Scheme", "topic": "crop_insurance"}
                ),
                Document(
                    page_content="Organic farming is a method of crop production that involves the use of biological fertilizers and pest control agents. Key practices include: crop rotation with leguminous crops, use of organic manure (FYM, compost, vermicompost), biological pest control using beneficial insects and microorganisms, avoiding synthetic fertilizers and pesticides, maintaining soil health through cover crops and green manures. Benefits include improved soil fertility, reduced environmental pollution, and higher market prices for organic produce.",
                    metadata={"source": "Organic_Farming_Guide", "topic": "farming_practices"}
                ),
                Document(
                    page_content="Integrated Pest Management (IPM) is a sustainable approach combining biological, cultural, physical and chemical tools to manage pests effectively. Components include: monitoring pest populations, identifying beneficial insects, using pheromone traps, implementing cultural practices like crop rotation and intercropping, applying biological control agents like Trichoderma and Pseudomonas, using chemical pesticides only as last resort. IPM reduces pesticide resistance, protects beneficial organisms, and maintains ecological balance.",
                    metadata={"source": "IPM_Guide", "topic": "pest_management"}
                ),
                Document(
                    page_content="Soil Health Card Scheme provides soil health information to farmers including nutrient status and recommendations for appropriate dosage of nutrients for improving soil health. The card contains information about 12 parameters: N, P, K (macro-nutrients), S (secondary nutrient), Zn, Fe, Cu, Mn, B (micro-nutrients), and pH, EC, OC (physical parameters). Based on soil analysis, the card recommends fertilizer doses and soil amendments required for different crops.",
                    metadata={"source": "Soil_Health_Card", "topic": "soil_management"}
                ),
                Document(
                    page_content="Drip irrigation is an efficient water management system that delivers water directly to plant roots through a network of valves, pipes, tubing, and emitters. Benefits include 30-50% water savings, reduced weed growth, lower labor costs, and improved crop yields. System components include water source, pump unit, filter, pressure regulator, main line, sub-main line, laterals, and drippers. Suitable for row crops, orchards, and vegetables. Initial investment is higher but operational costs are lower.",
                    metadata={"source": "Irrigation_Guide", "topic": "irrigation"}
                ),
                Document(
                    page_content="Crop rotation is the practice of growing different crops in succession on the same land to maintain soil fertility and break pest cycles. Benefits include improved soil structure, nutrient management, disease and pest control, and increased biodiversity. Common rotations: Rice-Wheat-Legume, Cotton-Wheat-Sugarcane, Maize-Mustard-Fodder crops. Leguminous crops like groundnut, soybean, and pulses fix nitrogen and improve soil fertility for subsequent crops.",
                    metadata={"source": "Crop_Rotation_Guide", "topic": "crop_management"}
                )
            ]
            
            self.vectorstore = FAISS.from_documents(sample_docs, self.embeddings_model)
            
            # Also create QA chain with sample vectorstore
            if self.llm:
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={"k": 3}
                    ),
                    return_source_documents=True
                )
            
            logger.info("Created sample vectorstore with comprehensive agricultural information.")
            
        except Exception as e:
            logger.error(f"Error creating sample vectorstore: {e}")
            self.vectorstore = None
    
    def search_knowledge_base(self, query: str) -> str:
        """Enhanced knowledge base search with comprehensive fallback"""
        try:
            logger.info(f"Searching knowledge base for: {query[:100]}...")
            
            # First attempt: Use LangChain QA chain if available
            if self.qa_chain:
                try:
                    result = self.qa_chain.invoke({"query": query})
                    answer = result.get("result", "")
                    
                    if answer and len(answer.strip()) > 50:
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
                                answer += f"\n\nSources: {', '.join(sources_info)}"
                        
                        logger.info("Successfully retrieved answer from QA chain")
                        return answer
                    else:
                        logger.warning("QA chain returned insufficient answer, trying direct search")
                        
                except Exception as e:
                    logger.error(f"QA chain failed: {e}")
            
            # Second attempt: Direct FAISS search
            if self.faiss_index and self.chunks:
                try:
                    return self._direct_search(query)
                except Exception as e:
                    logger.error(f"Direct search failed: {e}")
            
            # Third attempt: Pure LLM response if everything else fails
            if self.llm:
                logger.info("Using pure LLM fallback response")
                return self._generate_llm_response(query)
            
            # Final fallback
            return "I apologize, but I'm unable to search the knowledge base at the moment due to technical issues. Please try again later or consult with local agricultural experts."
            
        except Exception as e:
            logger.error(f"Critical error in knowledge search: {e}")
            return f"I encountered an error while searching for information about '{query}'. Please try rephrasing your question or contact technical support."
    
    def _direct_search(self, query: str) -> str:
        """Direct search using the original FAISS index"""
        try:
            logger.info("Performing direct FAISS search")
            
            # Get query embedding
            query_embedding = self.embeddings_model.embed_query(query)
            query_embedding = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index
            D, I = self.faiss_index.search(query_embedding, k=4)
            matched_chunks = [self.chunks[i] for i in I[0] if i < len(self.chunks)]
            
            if not matched_chunks:
                return self._generate_llm_response(query)
            
            # Generate response using matched chunks
            context = "\n\n".join(matched_chunks[:3])
            
            prompt = f"""You are an expert agricultural advisor. Answer the following question using the provided context from agricultural documents.

Context from knowledge base:
{context}

Question: {query}

Please provide a comprehensive, practical answer based on the context provided. If the context doesn't fully address the question, use your agricultural expertise to provide additional relevant information. Structure your response clearly and make it actionable for farmers.

Do not include emojis in your response."""
            
            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error in direct search: {e}")
            return self._generate_llm_response(query)
    
    def _generate_llm_response(self, query: str) -> str:
        """Generate response using only LLM knowledge"""
        try:
            prompt = f"""You are an expert agricultural advisor with comprehensive knowledge about Indian agriculture, farming practices, government schemes, and rural development.

User Question: "{query}"

Please provide a detailed, practical answer to this agricultural question. Include:
1. Direct answer to the question
2. Practical implementation steps if applicable
3. Important considerations or precautions
4. Relevant government schemes or support if applicable
5. Best practices and recommendations

Focus on being helpful, accurate, and practical. Structure your response clearly for easy understanding.

Do not include emojis in your response."""
            
            response = self.llm.invoke(prompt)
            return f"Based on agricultural expertise:\n\n{response.content.strip()}"
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return f"I understand you're asking about {query}. While I'm experiencing technical difficulties, I recommend consulting with local agricultural extension officers or visiting the nearest Krishi Vigyan Kendra (KVK) for detailed guidance on this topic."

# Create the enhanced tool instance
rag_instance = EnhancedRAGTool()

# Define the LangChain tool using StructuredTool
rag_tool = StructuredTool(
    name="knowledge_search",
    description="Search the agricultural knowledge base for comprehensive information about farming practices, crop management, government schemes (PM Kisan, PMFBY, Soil Health Card), fertilizers, pest control, organic farming, soil management, irrigation techniques, and other agricultural topics. This tool provides expert agricultural guidance with intelligent fallback responses when specific information isn't found in the database.",
    func=rag_instance.search_knowledge_base,
    args_schema=KnowledgeSearchInput
)