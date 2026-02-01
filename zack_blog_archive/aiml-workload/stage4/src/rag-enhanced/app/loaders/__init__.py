"""Document Loaders"""
from .base import LoadedDocument
from .pdf import PDFLoader
from .office import WordLoader, ExcelLoader
from .web import WebLoader
from .confluence import ConfluenceLoader

__all__ = ["LoadedDocument", "PDFLoader", "WordLoader", "ExcelLoader", "WebLoader", "ConfluenceLoader"]
