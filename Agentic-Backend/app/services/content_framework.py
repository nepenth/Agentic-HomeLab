"""
Multi-Modal Content Framework for unified content processing.

This module provides comprehensive content type detection, metadata extraction,
and unified content modeling for text, images, audio, and structured data.
"""

import hashlib
import json
import mimetypes
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, BinaryIO, TextIO, Tuple
from enum import Enum
from pathlib import Path
import magic
import aiofiles
from PIL import Image
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wave import WAVE

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("content_framework")


class ContentType(Enum):
    """Supported content types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STRUCTURED = "structured"
    BINARY = "binary"
    UNKNOWN = "unknown"


class ContentFormat(Enum):
    """Specific content formats."""
    # Text formats
    PLAIN_TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    HTML = "text/html"
    JSON = "application/json"
    XML = "application/xml"
    CSV = "text/csv"

    # Image formats
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    BMP = "image/bmp"
    TIFF = "image/tiff"

    # Audio formats
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    FLAC = "audio/flac"
    OGG = "audio/ogg"
    M4A = "audio/mp4"

    # Video formats
    MP4 = "video/mp4"
    AVI = "video/avi"
    MOV = "video/quicktime"
    WEBM = "video/webm"

    # Document formats
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@dataclass
class ContentMetadata:
    """Comprehensive content metadata."""
    content_type: ContentType
    format: ContentFormat
    mime_type: str
    size_bytes: int
    encoding: Optional[str] = None
    language: Optional[str] = None
    checksum: Optional[str] = None

    # Text-specific metadata
    char_count: Optional[int] = None
    word_count: Optional[int] = None
    line_count: Optional[int] = None
    avg_word_length: Optional[float] = None

    # Image-specific metadata
    width: Optional[int] = None
    height: Optional[int] = None
    color_mode: Optional[str] = None
    has_alpha: Optional[bool] = None
    dpi: Optional[Tuple[int, int]] = None

    # Audio-specific metadata
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bitrate: Optional[int] = None

    # Document-specific metadata
    page_count: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None

    # Processing metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    quality_score: Optional[float] = None

    # Additional custom metadata
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentData:
    """Unified content data container."""
    id: str
    source_url: Optional[str] = None
    local_path: Optional[str] = None
    original_filename: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    metadata: ContentMetadata = field(default_factory=lambda: ContentMetadata(
        content_type=ContentType.UNKNOWN,
        format=ContentFormat.PLAIN_TEXT,
        mime_type="application/octet-stream",
        size_bytes=0
    ))
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_processing_step(self, step_name: str, result: Any, duration_ms: float):
        """Add a processing step to history."""
        self.processing_history.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "result_summary": str(result)[:200] if result else None
        })
        self.updated_at = datetime.now()

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing history."""
        if not self.processing_history:
            return {"total_steps": 0, "total_time_ms": 0}

        total_time = sum(step["duration_ms"] for step in self.processing_history)
        return {
            "total_steps": len(self.processing_history),
            "total_time_ms": total_time,
            "steps": [step["step"] for step in self.processing_history]
        }


class ContentDetector:
    """Advanced content type detection engine."""

    def __init__(self):
        self.magic = magic.Magic(mime=True)

    async def detect_from_path(self, file_path: str) -> ContentMetadata:
        """Detect content type from file path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get basic file info
        stat = os.stat(file_path)
        size_bytes = stat.st_size

        # Detect MIME type
        mime_type = self.magic.from_file(file_path)

        # Determine content type and format
        content_type, content_format = self._classify_mime_type(mime_type)

        # Create base metadata
        metadata = ContentMetadata(
            content_type=content_type,
            format=content_format,
            mime_type=mime_type,
            size_bytes=size_bytes
        )

        # Extract detailed metadata based on type
        await self._extract_detailed_metadata(file_path, metadata)

        return metadata

    async def detect_from_bytes(self, data: bytes, filename: Optional[str] = None) -> ContentMetadata:
        """Detect content type from bytes."""
        size_bytes = len(data)

        # Try filename-based detection first
        if filename:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                content_type, content_format = self._classify_mime_type(mime_type)
                metadata = ContentMetadata(
                    content_type=content_type,
                    format=content_format,
                    mime_type=mime_type,
                    size_bytes=size_bytes
                )
                return metadata

        # Fallback to magic number detection
        mime_type = self.magic.from_buffer(data)
        content_type, content_format = self._classify_mime_type(mime_type)

        return ContentMetadata(
            content_type=content_type,
            format=content_format,
            mime_type=mime_type,
            size_bytes=size_bytes
        )

    async def detect_from_url(self, url: str) -> ContentMetadata:
        """Detect content type from URL (basic implementation)."""
        # Extract extension from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if filename:
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type:
                content_type, content_format = self._classify_mime_type(mime_type)
                return ContentMetadata(
                    content_type=content_type,
                    format=content_format,
                    mime_type=mime_type,
                    size_bytes=0  # Unknown for URLs
                )

        # Default fallback
        return ContentMetadata(
            content_type=ContentType.UNKNOWN,
            format=ContentFormat.PLAIN_TEXT,
            mime_type="application/octet-stream",
            size_bytes=0
        )

    def _classify_mime_type(self, mime_type: str) -> Tuple[ContentType, ContentFormat]:
        """Classify MIME type into content type and format."""
        # Text formats
        if mime_type.startswith("text/"):
            if mime_type == "text/plain":
                return ContentType.TEXT, ContentFormat.PLAIN_TEXT
            elif mime_type == "text/markdown":
                return ContentType.TEXT, ContentFormat.MARKDOWN
            elif mime_type == "text/html":
                return ContentType.TEXT, ContentFormat.HTML
            elif mime_type == "text/csv":
                return ContentType.STRUCTURED, ContentFormat.CSV
            else:
                return ContentType.TEXT, ContentFormat.PLAIN_TEXT

        # JSON/XML
        elif mime_type == "application/json":
            return ContentType.STRUCTURED, ContentFormat.JSON
        elif mime_type in ["application/xml", "text/xml"]:
            return ContentType.STRUCTURED, ContentFormat.XML

        # Image formats
        elif mime_type.startswith("image/"):
            format_map = {
                "image/jpeg": ContentFormat.JPEG,
                "image/png": ContentFormat.PNG,
                "image/gif": ContentFormat.GIF,
                "image/webp": ContentFormat.WEBP,
                "image/bmp": ContentFormat.BMP,
                "image/tiff": ContentFormat.TIFF
            }
            content_format = format_map.get(mime_type, ContentFormat.JPEG)
            return ContentType.IMAGE, content_format

        # Audio formats
        elif mime_type.startswith("audio/"):
            format_map = {
                "audio/mpeg": ContentFormat.MP3,
                "audio/wav": ContentFormat.WAV,
                "audio/flac": ContentFormat.FLAC,
                "audio/ogg": ContentFormat.OGG,
                "audio/mp4": ContentFormat.M4A
            }
            content_format = format_map.get(mime_type, ContentFormat.MP3)
            return ContentType.AUDIO, content_format

        # Video formats
        elif mime_type.startswith("video/"):
            format_map = {
                "video/mp4": ContentFormat.MP4,
                "video/avi": ContentFormat.AVI,
                "video/quicktime": ContentFormat.MOV,
                "video/webm": ContentFormat.WEBM
            }
            content_format = format_map.get(mime_type, ContentFormat.MP4)
            return ContentType.VIDEO, content_format

        # Document formats
        elif mime_type == "application/pdf":
            return ContentType.DOCUMENT, ContentFormat.PDF
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return ContentType.DOCUMENT, ContentFormat.DOCX
        elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return ContentType.DOCUMENT, ContentFormat.XLSX
        elif mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            return ContentType.DOCUMENT, ContentFormat.PPTX

        # Binary/unknown
        else:
            return ContentType.BINARY, ContentFormat.PLAIN_TEXT

    async def _extract_detailed_metadata(self, file_path: str, metadata: ContentMetadata):
        """Extract detailed metadata based on content type."""
        start_time = datetime.now()

        try:
            if metadata.content_type == ContentType.TEXT:
                await self._extract_text_metadata(file_path, metadata)
            elif metadata.content_type == ContentType.IMAGE:
                await self._extract_image_metadata(file_path, metadata)
            elif metadata.content_type == ContentType.AUDIO:
                await self._extract_audio_metadata(file_path, metadata)
            elif metadata.content_type == ContentType.DOCUMENT:
                await self._extract_document_metadata(file_path, metadata)

            # Calculate checksum
            metadata.checksum = await self._calculate_checksum(file_path)

        except Exception as e:
            logger.warning(f"Failed to extract detailed metadata for {file_path}: {e}")

        # Record processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        metadata.processing_time_ms = processing_time

    async def _extract_text_metadata(self, file_path: str, metadata: ContentMetadata):
        """Extract text-specific metadata."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            metadata.char_count = len(content)
            words = content.split()
            metadata.word_count = len(words)
            metadata.line_count = content.count('\n') + 1

            if words:
                metadata.avg_word_length = sum(len(word) for word in words) / len(words)

            # Detect encoding (simplified)
            metadata.encoding = "utf-8"

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                    content = await f.read()
                metadata.encoding = "latin-1"
                metadata.char_count = len(content)
            except Exception:
                metadata.encoding = "unknown"

    async def _extract_image_metadata(self, file_path: str, metadata: ContentMetadata):
        """Extract image-specific metadata."""
        try:
            with Image.open(file_path) as img:
                metadata.width = img.width
                metadata.height = img.height
                metadata.color_mode = img.mode
                metadata.has_alpha = img.mode in ('RGBA', 'LA', 'P')

                # Get DPI if available
                if hasattr(img, 'info') and 'dpi' in img.info:
                    dpi = img.info['dpi']
                    if isinstance(dpi, tuple):
                        metadata.dpi = dpi
                    else:
                        metadata.dpi = (dpi, dpi)

        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")

    async def _extract_audio_metadata(self, file_path: str, metadata: ContentMetadata):
        """Extract audio-specific metadata."""
        try:
            # Try different audio formats
            audio_file = None

            if file_path.lower().endswith('.mp3'):
                audio_file = MP3(file_path)
            elif file_path.lower().endswith('.flac'):
                audio_file = FLAC(file_path)
            elif file_path.lower().endswith('.wav'):
                audio_file = WAVE(file_path)
            else:
                # Try mutagen's generic loader
                from mutagen import File
                audio_file = File(file_path)

            if audio_file:
                metadata.duration_seconds = audio_file.info.length
                metadata.sample_rate = getattr(audio_file.info, 'sample_rate', None)
                metadata.channels = getattr(audio_file.info, 'channels', None)
                metadata.bitrate = getattr(audio_file.info, 'bitrate', None)

        except Exception as e:
            logger.warning(f"Failed to extract audio metadata: {e}")

    async def _extract_document_metadata(self, file_path: str, metadata: ContentMetadata):
        """Extract document-specific metadata."""
        # Basic implementation - could be extended with libraries like PyPDF2, python-docx, etc.
        try:
            if file_path.lower().endswith('.pdf'):
                # Placeholder for PDF metadata extraction
                metadata.page_count = 1  # Would need PyPDF2
            elif file_path.lower().endswith('.docx'):
                # Placeholder for DOCX metadata extraction
                metadata.page_count = 1  # Would need python-docx

        except Exception as e:
            logger.warning(f"Failed to extract document metadata: {e}")

    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                data = await f.read(65536)  # 64KB chunks
                if not data:
                    break
                sha256.update(data)

        return sha256.hexdigest()


class ContentCache:
    """Intelligent content caching with invalidation strategies."""

    def __init__(self, cache_dir: Optional[str] = None, max_size_mb: int = 1000):
        self.cache_dir = Path(cache_dir or settings.cache_dir or "/tmp/content_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.cache_index: Dict[str, Dict[str, Any]] = {}

        # Load existing cache index
        self._load_cache_index()

    def _load_cache_index(self):
        """Load cache index from disk."""
        index_file = self.cache_dir / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    self.cache_index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self.cache_index = {}

    def _save_cache_index(self):
        """Save cache index to disk."""
        index_file = self.cache_dir / "cache_index.json"
        try:
            with open(index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def _get_cache_key(self, content_id: str, operation: str) -> str:
        """Generate cache key."""
        return f"{content_id}_{operation}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{cache_key}.cache"

    async def get(self, content_id: str, operation: str) -> Optional[Any]:
        """Get cached content."""
        cache_key = self._get_cache_key(content_id, operation)
        cache_path = self._get_cache_path(cache_key)

        if cache_key not in self.cache_index or not cache_path.exists():
            return None

        cache_info = self.cache_index[cache_key]

        # Check if cache is expired
        if self._is_cache_expired(cache_info):
            await self.invalidate(content_id, operation)
            return None

        try:
            async with aiofiles.open(cache_path, 'rb') as f:
                data = await f.read()

            # Update access time
            cache_info['last_accessed'] = datetime.now().isoformat()
            self._save_cache_index()

            return data

        except Exception as e:
            logger.warning(f"Failed to read cache for {cache_key}: {e}")
            return None

    async def put(self, content_id: str, operation: str, data: bytes, ttl_seconds: int = 3600):
        """Store content in cache."""
        cache_key = self._get_cache_key(content_id, operation)
        cache_path = self._get_cache_path(cache_key)

        # Check cache size limits
        await self._enforce_size_limits()

        try:
            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(data)

            # Update index
            self.cache_index[cache_key] = {
                'content_id': content_id,
                'operation': operation,
                'size_bytes': len(data),
                'created_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'ttl_seconds': ttl_seconds
            }

            self._save_cache_index()

        except Exception as e:
            logger.error(f"Failed to write cache for {cache_key}: {e}")

    async def invalidate(self, content_id: str, operation: Optional[str] = None):
        """Invalidate cache entries."""
        keys_to_remove = []

        if operation:
            cache_key = self._get_cache_key(content_id, operation)
            keys_to_remove.append(cache_key)
        else:
            # Invalidate all operations for this content
            for cache_key, info in self.cache_index.items():
                if info['content_id'] == content_id:
                    keys_to_remove.append(cache_key)

        for cache_key in keys_to_remove:
            if cache_key in self.cache_index:
                cache_path = self._get_cache_path(cache_key)
                try:
                    if cache_path.exists():
                        cache_path.unlink()
                    del self.cache_index[cache_key]
                except Exception as e:
                    logger.warning(f"Failed to remove cache entry {cache_key}: {e}")

        if keys_to_remove:
            self._save_cache_index()

    def _is_cache_expired(self, cache_info: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        created_at = datetime.fromisoformat(cache_info['created_at'])
        ttl_seconds = cache_info.get('ttl_seconds', 3600)
        return (datetime.now() - created_at).total_seconds() > ttl_seconds

    async def _enforce_size_limits(self):
        """Enforce cache size limits by removing oldest entries."""
        total_size = sum(info['size_bytes'] for info in self.cache_index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if total_size <= max_size_bytes:
            return

        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self.cache_index.items(),
            key=lambda x: x[1]['last_accessed']
        )

        # Remove oldest entries until under limit
        for cache_key, info in sorted_entries:
            if total_size <= max_size_bytes:
                break

            cache_path = self._get_cache_path(cache_key)
            try:
                if cache_path.exists():
                    size = cache_path.stat().st_size
                    cache_path.unlink()
                    total_size -= size
                del self.cache_index[cache_key]
            except Exception as e:
                logger.warning(f"Failed to remove cache entry {cache_key}: {e}")

        self._save_cache_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(info['size_bytes'] for info in self.cache_index.values())
        total_entries = len(self.cache_index)

        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.max_size_mb,
            'utilization_percent': (total_size / (self.max_size_mb * 1024 * 1024)) * 100
        }


class ContentProcessor:
    """Unified content processing interface."""

    def __init__(self, cache: Optional[ContentCache] = None):
        self.detector = ContentDetector()
        self.cache = cache or ContentCache()

    async def process_file(self, file_path: str) -> ContentData:
        """Process a file and return unified content data."""
        # Detect content type and extract metadata
        metadata = await self.detector.detect_from_path(file_path)

        # Create content data object
        content_id = hashlib.md5(file_path.encode()).hexdigest()[:8]

        content_data = ContentData(
            id=content_id,
            local_path=file_path,
            original_filename=os.path.basename(file_path),
            metadata=metadata
        )

        # Load content if it's text-based
        if metadata.content_type in [ContentType.TEXT, ContentType.STRUCTURED]:
            try:
                async with aiofiles.open(file_path, 'r', encoding=metadata.encoding or 'utf-8') as f:
                    content_data.content = await f.read()
            except Exception as e:
                logger.warning(f"Failed to read text content from {file_path}: {e}")

        return content_data

    async def process_bytes(self, data: bytes, filename: Optional[str] = None) -> ContentData:
        """Process bytes and return unified content data."""
        # Detect content type
        metadata = await self.detector.detect_from_bytes(data, filename)

        # Create content data object
        content_id = hashlib.md5(data[:100]).hexdigest()[:8]  # Use first 100 bytes for ID

        content_data = ContentData(
            id=content_id,
            original_filename=filename,
            metadata=metadata
        )

        # Set content based on type
        if metadata.content_type in [ContentType.TEXT, ContentType.STRUCTURED]:
            try:
                content_data.content = data.decode(metadata.encoding or 'utf-8')
            except UnicodeDecodeError:
                content_data.content = data  # Keep as bytes
        else:
            content_data.content = data

        return content_data

    async def process_url(self, url: str) -> ContentData:
        """Process content from URL."""
        # Detect content type from URL
        metadata = await self.detector.detect_from_url(url)

        # Create content data object
        content_id = hashlib.md5(url.encode()).hexdigest()[:8]

        content_data = ContentData(
            id=content_id,
            source_url=url,
            metadata=metadata
        )

        return content_data

    async def enrich_metadata(self, content_data: ContentData) -> ContentData:
        """Enrich content metadata with additional analysis."""
        # This could include language detection, quality scoring, etc.
        # For now, just calculate a basic quality score

        metadata = content_data.metadata

        # Basic quality scoring
        quality_score = 0.5  # Base score

        if metadata.content_type == ContentType.TEXT:
            if metadata.word_count and metadata.word_count > 10:
                quality_score += 0.2
            if metadata.language:
                quality_score += 0.1

        elif metadata.content_type == ContentType.IMAGE:
            if metadata.width and metadata.height:
                # Prefer reasonable image sizes
                total_pixels = metadata.width * metadata.height
                if 10000 < total_pixels < 20000000:  # 10K to 20M pixels
                    quality_score += 0.3

        elif metadata.content_type == ContentType.AUDIO:
            if metadata.duration_seconds and metadata.duration_seconds > 10:
                quality_score += 0.2
            if metadata.bitrate and metadata.bitrate > 128000:  # >128kbps
                quality_score += 0.1

        metadata.quality_score = min(quality_score, 1.0)
        return content_data


# Global instances
content_detector = ContentDetector()
content_cache = ContentCache()
content_processor = ContentProcessor(content_cache)