import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import json
import pickle
from datetime import datetime

# Translation and NLP imports
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
import faiss

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicTranslator:
    """Handles translation using IndicTrans2 models"""
    
    def __init__(self, model_path: str = "ai4bharat/indictrans2-indic-en-1B", device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.processor = None
        
    def initialize_model(self):
        """Initialize the translation model and tokenizer"""
        try:
            from IndicTransToolkit.processor import IndicProcessor
            
            logger.info(f"Loading IndicTrans2 model: {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            
            if self.device == "cuda":
                self.model = self.model.to(self.device).half()
            else:
                self.model = self.model.to(self.device)
                
            self.model.eval()
            self.processor = IndicProcessor(inference=True)
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def translate_batch(self, texts: List[str], src_lang: str = "hin_Deva", 
                       tgt_lang: str = "eng_Latn", batch_size: int = 4) -> List[str]:
        """Translate a batch of texts"""
        if not self.model or not self.tokenizer:
            self.initialize_model()
            
        translations = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Preprocess the batch
            batch = self.processor.preprocess_batch(batch, src_lang=src_lang, tgt_lang=tgt_lang)
            
            # Tokenize
            inputs = self.tokenizer(
                batch,
                truncation=True,
                padding="longest",
                return_tensors="pt",
                return_attention_mask=True,
            ).to(self.device)
            
            # Generate translations
            with torch.no_grad():
                generated_tokens = self.model.generate(
                    **inputs,
                    use_cache=False,
                    min_length=0,
                    max_length=256,
                    num_beams=5,
                    num_return_sequences=1,
                )
            
            # Decode translations
            generated_tokens = self.tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
            
            # Postprocess
            batch_translations = self.processor.postprocess_batch(generated_tokens, lang=tgt_lang)
            translations.extend(batch_translations)
            
            # Clear memory
            del inputs
            if self.device == "cuda":
                torch.cuda.empty_cache()
        
        return translations

class FAISSVectorStore:
    """Handles FAISS vector store operations"""
    
    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.index = None
        self.documents = []
        self.metadata = []
        
    def initialize_embeddings(self):
        """Initialize the sentence transformer model"""
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts"""
        if not self.embedding_model:
            self.initialize_embeddings()
            
        logger.info(f"Creating embeddings for {len(texts)} texts")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.astype('float32')
    
    def build_index(self, embeddings: np.ndarray):
        """Build FAISS index from embeddings"""
        dimension = embeddings.shape[1]
        logger.info(f"Building FAISS index with dimension: {dimension}")
        
        # Use IndexFlatIP for cosine similarity
        self.index = faiss.IndexFlatIP(dimension)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        logger.info(f"FAISS index built with {self.index.ntotal} vectors")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[float, Dict]]:
        """Search for similar documents"""
        if not self.index or not self.embedding_model:
            raise ValueError("Index not built or embedding model not initialized")
            
        # Create query embedding
        query_embedding = self.embedding_model.encode([query]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata):
                results.append((float(score), self.metadata[idx]))
        
        return results
    
    def save(self, filepath: str):
        """Save FAISS index and metadata"""
        # Save FAISS index
        faiss.write_index(self.index, f"{filepath}.index")
        
        # Save metadata
        with open(f"{filepath}.metadata", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata,
                'embedding_model': self.embedding_model_name
            }, f)
        
        logger.info(f"FAISS index and metadata saved to {filepath}")
    
    def load(self, filepath: str):
        """Load FAISS index and metadata"""
        # Load FAISS index
        self.index = faiss.read_index(f"{filepath}.index")
        
        # Load metadata
        with open(f"{filepath}.metadata", 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.metadata = data['metadata']
            self.embedding_model_name = data['embedding_model']
            
        # Reinitialize embedding model
        self.initialize_embeddings()
        
        logger.info(f"FAISS index and metadata loaded from {filepath}")

class AgriculturalETLPipeline:
    """Main ETL Pipeline for agricultural query data"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.translator = IndicTranslator()
        self.vector_store = FAISSVectorStore()
        self.processed_data = None
        
    def extract(self, csv_path: str) -> pd.DataFrame:
        """Extract data from CSV file"""
        logger.info(f"Extracting data from {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if pd.isna(text):
            return ""
        
        # Basic cleaning
        text = str(text).strip()
        text = ' '.join(text.split())  # Remove extra whitespaces
        
        return text
    
    def transform(self, df: pd.DataFrame) -> List[Dict]:
        """Transform the data - clean and translate"""
        logger.info("Starting transformation process")
        
        # Clean the data
        df_clean = df.copy()
        df_clean['QueryText'] = df_clean['QueryText'].apply(self.clean_text)
        df_clean['KccAns'] = df_clean['KccAns'].apply(self.clean_text)
        
        # Remove rows with empty query or answer
        df_clean = df_clean[(df_clean['QueryText'] != "") & (df_clean['KccAns'] != "")]
        
        logger.info(f"After cleaning: {len(df_clean)} records remaining")
        
        # Prepare texts for translation
        query_texts = df_clean['QueryText'].tolist()
        answer_texts = df_clean['KccAns'].tolist()
        
        # Translate queries and answers
        logger.info("Translating queries...")
        translated_queries = self.translator.translate_batch(query_texts, src_lang="hin_Deva")
        
        logger.info("Translating answers...")
        translated_answers = self.translator.translate_batch(answer_texts, src_lang="hin_Deva")
        
        # Create processed documents
        processed_docs = []
        for i, row in df_clean.iterrows():
            doc = {
                'id': i,
                'original_query': row['QueryText'],
                'original_answer': row['KccAns'],
                'translated_query': translated_queries[i] if i < len(translated_queries) else "",
                'translated_answer': translated_answers[i] if i < len(translated_answers) else "",
                'state': row.get('StateName', ''),
                'district': row.get('DistrictName', ''),
                'block': row.get('BlockName', ''),
                'sector': row.get('Sector', ''),
                'category': row.get('Category', ''),
                'crop': row.get('Crop', ''),
                'query_type': row.get('QueryType', ''),
                'season': row.get('Season', ''),
                'created_on': row.get('CreatedOn', ''),
                'year': row.get('year', ''),
                'month': row.get('month', '')
            }
            processed_docs.append(doc)
        
        logger.info(f"Transformation completed: {len(processed_docs)} documents processed")
        return processed_docs
    
    def load(self, processed_docs: List[Dict], index_path: str):
        """Load data into FAISS vector store"""
        logger.info("Loading data into FAISS vector store")
        
        # Prepare documents for embedding
        # Combine query and answer for better semantic search
        documents = []
        metadata = []
        
        for doc in processed_docs:
            # Create searchable text combining query and context
            searchable_text = f"Query: {doc['translated_query']} Answer: {doc['translated_answer']}"
            documents.append(searchable_text)
            metadata.append(doc)
        
        # Store documents and metadata
        self.vector_store.documents = documents
        self.vector_store.metadata = metadata
        
        # Create embeddings
        embeddings = self.vector_store.create_embeddings(documents)
        
        # Build FAISS index
        self.vector_store.build_index(embeddings)
        
        # Save to disk
        self.vector_store.save(index_path)
        
        logger.info("Data loading completed")
    
    def run_pipeline(self, csv_path: str, output_path: str = "agricultural_qa_index"):
        """Run the complete ETL pipeline"""
        logger.info("Starting ETL Pipeline")
        
        try:
            # Extract
            df = self.extract(csv_path)
            
            # Transform
            processed_docs = self.transform(df)
            self.processed_data = processed_docs
            
            # Load
            self.load(processed_docs, output_path)
            
            logger.info("ETL Pipeline completed successfully")
            
            return {
                'status': 'success',
                'records_processed': len(processed_docs),
                'output_path': output_path
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def query_system(self, query: str, k: int = 5) -> List[Dict]:
        """Query the built system"""
        if not self.vector_store.index:
            raise ValueError("Vector store not built. Run pipeline first or load existing index.")
        
        results = self.vector_store.search(query, k)
        
        formatted_results = []
        for score, metadata in results:
            formatted_results.append({
                'score': score,
                'query': metadata['translated_query'],
                'answer': metadata['translated_answer'],
                'original_query': metadata['original_query'],
                'original_answer': metadata['original_answer'],
                'location': f"{metadata['district']}, {metadata['state']}",
                'crop': metadata['crop'],
                'category': metadata['category'],
                'query_type': metadata['query_type']
            })
        
        return formatted_results

# Usage example and utility functions
def main():
    """Main function to run the pipeline"""
    
    # Configuration
    config = {
        'batch_size': 4,
        'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2',
        'translation_model': 'ai4bharat/indictrans2-indic-en-1B'
    }
    
    # Initialize pipeline
    pipeline = AgriculturalETLPipeline(config)
    
    # Run pipeline
    result = pipeline.run_pipeline('few.csv', 'agricultural_qa_index')
    
    print(f"Pipeline result: {result}")
    
    # Example queries
    if result['status'] == 'success':
        sample_queries = [
            "How to control pests in wheat crop?",
            "What fertilizer should I use for potato?",
            "Weather information for farming",
            "Government schemes for farmers",
            "Mango tree diseases"
        ]
        
        print("\nSample Query Results:")
        for query in sample_queries:
            print(f"\nQuery: {query}")
            results = pipeline.query_system(query, k=3)
            
            for i, result in enumerate(results, 1):
                print(f"Result {i} (Score: {result['score']:.3f}):")
                print(f"  Q: {result['query'][:100]}...")
                print(f"  A: {result['answer'][:100]}...")
                print(f"  Location: {result['location']}")
                print(f"  Crop: {result['crop']}")

if __name__ == "__main__":
    main()