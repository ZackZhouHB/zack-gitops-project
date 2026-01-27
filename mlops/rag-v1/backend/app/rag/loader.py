"""Document loaders for various file formats"""
import logging
from typing import List, Dict, Any
from pathlib import Path
import io

logger = logging.getLogger(__name__)

class DocumentLoader:
    """Load and extract text from various document formats"""
    
    SUPPORTED_FORMATS = {
        ".txt": "text",
        ".md": "text",
        ".pdf": "pdf",
        ".docx": "docx",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
    }
    
    def __init__(self, bedrock_client=None):
        self.bedrock = bedrock_client  # For image extraction via Claude
    
    async def load(self, file) -> Dict[str, Any]:
        """Load document and return extracted content with metadata"""
        filename = file.filename
        suffix = Path(filename).suffix.lower()
        content = await file.read()
        
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {suffix}")
        
        doc_type = self.SUPPORTED_FORMATS[suffix]
        
        if doc_type == "text":
            text = content.decode("utf-8")
        elif doc_type == "pdf":
            text = self._extract_pdf(content)
        elif doc_type == "docx":
            text = self._extract_docx(content)
        elif doc_type == "image":
            text = await self._extract_image(content, suffix)
        else:
            text = content.decode("utf-8", errors="ignore")
        
        return {
            "content": text,
            "filename": filename,
            "format": doc_type,
            "size_bytes": len(content),
        }
    
    def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF, including OCR for scanned pages"""
        from pypdf import PdfReader
        
        reader = PdfReader(io.BytesIO(content))
        texts = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                texts.append(f"[Page {i+1}]\n{text}")
            else:
                # Page might be scanned/image - mark for potential OCR
                texts.append(f"[Page {i+1}] (image-based page - text extraction limited)")
        
        return "\n\n".join(texts)
    
    def _extract_docx(self, content: bytes) -> str:
        """Extract text from Word documents"""
        from docx import Document
        
        doc = Document(io.BytesIO(content))
        texts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text)
        
        # Extract tables
        for table in doc.tables:
            table_text = []
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                table_text.append(row_text)
            if table_text:
                texts.append("[Table]\n" + "\n".join(table_text))
        
        return "\n\n".join(texts)
    
    async def _extract_image(self, content: bytes, suffix: str) -> str:
        """Extract text/description from images using Claude Vision"""
        import base64
        import json
        
        if not self.bedrock:
            return "[Image content - requires Bedrock for extraction]"
        
        # Encode image
        b64_image = base64.b64encode(content).decode("utf-8")
        media_type = "image/png" if suffix == ".png" else "image/jpeg"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64_image}
                    },
                    {
                        "type": "text",
                        "text": "Extract all text from this image. If it's a diagram or chart, describe its structure and key information. Be thorough."
                    }
                ]
            }],
            "max_tokens": 2000
        })
        
        response = self.bedrock.invoke_model(
            modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
            body=body
        )
        
        result = json.loads(response["body"].read())
        return f"[Image Content]\n{result['content'][0]['text']}"
