from fastapi import FastAPI, HTTPException, UploadFile, File, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import json
import os
import uuid
import hashlib
from datetime import datetime

from .langchain_rag_service import LangChainRAGService
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LangChain RAG API", root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
rag_service = LangChainRAGService(config)

# Global history file - SEPARATE from original backend
GLOBAL_HISTORY_FILE = "/efs/langchain_chat_history/global_history.json"

def get_session_id(request: Request) -> str:
    """Generate session ID from client IP (same as original backend)"""
    client_ip = request.client.host
    return hashlib.md5(f"{client_ip}".encode()).hexdigest()[:8]

def load_global_history():
    """Load all conversations from global history"""
    try:
        if os.path.exists(GLOBAL_HISTORY_FILE):
            with open(GLOBAL_HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading global history: {e}")
    return []

def save_global_history(history):
    """Save all conversations to global history"""
    try:
        os.makedirs(os.path.dirname(GLOBAL_HISTORY_FILE), exist_ok=True)
        with open(GLOBAL_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving global history: {e}")

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class SettingsRequest(BaseModel):
    embedding_model: str

@app.on_event("startup")
async def startup_event():
    """Initialize LangChain RAG service on startup"""
    logger.info("Starting LangChain RAG service...")
    try:
        await rag_service.initialize()
        logger.info("LangChain RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing RAG service: {e}")

@app.get("/")
async def root(request: Request):
    """Root endpoint with service status checks"""
    try:
        session_id = get_session_id(request)
        
        # Get service health status
        health = await rag_service.health_check()
        components = health.get("components", {})
        
        return {
            "status": "healthy",
            "session_id": session_id,
            "weaviate_status": components.get("weaviate") == "healthy",
            "s3_status": components.get("s3") == "healthy", 
            "bedrock_status": components.get("bedrock") == "healthy",
            "message": "LangChain RAG API is running"
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        return {
            "status": "unhealthy",
            "session_id": get_session_id(request),
            "weaviate_status": False,
            "s3_status": False,
            "bedrock_status": False,
            "message": "LangChain RAG API error",
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = await rag_service.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """Upload and process document using LangChain"""
    try:
        session_id = get_session_id(request)
        result = await rag_service.process_document(file, session_id)
        return result
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/upload")
async def upload_document_alt(request: Request, file: UploadFile = File(...)):
    """Upload and process document (alias for /upload)"""
    return await upload_document(request, file)

@app.get("/documents")
async def list_documents():
    """List all processed documents"""
    try:
        documents = await rag_service.list_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(query_request: QueryRequest, request: Request):
    """Query documents using LangChain RAG chain with session memory"""
    try:
        session_id = get_session_id(request)
        logger.info(f"Query from session {session_id}: {query_request.question}")
        
        # Query with session context
        result = await rag_service.query(
            query_request.question, 
            session_id=session_id,
            top_k=query_request.top_k
        )
        
        # Add to global history with all fields
        history = load_global_history()
        history.append({
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "question": query_request.question,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "processing_time": result.get("processing_time", 0)
        })
        
        # Keep last 100 conversations
        if len(history) > 100:
            history = history[-100:]
        
        save_global_history(history)
        
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat-history")
async def get_chat_history():
    """Get chat history"""
    try:
        if os.path.exists(GLOBAL_HISTORY_FILE):
            with open(GLOBAL_HISTORY_FILE, 'r') as f:
                history = json.load(f)
            return {"history": history}
        return {"history": []}
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation-history")
async def get_conversation_history():
    """Get all conversations from all sessions"""
    try:
        history = load_global_history()
        # Return in reverse order (newest first)
        return {"history": list(reversed(history))}
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector-stats")
async def get_vector_stats():
    """Get vector database statistics"""
    try:
        return await rag_service.get_vector_stats()
    except Exception as e:
        logger.error(f"Failed to get vector stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from vector store"""
    try:
        result = await rag_service.delete_document(document_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def save_chat_history(question: str, answer: str):
    """Save chat interaction to history file"""
    try:
        os.makedirs(os.path.dirname(GLOBAL_HISTORY_FILE), exist_ok=True)
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer
        }
        
        history = []
        if os.path.exists(GLOBAL_HISTORY_FILE):
            with open(GLOBAL_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        history.append(history_entry)
        
        # Keep only last 100 entries
        if len(history) > 100:
            history = history[-100:]
        
        with open(GLOBAL_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")

@app.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history for a session"""
    try:
        rag_service.session_manager.clear_session(session_id)
        return {"message": "Conversation cleared", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to clear conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/stats")
async def get_conversation_stats():
    """Get conversation session statistics"""
    try:
        return rag_service.session_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/memory")
async def memory_metrics():
    """Get memory usage metrics"""
    try:
        import psutil
        process = psutil.Process()
        
        return {
            "memory_used_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "session_stats": rag_service.session_manager.get_stats()
        }
    except Exception as e:
        logger.error(f"Failed to get memory metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

