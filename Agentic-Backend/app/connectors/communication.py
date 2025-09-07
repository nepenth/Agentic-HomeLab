"""
Communication Content Connector.

This module provides connectors for communication platforms including:
- Email (IMAP/POP3)
- Slack API
- Discord API
"""

import imaplib
import email
import json
from email.header import decode_header
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import hashlib

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

logger = get_logger("communication_connector")


class EmailConnector(ContentConnector):
    """Connector for email using IMAP."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.imap_server = None
        self.email_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover emails from mailbox."""
        mailbox = source_config.get("mailbox", "INBOX")
        limit = source_config.get("limit", 10)
        unread_only = source_config.get("unread_only", False)
        since_date = source_config.get("since_date")

        try:
            # Connect to IMAP server
            await self._connect_imap()

            # Select mailbox
            self.imap_server.select(mailbox)

            # Search for messages
            search_criteria = []
            if unread_only:
                search_criteria.append("UNSEEN")
            if since_date:
                search_criteria.append(f'SINCE "{since_date}"')

            if search_criteria:
                status, messages = self.imap_server.search(None, *search_criteria)
            else:
                status, messages = self.imap_server.search(None, "ALL")

            if status != "OK":
                raise Exception(f"IMAP search failed: {status}")

            # Get message IDs
            message_ids = messages[0].split()
            message_ids = message_ids[-limit:] if len(message_ids) > limit else message_ids

            items = []
            for msg_id in reversed(message_ids):  # Most recent first
                try:
                    item = await self._fetch_email_header(msg_id, mailbox)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Failed to fetch email {msg_id}: {e}")
                    continue

            return items

        finally:
            await self._disconnect_imap()

    async def _connect_imap(self):
        """Connect to IMAP server."""
        if self.imap_server:
            return

        server = self.config.credentials.get("imap_server", "imap.gmail.com")
        port = self.config.credentials.get("imap_port", 993)
        username = self.config.credentials.get("username")
        password = self.config.credentials.get("password")

        if not all([server, username, password]):
            raise ValueError("IMAP server, username, and password are required")

        try:
            self.imap_server = imaplib.IMAP4_SSL(server, port)
            status, response = self.imap_server.login(username, password)

            if status != "OK":
                raise Exception(f"IMAP login failed: {response}")

        except Exception as e:
            raise Exception(f"Failed to connect to IMAP server: {e}")

    async def _disconnect_imap(self):
        """Disconnect from IMAP server."""
        if self.imap_server:
            try:
                self.imap_server.logout()
            except:
                pass
            self.imap_server = None

    async def _fetch_email_header(self, msg_id: bytes, mailbox: str) -> Optional[ContentItem]:
        """Fetch email header information."""
        try:
            status, msg_data = self.imap_server.fetch(msg_id, "(RFC822.HEADER)")

            if status != "OK":
                return None

            email_message = email.message_from_bytes(msg_data[0][1])

            # Extract header information
            subject = self._decode_header(email_message.get("Subject", ""))
            sender = self._decode_header(email_message.get("From", ""))
            to = self._decode_header(email_message.get("To", ""))
            date_str = email_message.get("Date", "")

            # Parse date
            try:
                # Use email.utils to parse date
                from email.utils import parsedate_to_datetime
                received_date = parsedate_to_datetime(date_str)
            except:
                received_date = datetime.now()

            # Create unique ID
            msg_id_str = msg_id.decode()
            email_id = f"{mailbox}_{msg_id_str}"

            # Extract preview text
            preview = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        preview = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                preview = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            preview = preview[:500] + "..." if len(preview) > 500 else preview

            return ContentItem(
                id=email_id,
                source=f"email:{mailbox}",
                connector_type=ConnectorType.COMMUNICATION,
                content_type=ContentType.TEXT,
                title=subject or "No Subject",
                description=preview,
                metadata={
                    "platform": "email",
                    "sender": sender,
                    "recipient": to,
                    "mailbox": mailbox,
                    "imap_id": msg_id_str,
                    "has_attachments": self._has_attachments(email_message),
                    "content_type": email_message.get_content_type(),
                    "size_bytes": len(email_message.as_bytes())
                },
                last_modified=received_date,
                tags=["email", "communication", mailbox.lower()]
            )

        except Exception as e:
            self.logger.error(f"Failed to parse email header: {e}")
            return None

    def _decode_header(self, header_value: str) -> str:
        """Decode email header with proper encoding."""
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += str(part)

            return decoded_string
        except Exception:
            return header_value

    def _has_attachments(self, email_message) -> bool:
        """Check if email has attachments."""
        if not email_message.is_multipart():
            return False

        for part in email_message.walk():
            if part.get_content_disposition() and "attachment" in part.get_content_disposition():
                return True

        return False

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch full email content."""
        if isinstance(content_ref, str):
            # Parse email ID
            parts = content_ref.split("_", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid email ID format: {content_ref}")
            mailbox, msg_id = parts
        else:
            mailbox = content_ref.metadata.get("mailbox", "INBOX")
            msg_id = content_ref.metadata.get("imap_id")

        if not msg_id:
            raise ValueError("Message ID not found")

        start_time = datetime.now()

        try:
            await self._connect_imap()
            self.imap_server.select(mailbox)

            # Fetch full message
            status, msg_data = self.imap_server.fetch(msg_id.encode(), "(RFC822)")

            if status != "OK":
                raise Exception(f"Failed to fetch email: {status}")

            email_message = email.message_from_bytes(msg_data[0][1])

            # Extract full content
            content_text = ""
            attachments = []

            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()

                    if content_type == "text/plain" and not part.get("Content-Disposition"):
                        content_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition"):
                        # Handle attachment
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                "filename": self._decode_header(filename),
                                "content_type": content_type,
                                "size": len(part.get_payload(decode=True))
                            })
            else:
                content_text = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ContentData(
                item=content_ref if isinstance(content_ref, ContentItem) else None,
                raw_data=email_message.as_bytes(),
                text_content=content_text,
                metadata={
                    "fetched_at": datetime.now().isoformat(),
                    "processing_time_ms": processing_time,
                    "attachments": attachments,
                    "has_attachments": len(attachments) > 0
                },
                processing_time_ms=processing_time
            )

        finally:
            await self._disconnect_imap()

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate email content."""
        if isinstance(content, ContentData):
            raw_data = content.raw_data
            text_content = content.text_content or ""
        else:
            raw_data = content
            try:
                email_message = email.message_from_bytes(raw_data)
                text_content = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            text_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    text_content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except Exception:
                text_content = ""

        errors = []
        warnings = []

        # Check email structure
        try:
            email_message = email.message_from_bytes(raw_data)

            # Check required headers
            if not email_message.get("From"):
                errors.append("Missing sender (From header)")
            if not email_message.get("To") and not email_message.get("Cc") and not email_message.get("Bcc"):
                errors.append("Missing recipients")
            if not email_message.get("Subject") and not email_message.get("Date"):
                warnings.append("Missing subject or date")

            # Check for spam indicators
            subject = email_message.get("Subject", "").lower()
            if any(word in subject for word in ["spam", "viagra", "lottery", "urgent"]):
                warnings.append("Subject contains potential spam indicators")

        except Exception as e:
            errors.append(f"Invalid email format: {e}")

        # Check content
        if len(text_content.strip()) == 0:
            warnings.append("Email has no text content")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="Email validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "content_size_bytes": len(raw_data),
                "text_length": len(text_content),
                "is_multipart": email.message_from_bytes(raw_data).is_multipart() if raw_data else False
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get email connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text"],
            "supported_protocols": ["imap", "pop3"],
            "features": ["authentication", "ssl_support", "attachment_handling"],
            "authentication_methods": ["password", "oauth2"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": False
        })
        return capabilities


class SlackConnector(ContentConnector):
    """Connector for Slack API."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_base_url = "https://slack.com/api"
        self.message_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from Slack."""
        content_type = source_config.get("content_type", "messages")
        channel = source_config.get("channel")
        limit = source_config.get("limit", 10)

        if content_type == "messages":
            if not channel:
                raise ValueError("Channel is required for messages")
            return await self._get_channel_messages(channel, limit)
        elif content_type == "channels":
            return await self._get_channels()
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    async def _get_channel_messages(self, channel: str, limit: int) -> List[ContentItem]:
        """Get messages from a Slack channel."""
        endpoint = f"{self.api_base_url}/conversations.history"
        params = {
            "channel": channel,
            "limit": min(limit, 100)
        }

        response = await self._make_authenticated_request("GET", endpoint, params=params)

        if not response.json_data.get("ok"):
            error = response.json_data.get("error", "Unknown error")
            raise Exception(f"Slack API error: {error}")

        messages = response.json_data.get("messages", [])
        return self._parse_slack_messages(messages, channel)

    async def _get_channels(self) -> List[ContentItem]:
        """Get list of Slack channels."""
        endpoint = f"{self.api_base_url}/conversations.list"
        params = {"types": "public_channel,private_channel"}

        response = await self._make_authenticated_request("GET", endpoint, params=params)

        if not response.json_data.get("ok"):
            error = response.json_data.get("error", "Unknown error")
            raise Exception(f"Slack API error: {error}")

        channels = response.json_data.get("channels", [])
        return self._parse_slack_channels(channels)

    async def _make_authenticated_request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
        """Make authenticated request to Slack API."""
        headers = {
            "Authorization": f"Bearer {self.config.credentials.get('bot_token', '')}",
            "Content-Type": "application/json"
        }

        return await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_data=data,
            timeout=30.0
        )

    def _parse_slack_messages(self, messages: List[Dict[str, Any]], channel: str) -> List[ContentItem]:
        """Parse Slack messages."""
        items = []

        for message in messages:
            try:
                message_id = message["ts"]
                user = message.get("user", "Unknown")
                text = message.get("text", "")

                # Parse timestamp
                timestamp = datetime.fromtimestamp(float(message_id))

                # Get user info if available
                user_profile = message.get("user_profile", {})
                user_name = user_profile.get("real_name", user_profile.get("name", user))

                # Handle different message types
                message_type = message.get("type", "message")
                if message_type == "message" and message.get("subtype"):
                    message_type = message["subtype"]

                # Create message URL
                team_id = self.config.credentials.get("team_id", "")
                url = f"https://slack.com/archives/{team_id}/{channel}/p{message_id.replace('.', '')}"

                item = ContentItem(
                    id=f"slack_{channel}_{message_id}",
                    source=f"slack:{channel}",
                    connector_type=ConnectorType.COMMUNICATION,
                    content_type=ContentType.TEXT,
                    title=f"Message from {user_name}",
                    description=text,
                    url=url,
                    metadata={
                        "platform": "slack",
                        "channel": channel,
                        "user": user,
                        "user_name": user_name,
                        "message_type": message_type,
                        "thread_ts": message.get("thread_ts"),
                        "reply_count": message.get("reply_count", 0),
                        "reactions": message.get("reactions", []),
                        "attachments": message.get("attachments", [])
                    },
                    last_modified=timestamp,
                    tags=["slack", "message", "communication", channel]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse Slack message: {e}")
                continue

        return items

    def _parse_slack_channels(self, channels: List[Dict[str, Any]]) -> List[ContentItem]:
        """Parse Slack channels."""
        items = []

        for channel in channels:
            try:
                channel_id = channel["id"]
                name = channel["name"]
                topic = channel.get("topic", {}).get("value", "")
                purpose = channel.get("purpose", {}).get("value", "")

                # Create channel URL
                team_id = self.config.credentials.get("team_id", "")
                url = f"https://slack.com/archives/{team_id}/{channel_id}"

                description = f"Channel: #{name}"
                if topic:
                    description += f"\nTopic: {topic}"
                if purpose:
                    description += f"\nPurpose: {purpose}"

                item = ContentItem(
                    id=f"slack_channel_{channel_id}",
                    source="slack:channels",
                    connector_type=ConnectorType.COMMUNICATION,
                    content_type=ContentType.TEXT,
                    title=f"#{name}",
                    description=description,
                    url=url,
                    metadata={
                        "platform": "slack",
                        "channel_id": channel_id,
                        "channel_name": name,
                        "is_private": channel.get("is_private", False),
                        "member_count": channel.get("num_members", 0),
                        "topic": topic,
                        "purpose": purpose
                    },
                    tags=["slack", "channel", "communication"]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse Slack channel: {e}")
                continue

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch Slack content."""
        if isinstance(content_ref, str):
            # Parse Slack message ID
            if content_ref.startswith("slack_"):
                parts = content_ref.split("_", 2)
                if len(parts) >= 3:
                    channel = parts[1]
                    message_ts = parts[2]
                else:
                    raise ValueError(f"Invalid Slack message ID format: {content_ref}")
            else:
                raise ValueError(f"Unsupported Slack ID format: {content_ref}")
        else:
            channel = content_ref.metadata.get("channel")
            message_ts = content_ref.id.split("_")[-1] if "_" in content_ref.id else content_ref.id

        start_time = datetime.now()

        # Get single message (this is a simplified approach)
        endpoint = f"{self.api_base_url}/conversations.history"
        params = {
            "channel": channel,
            "latest": message_ts,
            "limit": 1,
            "inclusive": True
        }

        response = await self._make_authenticated_request("GET", endpoint, params=params)

        if not response.json_data.get("ok"):
            error = response.json_data.get("error", "Unknown error")
            raise Exception(f"Failed to fetch Slack message: {error}")

        messages = response.json_data.get("messages", [])
        if not messages:
            raise Exception("Message not found")

        message = messages[0]

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=content_ref if isinstance(content_ref, ContentItem) else None,
            raw_data=json.dumps(message).encode('utf-8'),
            text_content=message.get("text", ""),
            structured_data=message,
            metadata={
                "fetched_at": datetime.now().isoformat(),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate Slack content."""
        if isinstance(content, ContentData):
            structured_data = content.structured_data
            text_content = content.text_content or ""
        else:
            try:
                structured_data = json.loads(content.decode('utf-8'))
                text_content = structured_data.get("text", "")
            except (UnicodeDecodeError, json.JSONDecodeError):
                structured_data = None
                text_content = ""

        errors = []
        warnings = []

        # Check Slack message structure
        if structured_data:
            if "ts" not in structured_data:
                errors.append("Missing timestamp (ts)")
            if "text" not in structured_data:
                errors.append("Missing message text")

            # Check for deleted messages
            if structured_data.get("deleted"):
                warnings.append("Message has been deleted")

            # Check for bot messages
            if structured_data.get("bot_id"):
                warnings.append("Message is from a bot")

        # Check content
        if len(text_content.strip()) == 0:
            warnings.append("Message has no text content")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="Slack content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "has_structured_data": structured_data is not None,
                "text_length": len(text_content),
                "is_deleted": structured_data.get("deleted", False) if structured_data else False,
                "is_bot": bool(structured_data and structured_data.get("bot_id"))
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get Slack connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text"],
            "supported_operations": ["channel_messages", "channels", "threads"],
            "features": ["real_time_updates", "authentication", "rate_limiting"],
            "authentication_methods": ["bot_token", "user_token"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": True
        })
        return capabilities


class DiscordConnector(ContentConnector):
    """Connector for Discord API."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_base_url = "https://discord.com/api/v10"
        self.message_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    async def discover(self, source_config: Dict[str, Any]) -> List[ContentItem]:
        """Discover content from Discord."""
        content_type = source_config.get("content_type", "messages")
        channel_id = source_config.get("channel_id")
        guild_id = source_config.get("guild_id")
        limit = source_config.get("limit", 10)

        if content_type == "messages":
            if not channel_id:
                raise ValueError("Channel ID is required for messages")
            return await self._get_channel_messages(channel_id, limit)
        elif content_type == "channels":
            if not guild_id:
                raise ValueError("Guild ID is required for channels")
            return await self._get_guild_channels(guild_id)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    async def _get_channel_messages(self, channel_id: str, limit: int) -> List[ContentItem]:
        """Get messages from a Discord channel."""
        endpoint = f"{self.api_base_url}/channels/{channel_id}/messages"
        params = {"limit": min(limit, 100)}

        response = await self._make_authenticated_request("GET", endpoint, params=params)

        if response.status_code != 200:
            raise Exception(f"Discord API error: HTTP {response.status_code}")

        messages = response.json_data
        return self._parse_discord_messages(messages, channel_id)

    async def _get_guild_channels(self, guild_id: str) -> List[ContentItem]:
        """Get channels from a Discord guild."""
        endpoint = f"{self.api_base_url}/guilds/{guild_id}/channels"

        response = await self._make_authenticated_request("GET", endpoint)

        if response.status_code != 200:
            raise Exception(f"Discord API error: HTTP {response.status_code}")

        channels = response.json_data
        return self._parse_discord_channels(channels, guild_id)

    async def _make_authenticated_request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
        """Make authenticated request to Discord API."""
        headers = {
            "Authorization": f"Bot {self.config.credentials.get('bot_token', '')}",
            "Content-Type": "application/json"
        }

        return await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json_data=data,
            timeout=30.0
        )

    def _parse_discord_messages(self, messages: List[Dict[str, Any]], channel_id: str) -> List[ContentItem]:
        """Parse Discord messages."""
        items = []

        for message in messages:
            try:
                message_id = message["id"]
                author = message.get("author", {})
                author_name = author.get("username", "Unknown")
                content = message.get("content", "")

                # Parse timestamp
                timestamp = datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))

                # Create message URL
                guild_id = self.config.credentials.get("guild_id", "")
                url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

                # Handle attachments
                attachments = message.get("attachments", [])
                has_attachments = len(attachments) > 0

                # Handle embeds
                embeds = message.get("embeds", [])
                has_embeds = len(embeds) > 0

                item = ContentItem(
                    id=f"discord_{channel_id}_{message_id}",
                    source=f"discord:{channel_id}",
                    connector_type=ConnectorType.COMMUNICATION,
                    content_type=ContentType.TEXT,
                    title=f"Message from {author_name}",
                    description=content,
                    url=url,
                    metadata={
                        "platform": "discord",
                        "channel_id": channel_id,
                        "author_id": author.get("id"),
                        "author_name": author_name,
                        "author_discriminator": author.get("discriminator"),
                        "mentions": message.get("mentions", []),
                        "attachments": attachments,
                        "embeds": embeds,
                        "has_attachments": has_attachments,
                        "has_embeds": has_embeds,
                        "reactions": message.get("reactions", []),
                        "pinned": message.get("pinned", False)
                    },
                    last_modified=timestamp,
                    tags=["discord", "message", "communication", channel_id]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse Discord message: {e}")
                continue

        return items

    def _parse_discord_channels(self, channels: List[Dict[str, Any]], guild_id: str) -> List[ContentItem]:
        """Parse Discord channels."""
        items = []

        for channel in channels:
            try:
                channel_id = channel["id"]
                name = channel["name"]
                channel_type = channel["type"]
                topic = channel.get("topic", "")

                # Create channel URL
                url = f"https://discord.com/channels/{guild_id}/{channel_id}"

                # Map channel types
                type_names = {
                    0: "text",
                    1: "dm",
                    2: "voice",
                    3: "group_dm",
                    4: "category",
                    5: "announcement",
                    13: "stage_voice",
                    15: "forum"
                }
                channel_type_name = type_names.get(channel_type, "unknown")

                description = f"Channel: #{name}"
                if topic:
                    description += f"\nTopic: {topic}"
                description += f"\nType: {channel_type_name}"

                item = ContentItem(
                    id=f"discord_channel_{channel_id}",
                    source=f"discord:guild:{guild_id}",
                    connector_type=ConnectorType.COMMUNICATION,
                    content_type=ContentType.TEXT,
                    title=f"#{name}",
                    description=description,
                    url=url,
                    metadata={
                        "platform": "discord",
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "channel_name": name,
                        "channel_type": channel_type,
                        "channel_type_name": channel_type_name,
                        "topic": topic,
                        "position": channel.get("position", 0),
                        "nsfw": channel.get("nsfw", False)
                    },
                    tags=["discord", "channel", "communication", channel_type_name]
                )

                items.append(item)

            except Exception as e:
                self.logger.error(f"Failed to parse Discord channel: {e}")
                continue

        return items

    async def fetch(self, content_ref: Union[str, ContentItem]) -> ContentData:
        """Fetch Discord content."""
        if isinstance(content_ref, str):
            # Parse Discord message ID
            if content_ref.startswith("discord_"):
                parts = content_ref.split("_", 2)
                if len(parts) >= 3:
                    channel_id = parts[1]
                    message_id = parts[2]
                else:
                    raise ValueError(f"Invalid Discord message ID format: {content_ref}")
            else:
                raise ValueError(f"Unsupported Discord ID format: {content_ref}")
        else:
            channel_id = content_ref.metadata.get("channel_id")
            message_id = content_ref.id.split("_")[-1] if "_" in content_ref.id else content_ref.id

        start_time = datetime.now()

        # Get single message
        endpoint = f"{self.api_base_url}/channels/{channel_id}/messages/{message_id}"

        response = await self._make_authenticated_request("GET", endpoint)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch Discord message: HTTP {response.status_code}")

        message = response.json_data

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContentData(
            item=content_ref if isinstance(content_ref, ContentItem) else None,
            raw_data=json.dumps(message).encode('utf-8'),
            text_content=message.get("content", ""),
            structured_data=message,
            metadata={
                "fetched_at": datetime.now().isoformat(),
                "processing_time_ms": processing_time
            },
            processing_time_ms=processing_time
        )

    async def validate(self, content: Union[ContentData, bytes]) -> ValidationResult:
        """Validate Discord content."""
        if isinstance(content, ContentData):
            structured_data = content.structured_data
            text_content = content.text_content or ""
        else:
            try:
                structured_data = json.loads(content.decode('utf-8'))
                text_content = structured_data.get("content", "")
            except (UnicodeDecodeError, json.JSONDecodeError):
                structured_data = None
                text_content = ""

        errors = []
        warnings = []

        # Check Discord message structure
        if structured_data:
            if "id" not in structured_data:
                errors.append("Missing message ID")
            if "content" not in structured_data:
                warnings.append("Missing message content")

            # Check for deleted messages
            if structured_data.get("deleted"):
                warnings.append("Message has been deleted")

            # Check for system messages
            if structured_data.get("type", 0) != 0:
                warnings.append("Message is a system message")

        # Check content
        if len(text_content.strip()) == 0:
            warnings.append("Message has no text content")

        is_valid = len(errors) == 0
        status = ValidationStatus.VALID if is_valid else ValidationStatus.INVALID
        if warnings and not errors:
            status = ValidationStatus.WARNING

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            message="Discord content validation completed",
            errors=errors,
            warnings=warnings,
            metadata={
                "has_structured_data": structured_data is not None,
                "text_length": len(text_content),
                "is_deleted": structured_data.get("deleted", False) if structured_data else False,
                "message_type": structured_data.get("type", 0) if structured_data else 0
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        """Get Discord connector capabilities."""
        capabilities = super().get_capabilities()
        capabilities.update({
            "supported_content_types": ["text"],
            "supported_operations": ["channel_messages", "guild_channels", "threads"],
            "features": ["real_time_updates", "authentication", "rate_limiting"],
            "authentication_methods": ["bot_token"],
            "rate_limiting": True,
            "retry_support": True,
            "batch_operations": True,
            "real_time_updates": True
        })
        return capabilities