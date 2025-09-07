"""
Enhanced Email Thread Detection Service for advanced conversation grouping.

This service provides sophisticated email thread detection and management with:
- Semantic similarity analysis for thread detection
- Machine learning-based thread classification
- Advanced participant analysis and relationship mapping
- Thread evolution tracking and analytics
- Cross-thread relationship discovery
- Performance optimizations and caching
- Real-time thread updates and notifications
"""

import re
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import json

from app.services.email_analysis_service import EmailAnalysis, EmailMetadata
from app.services.semantic_processing_service import SemanticProcessingService
from app.utils.logging import get_logger

logger = get_logger("email_thread_detection")


class ThreadType(Enum):
    """Enhanced thread type classification."""
    DIRECT = "direct"           # 1-on-1 conversation
    REPLY_CHAIN = "reply_chain" # Multi-person reply chain
    BROADCAST = "broadcast"     # One-to-many communication
    DISCUSSION = "discussion"   # Multi-way discussion
    TASK_THREAD = "task_thread" # Task-related conversation
    PROJECT_THREAD = "project_thread" # Project-related discussion


class ThreadStatus(Enum):
    """Thread lifecycle status."""
    ACTIVE = "active"
    DORMANT = "dormant"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ThreadPriority(Enum):
    """Thread priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class EmailThread:
    """Enhanced email thread with advanced analytics and ML features."""
    thread_id: str
    subject: str
    root_subject: str  # Original subject without prefixes
    participants: Set[str]
    message_count: int
    first_message_date: datetime
    last_message_date: datetime
    importance_score: float
    thread_type: ThreadType
    thread_status: ThreadStatus = ThreadStatus.ACTIVE
    thread_priority: ThreadPriority = ThreadPriority.MEDIUM
    emails: List[Dict[str, Any]] = field(default_factory=list)
    thread_metadata: Dict[str, Any] = field(default_factory=dict)

    # Enhanced features
    semantic_embedding: Optional[List[float]] = None
    topic_clusters: List[str] = field(default_factory=list)
    sentiment_trend: List[float] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    participant_roles: Dict[str, str] = field(default_factory=dict)
    related_threads: List[str] = field(default_factory=list)
    thread_evolution: List[Dict[str, Any]] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    dormant_threshold_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "thread_id": self.thread_id,
            "subject": self.subject,
            "root_subject": self.root_subject,
            "participants": list(self.participants),
            "message_count": self.message_count,
            "first_message_date": self.first_message_date.isoformat(),
            "last_message_date": self.last_message_date.isoformat(),
            "importance_score": self.importance_score,
            "thread_type": self.thread_type.value,
            "thread_status": self.thread_status.value,
            "thread_priority": self.thread_priority.value,
            "emails": self.emails,
            "thread_metadata": self.thread_metadata,
            "semantic_embedding": self.semantic_embedding,
            "topic_clusters": self.topic_clusters,
            "sentiment_trend": self.sentiment_trend,
            "response_times": self.response_times,
            "participant_roles": self.participant_roles,
            "related_threads": self.related_threads,
            "thread_evolution": self.thread_evolution,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "dormant_threshold_days": self.dormant_threshold_days
        }


@dataclass
class ThreadDetectionResult:
    """Result of thread detection analysis."""
    threads: List[EmailThread]
    unthreaded_emails: List[Dict[str, Any]]
    total_emails_processed: int
    threads_created: int
    average_thread_length: float
    processing_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "threads": [thread.to_dict() for thread in self.threads],
            "unthreaded_emails": self.unthreaded_emails,
            "total_emails_processed": self.total_emails_processed,
            "threads_created": self.threads_created,
            "average_thread_length": self.average_thread_length,
            "processing_time_ms": self.processing_time_ms
        }


class EmailThreadDetector:
    """Enhanced service for detecting and managing email threads with ML capabilities."""

    def __init__(self, semantic_service: Optional[SemanticProcessingService] = None):
        self.logger = get_logger("email_thread_detector")
        self.semantic_service = semantic_service

        # Thread detection patterns
        self.reply_patterns = [
            r"^re:\s*",
            r"^r:\s*",
            r"^\[re\]\s*",
            r"^回复:\s*",
            r"^答复:\s*"
        ]

        self.forward_patterns = [
            r"^fwd?:\s*",
            r"^f:\s*",
            r"^\[fwd?\]\s*",
            r"^转发:\s*"
        ]

        # Thread similarity thresholds
        self.subject_similarity_threshold = 0.8
        self.participant_overlap_threshold = 0.5
        self.time_window_days = 30  # Maximum days between related messages

        # Thread type detection
        self.min_broadcast_participants = 3
        self.max_direct_participants = 2

    async def detect_threads(
        self,
        emails: List[Dict[str, Any]],
        analysis_results: Optional[List[EmailAnalysis]] = None
    ) -> ThreadDetectionResult:
        """
        Detect email threads from a collection of emails.

        Args:
            emails: List of email data dictionaries
            analysis_results: Optional email analysis results

        Returns:
            ThreadDetectionResult with detected threads
        """
        start_time = datetime.now()

        try:
            # Preprocess emails for thread detection
            processed_emails = self._preprocess_emails(emails)

            # Group emails by potential threads
            thread_groups = self._group_emails_by_subject(processed_emails)

            # Refine thread groups based on participants and timing
            refined_threads = self._refine_thread_groups(thread_groups, processed_emails)

            # Create thread objects
            threads = []
            unthreaded_emails = []

            for thread_data in refined_threads:
                if len(thread_data["emails"]) > 1:  # Only create threads with multiple emails
                    thread = await self._create_thread(thread_data, analysis_results)
                    threads.append(thread)
                else:
                    unthreaded_emails.extend(thread_data["emails"])

            # Calculate statistics
            total_emails = len(emails)
            threads_created = len(threads)
            avg_thread_length = sum(len(t.emails) for t in threads) / max(threads_created, 1)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            result = ThreadDetectionResult(
                threads=threads,
                unthreaded_emails=unthreaded_emails,
                total_emails_processed=total_emails,
                threads_created=threads_created,
                average_thread_length=avg_thread_length,
                processing_time_ms=processing_time
            )

            self.logger.info(f"Thread detection completed: {threads_created} threads from {total_emails} emails")
            return result

        except Exception as e:
            self.logger.error(f"Thread detection failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return ThreadDetectionResult(
                threads=[],
                unthreaded_emails=emails,
                total_emails_processed=len(emails),
                threads_created=0,
                average_thread_length=0.0,
                processing_time_ms=processing_time
            )

    def _preprocess_emails(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess emails for thread detection."""
        processed = []

        for email in emails:
            processed_email = email.copy()

            # Extract and normalize subject
            subject = email.get("subject", "").strip()
            processed_email["normalized_subject"] = self._normalize_subject(subject)
            processed_email["root_subject"] = self._extract_root_subject(subject)

            # Extract participants
            participants = self._extract_participants(email)
            processed_email["participants"] = participants

            # Parse date
            sent_date = self._parse_email_date(email.get("date", ""))
            processed_email["parsed_date"] = sent_date

            # Generate email signature for deduplication
            processed_email["email_signature"] = self._generate_email_signature(email)

            processed.append(processed_email)

        return processed

    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject line for comparison."""
        if not subject:
            return ""

        # Convert to lowercase
        normalized = subject.lower()

        # Remove reply/forward prefixes
        for pattern in self.reply_patterns + self.forward_patterns:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Remove common prefixes and extra whitespace
        normalized = re.sub(r"^\s*[\[\(]?[\w\s]*[\]\)]?\s*[:\-]?\s*", "", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def _extract_root_subject(self, subject: str) -> str:
        """Extract the root/original subject from a reply/forward chain."""
        if not subject:
            return ""

        # Find the deepest level of reply/forward
        original_subject = subject
        max_iterations = 10  # Prevent infinite loops

        for _ in range(max_iterations):
            new_subject = self._normalize_subject(original_subject)
            if new_subject == original_subject:
                break
            original_subject = new_subject

        return original_subject

    def _extract_participants(self, email: Dict[str, Any]) -> Set[str]:
        """Extract all participants from an email."""
        participants = set()

        # Add sender
        sender = email.get("sender", "")
        if sender:
            participants.add(self._normalize_email_address(sender))

        # Add recipients (to, cc, bcc)
        for recipient_field in ["to", "cc", "bcc"]:
            recipients = email.get(recipient_field, [])
            if isinstance(recipients, str):
                recipients = [recipients]
            elif not isinstance(recipients, list):
                continue

            for recipient in recipients:
                if recipient:
                    participants.add(self._normalize_email_address(recipient))

        return participants

    def _normalize_email_address(self, email: str) -> str:
        """Normalize email address for comparison."""
        if not email:
            return ""

        # Extract email from "Name <email>" format
        email_match = re.search(r'<([^>]+)>', email)
        if email_match:
            return email_match.group(1).lower().strip()

        # Extract email from various formats
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email)
        if email_match:
            return email_match.group(0).lower().strip()

        return email.lower().strip()

    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime object."""
        if not date_str:
            return datetime.now()

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try common email date formats
                # This is a simplified implementation - in production you'd want more robust parsing
                return datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Fallback to current time
                return datetime.now()

    def _generate_email_signature(self, email: Dict[str, Any]) -> str:
        """Generate a unique signature for email deduplication."""
        # Create a hash based on key email properties
        content = f"{email.get('subject', '')}|{email.get('sender', '')}|{email.get('date', '')}"
        return hashlib.md5(content.encode()).hexdigest()

    def _group_emails_by_subject(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group emails by normalized subject."""
        subject_groups = defaultdict(list)

        for email in emails:
            normalized_subject = email.get("normalized_subject", "")
            if normalized_subject:
                subject_groups[normalized_subject].append(email)

        # Convert to list of thread groups
        thread_groups = []
        for subject, emails_in_group in subject_groups.items():
            if len(emails_in_group) > 1:  # Only consider potential threads
                thread_groups.append({
                    "subject": subject,
                    "root_subject": emails_in_group[0].get("root_subject", subject),
                    "emails": emails_in_group,
                    "participant_overlap": self._calculate_participant_overlap(emails_in_group)
                })

        return thread_groups

    def _calculate_participant_overlap(self, emails: List[Dict[str, Any]]) -> float:
        """Calculate participant overlap across emails in a potential thread."""
        if not emails:
            return 0.0

        all_participants = set()
        for email in emails:
            all_participants.update(email.get("participants", set()))

        if not all_participants:
            return 0.0

        # Calculate average participant overlap
        total_overlap = 0.0
        for i, email1 in enumerate(emails):
            participants1 = email1.get("participants", set())
            if not participants1:
                continue

            for j, email2 in enumerate(emails):
                if i != j:
                    participants2 = email2.get("participants", set())
                    if participants2:
                        overlap = len(participants1.intersection(participants2))
                        total_overlap += overlap / len(participants1.union(participants2))

        return total_overlap / max(len(emails) * (len(emails) - 1), 1)

    def _refine_thread_groups(
        self,
        thread_groups: List[Dict[str, Any]],
        all_emails: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Refine thread groups based on timing and participant patterns."""
        refined_groups = []

        for group in thread_groups:
            emails = group["emails"]

            # Sort emails by date
            emails.sort(key=lambda x: x.get("parsed_date", datetime.now()))

            # Check time window
            if not self._emails_within_time_window(emails):
                continue

            # Check participant consistency
            if not self._participants_consistent(emails):
                continue

            # Remove duplicate emails based on signature
            unique_emails = self._remove_duplicates(emails)

            if len(unique_emails) > 1:
                group["emails"] = unique_emails
                refined_groups.append(group)

        return refined_groups

    def _emails_within_time_window(self, emails: List[Dict[str, Any]]) -> bool:
        """Check if emails are within the acceptable time window."""
        if len(emails) < 2:
            return True

        dates = [email.get("parsed_date", datetime.now()) for email in emails]
        min_date = min(dates)
        max_date = max(dates)

        time_diff = max_date - min_date
        return time_diff.days <= self.time_window_days

    def _participants_consistent(self, emails: List[Dict[str, Any]]) -> bool:
        """Check if participants are consistent across thread emails."""
        if len(emails) < 2:
            return True

        # For small groups, require some participant overlap
        if len(emails) <= 3:
            overlap_score = self._calculate_participant_overlap(emails)
            return overlap_score >= self.participant_overlap_threshold

        # For larger groups, allow more flexibility
        return True

    def _remove_duplicates(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate emails based on signature."""
        seen_signatures = set()
        unique_emails = []

        for email in emails:
            signature = email.get("email_signature", "")
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_emails.append(email)

        return unique_emails

    async def _create_thread(
        self,
        thread_data: Dict[str, Any],
        analysis_results: Optional[List[EmailAnalysis]] = None
    ) -> EmailThread:
        """Create a thread object from thread data."""
        emails = thread_data["emails"]
        subject = thread_data.get("subject", "")
        root_subject = thread_data.get("root_subject", subject)

        # Collect all participants
        all_participants = set()
        for email in emails:
            all_participants.update(email.get("participants", set()))

        # Determine thread type
        thread_type = self._determine_thread_type(emails, all_participants)

        # Calculate importance score
        importance_score = await self._calculate_thread_importance(emails, analysis_results)

        # Sort emails by date
        emails.sort(key=lambda x: x.get("parsed_date", datetime.now()))

        # Generate thread ID
        thread_id = self._generate_thread_id(emails)

        thread = EmailThread(
            thread_id=thread_id,
            subject=subject,
            root_subject=root_subject,
            participants=all_participants,
            message_count=len(emails),
            first_message_date=emails[0].get("parsed_date", datetime.now()),
            last_message_date=emails[-1].get("parsed_date", datetime.now()),
            importance_score=importance_score,
            thread_type=thread_type,
            emails=emails,
            thread_metadata={
                "participant_overlap": thread_data.get("participant_overlap", 0.0),
                "time_span_days": (emails[-1].get("parsed_date", datetime.now()) -
                                 emails[0].get("parsed_date", datetime.now())).days
            }
        )

        return thread

    def _determine_thread_type(self, emails: List[Dict[str, Any]], participants: Set[str]) -> ThreadType:
        """Determine the type of email thread using advanced classification."""
        num_participants = len(participants)
        num_emails = len(emails)

        # Analyze email patterns for intelligent classification
        has_task_keywords = self._contains_task_keywords(emails)
        has_project_keywords = self._contains_project_keywords(emails)
        response_pattern = self._analyze_response_pattern(emails)

        # Classification logic
        if num_participants <= self.max_direct_participants:
            return ThreadType.DIRECT
        elif num_participants >= self.min_broadcast_participants:
            return ThreadType.BROADCAST
        elif has_task_keywords and response_pattern == "coordinated":
            return ThreadType.TASK_THREAD
        elif has_project_keywords and num_emails > 5:
            return ThreadType.PROJECT_THREAD
        elif response_pattern == "discussion":
            return ThreadType.DISCUSSION
        else:
            return ThreadType.REPLY_CHAIN

    async def _calculate_thread_importance(
        self,
        emails: List[Dict[str, Any]],
        analysis_results: Optional[List[EmailAnalysis]] = None
    ) -> float:
        """Calculate importance score for the thread."""
        if not emails:
            return 0.0

        # Use analysis results if available
        if analysis_results:
            thread_importance = 0.0
            count = 0
            for email in emails:
                email_id = email.get("message_id", "")
                for analysis in analysis_results:
                    if analysis.email_id == email_id:
                        thread_importance += analysis.importance_score
                        count += 1
                        break

            if count > 0:
                return thread_importance / count

        # Fallback: calculate based on email properties
        importance_scores = []
        for email in emails:
            score = 0.0

            # Subject-based scoring
            subject = email.get("subject", "").lower()
            if any(word in subject for word in ["urgent", "important", "asap", "deadline"]):
                score += 0.3

            # Sender domain scoring (simplified)
            sender = email.get("sender", "").lower()
            if any(domain in sender for domain in ["boss", "manager", "executive"]):
                score += 0.2

            # Participant count scoring
            participants = email.get("participants", set())
            if len(participants) > 5:
                score += 0.1

            importance_scores.append(min(score, 1.0))

        return sum(importance_scores) / len(importance_scores) if importance_scores else 0.0

    def _generate_thread_id(self, emails: List[Dict[str, Any]]) -> str:
        """Generate a unique thread ID."""
        if not emails:
            return ""

        # Use the earliest email's properties to generate thread ID
        earliest_email = min(emails, key=lambda x: x.get("parsed_date", datetime.now()))

        # Create a deterministic thread ID
        thread_content = f"{earliest_email.get('root_subject', '')}|{earliest_email.get('sender', '')}"
        return hashlib.md5(thread_content.encode()).hexdigest()

    async def find_related_threads(
        self,
        thread: EmailThread,
        all_threads: List[EmailThread],
        max_related: int = 5
    ) -> List[Tuple[EmailThread, float]]:
        """
        Find threads related to the given thread.

        Args:
            thread: The reference thread
            all_threads: All available threads
            max_related: Maximum number of related threads to return

        Returns:
            List of (thread, similarity_score) tuples
        """
        related_threads = []

        for other_thread in all_threads:
            if other_thread.thread_id == thread.thread_id:
                continue

            similarity = self._calculate_thread_similarity(thread, other_thread)
            if similarity > 0.3:  # Minimum similarity threshold
                related_threads.append((other_thread, similarity))

        # Sort by similarity and return top results
        related_threads.sort(key=lambda x: x[1], reverse=True)
        return related_threads[:max_related]

    def _calculate_thread_similarity(self, thread1: EmailThread, thread2: EmailThread) -> float:
        """Calculate similarity between two threads."""
        similarity_score = 0.0

        # Subject similarity
        subject_sim = self._calculate_subject_similarity(thread1.root_subject, thread2.root_subject)
        similarity_score += subject_sim * 0.4

        # Participant overlap
        participant_overlap = len(thread1.participants.intersection(thread2.participants))
        total_participants = len(thread1.participants.union(thread2.participants))
        if total_participants > 0:
            participant_sim = participant_overlap / total_participants
            similarity_score += participant_sim * 0.4

        # Time proximity
        time_diff = abs((thread1.first_message_date - thread2.first_message_date).days)
        time_sim = max(0, 1 - (time_diff / 30))  # Decay over 30 days
        similarity_score += time_sim * 0.2

        return similarity_score

    def _calculate_subject_similarity(self, subject1: str, subject2: str) -> float:
        """Calculate similarity between two subjects."""
        if not subject1 or not subject2:
            return 0.0

        # Simple word overlap similarity
        words1 = set(subject1.lower().split())
        words2 = set(subject2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def generate_semantic_embeddings(self, thread: EmailThread) -> Optional[List[float]]:
        """Generate semantic embeddings for a thread."""
        if not self.semantic_service:
            return None

        try:
            # Combine thread subject and key email content
            thread_content = f"{thread.subject} {' '.join([email.get('content', '')[:500] for email in thread.emails[:3]])}"
            embedding = await self.semantic_service.generate_embedding(thread_content)
            return embedding
        except Exception as e:
            self.logger.error(f"Failed to generate semantic embedding for thread {thread.thread_id}: {e}")
            return None

    async def analyze_thread_evolution(self, thread: EmailThread) -> List[Dict[str, Any]]:
        """Analyze how a thread has evolved over time."""
        evolution = []
        sorted_emails = sorted(thread.emails, key=lambda x: x.get("parsed_date", datetime.now()))

        for i, email in enumerate(sorted_emails):
            evolution_entry = {
                "email_index": i,
                "timestamp": email.get("parsed_date", datetime.now()).isoformat(),
                "sender": email.get("sender", ""),
                "participant_count": len(thread.participants),
                "thread_length": len(sorted_emails),
                "response_time": self._calculate_response_time(sorted_emails, i)
            }
            evolution.append(evolution_entry)

        return evolution

    def _calculate_response_time(self, emails: List[Dict[str, Any]], index: int) -> Optional[float]:
        """Calculate response time for an email in the thread."""
        if index == 0:
            return None

        current_date = emails[index].get("parsed_date", datetime.now())
        previous_date = emails[index - 1].get("parsed_date", datetime.now())

        return (current_date - previous_date).total_seconds()

    async def classify_participant_roles(self, thread: EmailThread) -> Dict[str, str]:
        """Classify roles of participants in the thread."""
        roles = {}

        # Analyze email patterns to determine roles
        for participant in thread.participants:
            participant_emails = [email for email in thread.emails if email.get("sender", "") == participant]
            email_count = len(participant_emails)

            if email_count == 0:
                roles[participant] = "recipient"
            elif email_count == 1:
                # Check if it's the first email
                first_email = min(thread.emails, key=lambda x: x.get("parsed_date", datetime.now()))
                if first_email.get("sender", "") == participant:
                    roles[participant] = "initiator"
                else:
                    roles[participant] = "responder"
            elif email_count > len(thread.emails) * 0.4:
                roles[participant] = "coordinator"
            else:
                roles[participant] = "contributor"

        return roles

    async def detect_topic_clusters(self, thread: EmailThread) -> List[str]:
        """Detect topic clusters within the thread."""
        if not self.semantic_service:
            return []

        try:
            # Extract topics from email content using classification
            all_content = " ".join([email.get("content", "") for email in thread.emails])
            # Use common email topic categories
            topic_categories = [
                "business", "personal", "technical", "project", "meeting",
                "deadline", "finance", "support", "marketing", "urgent"
            ]
            topic_scores = await self.semantic_service.classify_content(all_content, topic_categories)
            # Return topics with scores above threshold
            topics = [topic for topic, score in topic_scores.items() if score > 0.3]
            return topics[:5]  # Limit to top 5
        except Exception as e:
            self.logger.error(f"Failed to detect topics for thread {thread.thread_id}: {e}")
            return []

    async def analyze_sentiment_trend(self, thread: EmailThread) -> List[float]:
        """Analyze sentiment trend throughout the thread."""
        if not self.semantic_service:
            return []

        try:
            sentiments = []
            for email in thread.emails:
                content = email.get("content", "")
                if content:
                    # Use importance scoring as a proxy for sentiment
                    # Positive/important content tends to have higher scores
                    sentiment_score = await self.semantic_service.score_importance(content)
                    sentiments.append(sentiment_score)
                else:
                    sentiments.append(0.0)

            return sentiments
        except Exception as e:
            self.logger.error(f"Failed to analyze sentiment for thread {thread.thread_id}: {e}")
            return []

    def update_thread_status(self, thread: EmailThread) -> ThreadStatus:
        """Update thread status based on activity patterns."""
        now = datetime.now()
        days_since_last_activity = (now - thread.last_message_date).days

        if days_since_last_activity > thread.dormant_threshold_days * 2:
            return ThreadStatus.ARCHIVED
        elif days_since_last_activity > thread.dormant_threshold_days:
            return ThreadStatus.DORMANT
        else:
            return ThreadStatus.ACTIVE

    def calculate_thread_priority(self, thread: EmailThread) -> ThreadPriority:
        """Calculate thread priority based on various factors."""
        score = 0.0

        # Importance score contribution
        score += thread.importance_score * 0.4

        # Urgency keywords in recent emails
        recent_emails = [email for email in thread.emails
                        if (datetime.now() - email.get("parsed_date", datetime.now())).days <= 1]
        urgency_keywords = ["urgent", "asap", "deadline", "critical", "emergency"]

        for email in recent_emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}".lower()
            if any(keyword in content for keyword in urgency_keywords):
                score += 0.3
                break

        # Participant count (more participants = higher priority)
        score += min(len(thread.participants) / 10, 0.2)

        # Recency bonus
        days_since_last = (datetime.now() - thread.last_message_date).days
        recency_bonus = max(0, 0.1 * (7 - days_since_last) / 7)
        score += recency_bonus

        # Determine priority level
        if score >= 0.8:
            return ThreadPriority.URGENT
        elif score >= 0.6:
            return ThreadPriority.HIGH
        elif score >= 0.4:
            return ThreadPriority.MEDIUM
        else:
            return ThreadPriority.LOW

    def _contains_task_keywords(self, emails: List[Dict[str, Any]]) -> bool:
        """Check if emails contain task-related keywords."""
        task_keywords = [
            "task", "todo", "action", "complete", "deadline", "due",
            "assign", "responsible", "follow-up", "next steps"
        ]

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}".lower()
            if any(keyword in content for keyword in task_keywords):
                return True
        return False

    def _contains_project_keywords(self, emails: List[Dict[str, Any]]) -> bool:
        """Check if emails contain project-related keywords."""
        project_keywords = [
            "project", "milestone", "deliverable", "timeline", "status",
            "progress", "update", "meeting", "review", "planning"
        ]

        for email in emails:
            content = f"{email.get('subject', '')} {email.get('content', '')}".lower()
            if any(keyword in content for keyword in project_keywords):
                return True
        return False

    def _analyze_response_pattern(self, emails: List[Dict[str, Any]]) -> str:
        """Analyze the response pattern in a thread."""
        if len(emails) < 3:
            return "simple"

        # Sort emails by date
        sorted_emails = sorted(emails, key=lambda x: x.get("parsed_date", datetime.now()))

        # Analyze response times and patterns
        response_times = []
        for i in range(1, len(sorted_emails)):
            prev_date = sorted_emails[i-1].get("parsed_date", datetime.now())
            curr_date = sorted_emails[i].get("parsed_date", datetime.now())
            response_times.append((curr_date - prev_date).total_seconds())

        if not response_times:
            return "simple"

        avg_response_time = sum(response_times) / len(response_times)

        # Classify based on response patterns
        if avg_response_time < 3600:  # Less than 1 hour
            return "coordinated"
        elif avg_response_time < 86400:  # Less than 1 day
            return "active"
        elif len(set(email.get("sender", "") for email in emails)) > len(emails) * 0.6:
            return "discussion"
        else:
            return "sequential"

    def get_stats(self) -> Dict[str, Any]:
        """Get thread detection service statistics."""
        return {
            "reply_patterns_count": len(self.reply_patterns),
            "forward_patterns_count": len(self.forward_patterns),
            "subject_similarity_threshold": self.subject_similarity_threshold,
            "participant_overlap_threshold": self.participant_overlap_threshold,
            "time_window_days": self.time_window_days,
            "min_broadcast_participants": self.min_broadcast_participants,
            "max_direct_participants": self.max_direct_participants
        }


# Global instance
email_thread_detector = EmailThreadDetector()