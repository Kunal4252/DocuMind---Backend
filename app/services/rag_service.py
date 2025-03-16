import os
from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_huggingface import HuggingFaceEndpoint

# App imports
from app.services.langchain_document_service import LangChainDocumentService
from app.models.chat_history import ChatHistory

# Hugging Face configuration
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")

# Debug: Print partial API key to verify it's loaded
print(f"HF API Key: {HF_API_KEY[:4]}...{HF_API_KEY[-4:] if HF_API_KEY and len(HF_API_KEY) > 8 else 'None or too short'}")

class RAGService:
    def __init__(self):
        # Init document service with Qdrant
        self.doc_service = LangChainDocumentService()
        
        try:
            # Init the LLM using Hugging Face Inference API
            self.llm = HuggingFaceEndpoint(
                repo_id=MISTRAL_MODEL_NAME,
                huggingfacehub_api_token=HF_API_KEY,
                task="text-generation",
                temperature=0.2,
                max_new_tokens=512,
                do_sample=True
            )
            print("Successfully initialized HuggingFaceEndpoint")
            
            # Verify Qdrant collection
            self.doc_service.verify_collection()
            
        except Exception as e:
            print(f"Error initializing HuggingFaceEndpoint: {str(e)}")
            # Fallback to a simple model or raise an exception
            raise
        
        # Customize the single-document RAG prompt
        template = """
        You are a helpful document assistant. Use the following context from the document to answer the user's question.
        If you don't know the answer based on the context, just say that the information is not in the document.
        
        Context: {context}
        
        Chat History: {chat_history}
        
        Question: {question}
        
        Answer:
        """
        
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
    
    def query_document(self, query: str, document_id: str, db: Session = None, chat_history=None, top_k: int = 5):
        """Query a specific document using direct vector retrieval"""
        try:
            # 1. First, attempt to retrieve relevant chunks via vector search
            chunks = self.doc_service.retrieve_relevant_chunks(query, document_id, top_k)
            
            # If no chunks found via vector search and db is provided, fall back to database retrieval
            if not chunks and db is not None:
                print("Vector search returned no results. Falling back to database retrieval.")
                chunks = self.doc_service.get_chunks_from_database(db, document_id, top_k)
            
            # Handle empty results
            if not chunks:
                return {
                    "answer": "I couldn't find any relevant information about this in the document. Please try rephrasing your question or ask about a different topic covered in the document.",
                    "source_documents": [],
                    "document_id": document_id
                }
            
            # 2. Format the context from retrieved chunks
            context = "\n\n".join([chunk["content"] for chunk in chunks])
            
            # 3. Format chat history if provided (limited to last 5 interactions)
            chat_history_text = ""
            if chat_history and len(chat_history) > 0:
                # Only include up to 5 most recent interactions
                recent_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
                
                history_items = []
                for user_msg, bot_msg in recent_history:
                    history_items.append(f"User: {user_msg}\nAssistant: {bot_msg}")
                chat_history_text = "\n\n".join(history_items)
                print(f"Including {len(recent_history)} recent interactions in prompt context")
            
            # 4. Create a prompt with context and chat history
            prompt = f"""
            Answer the following question based only on the provided context:
            
            Context:
            {context}
            
            {f"Previous conversation (most recent only):\n{chat_history_text}\n\n" if chat_history_text else ""}
            Question: {query}
            
            Answer:
            """
            
            # 5. Send directly to LLM
            response = self.llm.invoke(prompt)
            
            return {
                "answer": response,
                "source_documents": chunks,
                "document_id": document_id
            }
        except Exception as e:
            print(f"Error in query_document: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to query document: {str(e)}"
            )
            
    def save_chat_history(self, db: Session, user_id: str, document_id: str, 
                         user_message: str, bot_response: str) -> ChatHistory:
        """Save chat interaction to database"""
        try:
            chat_entry = ChatHistory(
                user_id=user_id,
                document_id=document_id,
                user_message=user_message,
                bot_response=bot_response
            )
            
            db.add(chat_entry)
            db.commit()
            db.refresh(chat_entry)
            
            return chat_entry
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save chat history: {str(e)}"
            )
            
    def get_chat_history(self, db: Session, user_id: str, document_id: str) -> List[tuple]:
        """Get limited chat history (last 5 entries) for RAG context"""
        try:
            # Get only the last 5 interactions to avoid context length issues
            history = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.document_id == document_id
            ).order_by(ChatHistory.timestamp.desc()).limit(5).all()
            
            # Reverse the list to get chronological order (oldest first)
            history.reverse()
            
            # Format for LangChain's memory format
            formatted_history = [
                (entry.user_message, entry.bot_response) for entry in history
            ]
            
            print(f"Using last {len(formatted_history)} chat history entries for context")
            return formatted_history
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve chat history: {str(e)}"
            )
            
    def get_full_chat_history(self, db: Session, user_id: str, document_id: str) -> List[ChatHistory]:
        """Get complete chat history for UI display"""
        try:
            # Get all chat history for the document
            history = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.document_id == document_id
            ).order_by(ChatHistory.timestamp).all()
            
            return history
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve full chat history: {str(e)}"
            )