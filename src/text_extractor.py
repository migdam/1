"""Multi-format text extraction for books."""

import re
import chardet
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Import extraction libraries with error handling
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import langdetect
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False


class TextExtractor:
    """Extract text from various book formats."""

    def __init__(self, logger=None):
        """Initialize text extractor.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message if logger is available.

        Args:
            level: Log level (info, warning, error, debug)
            message: Message to log
        """
        if self.logger:
            getattr(self.logger, level)(message)

    def extract(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from a file based on its format.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (extracted_text, metadata)
        """
        if not file_path.exists():
            self._log('error', f"File not found: {file_path}")
            return None, {'error': 'File not found'}

        file_format = file_path.suffix.lower()
        self._log('info', f"Extracting text from {file_path.name} ({file_format})")

        start_time = datetime.now()

        try:
            if file_format == '.pdf':
                text, metadata = self._extract_pdf(file_path)
            elif file_format in ['.epub']:
                text, metadata = self._extract_epub(file_path)
            elif file_format in ['.txt']:
                text, metadata = self._extract_txt(file_path)
            elif file_format in ['.docx']:
                text, metadata = self._extract_docx(file_path)
            elif file_format in ['.html', '.htm']:
                text, metadata = self._extract_html(file_path)
            else:
                self._log('warning', f"Unsupported format: {file_format}")
                return None, {'error': f'Unsupported format: {file_format}'}

            # Calculate extraction time
            extraction_time = (datetime.now() - start_time).total_seconds()
            metadata['extraction_time'] = extraction_time

            # Validate and clean text
            if text:
                text = self._clean_text(text)
                metadata['word_count'] = len(text.split())
                metadata['char_count'] = len(text)

                # Detect language
                if HAS_LANGDETECT and text.strip():
                    try:
                        metadata['detected_language'] = langdetect.detect(text[:1000])
                    except:
                        metadata['detected_language'] = 'unknown'

                self._log('info', f"Extracted {metadata.get('word_count', 0)} words in {extraction_time:.2f}s")
            else:
                self._log('warning', f"No text extracted from {file_path.name}")

            return text, metadata

        except Exception as e:
            self._log('error', f"Error extracting text from {file_path.name}: {str(e)}")
            return None, {'error': str(e)}

    def _extract_pdf(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (text, metadata)
        """
        if not HAS_PYMUPDF:
            return None, {'error': 'PyMuPDF not installed'}

        metadata = {}
        text_blocks = []

        try:
            with fitz.open(file_path) as doc:
                # Extract metadata
                metadata['title'] = doc.metadata.get('title', '')
                metadata['author'] = doc.metadata.get('author', '')
                metadata['page_count'] = len(doc)

                # Extract text from each page
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        text_blocks.append(text)

            full_text = '\n\n'.join(text_blocks)
            return full_text, metadata

        except Exception as e:
            return None, {'error': f'PDF extraction error: {str(e)}'}

    def _extract_epub(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from EPUB file.

        Args:
            file_path: Path to EPUB file

        Returns:
            Tuple of (text, metadata)
        """
        if not HAS_EBOOKLIB:
            return None, {'error': 'ebooklib not installed'}

        metadata = {}
        text_blocks = []

        try:
            book = epub.read_epub(str(file_path))

            # Extract metadata
            metadata['title'] = book.get_metadata('DC', 'title')
            metadata['author'] = book.get_metadata('DC', 'creator')

            if metadata['title']:
                metadata['title'] = metadata['title'][0][0] if metadata['title'] else ''
            if metadata['author']:
                metadata['author'] = metadata['author'][0][0] if metadata['author'] else ''

            # Extract text from items
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text()
                    if text.strip():
                        text_blocks.append(text)

            full_text = '\n\n'.join(text_blocks)
            return full_text, metadata

        except Exception as e:
            return None, {'error': f'EPUB extraction error: {str(e)}'}

    def _extract_txt(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from TXT file.

        Args:
            file_path: Path to TXT file

        Returns:
            Tuple of (text, metadata)
        """
        metadata = {}

        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'

            # Read file with detected encoding
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                text = f.read()

            metadata['encoding'] = encoding
            return text, metadata

        except Exception as e:
            return None, {'error': f'TXT extraction error: {str(e)}'}

    def _extract_docx(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from DOCX file.

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (text, metadata)
        """
        if not HAS_DOCX:
            return None, {'error': 'python-docx not installed'}

        metadata = {}
        text_blocks = []

        try:
            doc = Document(file_path)

            # Extract metadata
            core_props = doc.core_properties
            metadata['title'] = core_props.title or ''
            metadata['author'] = core_props.author or ''

            # Extract text from paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_blocks.append(para.text)

            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_blocks.append(cell.text)

            full_text = '\n\n'.join(text_blocks)
            return full_text, metadata

        except Exception as e:
            return None, {'error': f'DOCX extraction error: {str(e)}'}

    def _extract_html(self, file_path: Path) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract text from HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            Tuple of (text, metadata)
        """
        metadata = {}

        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'

            # Read and parse HTML
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract metadata
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text()

            # Extract text
            text = soup.get_text()
            metadata['encoding'] = encoding

            return text, metadata

        except Exception as e:
            return None, {'error': f'HTML extraction error: {str(e)}'}

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple blank lines -> double newline
        text = re.sub(r' +', ' ', text)  # Multiple spaces -> single space
        text = re.sub(r'\t+', ' ', text)  # Tabs -> single space

        # Remove common artifacts
        text = re.sub(r'\x0c', '', text)  # Form feed
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)  # Control characters

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def validate_text(self, text: str, min_length: int = 100) -> bool:
        """Validate that extracted text is usable.

        Args:
            text: Text to validate
            min_length: Minimum character length

        Returns:
            True if text is valid
        """
        if not text:
            return False

        if len(text) < min_length:
            return False

        # Check for reasonable character distribution (not all garbage)
        alphanumeric_count = sum(c.isalnum() for c in text[:1000])
        if alphanumeric_count < 100:  # Less than 10% alphanumeric in first 1000 chars
            return False

        return True


def extract_book_text(
    file_path: Path,
    output_path: Optional[Path] = None,
    logger=None
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Convenience function to extract text from a book file.

    Args:
        file_path: Path to book file
        output_path: Optional path to save extracted text
        logger: Optional logger instance

    Returns:
        Tuple of (text, metadata)
    """
    extractor = TextExtractor(logger=logger)
    text, metadata = extractor.extract(file_path)

    # Save to file if requested
    if text and output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        if logger:
            logger.info(f"Saved extracted text to {output_path}")

    return text, metadata
