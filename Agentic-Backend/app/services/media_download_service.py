"""
Media Download Service

This service handles downloading and caching media files from various sources,
with support for rate limiting, error handling, and storage management.
"""

import asyncio
import aiofiles
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import mimetypes
from urllib.parse import urlparse

from app.utils.logging import get_logger

logger = get_logger("media_download_service")


class MediaDownloadError(Exception):
    """Custom exception for media download operations."""
    pass


class DownloadResult:
    """Result of a media download operation."""

    def __init__(self):
        self.success = True
        self.file_path = ""
        self.file_size = 0
        self.content_type = ""
        self.download_time = 0.0
        self.error_message = ""
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "download_time": self.download_time,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class MediaDownloadService:
    """Service for downloading and managing media files."""

    def __init__(
        self,
        cache_dir: str = "/app/media_cache",
        max_concurrent_downloads: int = 3,
        timeout_seconds: int = 30,
        max_file_size_mb: int = 50
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent_downloads
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.semaphore = asyncio.Semaphore(max_concurrent_downloads)

        # Supported media types
        self.supported_types = {
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
            'video': ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/webm'],
            'audio': ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/m4a']
        }

        # Rate limiting (requests per minute per domain)
        self.rate_limits = {}
        self.request_counts = {}

    async def download_media(
        self,
        url: str,
        filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> DownloadResult:
        """
        Download media from URL and save to cache directory.

        Args:
            url: Media URL to download
            filename: Optional custom filename
            headers: Optional HTTP headers

        Returns:
            DownloadResult with download information
        """
        async with self.semaphore:  # Limit concurrent downloads
            result = DownloadResult()
            start_time = datetime.now()

            try:
                # Check rate limit
                domain = urlparse(url).netloc
                if not await self._check_rate_limit(domain):
                    result.success = False
                    result.error_message = f"Rate limit exceeded for domain: {domain}"
                    return result

                # Generate filename if not provided
                if not filename:
                    filename = self._generate_filename(url)

                file_path = self.cache_dir / filename

                # Check if file already exists
                if file_path.exists():
                    result.success = True
                    result.file_path = str(file_path)
                    result.file_size = file_path.stat().st_size
                    result.content_type = self._get_content_type_from_path(file_path)
                    result.download_time = 0.0
                    result.metadata = {"cached": True}
                    return result

                # Download the file
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    request_headers = headers or {}
                    request_headers.update({
                        'User-Agent': 'Agentic-Backend/1.0',
                        'Accept': '*/*'
                    })

                    async with session.get(url, headers=request_headers) as response:
                        if response.status != 200:
                            result.success = False
                            result.error_message = f"HTTP {response.status}: {response.reason}"
                            return result

                        # Check content type
                        content_type = response.headers.get('content-type', '').lower()
                        if not self._is_supported_content_type(content_type):
                            result.success = False
                            result.error_message = f"Unsupported content type: {content_type}"
                            return result

                        # Check content length
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > self.max_file_size:
                            result.success = False
                            result.error_message = f"File too large: {content_length} bytes (max: {self.max_file_size})"
                            return result

                        # Download and save file
                        downloaded_size = 0
                        async with aiofiles.open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                if downloaded_size + len(chunk) > self.max_file_size:
                                    result.success = False
                                    result.error_message = "File size limit exceeded during download"
                                    file_path.unlink(missing_ok=True)
                                    return result

                                await f.write(chunk)
                                downloaded_size += len(chunk)

                        # Verify download
                        if not file_path.exists():
                            result.success = False
                            result.error_message = "File was not saved successfully"
                            return result

                        result.success = True
                        result.file_path = str(file_path)
                        result.file_size = downloaded_size
                        result.content_type = content_type or self._get_content_type_from_path(file_path)
                        result.download_time = (datetime.now() - start_time).total_seconds()
                        result.metadata = {
                            "url": url,
                            "domain": domain,
                            "headers": dict(response.headers),
                            "cached": False
                        }

                        logger.info(f"Downloaded media: {url} -> {file_path} ({downloaded_size} bytes)")
                        return result

            except asyncio.TimeoutError:
                result.success = False
                result.error_message = "Download timeout"
            except aiohttp.ClientError as e:
                result.success = False
                result.error_message = f"Network error: {str(e)}"
            except Exception as e:
                result.success = False
                result.error_message = f"Download failed: {str(e)}"
                logger.error(f"Media download failed for {url}: {e}")

            result.download_time = (datetime.now() - start_time).total_seconds()
            return result

    async def batch_download_media(
        self,
        urls: List[Dict[str, Any]]
    ) -> List[DownloadResult]:
        """
        Download multiple media files in batch.

        Args:
            urls: List of dictionaries with 'url' and optional 'filename' keys

        Returns:
            List of DownloadResult objects
        """
        async def download_single(item: Dict[str, Any]) -> DownloadResult:
            """Download a single media file with error handling."""
            try:
                url = item.get('url')
                filename = item.get('filename')
                headers = item.get('headers')

                if not url:
                    result = DownloadResult()
                    result.success = False
                    result.error_message = "Missing URL"
                    return result

                return await self.download_media(url, filename, headers)

            except Exception as e:
                result = DownloadResult()
                result.success = False
                result.error_message = f"Batch download failed: {str(e)}"
                return result

        # Create tasks for all downloads
        tasks = [download_single(item) for item in urls]

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = DownloadResult()
                error_result.success = False
                error_result.error_message = f"Task failed: {str(result)}"
                final_results.append(error_result)
            else:
                final_results.append(result)

        logger.info(f"Batch downloaded {len(urls)} media files")
        return final_results

    async def cleanup_old_files(self, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old cached files.

        Args:
            max_age_days: Maximum age of files to keep

        Returns:
            Cleanup statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            deleted_files = []
            total_size_freed = 0

            for file_path in self.cache_dir.glob('*'):
                if file_path.is_file():
                    # Check file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        total_size_freed += size

            return {
                "deleted_files": len(deleted_files),
                "total_size_freed": total_size_freed,
                "max_age_days": max_age_days,
                "deleted_file_list": deleted_files
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {
                "error": str(e),
                "deleted_files": 0,
                "total_size_freed": 0
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache directory statistics."""
        try:
            total_files = 0
            total_size = 0
            file_types = {}

            for file_path in self.cache_dir.glob('*'):
                if file_path.is_file():
                    total_files += 1
                    size = file_path.stat().st_size
                    total_size += size

                    # Categorize by file type
                    content_type = self._get_content_type_from_path(file_path)
                    if content_type:
                        category = self._get_media_category(content_type)
                        file_types[category] = file_types.get(category, 0) + 1

            return {
                "cache_directory": str(self.cache_dir),
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
                "max_concurrent_downloads": self.max_concurrent
            }

        except Exception as e:
            return {
                "error": str(e),
                "cache_directory": str(self.cache_dir)
            }

    async def _check_rate_limit(self, domain: str) -> bool:
        """Check if domain rate limit allows the request."""
        now = datetime.now()
        minute_key = f"{domain}:{now.strftime('%Y-%m-%d %H:%M')}"

        # Clean up old entries
        cutoff = now - timedelta(minutes=1)
        self.request_counts = {
            k: v for k, v in self.request_counts.items()
            if datetime.fromisoformat(k.split(':', 1)[1] + ':00') > cutoff
        }

        # Check current count
        current_count = self.request_counts.get(minute_key, 0)
        max_requests = self.rate_limits.get(domain, 60)  # Default 60 requests per minute

        if current_count >= max_requests:
            return False

        # Increment count
        self.request_counts[minute_key] = current_count + 1
        return True

    def _generate_filename(self, url: str) -> str:
        """Generate a unique filename for the URL."""
        # Create hash of URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Get file extension from URL or content type
        parsed = urlparse(url)
        path = parsed.path
        extension = Path(path).suffix

        if not extension:
            extension = '.bin'  # Default extension

        # Combine hash with original filename
        original_name = Path(path).stem
        if original_name:
            filename = f"{original_name}_{url_hash}{extension}"
        else:
            filename = f"{url_hash}{extension}"

        return filename

    def _is_supported_content_type(self, content_type: str) -> bool:
        """Check if content type is supported."""
        if not content_type:
            return True  # Allow if unknown

        for category, types in self.supported_types.items():
            if content_type in types:
                return True

        return False

    def _get_content_type_from_path(self, file_path: Path) -> str:
        """Get content type from file path."""
        return mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'

    def _get_media_category(self, content_type: str) -> str:
        """Get media category from content type."""
        for category, types in self.supported_types.items():
            if content_type in types:
                return category
        return 'other'


# Global instance
media_download_service = MediaDownloadService()