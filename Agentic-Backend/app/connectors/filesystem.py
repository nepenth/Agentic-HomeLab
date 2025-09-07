"""
File System Content Connector.

This module provides connectors for file system sources including:
- Local file systems
- Cloud storage (AWS S3, Google Cloud Storage, Azure Blob Storage)
- Network file systems
- FTP/SFTP servers
"""

import os
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncio

from app.connectors.base import (
    ContentConnector,
    ContentItem,
    ContentData,
    ValidationResult,
    ConnectorConfig,
    ConnectorType,
    ContentType,
    ValidationStatus
)
from app.utils.logging import get_logger

logger = get_logger("filesystem_connector")


class LocalFileSystemConnector(ContentConnector):
    """Connector for local file systems."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.file_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover files from local file system."""
        directory = source_config.get("directory", ".")
        recursive = source_config.get("recursive", True)
        file_patterns = source_config.get("file_patterns", ["*"])
        limit = source_config.get("limit", 100)

        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"Path is not a directory: {directory}")

        # Discover files
        files = []
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    if self._matches_patterns(filepath, file_patterns):
                        files.append(filepath)
                        if len(files) >= limit:
                            break
                if len(files) >= limit:
                    break
        else:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath) and self._matches_patterns(filepath, file_patterns):
                    files.append(filepath)
                    if len(files) >= limit:
                        break

        # Convert to ContentItems
        items = []
        for filepath in files:
            try:
                item = await self._create_file_item(filepath, directory)
                if item:
                    items.append(item)
            except Exception as e:
                self.logger.error(f"Failed to process file {filepath}: {e}")
                continue

        return items

    def _matches_patterns(self, filepath: str, patterns: List[str]) -> bool:
        """Check if file matches any of the patterns."""
        filename = os.path.basename(filepath)

        for pattern in patterns:
            if pattern == "*":
                return True
            elif pattern.startswith("*."):
                # Extension pattern
                ext = pattern[2:]
                if filename.endswith(f".{ext}"):
                    return True
            elif "*" in pattern:
                # Wildcard pattern
                import fnmatch
                if fnmatch.fnmatch(filename, pattern):
                    return True
            else:
                # Exact match
                if filename == pattern:
                    return True

        return False

    async def _create_file_item(self, filepath: str, base_directory: str) -> Optional[ContentItem]:
        """Create ContentItem from file path."""
        try:
            stat = os.stat(filepath)
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            # Get MIME type
            mime_type, encoding = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "application/octet-stream"

            # Determine content type
            content_type = self._determine_content_type(filepath, mime_type)

            # Create relative path
            rel_path = os.path.relpath(filepath, base_directory)

            # Create unique ID
            file_id = hashlib.md5(filepath.encode()).hexdigest()

            # Get file preview (first few lines for text files)
            preview = ""
            if content_type == ContentType.TEXT and file_size < 10240:  # 10KB limit
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        preview = f.read(500)
                except Exception:
                    preview = ""

            item = ContentItem(
                id=file_id,
                source=f"filesystem:{base_directory}",
                connector_type=ConnectorType.FILE_SYSTEM,
                content_type=content_type,
                title=os.path.basename(filepath),
                description=preview or f"File: {rel_path}",
                url=f"file://{filepath}",
                metadata={
                    "platform": "filesystem",
                    "filepath": filepath,
                    "relative_path": rel_path,
                    "filename": os.path.basename(filepath),
                    "directory": os.path.dirname(filepath),
                    "mime_type": mime_type,
                    "encoding": encoding,
                    "file_size": file_size,
                    "is_text": content_type == ContentType.TEXT,
                    "is_image": content_type == ContentType.IMAGE,
                    "is_audio": content_type == ContentType.AUDIO,
                    "is_video": content_type == ContentType.VIDEO,
                    "is_document": content_type == ContentType.DOCUMENT
                },
                last_modified=modified_time,
                size_bytes=file_size,
                tags=["filesystem", "file", str(content_type.value)]
            )

            return item

        except Exception as e:
            self.logger.error(f"Failed to create file item for {filepath}: {e}")
            return None

    def _determine_content_type(self, filepath: str, mime_type: str) -> ContentType:
        """Determine content type from file path and MIME type."""
        # Check by MIME type first
        if mime_type:
            if mime_type.startswith("text/"):
                return ContentType.TEXT
            elif mime_type.startswith("image/"):
                return ContentType.IMAGE
            elif mime_type.startswith("audio/"):
                return ContentType.AUDIO
            elif mime_type.startswith("video/"):
                return ContentType.VIDEO
            elif mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                return ContentType.DOCUMENT
            elif mime_type in ["application/json", "application/xml", "text/csv"]:
                return ContentType.STRUCTURED

        # Check by file extension
        ext = Path(filepath).suffix.lower()
        if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.xml', '.json', '.csv']:
            return ContentType.TEXT
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            return ContentType.IMAGE
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.aac']:
            return ContentType.AUDIO
        elif ext in ['.mp4', '.avi', '.mov', '.webm', '.mkv']:
            return ContentType.VIDEO
        elif ext in ['.pdf', '.doc', '.docx', '.xlsx', '.pptx']:
            return ContentType.DOCUMENT

        return ContentType.UNKNOWN

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch file content."""
        if isinstance(content_ref, str):
            filepath = content_ref
        else:
            filepath = content_ref.metadata.get("filepath")

        if not filepath or not os.path.exists(filepath):
            raise ValueError(f"File not found: {filepath}")

        start_time = datetime.now()

        # Read file content
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read()

            # Try to decode text content
            text_content = None
            structured_data = None

            mime_type = content_ref.metadata.get("mime_type") if isinstance(content_ref, ContentItem) else None
            if mime_type and mime_type.startswith("text/"):
                try:
                    text_content = raw_data.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    pass
            elif mime_type == "application/json":
                try:
                    structured_data = json.loads(raw_data.decode('utf-8'))
                    text_content = json.dumps(structured_data, indent=2)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ContentData(
                item=content_ref if isinstance(content_ref, ContentItem) else None,
                raw_data=raw_data,
                text_content=text_content,
                structured_data=structured_data,
                metadata={
                    "fetched_at": datetime.now().isoformat(),
                    "processing_time_ms": processing_time,
                    "file_exists": True
                },
                processing_time_ms=processing_time
            )

        except Exception as e:
            raise Exception(f"Failed to read file {filepath}: {e}")

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate file content."""
        if isinstance(content, ContentData):
            raw_data = content.raw_data
            item = content.item
        else:
            raw_data = content
            item = None

        errors = []
        warnings = []

        # Check file size
        file_size = len(raw_data)
        if file_size == 0:
            errors.append("File is empty")
        elif file_size > 100 * 1024 * 1024:  # 100MB limit
            warnings.append("File is very large (>100MB)")

        # Check if it's a valid file
        if item:
            filepath = item.metadata.get("filepath")
            if filepath and not os.path.exists(filepath):
                errors.append("File no longer exists")

        # Try to detect content type issues
        if raw_data:
            # Check for binary vs text content
            try:
                text_content = raw_data.decode('utf-8')
                # If we can decode as UTF-8, it's likely text
                if len(text_content) > 0:
                    # Check for null bytes (indicates binary)
                    if '\x00' in text_content:
                        warnings.append("File contains null bytes (may be binary)")
            except UnicodeDecodeError:
                # Binary file, which is fine
                pass

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="File content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "file_size_bytes": file_size,
                "is_empty": file_size == 0,
                "is_binary": self._is_binary_content(raw_data)
            }
        )

    def _is_binary_content(self, data: bytes) -> bool:
        """Check if content appears to be binary."""
        if not data:
            return False

        # Check for null bytes
        if b'\x00' in data:
            return True

        # Try to decode as UTF-8
        try:
            data.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Get local filesystem connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "image", "audio", "video", "document", "structured"],
            "supported_operations": ["directory_scan", "file_read", "pattern_matching"],
            "features": ["recursive_scanning", "file_filtering", "metadata_extraction"],
            "authentication_methods": ["none"],
            "rate_limiting": False,
            "retry_support": False,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities


class S3Connector(ContentConnector):
    """Connector for AWS S3."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.s3_client = None
        self.bucket_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 600  # 10 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover objects from S3 bucket."""
        bucket_name = source_config.get("bucket_name")
        prefix = source_config.get("prefix", "")
        max_keys = source_config.get("max_keys", 100)

        if not bucket_name:
            raise ValueError("Bucket name is required")

        try:
            # Initialize S3 client if needed
            await self._init_s3_client()

            # List objects
            objects = await self._list_objects(bucket_name, prefix, max_keys)

            # Convert to ContentItems
            items = []
            for obj in objects:
                try:
                    item = await self._create_s3_item(obj, bucket_name)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Failed to process S3 object {obj.get('Key')}: {e}")
                    continue

            return items

        except Exception as e:
            raise Exception(f"Failed to discover S3 objects: {e}")

    async def _init_s3_client(self):
        """Initialize S3 client."""
        if self.s3_client:
            return

        try:
            # Use boto3 for S3 operations (would need to be installed)
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.credentials.get('aws_access_key_id'),
                aws_secret_access_key=self.config.credentials.get('aws_secret_access_key'),
                region_name=self.config.credentials.get('aws_region', 'us-east-1')
            )
        except ImportError:
            raise Exception("boto3 is required for S3 operations")

    async def _list_objects(self, bucket_name: str, prefix: str, max_keys: int) -> List[Dict[str, Any]]:
        """List objects in S3 bucket."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            return response.get('Contents', [])
        except Exception as e:
            raise Exception(f"Failed to list S3 objects: {e}")

    async def _create_s3_item(self, obj: Dict[str, Any], bucket_name: str) -> Optional[ContentItem]:
        """Create ContentItem from S3 object."""
        try:
            key = obj['Key']
            size = obj['Size']
            last_modified = obj['LastModified']

            # Get MIME type
            mime_type, encoding = mimetypes.guess_type(key)
            if not mime_type:
                mime_type = "application/octet-stream"

            # Determine content type
            content_type = self._determine_content_type_from_key(key, mime_type)

            # Create unique ID
            object_id = hashlib.md5(f"{bucket_name}:{key}".encode()).hexdigest()

            # Create S3 URL
            url = f"https://{bucket_name}.s3.amazonaws.com/{key}"

            item = ContentItem(
                id=object_id,
                source=f"s3:{bucket_name}",
                connector_type=ConnectorType.FILE_SYSTEM,
                content_type=content_type,
                title=key.split('/')[-1],  # filename
                description=f"S3 Object: {key}",
                url=url,
                metadata={
                    "platform": "s3",
                    "bucket": bucket_name,
                    "key": key,
                    "mime_type": mime_type,
                    "encoding": encoding,
                    "size_bytes": size,
                    "is_text": content_type == ContentType.TEXT,
                    "is_image": content_type == ContentType.IMAGE,
                    "is_audio": content_type == ContentType.AUDIO,
                    "is_video": content_type == ContentType.VIDEO,
                    "is_document": content_type == ContentType.DOCUMENT,
                    "storage_class": obj.get('StorageClass'),
                    "etag": obj.get('ETag')
                },
                last_modified=last_modified,
                size_bytes=size,
                tags=["s3", "aws", "cloud", str(content_type.value)]
            )

            return item

        except Exception as e:
            self.logger.error(f"Failed to create S3 item: {e}")
            return None

    def _determine_content_type_from_key(self, key: str, mime_type: str) -> ContentType:
        """Determine content type from S3 key and MIME type."""
        # Same logic as local filesystem
        if mime_type:
            if mime_type.startswith("text/"):
                return ContentType.TEXT
            elif mime_type.startswith("image/"):
                return ContentType.IMAGE
            elif mime_type.startswith("audio/"):
                return ContentType.AUDIO
            elif mime_type.startswith("video/"):
                return ContentType.VIDEO
            elif mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                return ContentType.DOCUMENT
            elif mime_type in ["application/json", "application/xml", "text/csv"]:
                return ContentType.STRUCTURED

        # Check by file extension
        ext = Path(key).suffix.lower()
        if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.xml', '.json', '.csv']:
            return ContentType.TEXT
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            return ContentType.IMAGE
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.aac']:
            return ContentType.AUDIO
        elif ext in ['.mp4', '.avi', '.mov', '.webm', '.mkv']:
            return ContentType.VIDEO
        elif ext in ['.pdf', '.doc', '.docx', '.xlsx', '.pptx']:
            return ContentType.DOCUMENT

        return ContentType.UNKNOWN

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch S3 object content."""
        if isinstance(content_ref, str):
            # Parse S3 URL or key
            if content_ref.startswith("s3://"):
                # s3://bucket/key format
                parts = content_ref[5:].split("/", 1)
                bucket_name = parts[0]
                key = parts[1] if len(parts) > 1 else ""
            else:
                raise ValueError(f"Invalid S3 reference: {content_ref}")
        else:
            bucket_name = content_ref.metadata.get("bucket")
            key = content_ref.metadata.get("key")

        if not bucket_name or not key:
            raise ValueError("Bucket name and key are required")

        start_time = datetime.now()

        try:
            # Initialize S3 client
            await self._init_s3_client()

            # Get object
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            raw_data = response['Body'].read()

            # Try to decode text content
            text_content = None
            structured_data = None

            mime_type = content_ref.metadata.get("mime_type") if isinstance(content_ref, ContentItem) else None
            if mime_type and mime_type.startswith("text/"):
                try:
                    text_content = raw_data.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    pass
            elif mime_type == "application/json":
                try:
                    structured_data = json.loads(raw_data.decode('utf-8'))
                    text_content = json.dumps(structured_data, indent=2)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ContentData(
                item=content_ref if isinstance(content_ref, ContentItem) else None,
                raw_data=raw_data,
                text_content=text_content,
                structured_data=structured_data,
                metadata={
                    "fetched_at": datetime.now().isoformat(),
                    "processing_time_ms": processing_time,
                    "bucket": bucket_name,
                    "key": key
                },
                processing_time_ms=processing_time
            )

        except Exception as e:
            raise Exception(f"Failed to fetch S3 object: {e}")

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate S3 object content."""
        # Similar validation logic as local filesystem
        if isinstance(content, ContentData):
            raw_data = content.raw_data
        else:
            raw_data = content

        errors = []
        warnings = []

        # Check object size
        object_size = len(raw_data)
        if object_size == 0:
            errors.append("S3 object is empty")
        elif object_size > 100 * 1024 * 1024:  # 100MB limit
            warnings.append("S3 object is very large (>100MB)")

        # Basic content validation
        if raw_data:
            try:
                text_content = raw_data.decode('utf-8')
                if '\x00' in text_content:
                    warnings.append("Object contains null bytes (may be binary)")
            except UnicodeDecodeError:
                pass

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="S3 object validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "object_size_bytes": object_size,
                "is_empty": object_size == 0,
                "is_binary": self._is_binary_content(raw_data)
            }
        )

    def _is_binary_content(self, data: bytes) -> bool:
        """Check if content appears to be binary."""
        if not data:
            return False

        # Check for null bytes
        if b'\x00' in data:
            return True

        # Try to decode as UTF-8
        try:
            data.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Get S3 connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "image", "audio", "video", "document", "structured"],
            "supported_operations": ["bucket_scan", "object_read", "prefix_filtering"],
            "features": ["cloud_storage", "versioning", "metadata_support"],
            "authentication_methods": ["aws_credentials"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities


class GoogleCloudStorageConnector(ContentConnector):
    """Connector for Google Cloud Storage."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.gcs_client = None
        self.bucket_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 600  # 10 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover objects from GCS bucket."""
        bucket_name = source_config.get("bucket_name")
        prefix = source_config.get("prefix", "")
        max_results = source_config.get("max_results", 100)

        if not bucket_name:
            raise ValueError("Bucket name is required")

        try:
            # Initialize GCS client if needed
            await self._init_gcs_client()

            # List objects
            blobs = await self._list_blobs(bucket_name, prefix, max_results)

            # Convert to ContentItems
            items = []
            for blob in blobs:
                try:
                    item = await self._create_gcs_item(blob, bucket_name)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Failed to process GCS blob {blob.name}: {e}")
                    continue

            return items

        except Exception as e:
            raise Exception(f"Failed to discover GCS objects: {e}")

    async def _init_gcs_client(self):
        """Initialize GCS client."""
        if self.gcs_client:
            return

        try:
            # Use google-cloud-storage (would need to be installed)
            from google.cloud import storage
            self.gcs_client = storage.Client.from_service_account_json(
                self.config.credentials.get('service_account_key_file')
            )
        except ImportError:
            raise Exception("google-cloud-storage is required for GCS operations")

    async def _list_blobs(self, bucket_name: str, prefix: str, max_results: int) -> List[Any]:
        """List blobs in GCS bucket."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix, max_results=max_results))
            return blobs
        except Exception as e:
            raise Exception(f"Failed to list GCS blobs: {e}")

    async def _create_gcs_item(self, blob, bucket_name: str) -> Optional[ContentItem]:
        """Create ContentItem from GCS blob."""
        try:
            # Get MIME type
            mime_type = blob.content_type or mimetypes.guess_type(blob.name)[0] or "application/octet-stream"

            # Determine content type
            content_type = self._determine_content_type_from_name(blob.name, mime_type)

            # Create unique ID
            object_id = hashlib.md5(f"{bucket_name}:{blob.name}".encode()).hexdigest()

            # Create GCS URL
            url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"

            item = ContentItem(
                id=object_id,
                source=f"gcs:{bucket_name}",
                connector_type=ConnectorType.FILE_SYSTEM,
                content_type=content_type,
                title=blob.name.split('/')[-1],  # filename
                description=f"GCS Object: {blob.name}",
                url=url,
                metadata={
                    "platform": "gcs",
                    "bucket": bucket_name,
                    "name": blob.name,
                    "mime_type": mime_type,
                    "size_bytes": blob.size,
                    "is_text": content_type == ContentType.TEXT,
                    "is_image": content_type == ContentType.IMAGE,
                    "is_audio": content_type == ContentType.AUDIO,
                    "is_video": content_type == ContentType.VIDEO,
                    "is_document": content_type == ContentType.DOCUMENT,
                    "storage_class": blob.storage_class,
                    "generation": blob.generation
                },
                last_modified=blob.updated,
                size_bytes=blob.size,
                tags=["gcs", "google_cloud", "cloud", str(content_type.value)]
            )

            return item

        except Exception as e:
            self.logger.error(f"Failed to create GCS item: {e}")
            return None

    def _determine_content_type_from_name(self, name: str, mime_type: str) -> ContentType:
        """Determine content type from GCS object name and MIME type."""
        # Similar logic as other connectors
        if mime_type:
            if mime_type.startswith("text/"):
                return ContentType.TEXT
            elif mime_type.startswith("image/"):
                return ContentType.IMAGE
            elif mime_type.startswith("audio/"):
                return ContentType.AUDIO
            elif mime_type.startswith("video/"):
                return ContentType.VIDEO
            elif mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                return ContentType.DOCUMENT
            elif mime_type in ["application/json", "application/xml", "text/csv"]:
                return ContentType.STRUCTURED

        # Check by file extension
        ext = Path(name).suffix.lower()
        if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.xml', '.json', '.csv']:
            return ContentType.TEXT
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            return ContentType.IMAGE
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.aac']:
            return ContentType.AUDIO
        elif ext in ['.mp4', '.avi', '.mov', '.webm', '.mkv']:
            return ContentType.VIDEO
        elif ext in ['.pdf', '.doc', '.docx', '.xlsx', '.pptx']:
            return ContentType.DOCUMENT

        return ContentType.UNKNOWN

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch GCS object content."""
        if isinstance(content_ref, str):
            # Parse GCS URL
            if content_ref.startswith("gs://"):
                # gs://bucket/name format
                parts = content_ref[5:].split("/", 1)
                bucket_name = parts[0]
                name = parts[1] if len(parts) > 1 else ""
            else:
                raise ValueError(f"Invalid GCS reference: {content_ref}")
        else:
            bucket_name = content_ref.metadata.get("bucket")
            name = content_ref.metadata.get("name")

        if not bucket_name or not name:
            raise ValueError("Bucket name and object name are required")

        start_time = datetime.now()

        try:
            # Initialize GCS client
            await self._init_gcs_client()

            # Get blob
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(name)

            # Download content
            raw_data = blob.download_as_bytes()

            # Try to decode text content
            text_content = None
            structured_data = None

            mime_type = content_ref.metadata.get("mime_type") if isinstance(content_ref, ContentItem) else None
            if mime_type and mime_type.startswith("text/"):
                try:
                    text_content = raw_data.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    pass
            elif mime_type == "application/json":
                try:
                    structured_data = json.loads(raw_data.decode('utf-8'))
                    text_content = json.dumps(structured_data, indent=2)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ContentData(
                item=content_ref if isinstance(content_ref, ContentItem) else None,
                raw_data=raw_data,
                text_content=text_content,
                structured_data=structured_data,
                metadata={
                    "fetched_at": datetime.now().isoformat(),
                    "processing_time_ms": processing_time,
                    "bucket": bucket_name,
                    "name": name
                },
                processing_time_ms=processing_time
            )

        except Exception as e:
            raise Exception(f"Failed to fetch GCS object: {e}")

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate GCS object content."""
        # Similar validation logic as other cloud storage connectors
        if isinstance(content, ContentData):
            raw_data = content.raw_data
        else:
            raw_data = content

        errors = []
        warnings = []

        # Check object size
        object_size = len(raw_data)
        if object_size == 0:
            errors.append("GCS object is empty")
        elif object_size > 100 * 1024 * 1024:  # 100MB limit
            warnings.append("GCS object is very large (>100MB)")

        # Basic content validation
        if raw_data:
            try:
                text_content = raw_data.decode('utf-8')
                if '\x00' in text_content:
                    warnings.append("Object contains null bytes (may be binary)")
            except UnicodeDecodeError:
                pass

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="GCS object validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "object_size_bytes": object_size,
                "is_empty": object_size == 0,
                "is_binary": self._is_binary_content(raw_data)
            }
        )

    def _is_binary_content(self, data: bytes) -> bool:
        """Check if content appears to be binary."""
        if not data:
            return False

        # Check for null bytes
        if b'\x00' in data:
            return True

        # Try to decode as UTF-8
        try:
            data.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True

    def get_capabilities(self) -> Dict[str, Any]:
        """Get GCS connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text", "image", "audio", "video", "document", "structured"],
            "supported_operations": ["bucket_scan", "object_read", "prefix_filtering"],
            "features": ["cloud_storage", "versioning", "metadata_support"],
            "authentication_methods": ["service_account"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities