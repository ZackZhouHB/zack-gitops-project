from fastapi import FastAPI, HTTPException, UploadFile, File, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import json
import os
import hashlib
import asyncio
from datetime import datetime

from .weaviate_service import WeaviateService
from .document_service import DocumentService
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Shared RAG API", root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
weaviate_service = WeaviateService(config)
doc_service = DocumentService(config)

# Global history file
GLOBAL_HISTORY_FILE = "/efs/chat_history/global_history.json"

@app.on_event("startup")
async def startup_event():
    """Run automatic indexing on startup"""
    logger.info("Starting up - checking for unindexed documents...")
    try:
        await auto_index_documents()
    except Exception as e:
        logger.error(f"Error during startup indexing: {e}")

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class SettingsRequest(BaseModel):
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    chunking_method: str

def get_session_id(request: Request) -> str:
    """Generate session ID from client IP + timestamp"""
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

async def auto_index_documents():
    """Background task to automatically index unindexed documents"""
    try:
        # Check if Weaviate is available first
        if not weaviate_service.check_connection():
            logger.warning("⚠️  Weaviate not available, skipping auto-indexing")
            return

        # Get all documents from S3
        s3_docs = doc_service.list_s3_documents()

        # Get indexed documents from Weaviate
        indexed_docs = set()
        try:
            if weaviate_service.client:  # Additional safety check
                result = weaviate_service.client.query.aggregate("Document").with_meta_count().do()
                all_docs = weaviate_service.client.query.get("Document", ["filename"]).do()
                if "data" in all_docs and "Get" in all_docs["data"]:
                    indexed_docs = {doc["filename"] for doc in all_docs["data"]["Get"]["Document"]}
        except Exception as e:
            logger.warning(f"Could not get indexed documents: {e}")

        # Find unindexed documents
        unindexed = []
        for doc in s3_docs:  # s3_docs is already a list, not {"documents": [...]}
            if doc["filename"] not in indexed_docs:
                unindexed.append(doc["filename"])

        if unindexed:
            logger.info(f"Found {len(unindexed)} unindexed documents, indexing...")
            for filename in unindexed:
                try:
                    # Download and extract content
                    content = await doc_service.get_document_content(filename)
                    if content:
                        success = weaviate_service.index_document(filename, content)
                        if success:
                            logger.info(f"✅ Auto-indexed: {filename}")
                        else:
                            logger.warning(f"⚠️  Failed to auto-index: {filename}")
                    else:
                        logger.warning(f"⚠️  Could not extract content from: {filename}")
                except Exception as e:
                    logger.error(f"❌ Error auto-indexing {filename}: {e}")
        else:
            logger.info("✅ No unindexed documents found")

    except Exception as e:
        logger.error(f"❌ Error in auto-index task: {e}")

@app.get("/")
async def health(request: Request, background_tasks: BackgroundTasks):
    session_id = get_session_id(request)
    
    return {
        "status": "healthy", 
        "session_id": session_id,
        "weaviate_status": weaviate_service.check_connection(),
        "s3_status": doc_service.check_s3_connection(),
        "bedrock_status": weaviate_service.check_bedrock_connection()
    }

@app.post("/query")
async def query(query_request: QueryRequest, request: Request):
    try:
        session_id = get_session_id(request)
        logger.info(f"Query from session {session_id}: {query_request.question}")
        
        # Process query
        result = weaviate_service.query_with_user_context(query_request.question, query_request.top_k, session_id)
        
        # Add to global history
        history = load_global_history()
        history.append({
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "question": query_request.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "processing_time": result["processing_time"]
        })
        
        # Keep last 100 conversations globally
        if len(history) > 100:
            history = history[-100:]
        
        save_global_history(history)
        
        return result
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation-history")
async def get_history():
    """Get all conversations from all sessions"""
    try:
        history = load_global_history()
        # Return in reverse order (newest first)
        return {"history": list(reversed(history))}
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/cleanup-duplicates")
async def cleanup_duplicates():
    """Remove duplicate documents from Weaviate"""
    try:
        # Get all documents
        all_docs = weaviate_service.client.query.get("Document", ["filename"]).with_additional(["id"]).do()
        
        if "data" not in all_docs or "Get" not in all_docs["data"] or "Document" not in all_docs["data"]["Get"]:
            return {"message": "No documents found"}
        
        # Group by filename
        filename_groups = {}
        for doc in all_docs["data"]["Get"]["Document"]:
            filename = doc["filename"]
            doc_id = doc["_additional"]["id"]
            
            if filename not in filename_groups:
                filename_groups[filename] = []
            filename_groups[filename].append(doc_id)
        
        # Delete duplicates (keep only the first one)
        deleted_count = 0
        for filename, doc_ids in filename_groups.items():
            if len(doc_ids) > 1:
                # Delete all but the first one
                for doc_id in doc_ids[1:]:
                    weaviate_service.client.data_object.delete(doc_id, class_name="Document")
                    deleted_count += 1
                logger.info(f"Removed {len(doc_ids)-1} duplicates of {filename}")
        
        return {"message": f"Cleaned up {deleted_count} duplicate documents"}
        
    except Exception as e:
        logger.error(f"Error cleaning duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/auto-index")
async def trigger_auto_index(background_tasks: BackgroundTasks):
    """Manually trigger automatic indexing of unindexed documents"""
    background_tasks.add_task(auto_index_documents)
    return {"message": "Auto-indexing triggered"}

@app.post("/documents/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    try:
        session_id = get_session_id(request)
        
        # Extract text content first for Weaviate indexing
        content = await doc_service.extract_text_content(file)
        
        # Upload to S3
        success = await doc_service.upload_to_s3(file, session_id)
        if success:
            # Index document in Weaviate
            indexed = weaviate_service.index_document(file.filename, content)
            if indexed:
                return {"message": f"Uploaded and indexed {file.filename}"}
            else:
                logger.warning(f"Document {file.filename} uploaded to S3 but failed to index in Weaviate")
                return {"message": f"Uploaded {file.filename} (indexing failed - will retry automatically)"}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload document")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_docs():
    try:
        docs = doc_service.list_s3_documents()
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{filename}/download")
async def download_document(filename: str, request: Request):
    """Generate a pre-signed URL for downloading a document"""
    session_id = get_session_id(request)
    logger.info(f"Download request for {filename} by session {session_id}")
    
    try:
        # Generate pre-signed URL (valid for 1 hour)
        download_url = doc_service.generate_download_url(filename, expiration=3600)
        return {
            "download_url": download_url,
            "filename": filename,
            "expires_in": 3600
        }
    except Exception as e:
        logger.error(f"Error generating download URL for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")

@app.delete("/documents/{filename}")
async def delete_document(filename: str, request: Request):
    """Delete a document from S3"""
    try:
        session_id = get_session_id(request)

        # Delete from S3
        s3_key = f"documents/{filename}"
        doc_service.s3_client.delete_object(
            Bucket=doc_service.config.S3_BUCKET_NAME,
            Key=s3_key
        )

        # Delete text version
        text_key = f"text/{filename}.txt"
        try:
            doc_service.s3_client.delete_object(
                Bucket=doc_service.config.S3_BUCKET_NAME,
                Key=text_key
            )
        except:
            pass  # Text version might not exist

        logger.info(f"Document deleted by {session_id}: {filename}")
        return {"message": f"Document {filename} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/reindex/{filename}")
async def reindex_document(filename: str, request: Request):
    """Re-index a document from S3 to Weaviate"""
    try:
        session_id = get_session_id(request)
        logger.info(f"Re-indexing document: {filename} by {session_id}")

        # Download document from S3
        s3_key = f"documents/{filename}"
        try:
            response = doc_service.s3_client.get_object(
                Bucket=doc_service.config.S3_BUCKET_NAME,
                Key=s3_key
            )
            content = response['Body'].read()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Document not found: {filename}")

        # Extract text content
        text_content = doc_service._extract_text(content, filename)

        if not text_content:
            raise HTTPException(status_code=400, detail=f"No text content extracted from {filename}")

        # Index in Weaviate
        success = weaviate_service.index_document(filename, text_content)

        if success:
            logger.info(f"Successfully re-indexed: {filename}")
            return {"message": f"Document {filename} re-indexed successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to index document")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-indexing document {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/settings")
async def update_settings(settings: SettingsRequest, request: Request):
    """Update embedding and chunking settings"""
    try:
        session_id = get_session_id(request)
        logger.info(f"Settings update from {session_id}: {settings}")
        
        # Update Weaviate service settings
        weaviate_service.update_settings(settings.dict())
        
        return {"message": "Settings updated successfully"}
    except Exception as e:
        logger.error(f"Settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vector-stats")
async def get_vector_stats():
    """Get vector database statistics"""
    try:
        stats = weaviate_service.get_vector_stats()
        return stats
    except Exception as e:
        logger.error(f"Vector stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
