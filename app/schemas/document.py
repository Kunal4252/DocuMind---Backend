from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Request schemas
class DocumentUploadRequest(BaseModel):
    title: str

class DocumentChatRequest(BaseModel):
    message: str

# Response schemas
class DocumentChunkMetadata(BaseModel):
    document_id: str
    user_id: str
    chunk_index: int
    vector_db_id: str

class RelevantChunk(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    relevance_score: float

class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str
    file_url: str
    processing_status: Dict[str, Any]

class DocumentChatResponse(BaseModel):
    answer: str
    document_id: str
    source_documents: List[RelevantChunk]

class ChatHistoryEntry(BaseModel):
    id: str
    timestamp: datetime
    user_message: str
    bot_response: str

class DocumentChatHistoryResponse(BaseModel):
    document_id: str
    title: str
    chat_history: List[ChatHistoryEntry]

class DocumentListEntry(BaseModel):
    id: str
    title: str
    file_url: str
    uploaded_at: datetime

class DocumentListResponse(BaseModel):
    documents: List[DocumentListEntry] 