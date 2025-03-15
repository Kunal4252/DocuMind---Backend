import os
import uuid  # Make sure this import is uncommented
import tempfile
from typing import List, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
# from langchain_core.documents import Document as LCDocument - not directly used

# Qdrant specific imports
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, MatchValue

# App imports
from app.models.document_chunk import DocumentChunk

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "document_chunks"
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # The dimension for all-MiniLM-L6-v2

# Use a singleton pattern or connection pool for Qdrant client
class QdrantConnectionManager:
    _instance = None
    
    @classmethod
    def get_client(cls):
        if cls._instance is None:
            cls._instance = QdrantClient(
                url=QDRANT_URL, 
                api_key=QDRANT_API_KEY,
                timeout=30  # Add appropriate timeout
            )
        return cls._instance

class LangChainDocumentService:
    def __init__(self):
        # Initialize the HuggingFace Inference API for embeddings
        self.embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=HF_API_KEY,
            model_name=EMBEDDING_MODEL_NAME
        )
        
        # Initialize Qdrant client with retries
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                self.client = QdrantClient(
                    url=QDRANT_URL, 
                    api_key=QDRANT_API_KEY,
                    timeout=10  # Shorter timeout for faster feedback
                )
                # Test connection
                collections = self.client.get_collections()
                print(f"Successfully connected to Qdrant")
                break
            except Exception as e:
                retry_count += 1
                print(f"Error connecting to Qdrant (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count >= max_retries:
                    print("Could not connect to Qdrant after multiple attempts.")
                    # Continue with degraded functionality
                    self.client = None
                time.sleep(1)  # Wait before retrying
        
        # Check if collection exists, if not create it
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE
                )
            )
        
        # Initialize the vector store with Qdrant
        self.vector_store = Qdrant(
            client=self.client,
            collection_name=COLLECTION_NAME,
            embeddings=self.embeddings,
        )
    
    async def process_document(self, db: Session, file: UploadFile, document_id: str, user_id: str) -> Dict[str, Any]:
        """Process document (PDF or DOCX) with LangChain and store in Qdrant"""
        temp_file_path = None
        try:
            # Create a temporary file to store the uploaded document
            file_extension = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                contents = await file.read()
                temp_file.write(contents)
                temp_file_path = temp_file.name
            
            # Load document using appropriate LangChain loader based on file type
            if file_extension == '.pdf':
                loader = PyPDFLoader(temp_file_path)
            elif file_extension =='.docx':
                from langchain_community.document_loaders import UnstructuredWordDocumentLoader
                loader = UnstructuredWordDocumentLoader(temp_file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            documents = loader.load()
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            chunks = text_splitter.split_documents(documents)
            
            # Process and store chunks
            db_chunks = []
            vector_ids = []  # To store the UUIDs for Qdrant
            
            # Format with metadata
            for i, chunk in enumerate(chunks):
                # Create a unique UUID for vector store
                vector_db_id = str(uuid.uuid4())  # Generate proper UUID
                vector_ids.append(vector_db_id)  # Add to our list
                
                # Add metadata to each chunk
                chunk.metadata.update({
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "vector_db_id": vector_db_id,
                    "file_type": file_extension[1:]  # Store file type without dot
                })
                
                # Create database record
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk.page_content,
                    vector_db_id=vector_db_id  # Store the UUID in the database
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)
            
            # Before adding documents to Qdrant, print one for debugging:
            if chunks:
                print(f"Adding chunk with metadata: {chunks[0].metadata}")
            
            # Explicitly set metadatas when adding documents:
            self.vector_store.add_documents(
                documents=chunks, 
                ids=vector_ids,
                metadatas=[chunk.metadata for chunk in chunks]
            )
            
            # Commit database changes
            db.commit()
            
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
            return {
                "document_id": document_id,
                "chunks_processed": len(chunks),
                "status": "success",
                "file_type": file_extension[1:]
            }
            
        except Exception as e:
            # Clean up in case of error
            db.rollback()
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process document: {str(e)}"
            )
    
    def retrieve_relevant_chunks(self, query: str, document_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for a query from a specific document"""
        try:
            # First, verify collection has documents
            collection_info = self.client.get_collection(COLLECTION_NAME)
            print(f"Total vectors in collection: {collection_info.points_count}")
            
            # First try: Direct search without filters to see what metadata looks like
            print("Trying search without filters to inspect metadata structure")
            try:
                docs_without_filter = self.vector_store.similarity_search_with_score(query, k=5)
                if docs_without_filter:
                    doc, score = docs_without_filter[0]
                    print(f"FOUND DOCUMENT! Metadata structure: {doc.metadata}")
                    
                    # If we find the right document in this sample, just filter manually
                    results = []
                    for doc, score in docs_without_filter:
                        if doc.metadata.get("document_id") == document_id:
                            results.append({
                                "content": doc.page_content, 
                                "metadata": doc.metadata,
                                "relevance_score": score
                            })
                            
                    if results:
                        print(f"Found {len(results)} results via direct metadata match")
                        return results
            except Exception as e:
                print(f"Error in initial search: {e}")
            
            # Try different filter keys based on typical Qdrant/LangChain patterns
            possible_keys = ["document_id", "metadata.document_id"]
            
            for key in possible_keys:
                try:
                    print(f"Trying with filter key: {key}")
                    filter_condition = Filter(
                        must=[
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
                    
                    docs = self.vector_store.similarity_search_with_score(
                        query,
                        k=k,
                        filter=filter_condition
                    )
                    
                    if docs:
                        print(f"SUCCESS with key '{key}'! Found {len(docs)} results.")
                        results = []
                        for doc, score in docs:
                            results.append({
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "relevance_score": score
                            })
                        return results
                except Exception as e:
                    print(f"Error with key '{key}': {e}")
            
            # Last resort: Direct access to Qdrant API
            print("Trying direct Qdrant API access")
            try:
                # First get all document IDs from your database
                # Then query Qdrant by vector similarity and manually filter
                vector = self.embeddings.embed_query(query)
                search_result = self.client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=vector,
                    limit=20
                )
                
                if search_result:
                    print(f"Direct Qdrant API returned {len(search_result)} results")
                    print(f"First result payload: {search_result[0].payload}")
                    
                    # We'd need to reconstruct the documents from these results
                    # This is complex and dependent on exactly how data is stored
                    
                    # For now, let's just print what we found to help debug
                    for point in search_result:
                        print(f"Point ID: {point.id}, Score: {point.score}")
                        for key, value in point.payload.items():
                            print(f"  {key}: {value}")
            except Exception as e:
                print(f"Error with direct Qdrant API: {e}")
            
            # If we still have no results, try a new approach by querying directly from the database
            print("No results from vector search, retrieving from database directly")
            
            # Note: This doesn't use vector similarity, just returns chunks from this document
            return []
            
        except Exception as e:
            print(f"Overall error in vector search: {str(e)}")
            return []
    
    def get_document_retriever(self, document_id: str, k: int = 5):
        """Get a document-specific retriever for the RAG chain"""
        # Create filter for specific document_id
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="metadata.document_id",
                    match=MatchValue(value=document_id)
                )
            ]
        )
        
        # Create a filtered retriever
        return self.vector_store.as_retriever(
            search_kwargs={"k": k, "filter": filter_condition}
        ) 

    def get_chunks_from_database(self, db: Session, document_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve document chunks directly from database when vector search fails"""
        try:
            # Get chunks from database
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).limit(k).all()
            
            results = []
            for chunk in chunks:
                results.append({
                    "content": chunk.content,
                    "metadata": {
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "vector_db_id": chunk.vector_db_id
                    },
                    "relevance_score": 1.0  # Default score since not from vector search
                })
            
            return results
        except Exception as e:
            print(f"Error retrieving from database: {str(e)}")
            return [] 
