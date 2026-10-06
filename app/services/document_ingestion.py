import logging
import re
from typing import List, Dict, Any
from pathlib import Path
import pypdf
from docx import Document as DocxDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentIngestionService:
    """Service for ingesting and processing documents."""
    
    def __init__(self):
        """Initialize the document ingestion service."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Initialized DocumentIngestionService with model: {settings.embedding_model}")
    
    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        Extract text from various file formats.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (pdf, docx, txt, md)
            
        Returns:
            Extracted text content
        """
        try:
            if file_type.lower() == 'pdf':
                return self._extract_from_pdf(file_path)
            elif file_type.lower() in ['docx', 'doc']:
                return self._extract_from_docx(file_path)
            elif file_type.lower() in ['txt', 'md']:
                return self._extract_from_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()

    def extract_pages(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """Extract text while preserving page locations when the format has pages."""
        if file_type.lower() == "pdf":
            pages = []
            with open(file_path, "rb") as file:
                for page_number, page in enumerate(
                    pypdf.PdfReader(file).pages,
                    start=1,
                ):
                    pages.append({
                        "page_number": page_number,
                        "text": page.extract_text() or "",
                    })
            return pages
        return [{
            "page_number": None,
            "text": self.extract_text(file_path, file_type),
        }]

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize extracted text without interpreting document instructions."""
        text = text.replace("\x00", "")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        doc = DocxDocument(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    def _extract_from_text(self, file_path: str) -> str:
        """Extract text from plain text file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        chunks = self.text_splitter.split_text(text)
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            texts: List of text chunks
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
    
    def process_document(self, file_path: str, file_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a document end-to-end.
        
        Args:
            file_path: Path to the document
            file_type: Type of file
            metadata: Optional metadata
            
        Returns:
            Dictionary with processed chunks and embeddings
        """
        logger.info(f"Processing document: {file_path}")
        
        chunks = []
        chunk_metadata = []
        for page in self.extract_pages(file_path, file_type):
            page_text = self.clean_text(page["text"])
            if not page_text:
                continue
            for chunk in self.chunk_text(page_text):
                chunks.append(chunk)
                chunk_metadata.append({
                    "page_number": page["page_number"],
                    **(metadata or {}),
                })
        
        embeddings = self.generate_embeddings(chunks) if chunks else []
        
        return {
            "chunks": chunks,
            "embeddings": embeddings,
            "chunk_metadata": chunk_metadata,
            "metadata": metadata or {},
            "num_chunks": len(chunks)
        }


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> DocumentIngestionService:
    """Get singleton instance of DocumentIngestionService."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService()
    return _ingestion_service
