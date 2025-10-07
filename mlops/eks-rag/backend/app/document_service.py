import boto3
import io
import time
import logging
from typing import List, Dict, Any
from fastapi import UploadFile
from botocore.exceptions import ClientError
import PyPDF2
import docx
import pandas as pd
from pptx import Presentation

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, config):
        self.config = config
        self.s3_client = None
        self._connect_s3()
    
    def _connect_s3(self):
        """Connect to S3"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.config.AWS_REGION
            )
            logger.info("Connected to S3")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
    
    def check_s3_connection(self) -> bool:
        """Check if S3 is accessible"""
        try:
            if self.s3_client is None:
                return False
            self.s3_client.head_bucket(Bucket=self.config.S3_BUCKET_NAME)
            return True
        except Exception as e:
            logger.error(f"S3 connection check failed: {e}")
            return False
    
    async def upload_to_s3(self, file: UploadFile, user_prefix: str = "") -> bool:
        """Upload file to S3 with text extraction - shared across all users"""
        try:
            # Read file content
            content = await file.read()
            
            # Extract text based on file type
            text_content = self._extract_text(content, file.filename)
            
            # Upload original file to shared location (no user prefix)
            original_key = f"documents/{file.filename}"
            self.s3_client.put_object(
                Bucket=self.config.S3_BUCKET_NAME,
                Key=original_key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream',
                Metadata={
                    'original-filename': file.filename,
                    'upload-timestamp': str(int(time.time())),
                    'uploaded-by': user_prefix
                }
            )
            
            # Upload extracted text for Kendra indexing to shared location
            if text_content:
                text_key = f"text/{file.filename}.txt"
                self.s3_client.put_object(
                    Bucket=self.config.S3_BUCKET_NAME,
                    Key=text_key,
                    Body=text_content.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'source-file': file.filename,
                        'extracted-text': 'true',
                        'uploaded-by': user_prefix
                    }
                )
                logger.info(f"Uploaded {file.filename} to shared location (uploaded by {user_prefix})")
            else:
                logger.warning(f"No text extracted from {file.filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def _extract_text(self, content: bytes, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            file_ext = filename.lower().split('.')[-1]
            
            if file_ext in ['txt', 'md']:
                return content.decode('utf-8')
            
            elif file_ext == 'pdf':
                return self._extract_pdf_text(content)
            
            elif file_ext == 'docx':
                return self._extract_docx_text(content)
            
            elif file_ext in ['xlsx', 'csv']:
                return self._extract_excel_text(content, file_ext)
            
            elif file_ext == 'pptx':
                return self._extract_pptx_text(content)
            
            else:
                logger.warning(f"Unsupported file type: {file_ext}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            return ""
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from Word document"""
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            
            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""
    
    def _extract_excel_text(self, content: bytes, file_ext: str) -> str:
        """Extract text from Excel/CSV"""
        try:
            if file_ext == 'csv':
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
            
            # Convert DataFrame to text representation
            text_parts = []
            text_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
            text_parts.append(f"Rows: {len(df)}")
            text_parts.append("\nData:")
            text_parts.append(df.to_string(max_rows=100))  # Limit to first 100 rows
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting Excel/CSV text: {e}")
            return ""
    
    def _extract_pptx_text(self, content: bytes) -> str:
        """Extract text from PowerPoint"""
        try:
            ppt_file = io.BytesIO(content)
            prs = Presentation(ppt_file)
            
            text_parts = []
            for slide_num, slide in enumerate(prs.slides, 1):
                text_parts.append(f"Slide {slide_num}:")
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_parts.append(shape.text)
                text_parts.append("")  # Empty line between slides
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting PPTX text: {e}")
            return ""
    
    def list_s3_documents(self, user_prefix: str = "") -> List[Dict[str, Any]]:
        """List all shared documents in S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.S3_BUCKET_NAME,
                Prefix="documents/"  # Shared location, no user prefix
            )
            
            documents = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                filename = key.replace("documents/", "")
                
                if filename:  # Skip empty filenames
                    # Get metadata to show who uploaded
                    try:
                        head_response = self.s3_client.head_object(
                            Bucket=self.config.S3_BUCKET_NAME,
                            Key=key
                        )
                        uploaded_by = head_response.get('Metadata', {}).get('uploaded-by', 'unknown')
                    except:
                        uploaded_by = 'unknown'
                    
                    documents.append({
                        'filename': filename,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'key': key,
                        'uploaded_by': uploaded_by
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing S3 documents: {e}")
            return []
    
    async def extract_text_content(self, file: UploadFile) -> str:
        """Extract text content from uploaded file for Weaviate indexing"""
        try:
            content = await file.read()
            # Reset file position for potential re-reading
            await file.seek(0)
            return self._extract_text(content, file.filename)
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""
    
    def delete_s3_document(self, filename: str, user_prefix: str = "") -> bool:
        """Delete document from shared S3 location"""
        try:
            # Delete both original and text versions from shared location
            keys_to_delete = [
                f"documents/{filename}",
                f"text/{filename}.txt"
            ]
            
            for key in keys_to_delete:
                try:
                    self.s3_client.delete_object(
                        Bucket=self.config.S3_BUCKET_NAME,
                        Key=key
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] != 'NoSuchKey':
                        raise
            
            logger.info(f"Deleted {filename} from shared S3 location (requested by {user_prefix})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting S3 document: {e}")
            return False
    
    async def get_document_content(self, filename: str) -> str:
        """Download document from S3 and extract text content"""
        try:
            # Download document from S3
            response = self.s3_client.get_object(
                Bucket=self.config.S3_BUCKET_NAME,
                Key=f"documents/{filename}"
            )
            content = response['Body'].read()
            
            # Extract text content
            return self._extract_text(content, filename)
            
        except Exception as e:
            logger.error(f"Error getting document content for {filename}: {e}")
            return ""
    
    def generate_download_url(self, filename: str, expiration: int = 3600) -> str:
        """Generate a pre-signed URL for downloading a document from S3"""
        try:
            s3_key = f"documents/{filename}"
            
            # Generate pre-signed URL
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config.S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated download URL for {filename} (expires in {expiration}s)")
            return download_url
            
        except Exception as e:
            logger.error(f"Error generating download URL for {filename}: {e}")
            raise e
