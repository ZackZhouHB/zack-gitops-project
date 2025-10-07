import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

from .kendra_service import KendraService
from .document_service import DocumentService
from .session_service import SessionService
from .config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AWS EKS RAG API",
    root_path="/api"  # Handle /api prefix from Ingress
    description="RAG system with Kendra, S3, and EFS integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
config = Config()
kendra_service = KendraService(config)
doc_service = DocumentService(config)
session_service = SessionService()

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]
    processing_time: float

def get_user_history_file(session_id: str):
    """Get user-specific chat history file path"""
    return f"/efs/chat_history/user-{session_id}-history.json"

def load_conversation_history(session_id: str):
    """Load conversation history for specific user"""
    history_file = get_user_history_file(session_id)
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading conversation history for {session_id}: {e}")
    return []

def save_conversation_history(session_id: str, history):
    """Save conversation history for specific user"""
    history_file = get_user_history_file(session_id)
    try:
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving conversation history for {session_id}: {e}")

@app.get("/")
async def health_check(request: Request):
    """Health check endpoint"""
    session_id = session_service.get_session_id(request)
    return {
        "status": "healthy",
        "service": "AWS EKS RAG API",
        "session_id": session_id,
        "kendra_status": kendra_service.check_connection(),
        "s3_status": doc_service.check_s3_connection(),
        "bedrock_status": kendra_service.check_bedrock_connection()
    }

@app.post("/documents/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """Upload document to S3 with user isolation"""
    try:
        session_id = session_service.get_session_id(request)
        user_prefix = session_service.get_user_prefix(session_id)
        
        # Support multiple file types
        allowed_extensions = ['.txt', '.md', '.pdf', '.docx', '.xlsx', '.pptx', '.csv']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        success = await doc_service.upload_to_s3(file, user_prefix)
        if success:
            return {"message": f"Successfully uploaded {file.filename}", "session_id": session_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file")
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/sync")
async def sync_documents(request: Request):
    """Sync S3 documents with Kendra index for specific user"""
    try:
        session_id = session_service.get_session_id(request)
        user_prefix = session_service.get_user_prefix(session_id)
        
        job_id = kendra_service.start_data_source_sync(user_prefix)
        return {
            "message": "Document sync started",
            "job_id": job_id,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error syncing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: Request, query_request: QueryRequest):
    """Query the RAG system using Kendra + Bedrock with user context"""
    try:
        session_id = session_service.get_session_id(request)
        user_prefix = session_service.get_user_prefix(session_id)
        
        result = kendra_service.query_with_user_context(query_request.question, query_request.top_k, user_prefix)
        
        # Save to user-specific conversation history on EFS
        history = load_conversation_history(session_id)
        history.append({
            "timestamp": datetime.now().isoformat(),
            "question": query_request.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "processing_time": result["processing_time"],
            "session_id": session_id
        })
        # Keep only last 100 conversations per user
        if len(history) > 100:
            history = history[-100:]
        save_conversation_history(session_id, history)
        
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation-history")
async def get_conversation_history(request: Request):
    """Get conversation history from EFS for specific user"""
    try:
        session_id = session_service.get_session_id(request)
        history = load_conversation_history(session_id)
        return {"history": history, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents(request: Request):
    """List documents in S3 for specific user"""
    try:
        session_id = session_service.get_session_id(request)
        user_prefix = session_service.get_user_prefix(session_id)
        
        documents = doc_service.list_s3_documents(user_prefix)
        return {"documents": documents, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/sync-status/{job_id}")
async def get_sync_status(job_id: str):
    """Get sync job status"""
    try:
        status = kendra_service.get_sync_status(job_id)
        return {"job_id": job_id, "status": status}
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
async def delete_document(request: Request, filename: str):
    """Delete document from S3 for specific user"""
    try:
        session_id = session_service.get_session_id(request)
        user_prefix = session_service.get_user_prefix(session_id)
        
        success = doc_service.delete_s3_document(filename, user_prefix)
        if success:
            return {"message": f"Successfully deleted {filename}", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
