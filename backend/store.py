import os
import faiss
import pickle
import pandas as pd
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from typing import List
import dotenv
import fitz  # PyMuPDF - correct import
import docx
from pathlib import Path
import json

dotenv.load_dotenv()

INDEX_PATH = "faiss_store/index.faiss"
META_PATH = "faiss_store/meta.pkl"
CHUNK_SIZE = 500
OVERLAP_SIZE = 50
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"  # Better than all-MiniLM-L6-v2
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.pdf': 'pdf',
    '.csv': 'csv', 
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.txt': 'text',
    '.docx': 'docx',
    '.json': 'json',
    '.xlsx': 'excel',
    '.xls': 'excel'
}

def find_files_in_folder(folder_path: str, recursive: bool = True) -> List[str]:
    """Find all supported files in folder recursively"""
    file_paths = []
    if recursive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_ext = Path(file).suffix.lower()
                if file_ext in SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    file_type = SUPPORTED_EXTENSIONS[file_ext]
                    print(f"Found {file_type.upper()}: {full_path}")
                    file_paths.append(full_path)
    else:
        for file in os.listdir(folder_path):
            file_ext = Path(file).suffix.lower()
            if file_ext in SUPPORTED_EXTENSIONS:
                file_paths.append(os.path.join(folder_path, file))
    return file_paths

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz)"""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def extract_text_from_file(file_path: str) -> str:
    """Extract text from any supported file format"""
    file_ext = Path(file_path).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            return extract_text_from_pdf(file_path)
        
        elif file_ext == '.csv':
            try:
                # Try with different encodings if needed
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin-1')
            
            text = f"CSV File: {os.path.basename(file_path)}\n"
            text += f"Total Rows: {len(df)}\n"
            text += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            text += "Sample Data:\n"
            text += df.head(10).to_string(index=False)
            
            if len(df) > 10:
                text += f"\n\n... and {len(df) - 10} more rows"
            
            # Add statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if not numeric_cols.empty:
                text += "\n\nNumeric Column Statistics:\n"
                text += df[numeric_cols].describe().to_string()
            
            # Add unique values for categorical columns (if reasonable number)
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                unique_vals = df[col].nunique()
                if unique_vals <= 20:  # Only show if reasonable number
                    text += f"\n\nUnique values in {col}:\n"
                    text += ", ".join(df[col].unique().astype(str))
            
            return text
        
        elif file_ext in ['.xlsx', '.xls']:
            excel_file = pd.ExcelFile(file_path)
            text = f"Excel File: {os.path.basename(file_path)}\n"
            text += f"Sheets: {', '.join(excel_file.sheet_names)}\n\n"
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                text += f"Sheet: {sheet_name}\n"
                text += f"Rows: {len(df)}, Columns: {len(df.columns)}\n"
                text += f"Column Names: {', '.join(df.columns.tolist())}\n"
                text += "Sample Data:\n"
                text += df.head(5).to_string(index=False)
                text += "\n\n"
            return text
        
        elif file_ext in ['.md', '.markdown', '.txt']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
        
        elif file_ext == '.docx':
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return json.dumps(data, indent=2, ensure_ascii=False)
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def create_chunks_with_overlap(text: str, chunk_size: int, overlap_size: int) -> List[str]:
    """Create overlapping chunks from text"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if len(chunk.strip()) > 50:  # Only add meaningful chunks
            chunks.append(chunk.strip())
        
        start = end - overlap_size
        
        if end >= len(text):
            break
    
    return chunks

def load_files_and_chunk(file_paths: List[str], chunk_size: int) -> List[str]:
    """Load and chunk all supported file formats"""
    all_chunks = []
    
    for path in file_paths:
        print(f"Processing: {os.path.basename(path)}")
        
        # Extract text from file
        full_text = extract_text_from_file(path)
        
        if not full_text or not full_text.strip():
            print(f"  Warning: No text extracted from {path}")
            continue
        
        print(f"  Extracted {len(full_text)} characters")
        
        # Create overlapping chunks
        chunks = create_chunks_with_overlap(full_text, chunk_size, OVERLAP_SIZE)
        
        if not chunks:
            print(f"  Warning: No valid chunks created from {path}")
            continue
        
        # Add file info to each chunk
        for chunk in chunks:
            file_ext = Path(path).suffix.lower()
            file_type = SUPPORTED_EXTENSIONS.get(file_ext, 'unknown')
            tagged_chunk = f"[{file_type.upper()}: {os.path.basename(path)}]\n{chunk}"
            all_chunks.append(tagged_chunk)
        
        print(f"  Created {len(chunks)} chunks")
    
    return all_chunks

def embed_chunks(chunks: List[str], model_name: str):
    """Create embeddings for chunks"""
    print(f"Creating embeddings for {len(chunks)} chunks...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks, show_progress_bar=True)
    return embeddings

def save_faiss_index(embeddings, chunks, index_path, meta_path):
    """Save FAISS index and chunks"""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(chunks, f)
    print(f"Saved FAISS index with {index.ntotal} vectors")

def load_faiss_index(index_path, meta_path):
    """Load FAISS index and chunks"""
    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

if __name__ == "__main__":
    # Find all supported files
    FILE_PATHS = find_files_in_folder("../datasets", recursive=True)
    print(f"Found {len(FILE_PATHS)} supported files in the 'datasets' folder.")
    
    if not FILE_PATHS:
        print("No supported files found. Please check your datasets folder.")
        print("Supported formats: PDF, CSV, Excel, Markdown, DOCX, JSON, Text")
        exit()
    
    if not os.path.exists(INDEX_PATH):
        print("Creating FAISS index...")
        chunks = load_files_and_chunk(FILE_PATHS, CHUNK_SIZE)
        
        if not chunks:
            print("No chunks created. Exiting...")
            exit()
        
        embeddings = embed_chunks(chunks, EMBEDDING_MODEL)
        save_faiss_index(embeddings, chunks, INDEX_PATH, META_PATH)
        print("Indexing complete!")
    else:
        print("Loading existing FAISS index...")
    
    index, chunks = load_faiss_index(INDEX_PATH, META_PATH)
    print(f"Loaded index with {index.ntotal} document chunks")
    
    # Show file type statistics
    file_types = {}
    sources = {}
    for chunk in chunks:
        if chunk.startswith('['):
            try:
                file_info = chunk.split(']\n')[0][1:]  # Extract file info
                file_type = file_info.split(':')[0].strip()
                source = file_info.split(':')[1].strip() if ':' in file_info else 'Unknown'
                
                file_types[file_type] = file_types.get(file_type, 0) + 1
                sources[source] = sources.get(source, 0) + 1
            except:
                continue
    
    print("\nDocument Type Statistics:")
    for file_type, count in sorted(file_types.items()):
        print(f"  {file_type}: {count} chunks")
    
    print(f"\nTotal unique source files: {len(sources)}")
    
    