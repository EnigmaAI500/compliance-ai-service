"""
Ingest sanctions and FATF data into the document store for RAG.
This script runs on startup to populate the vector store with compliance context.
"""
import json
import os
import time
from pathlib import Path
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from .rag_engine import embed
from .storage import doc_store


def ingest_fatf_json():
    """Load and ingest FATF countries JSON into the document store."""
    fatf_path = Path(__file__).parent.parent / "sunction-lists" / "fatf-countries.json"
    
    if not fatf_path.exists():
        print(f"⚠️  FATF JSON not found at {fatf_path}")
        return 0
    
    print(f"📄 Loading FATF JSON...")
    start_time = time.time()
    
    try:
        with open(fatf_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks_added = 0
        
        # Ingest metadata
        metadata_text = f"""
FATF (Financial Action Task Force) Data
Source: {data.get('source', 'N/A')}
As of: {data.get('as_of', 'N/A')}

The FATF maintains lists of jurisdictions with strategic AML/CFT/CPF deficiencies.
"""
        print(f"  ⏳ Embedding FATF metadata...")
        emb = embed(metadata_text)
        doc_store.add_chunk(metadata_text, emb)
        chunks_added += 1
        
        # Ingest each category
        for category in data.get('categories', []):
            category_text = f"""
FATF Category: {category['category_name']}
Key: {category['category_key']}
Also known as: {', '.join(category.get('aka', []))}

Description: {category['description']}

Countries in this category:
{chr(10).join(f"- {country}" for country in category.get('countries', []))}
"""
            print(f"  ⏳ Embedding FATF category: {category['category_key']}...")
            emb = embed(category_text)
            doc_store.add_chunk(category_text, emb)
            chunks_added += 1
        
        elapsed = time.time() - start_time
        print(f"✅ Ingested FATF data: {chunks_added} chunks in {elapsed:.1f}s")
        return chunks_added
    
    except Exception as e:
        print(f"❌ Error ingesting FATF data: {e}")
        return 0


def ingest_un_html():
    """Load and ingest UN sanctions HTML into the document store (LIMITED)."""
    un_path = Path(__file__).parent.parent / "sunction-lists" / "UN-sunctions-list.html"
    
    if not un_path.exists():
        print(f"⚠️  UN HTML not found at {un_path}")
        return 0
    
    print(f"📄 Loading UN HTML...")
    start_time = time.time()
    
    try:
        with open(un_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text from HTML
        text_content = soup.get_text(separator='\n', strip=True)
        
        # OPTIMIZATION: Limit to first 10,000 characters to speed up startup
        text_content = text_content[:10000]
        
        # Split into larger chunks (5000 characters) to reduce embedding calls
        chunk_size = 5000
        chunks_added = 0
        max_chunks = 3  # Limit to 3 chunks for fast startup
        
        # Add header
        header = "UN Sanctions List\nThis list contains individuals and entities subject to United Nations sanctions.\n\n"
        
        for i in range(0, len(text_content), chunk_size):
            if chunks_added >= max_chunks:
                break
            
            chunk = text_content[i:i + chunk_size]
            if i == 0:
                chunk = header + chunk
            
            if chunk.strip():
                print(f"  ⏳ Embedding UN chunk {chunks_added + 1}/{max_chunks}...")
                emb = embed(chunk)
                doc_store.add_chunk(chunk, emb)
                chunks_added += 1
        
        elapsed = time.time() - start_time
        print(f"✅ Ingested UN sanctions: {chunks_added} chunks in {elapsed:.1f}s")
        return chunks_added
    
    except Exception as e:
        print(f"❌ Error ingesting UN data: {e}")
        return 0


def ingest_eu_pdf():
    """Load and ingest EU sanctions PDF into the document store (LIMITED)."""
    eu_path = Path(__file__).parent.parent / "sunction-lists" / "EU-suctions-list.pdf"
    
    if not eu_path.exists():
        print(f"⚠️  EU PDF not found at {eu_path}")
        return 0
    
    print(f"📄 Loading EU PDF...")
    start_time = time.time()
    
    try:
        reader = PdfReader(str(eu_path))
        
        chunks_added = 0
        chunk_size = 5000  # Larger chunks
        max_chunks = 3  # Limit to 3 chunks for fast startup
        max_pages = 5  # Only read first 5 pages
        
        # Add header
        header = "EU Sanctions List\nThis list contains individuals and entities subject to European Union sanctions.\n\n"
        
        full_text = header
        
        # Extract text from LIMITED pages
        pages_to_read = min(len(reader.pages), max_pages)
        print(f"  📖 Reading first {pages_to_read} pages of EU PDF...")
        
        for page_num in range(pages_to_read):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                full_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        # Split into chunks
        for i in range(0, len(full_text), chunk_size):
            if chunks_added >= max_chunks:
                break
            
            chunk = full_text[i:i + chunk_size]
            
            if chunk.strip():
                print(f"  ⏳ Embedding EU chunk {chunks_added + 1}/{max_chunks}...")
                emb = embed(chunk)
                doc_store.add_chunk(chunk, emb)
                chunks_added += 1
        
        elapsed = time.time() - start_time
        print(f"✅ Ingested EU sanctions: {chunks_added} chunks in {elapsed:.1f}s")
        return chunks_added
    
    except Exception as e:
        print(f"❌ Error reading EU PDF: {e}")
        return 0


def ingest_all_sanctions():
    """Ingest all sanctions data on startup."""
    print("\n" + "="*50)
    print("🔄 Ingesting sanctions data into RAG system...")
    print("="*50 + "\n")
    
    total_chunks = 0
    
    total_chunks += ingest_fatf_json()
    total_chunks += ingest_un_html()
    total_chunks += ingest_eu_pdf()
    
    print("\n" + "="*50)
    print(f"✅ Total chunks ingested: {total_chunks}")
    print("="*50 + "\n")
    
    return total_chunks


if __name__ == "__main__":
    ingest_all_sanctions()
