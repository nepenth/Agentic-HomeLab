"""
Email Analysis Service for AI-powered email processing and categorization.

This service provides comprehensive email analysis capabilities including:
- Importance scoring and categorization
- Content analysis and summarization
- Sender reputation analysis
- Thread detection and grouping
- Attachment analysis
- Spam detection
- Urgency assessment
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from email.header import decode_header
from email.utils import parsedate_to_datetime

from app.services.ollama_client import ollama_client
from app.services.semantic_processing_service import semantic_processing_service
from app.utils.logging import get_logger

logger = get_logger("email_analysis_service")


@dataclass
class EmailAnalysis:
    """Result of email analysis."""
    email_id: str
    importance_score: float  # 0.0 to 1.0
    categories: List[str]
    urgency_level: str  # "low", "medium", "high", "urgent"
    sender_reputation: float  # 0.0 to 1.0
    content_summary: str
    key_topics: List[str]
    action_required: bool
    suggested_actions: List[str]
    thread_info: Optional[Dict[str, Any]] = None
    attachment_analysis: Optional[Dict[str, Any]] = None
    spam_probability: float = 0.0
    processing_time_ms: float = 0.0
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "email_id": self.email_id,
            "importance_score": self.importance_score,
            "categories": self.categories,
            "urgency_level": self.urgency_level,
            "sender_reputation": self.sender_reputation,
            "content_summary": self.content_summary,
            "key_topics": self.key_topics,
            "action_required": self.action_required,
            "suggested_actions": self.suggested_actions,
            "thread_info": self.thread_info,
            "attachment_analysis": self.attachment_analysis,
            "spam_probability": self.spam_probability,
            "processing_time_ms": self.processing_time_ms,
            "analyzed_at": self.analyzed_at.isoformat()
        }


@dataclass
class EmailMetadata:
    """Email metadata extracted for analysis."""
    subject: str
    sender: str
    sender_domain: str
    recipients: List[str]
    received_date: datetime
    content_length: int
    has_attachments: bool
    attachment_count: int
    content_type: str
    message_id: str
    thread_id: Optional[str] = None
    references: List[str] = field(default_factory=list)


class EmailAnalysisService:
    """Service for analyzing emails using AI and rule-based methods."""

    def __init__(self):
        self.logger = get_logger("email_analysis_service")

        # Analysis configuration
        self.importance_threshold = 0.7
        self.spam_threshold = 0.8
        self.urgency_keywords = {
            "urgent": 1.0, "asap": 0.9, "immediate": 0.9, "emergency": 1.0,
            "deadline": 0.8, "critical": 0.9, "important": 0.7, "priority": 0.8
        }
        self.spam_keywords = [
            "lottery", "winner", "viagra", "casino", "free money",
            "urgent business", "inheritance", "prince", "nigeria"
        ]

        # Known sender reputation scores (could be loaded from database)
        self.sender_reputation_cache: Dict[str, float] = {}

    async def analyze_email(
        self,
        email_content: str,
        email_metadata: Dict[str, Any],
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> EmailAnalysis:
        """
        Perform comprehensive analysis of an email.

        Args:
            email_content: Full email text content
            email_metadata: Email metadata (subject, sender, etc.)
            attachments: List of attachment information

        Returns:
            EmailAnalysis object with detailed analysis results
        """
        start_time = datetime.now()

        try:
            # Extract and normalize metadata
            metadata = self._extract_metadata(email_metadata)

            # Perform parallel analysis tasks
            tasks = [
                self._analyze_importance(email_content, metadata),
                self._categorize_email(email_content, metadata),
                self._assess_sender_reputation(metadata.sender, metadata.sender_domain),
                self._detect_spam(email_content, metadata),
                self._analyze_attachments(attachments or []),
                self._extract_key_topics(email_content),
                self._generate_summary(email_content),
                self._detect_thread_info(metadata)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions in parallel tasks and extract values
            importance_score = 0.5 if isinstance(results[0], Exception) else float(results[0])
            categories = ["general"] if isinstance(results[1], Exception) else list(results[1])
            sender_reputation = 0.5 if isinstance(results[2], Exception) else float(results[2])
            spam_probability = 0.0 if isinstance(results[3], Exception) else float(results[3])
            attachment_analysis = None if isinstance(results[4], Exception) else results[4]
            key_topics = [] if isinstance(results[5], Exception) else list(results[5])
            content_summary = "Analysis failed" if isinstance(results[6], Exception) else str(results[6])
            thread_info = None if isinstance(results[7], Exception) else results[7]

            # Calculate urgency level
            urgency_level = self._calculate_urgency_level(importance_score, email_content, metadata)

            # Determine if action is required
            action_required = importance_score >= self.importance_threshold and spam_probability < self.spam_threshold

            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(
                categories, urgency_level, action_required, attachment_analysis
            )

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            analysis = EmailAnalysis(
                email_id=metadata.message_id,
                importance_score=importance_score,
                categories=categories,
                urgency_level=urgency_level,
                sender_reputation=sender_reputation,
                content_summary=content_summary,
                key_topics=key_topics,
                action_required=action_required,
                suggested_actions=suggested_actions,
                thread_info=thread_info,
                attachment_analysis=attachment_analysis,
                spam_probability=spam_probability,
                processing_time_ms=processing_time
            )

            self.logger.info(f"Email analysis completed for {metadata.message_id} in {processing_time:.2f}ms")
            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze email: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Return minimal analysis on failure
            return EmailAnalysis(
                email_id=email_metadata.get("message_id", "unknown"),
                importance_score=0.5,
                categories=["general"],
                urgency_level="medium",
                sender_reputation=0.5,
                content_summary="Analysis failed",
                key_topics=[],
                action_required=False,
                suggested_actions=["Review manually"],
                spam_probability=0.0,
                processing_time_ms=processing_time
            )

    def _extract_metadata(self, email_metadata: Dict[str, Any]) -> EmailMetadata:
        """Extract and normalize email metadata."""
        subject = self._decode_header_value(email_metadata.get("subject", ""))
        sender = self._decode_header_value(email_metadata.get("sender", ""))
        sender_domain = sender.split("@")[-1] if "@" in sender else ""

        recipients = []
        for recipient_field in ["to", "cc", "bcc"]:
            if recipient_field in email_metadata:
                recipients.extend(self._parse_recipients(email_metadata[recipient_field]))

        # Parse received date
        received_date = datetime.now()
        if "date" in email_metadata:
            try:
                received_date = parsedate_to_datetime(email_metadata["date"])
            except:
                pass

        return EmailMetadata(
            subject=subject,
            sender=sender,
            sender_domain=sender_domain,
            recipients=recipients,
            received_date=received_date,
            content_length=email_metadata.get("content_length", 0),
            has_attachments=email_metadata.get("has_attachments", False),
            attachment_count=email_metadata.get("attachment_count", 0),
            content_type=email_metadata.get("content_type", "text/plain"),
            message_id=email_metadata.get("message_id", ""),
            thread_id=email_metadata.get("thread_id"),
            references=email_metadata.get("references", [])
        )

    def _decode_header_value(self, value: str) -> str:
        """Decode email header values."""
        if not value:
            return ""

        try:
            decoded_parts = decode_header(value)
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
            return value

    def _parse_recipients(self, recipient_str: str) -> List[str]:
        """Parse recipient string into list of email addresses."""
        if not recipient_str:
            return []

        # Simple regex to extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, recipient_str)

    async def _analyze_importance(self, content: str, metadata: EmailMetadata) -> float:
        """Analyze email importance using AI and rule-based methods."""
        try:
            # Rule-based scoring
            rule_score = self._calculate_rule_based_importance(content, metadata)

            # AI-based scoring
            ai_score = await self._calculate_ai_importance(content, metadata)

            # Combine scores (weighted average)
            combined_score = (rule_score * 0.4) + (ai_score * 0.6)

            return max(0.0, min(1.0, combined_score))

        except Exception as e:
            self.logger.warning(f"Importance analysis failed, using rule-based only: {e}")
            return self._calculate_rule_based_importance(content, metadata)

    def _calculate_rule_based_importance(self, content: str, metadata: EmailMetadata) -> float:
        """Calculate importance using rule-based heuristics."""
        score = 0.5  # Base score

        # Subject analysis
        subject_lower = metadata.subject.lower()
        if any(word in subject_lower for word in ["urgent", "important", "asap", "deadline"]):
            score += 0.2

        # Content analysis
        content_lower = content.lower()
        urgency_words = sum(1 for word in self.urgency_keywords.keys() if word in content_lower)
        score += min(0.2, urgency_words * 0.05)

        # Sender analysis
        if metadata.sender_domain in ["gmail.com", "outlook.com", "yahoo.com"]:
            score -= 0.1  # Penalize common domains slightly

        # Time-based scoring
        hours_old = (datetime.now() - metadata.received_date).total_seconds() / 3600
        if hours_old < 1:
            score += 0.1  # Recent emails get slight boost

        # Attachment bonus
        if metadata.has_attachments:
            score += 0.1

        return max(0.0, min(1.0, score))

    async def _calculate_ai_importance(self, content: str, metadata: EmailMetadata) -> float:
        """Calculate importance using AI analysis."""
        try:
            prompt = f"""
            Analyze the importance of this email on a scale from 0.0 to 1.0, where:
            - 1.0 = Extremely important (requires immediate action)
            - 0.5 = Moderately important (should review when possible)
            - 0.0 = Not important (can be ignored or archived)

            Consider:
            - Urgency and deadlines mentioned
            - Business impact or consequences
            - Personal relevance
            - Request for action or response
            - Sender's position/authority

            Subject: {metadata.subject}
            Sender: {metadata.sender}
            Content: {content[:1000]}...

            Return only a single number between 0.0 and 1.0.
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                response_text = response['response'].strip()
                try:
                    score = float(response_text)
                    return max(0.0, min(1.0, score))
                except ValueError:
                    # Try to extract number from text
                    import re
                    numbers = re.findall(r'(\d+\.?\d*)', response_text)
                    if numbers:
                        return max(0.0, min(1.0, float(numbers[0])))

            return 0.5  # Default if parsing fails

        except Exception as e:
            self.logger.warning(f"AI importance calculation failed: {e}")
            return 0.5

    async def _categorize_email(self, content: str, metadata: EmailMetadata) -> List[str]:
        """Categorize email into relevant categories."""
        try:
            prompt = f"""
            Categorize this email into 2-4 relevant categories from the following options:
            - work/business
            - personal
            - finance/billing
            - marketing/promotional
            - social/networking
            - news/updates
            - support/help
            - legal/compliance
            - education/learning
            - travel
            - health/medical
            - shopping
            - entertainment
            - spam/junk
            - other

            Subject: {metadata.subject}
            Sender: {metadata.sender}
            Content: {content[:800]}...

            Return categories as a JSON array of strings.
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                try:
                    response_text = response['response']
                    # Try to extract JSON array
                    json_start = response_text.find('[')
                    json_end = response_text.rfind(']') + 1

                    if json_start != -1 and json_end != -1:
                        json_str = response_text[json_start:json_end]
                        categories = json.loads(json_str)
                        if isinstance(categories, list):
                            return [cat.strip().lower() for cat in categories if cat.strip()]

                except json.JSONDecodeError:
                    pass

            # Fallback categorization
            return self._fallback_categorization(content, metadata)

        except Exception as e:
            self.logger.warning(f"AI categorization failed: {e}")
            return self._fallback_categorization(content, metadata)

    def _fallback_categorization(self, content: str, metadata: EmailMetadata) -> List[str]:
        """Fallback categorization using keyword matching."""
        categories = []
        content_lower = content.lower()
        subject_lower = metadata.subject.lower()

        # Simple keyword-based categorization
        if any(word in content_lower for word in ["invoice", "payment", "billing", "receipt"]):
            categories.append("finance/billing")
        if any(word in content_lower for word in ["meeting", "project", "deadline", "report"]):
            categories.append("work/business")
        if any(word in content_lower for word in ["friend", "family", "personal"]):
            categories.append("personal")
        if any(word in subject_lower for word in ["newsletter", "promotion", "offer"]):
            categories.append("marketing/promotional")

        return categories or ["general"]

    async def _assess_sender_reputation(self, sender: str, domain: str) -> float:
        """Assess sender reputation score."""
        # Check cache first
        cache_key = f"{sender}@{domain}"
        if cache_key in self.sender_reputation_cache:
            return self.sender_reputation_cache[cache_key]

        # Simple reputation scoring
        score = 0.5  # Base score

        # Domain-based scoring
        trusted_domains = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com"]
        if domain in trusted_domains:
            score += 0.2

        # Known spam domains
        spam_domains = ["spam.com", "junkmail.com"]
        if domain in spam_domains:
            score -= 0.3

        # Length and format checks
        if len(sender) > 3 and "@" in sender:
            score += 0.1

        # Cache the result
        final_score = max(0.0, min(1.0, score))
        self.sender_reputation_cache[cache_key] = final_score

        return final_score

    async def _detect_spam(self, content: str, metadata: EmailMetadata) -> float:
        """Detect spam probability."""
        spam_indicators = 0
        total_indicators = 0

        # Keyword-based spam detection
        content_lower = content.lower()
        subject_lower = metadata.subject.lower()

        for keyword in self.spam_keywords:
            total_indicators += 1
            if keyword in content_lower or keyword in subject_lower:
                spam_indicators += 1

        # Check for excessive caps
        caps_ratio = sum(1 for c in metadata.subject if c.isupper()) / max(1, len(metadata.subject))
        if caps_ratio > 0.5:
            spam_indicators += 1
            total_indicators += 1

        # Check for suspicious sender patterns
        if re.search(r'\d{8,}', metadata.sender):  # Long numbers in sender
            spam_indicators += 1
            total_indicators += 1

        # Calculate probability
        if total_indicators == 0:
            return 0.0

        return min(1.0, spam_indicators / total_indicators)

    async def _analyze_attachments(self, attachments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze email attachments."""
        if not attachments:
            return {"has_attachments": False, "count": 0, "analysis": []}

        analysis = []
        total_size = 0

        for attachment in attachments:
            attachment_info = {
                "filename": attachment.get("filename", "unknown"),
                "content_type": attachment.get("content_type", "unknown"),
                "size_bytes": attachment.get("size", 0),
                "risk_level": "low"
            }

            # Risk assessment
            filename = attachment_info["filename"].lower()
            if any(ext in filename for ext in [".exe", ".bat", ".scr", ".pif"]):
                attachment_info["risk_level"] = "high"
            elif any(ext in filename for ext in [".doc", ".xls", ".pdf", ".zip"]):
                attachment_info["risk_level"] = "medium"

            total_size += attachment_info["size_bytes"]
            analysis.append(attachment_info)

        return {
            "has_attachments": True,
            "count": len(attachments),
            "total_size_bytes": total_size,
            "analysis": analysis
        }

    async def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from email content."""
        try:
            prompt = f"""
            Extract 3-5 key topics or themes from this email content.
            Return them as a JSON array of strings.

            Content: {content[:1000]}...
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                try:
                    response_text = response['response']
                    json_start = response_text.find('[')
                    json_end = response_text.rfind(']') + 1

                    if json_start != -1 and json_end != -1:
                        json_str = response_text[json_start:json_end]
                        topics = json.loads(json_str)
                        if isinstance(topics, list):
                            return [topic.strip() for topic in topics if topic.strip()]

                except json.JSONDecodeError:
                    pass

            # Fallback: extract nouns as topics
            return self._extract_nouns_as_topics(content)

        except Exception as e:
            self.logger.warning(f"Topic extraction failed: {e}")
            return self._extract_nouns_as_topics(content)

    def _extract_nouns_as_topics(self, content: str) -> List[str]:
        """Simple noun extraction as fallback for topics."""
        # Very basic noun extraction (could be improved with NLP library)
        words = re.findall(r'\b[A-Z][a-z]+\b', content)
        return list(set(words))[:5] if words else ["general"]

    async def _generate_summary(self, content: str) -> str:
        """Generate a concise summary of the email content."""
        try:
            prompt = f"""
            Summarize this email in 2-3 sentences, capturing the main points and any actions required.

            Content: {content[:1500]}...
            """

            response = await ollama_client.generate(prompt=prompt, stream=False)

            if response and 'response' in response:
                summary = response['response'].strip()
                if len(summary) > 10:  # Basic validation
                    return summary

            # Fallback summary
            return f"Email about: {content[:100]}..."

        except Exception as e:
            self.logger.warning(f"Summary generation failed: {e}")
            return f"Email content: {content[:100]}..."

    async def _detect_thread_info(self, metadata: EmailMetadata) -> Dict[str, Any]:
        """Detect thread information from email metadata."""
        thread_info = {
            "is_thread": False,
            "thread_id": None,
            "position_in_thread": 0,
            "thread_size": 1
        }

        # Check for thread indicators
        if metadata.thread_id or metadata.references:
            thread_info["is_thread"] = True
            thread_info["thread_id"] = metadata.thread_id or metadata.references[0] if metadata.references else None
            thread_info["position_in_thread"] = len(metadata.references) + 1

        return thread_info

    def _calculate_urgency_level(self, importance_score: float, content: str, metadata: EmailMetadata) -> str:
        """Calculate urgency level based on importance and content analysis."""
        if importance_score >= 0.9:
            return "urgent"
        elif importance_score >= 0.7:
            return "high"
        elif importance_score >= 0.4:
            return "medium"
        else:
            return "low"

    def _generate_suggested_actions(self, categories: List[str], urgency_level: str,
                                  action_required: bool, attachment_analysis: Optional[Dict[str, Any]]) -> List[str]:
        """Generate suggested actions based on email analysis."""
        actions = []

        if not action_required:
            actions.append("Archive or delete")
            return actions

        # Category-based actions
        if "work/business" in categories:
            actions.append("Review and respond during work hours")
        if "finance/billing" in categories:
            actions.append("Review financial details carefully")
        if "support/help" in categories:
            actions.append("Escalate to appropriate team if needed")

        # Urgency-based actions
        if urgency_level in ["urgent", "high"]:
            actions.append("Respond immediately")
        elif urgency_level == "medium":
            actions.append("Respond within 24 hours")

        # Attachment-based actions
        if attachment_analysis and attachment_analysis.get("has_attachments"):
            actions.append("Review attachments for security risks")
            if any(att.get("risk_level") == "high" for att in attachment_analysis.get("analysis", [])):
                actions.append("⚠️ High-risk attachment detected - scan before opening")

        return actions[:3]  # Limit to top 3 actions

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "sender_reputation_cache_size": len(self.sender_reputation_cache),
            "importance_threshold": self.importance_threshold,
            "spam_threshold": self.spam_threshold,
            "urgency_keywords_count": len(self.urgency_keywords),
            "spam_keywords_count": len(self.spam_keywords)
        }


# Global instance
email_analysis_service = EmailAnalysisService()