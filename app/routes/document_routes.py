from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.chat_history import ChatHistory
from app.models.document_chunk import DocumentChunk
from app.services.cloudinary_upload_service import CloudinaryUploadService
from app.services.langchain_document_service import LangChainDocumentService, COLLECTION_NAME
from app.services.rag_service import RAGService
from app.schemas.document import (
    DocumentChatRequest,
    DocumentUploadResponse, DocumentChatResponse,
    DocumentChatHistoryResponse, DocumentListResponse,
    DocumentListEntry
)
from app.services.file_validation_service import FileValidationService

document_router = APIRouter(prefix="/documents", tags=["documents"])

cloudinary_service = CloudinaryUploadService()
doc_service = LangChainDocumentService()
rag_service = RAGService()

@document_router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        
        FileValidationService.validate_file(file, 'document')
        
        file_url = cloudinary_service.upload_file(
            file,
            'document',
            user_id
        )
        
        document = Document(
            user_id=user_id,
            title=title,
            file_url=file_url
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        document_id = document.id
        
        await file.seek(0)
        
        processing_result = await doc_service.process_document(
            db=db,
            file=file,
            document_id=document_id,
            user_id=user_id
        )
        
        return {
            "document_id": document_id,
            "title": title,
            "file_url": file_url,
            "processing_status": processing_result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        if 'document' in locals() and 'db' in locals():
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@document_router.post("/chat/{document_id}", response_model=DocumentChatResponse)
async def chat_with_document(
    document_id: str,
    request: DocumentChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or doesn't belong to you"
            )
        
        chat_history = rag_service.get_chat_history(db, user_id, document_id)
        
        result = rag_service.query_document(
            query=request.message,
            document_id=document_id,
            db=db,
            chat_history=chat_history
        )
        
        rag_service.save_chat_history(
            db=db,
            user_id=user_id,
            document_id=document_id,
            user_message=request.message,
            bot_response=result["answer"]
        )
        
        return {
            "answer": result["answer"],
            "document_id": document_id,
            "source_documents": result["source_documents"]
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@document_router.get("/chat/{document_id}/history", response_model=DocumentChatHistoryResponse)
async def get_document_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or doesn't belong to you"
            )
        
        history_entries = rag_service.get_full_chat_history(db, user_id, document_id)
        
        chat_history = []
        for entry in history_entries:
            chat_history.append({
                "id": entry.id,
                "timestamp": entry.timestamp,
                "user_message": entry.user_message,
                "bot_response": entry.bot_response
            })
        
        return {
            "document_id": document_id,
            "title": document.title,
            "chat_history": chat_history
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@document_router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        document_list = [
            DocumentListEntry(
                id=doc.id,
                title=doc.title,
                file_url=doc.file_url,
                uploaded_at=doc.uploaded_at
            )
            for doc in documents
        ]
        
        return {"documents": document_list}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@document_router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or doesn't belong to you"
            )
        
        # Get all document chunks to find vector_db_ids
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).all()
        
        vector_ids = [chunk.vector_db_id for chunk in chunks]
        
        # Delete vectors from Qdrant if available
        if vector_ids and len(vector_ids) > 0:
            try:
                # Get Qdrant client
                qdrant_client = doc_service.client
                if qdrant_client:
                    # Delete vectors from Qdrant collection
                    qdrant_client.delete(
                        collection_name=COLLECTION_NAME,
                        points_selector=vector_ids
                    )
            except Exception:
                # Continue with deletion even if Qdrant deletion fails
                pass
        
        # Delete chat history
        db.query(ChatHistory).filter(
            ChatHistory.document_id == document_id
        ).delete(synchronize_session=False)
        
        # Delete document chunks
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)
        
        # Delete the document
        db.delete(document)
        
        # Commit all changes
        db.commit()
        
        return {
            "success": True,
            "message": f"Document '{document.title}' and all associated data deleted successfully"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()  # Roll back changes in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
