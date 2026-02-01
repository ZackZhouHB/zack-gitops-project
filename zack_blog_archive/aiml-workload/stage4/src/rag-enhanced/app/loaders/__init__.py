"""Document Loaders"""
from .base import LoadedDocument
from .pdf import PDFLoader
from .office import WordLoader, ExcelLoader

__all__ = ["LoadedDocument", "PDFLoader", "WordLoader", "ExcelLoader"]
