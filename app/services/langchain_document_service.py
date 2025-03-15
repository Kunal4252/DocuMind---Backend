import os
import uuid
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

# Qdrant specific imports
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, FieldCondition, MatchValue

# App imports
from app.models.document_chunk import DocumentChunk
from app.models.document import Document

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "document_chunks"
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # The dimension for all-MiniLM-L6-v2

# Use a singleton pattern for Qdrant client
class QdrantConnectionManager:
    _instance = None
    
    @classmethod
    def get_client(cls):
        if cls._instance is None:
            cls._instance = QdrantClient(
                url=QDRANT_URL, 
                api_key=QDRANT_API_KEY,
                timeout=30
            )
        return cls._instance

class LangChainDocumentService:
    def __init__(self):
        # Initialize the HuggingFace Inference API for embeddings
        self.embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=HF_API_KEY,
            model_name=EMBEDDING_MODEL_NAME
        )
        
        # Initialize Qdrant client using the connection manager
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                self.client = QdrantConnectionManager.get_client()
                # Test connection
                collections = self.client.get_collections()
                print(f"Successfully connected to Qdrant")
                break
            except Exception as e:
                retry_count += 1
                print(f"Error connecting to Qdrant (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count >= max_retries:
                    print("Could not connect to Qdrant after multiple attempts.")
                    self.client = None
                time.sleep(1)  # Wait before retrying
        
        # Initialize collection if needed
        self._initialize_collection()
        
        # Initialize the vector store with Qdrant
        self.vector_store = Qdrant(
            client=self.client,
            collection_name=COLLECTION_NAME,
            embeddings=self.embeddings,
        )
    
    def _initialize_collection(self):
        """Initialize the Qdrant collection with proper schema"""
        if not self.client:
            print("Qdrant client not initialized, skipping collection setup")
            return
            
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if COLLECTION_NAME not in collection_names:
                print(f"Creating collection: {COLLECTION_NAME}")
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=models.Distance.COSINE
                    ),
                    # Define payload schema to ensure consistency
                    on_disk_payload=True  # Store payload on disk for large collections
                )
                print(f"Collection {COLLECTION_NAME} created successfully")
        except Exception as e:
            print(f"Error initializing collection: {str(e)}")
    
    def verify_collection(self):
        """Verify the collection exists and inspect sample data"""
        try:
            # Check if collection exists
            collection_info = self.client.get_collection(COLLECTION_NAME)
            print(f"Collection {COLLECTION_NAME} exists with {collection_info.points_count} points")
            
            # Get a sample point to check schema if any points exist
            if collection_info.points_count > 0:
                points = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=1
                )[0]
                
                if points:
                    print(f"Sample point payload: {points[0].payload}")
                    return True
            
            return collection_info.points_count > 0
        except Exception as e:
            print(f"Error verifying collection: {str(e)}")
            return False
    
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
            elif file_extension == '.docx':
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
            vector_ids = []
            texts = []
            metadatas = []
            
            # Debug info
            print(f"Processing {len(chunks)} chunks for document {document_id}")
            
            # Format with metadata
            for i, chunk in enumerate(chunks):
                # Create a unique UUID for vector store
                vector_db_id = str(uuid.uuid4())
                vector_ids.append(vector_db_id)
                
                # Store the original text content
                texts.append(chunk.page_content)
                
                # Create consistent metadata
                metadata = {
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "vector_db_id": vector_db_id,
                    "file_type": file_extension[1:],
                    "page_content": chunk.page_content  # Store content in metadata for direct access
                }
                
                # Update the chunk's metadata
                chunk.metadata.update(metadata)
                metadatas.append(metadata)
                
                # Create database record
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk.page_content,
                    vector_db_id=vector_db_id
                )
                db.add(db_chunk)
                db_chunks.append(db_chunk)
            
            if chunks:
                print(f"Sample chunk metadata: {metadatas[0]}")
                
                # Add to vector store - use the properly constructed texts and metadatas
                self.vector_store.add_texts(
                    texts=texts,
                    metadatas=metadatas,
                    ids=vector_ids
                )
                
                print(f"Added {len(texts)} chunks to vector store")
            
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
            # Verify we have a connection to Qdrant
            if not self.client:
                print("Qdrant client not available, falling back to database retrieval")
                return []
            
            # First, verify collection has documents
            collection_info = self.client.get_collection(COLLECTION_NAME)
            print(f"Total vectors in collection: {collection_info.points_count}")
            
            if collection_info.points_count == 0:
                print("Collection is empty, no documents to search")
                return []
            
            # Create filter for specific document
            filter_condition = {
                "filter": Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            }
            
            # Get results from vector store
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                **filter_condition
            )
            
            if not results:
                print(f"No results found for document_id={document_id}")
                return []
            
            processed_results = []
            for doc, score in results:
                processed_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": float(score)  # Convert numpy float to Python float if needed
                })
            
            print(f"Found {len(processed_results)} relevant chunks")
            return processed_results
            
        except Exception as e:
            print(f"Error in vector search: {str(e)}")
            return []
    
    def get_document_retriever(self, document_id: str, k: int = 5):
        """Get a document-specific retriever for the RAG chain"""
        # Create filter for specific document_id
        filter_condition = {
            "filter": Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            ),
            "k": k
        }
        
        # Create a filtered retriever
        return self.vector_store.as_retriever(
            search_kwargs=filter_condition
        )

    def get_chunks_from_database(self, db: Session, document_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve document chunks directly from database when vector search fails"""
        try:
            # Get chunks from database
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).limit(k).all()
            
            # First, get the document to retrieve the user_id
            if chunks:
                document = db.query(Document).filter(Document.id == document_id).first()
                user_id = document.user_id if document else "unknown"
            else:
                user_id = "unknown"
            
            results = []
            for chunk in chunks:
                results.append({
                    "content": chunk.content,
                    "metadata": {
                        "document_id": chunk.document_id,
                        "user_id": user_id,
                        "chunk_index": chunk.chunk_index,
                        "vector_db_id": chunk.vector_db_id,
                        "file_type": "unknown"
                    },
                    "relevance_score": 1.0
                })
            
            print(f"Retrieved {len(results)} chunks directly from database")
            return results
        except Exception as e:
            print(f"Error retrieving from database: {str(e)}")
            return []
    
    def query_document(self, db: Session, document_id: str, query: str, k: int = 5):
        """Query a document by ID and return relevant chunks"""
        # First try vector search
        results = self.retrieve_relevant_chunks(query, document_id, k)
        
        # If no results, fall back to database retrieval
        if not results:
            print(f"No vector results found, retrieving from database")
            results = self.get_chunks_from_database(db, document_id, k)
        
        return {
            "document_id": document_id,
            "query": query,
            "results": results,
            "total_chunks": len(results)
        }