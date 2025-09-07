"""
Content Validation and Sanitization Service.

This service provides comprehensive validation and sanitization for different content types
including text, images, audio, and video content to ensure security and data integrity.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import magic
import mimetypes
from pathlib import Path

from app.utils.logging import get_logger

logger = get_logger("content_validation_service")


class ContentValidationService:
    """Service for validating and sanitizing content."""

    def __init__(self):
        # Content type validation rules
        self.max_file_sizes = {
            'text': 10 * 1024 * 1024,      # 10MB
            'image': 50 * 1024 * 1024,     # 50MB
            'audio': 100 * 1024 * 1024,    # 100MB
            'video': 500 * 1024 * 1024,    # 500MB
            'document': 25 * 1024 * 1024,  # 25MB
        }

        # Allowed MIME types
        self.allowed_mime_types = {
            'text': [
                'text/plain', 'text/html', 'text/markdown', 'text/csv',
                'application/json', 'application/xml', 'application/pdf'
            ],
            'image': [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'image/svg+xml', 'image/bmp', 'image/tiff'
            ],
            'audio': [
                'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac',
                'audio/aac', 'audio/mp4', 'audio/webm'
            ],
            'video': [
                'video/mp4', 'video/webm', 'video/ogg', 'video/avi',
                'video/mov', 'video/wmv', 'video/flv'
            ],
            'document': [
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain', 'text/csv'
            ]
        }

        # Dangerous file signatures to block
        self.dangerous_signatures = [
            b'<?php', b'<%', b'<script', b'javascript:',
            b'vbscript:', b'onload=', b'onerror=',
            b'<iframe', b'<object', b'<embed'
        ]

    async def validate_content(
        self,
        content: bytes,
        content_type: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate content based on type and security rules.

        Args:
            content: Raw content bytes
            content_type: Type of content (text, image, audio, video, document)
            filename: Original filename if available
            metadata: Additional metadata

        Returns:
            Validation result with status and details
        """
        try:
            result = {
                'is_valid': True,
                'content_type': content_type,
                'warnings': [],
                'errors': [],
                'sanitized': False,
                'metadata': metadata or {},
                'validated_at': datetime.now().isoformat()
            }

            # Size validation
            if not self._validate_size(content, content_type):
                result['is_valid'] = False
                result['errors'].append(f"Content size exceeds maximum allowed for {content_type}")

            # MIME type validation
            detected_mime = self._detect_mime_type(content, filename)
            if not self._validate_mime_type(detected_mime, content_type):
                result['is_valid'] = False
                result['errors'].append(f"Invalid MIME type {detected_mime} for {content_type}")
            else:
                result['metadata']['detected_mime_type'] = detected_mime

            # Security validation
            security_issues = self._check_security(content, content_type)
            if security_issues:
                result['warnings'].extend(security_issues)
                if any('dangerous' in issue.lower() for issue in security_issues):
                    result['is_valid'] = False
                    result['errors'].extend(security_issues)

            # Content-specific validation
            content_validation = await self._validate_content_specific(content, content_type)
            if not content_validation['valid']:
                result['is_valid'] = False
                result['errors'].extend(content_validation['errors'])

            result['metadata'].update(content_validation.get('metadata', {}))

            # Sanitization if needed
            if result['is_valid'] and content_type in ['text', 'document']:
                sanitized_content, was_sanitized = self._sanitize_content(content, content_type)
                if was_sanitized:
                    result['sanitized'] = True
                    result['metadata']['original_size'] = len(content)
                    result['metadata']['sanitized_size'] = len(sanitized_content)

            logger.info(f"Content validation completed: valid={result['is_valid']}, type={content_type}")
            return result

        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return {
                'is_valid': False,
                'content_type': content_type,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'sanitized': False,
                'metadata': metadata or {},
                'validated_at': datetime.now().isoformat()
            }

    def _validate_size(self, content: bytes, content_type: str) -> bool:
        """Validate content size against limits."""
        max_size = self.max_file_sizes.get(content_type, 10 * 1024 * 1024)  # 10MB default
        return len(content) <= max_size

    def _detect_mime_type(self, content: bytes, filename: Optional[str] = None) -> str:
        """Detect MIME type from content and filename."""
        try:
            # First try magic library for content-based detection
            detected = magic.from_buffer(content, mime=True)
            if detected and detected != 'application/octet-stream':
                return detected
        except Exception:
            pass

        # Fallback to filename-based detection
        if filename:
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                return guessed

        return 'application/octet-stream'

    def _validate_mime_type(self, mime_type: str, content_type: str) -> bool:
        """Validate MIME type against allowed types."""
        allowed_types = self.allowed_mime_types.get(content_type, [])
        return mime_type in allowed_types

    def _check_security(self, content: bytes, content_type: str) -> List[str]:
        """Check content for security issues."""
        issues = []

        # Check for dangerous file signatures
        content_str = content.decode('utf-8', errors='ignore').lower()
        for signature in self.dangerous_signatures:
            if signature in content:
                issues.append(f"Dangerous content signature detected: {signature.decode()}")

        # Check for suspicious patterns
        if content_type in ['text', 'document']:
            suspicious_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'vbscript:',
                r'on\w+\s*=',
                r'<iframe[^>]*>',
                r'<object[^>]*>',
                r'<embed[^>]*>'
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, content_str, re.IGNORECASE | re.DOTALL):
                    issues.append(f"Suspicious pattern detected: {pattern}")

        # Check for extremely long lines (potential DoS)
        lines = content_str.split('\n')
        long_lines = [line for line in lines if len(line) > 10000]
        if long_lines:
            issues.append(f"Detected {len(long_lines)} extremely long lines (potential DoS)")

        return issues

    async def _validate_content_specific(self, content: bytes, content_type: str) -> Dict[str, Any]:
        """Perform content-type specific validation."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        if content_type == 'text':
            result.update(await self._validate_text_content(content))
        elif content_type == 'image':
            result.update(await self._validate_image_content(content))
        elif content_type == 'audio':
            result.update(await self._validate_audio_content(content))
        elif content_type == 'video':
            result.update(await self._validate_video_content(content))
        elif content_type == 'document':
            result.update(await self._validate_document_content(content))

        return result

    async def _validate_text_content(self, content: bytes) -> Dict[str, Any]:
        """Validate text content."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        try:
            text = content.decode('utf-8')

            # Check encoding
            if len(content) != len(text.encode('utf-8')):
                result['errors'].append("Content contains invalid UTF-8 characters")

            # Check for null bytes
            if '\x00' in text:
                result['errors'].append("Content contains null bytes")

            # Basic text statistics
            result['metadata'].update({
                'character_count': len(text),
                'line_count': len(text.split('\n')),
                'word_count': len(text.split()),
                'encoding': 'utf-8'
            })

        except UnicodeDecodeError:
            result['valid'] = False
            result['errors'].append("Content is not valid UTF-8 text")

        return result

    async def _validate_image_content(self, content: bytes) -> Dict[str, Any]:
        """Validate image content."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        # Basic image validation - check for common image headers
        if len(content) < 8:
            result['valid'] = False
            result['errors'].append("Content too small to be a valid image")
            return result

        # Check for common image signatures
        signatures = {
            b'\xff\xd8\xff': 'JPEG',
            b'\x89PNG\r\n\x1a\n': 'PNG',
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF',
            b'RIFF': 'WebP/RIFF',
            b'BM': 'BMP'
        }

        detected_format = None
        for sig, fmt in signatures.items():
            if content.startswith(sig):
                detected_format = fmt
                break

        if not detected_format:
            result['valid'] = False
            result['errors'].append("No valid image signature detected")
        else:
            result['metadata']['detected_format'] = detected_format

        return result

    async def _validate_audio_content(self, content: bytes) -> Dict[str, Any]:
        """Validate audio content."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        if len(content) < 12:
            result['valid'] = False
            result['errors'].append("Content too small to be valid audio")
            return result

        # Check for common audio signatures
        signatures = {
            b'ID3': 'MP3 with ID3',
            b'RIFF': 'WAV',
            b'OggS': 'OGG',
            b'fLaC': 'FLAC'
        }

        detected_format = None
        for sig, fmt in signatures.items():
            if content.startswith(sig):
                detected_format = fmt
                break

        if not detected_format:
            result['warnings'] = ["Could not detect audio format from signature"]
        else:
            result['metadata']['detected_format'] = detected_format

        return result

    async def _validate_video_content(self, content: bytes) -> Dict[str, Any]:
        """Validate video content."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        if len(content) < 12:
            result['valid'] = False
            result['errors'].append("Content too small to be valid video")
            return result

        # Check for common video signatures
        signatures = {
            b'ftyp': 'MP4',
            b'RIFF': 'AVI',
            b'FLV': 'FLV'
        }

        detected_format = None
        for sig, fmt in signatures.items():
            if sig in content[:20]:  # Check in first 20 bytes
                detected_format = fmt
                break

        if not detected_format:
            result['warnings'] = ["Could not detect video format from signature"]
        else:
            result['metadata']['detected_format'] = detected_format

        return result

    async def _validate_document_content(self, content: bytes) -> Dict[str, Any]:
        """Validate document content."""
        result = {'valid': True, 'errors': [], 'metadata': {}}

        # Check for PDF signature
        if content.startswith(b'%PDF-'):
            result['metadata']['document_type'] = 'PDF'
        # Check for Office document signatures
        elif content.startswith(b'PK\x03\x04'):  # ZIP-based Office documents
            result['metadata']['document_type'] = 'Office Document'
        elif content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):  # OLE2 (older Office)
            result['metadata']['document_type'] = 'Legacy Office Document'
        else:
            result['warnings'] = ["Could not detect document format"]

        return result

    def _sanitize_content(self, content: bytes, content_type: str) -> tuple[bytes, bool]:
        """Sanitize content to remove potentially dangerous elements."""
        if content_type not in ['text', 'document']:
            return content, False

        try:
            text = content.decode('utf-8')
            original_text = text

            # Remove potentially dangerous HTML/script content
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',
                r'<iframe[^>]*>.*?</iframe>',
                r'<object[^>]*>.*?</object>',
                r'<embed[^>]*>.*?</embed>',
                r'on\w+\s*=',
                r'javascript:',
                r'vbscript:',
                r'data:text/html'
            ]

            for pattern in dangerous_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

            # Remove null bytes
            text = text.replace('\x00', '')

            # Check if content was modified
            was_modified = text != original_text

            return text.encode('utf-8'), was_modified

        except Exception as e:
            logger.warning(f"Content sanitization failed: {e}")
            return content, False

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return {
            'max_file_sizes': self.max_file_sizes,
            'supported_content_types': list(self.allowed_mime_types.keys()),
            'total_mime_types_supported': sum(len(types) for types in self.allowed_mime_types.values()),
            'dangerous_signatures_count': len(self.dangerous_signatures)
        }


# Global instance
content_validation_service = ContentValidationService()