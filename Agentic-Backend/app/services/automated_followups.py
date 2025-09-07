"""
Automated Follow-ups Service for intelligent email follow-up scheduling.

This service provides smart follow-up scheduling, reminder management,
and automated task creation based on email content analysis.
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re

from app.services.email_analysis_service import EmailAnalysis
from app.utils.logging import get_logger


class FollowUpType(Enum):
    """Types of automated follow-ups."""
    RESPONSE_REMINDER = "response_reminder"
    DEADLINE_FOLLOWUP = "deadline_followup"
    MEETING_FOLLOWUP = "meeting_followup"
    TASK_FOLLOWUP = "task_followup"
    INFORMATION_REQUEST = "information_request"
    CUSTOM_FOLLOWUP = "custom_followup"


class FollowUpPriority(Enum):
    """Priority levels for follow-ups."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FollowUpStatus(Enum):
    """Status of follow-up items."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


@dataclass
class FollowUpItem:
    """Represents a scheduled follow-up item."""
    id: str
    email_id: str
    follow_up_type: FollowUpType
    priority: FollowUpPriority
    status: FollowUpStatus
    scheduled_time: datetime
    created_time: datetime
    subject: str
    recipient: str
    content_preview: str
    trigger_reason: str
    completed_time: Optional[datetime] = None
    follow_up_content: Optional[str] = None
    reminder_count: int = 0
    last_reminder_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FollowUpTemplate:
    """Template for generating follow-up content."""
    id: str
    name: str
    type: FollowUpType
    template_text: str
    variables: List[str]
    conditions: Dict[str, Any]


class AutomatedFollowupsService:
    """Service for managing automated email follow-ups."""

    def __init__(self):
        self.logger = get_logger("automated_followups")
        self.follow_ups: Dict[str, FollowUpItem] = {}
        self.templates: Dict[str, FollowUpTemplate] = {}

        # Default follow-up intervals (in hours)
        self.default_intervals = {
            FollowUpType.RESPONSE_REMINDER: 24,  # 1 day
            FollowUpType.DEADLINE_FOLLOWUP: 48,   # 2 days
            FollowUpType.MEETING_FOLLOWUP: 2,     # 2 hours
            FollowUpType.TASK_FOLLOWUP: 72,       # 3 days
            FollowUpType.INFORMATION_REQUEST: 168, # 1 week
        }

        # Initialize default templates
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default follow-up templates."""
        templates = [
            FollowUpTemplate(
                id="response_reminder",
                name="Response Reminder",
                type=FollowUpType.RESPONSE_REMINDER,
                template_text="Hi {recipient_name},\n\nI wanted to follow up on my previous email regarding '{subject}'. I understand you might be busy, but I'd appreciate any updates on this matter.\n\nBest regards,\n{sender_name}",
                variables=["recipient_name", "subject", "sender_name"],
                conditions={"importance_threshold": 0.7, "days_since_sent": 2}
            ),
            FollowUpTemplate(
                id="meeting_followup",
                name="Meeting Follow-up",
                type=FollowUpType.MEETING_FOLLOWUP,
                template_text="Hi {recipient_name},\n\nFollowing up on our meeting about '{subject}'. As discussed, here are the key action items:\n\n{action_items}\n\nPlease let me know if you need any additional information.\n\nBest regards,\n{sender_name}",
                variables=["recipient_name", "subject", "action_items", "sender_name"],
                conditions={"contains_meeting_keywords": True, "hours_since_meeting": 2}
            ),
            FollowUpTemplate(
                id="deadline_followup",
                name="Deadline Follow-up",
                type=FollowUpType.DEADLINE_FOLLOWUP,
                template_text="Hi {recipient_name},\n\nThis is a gentle reminder about the upcoming deadline for '{subject}' on {deadline_date}.\n\nPlease let me know if you need any assistance or have questions.\n\nBest regards,\n{sender_name}",
                variables=["recipient_name", "subject", "deadline_date", "sender_name"],
                conditions={"contains_deadline": True, "days_until_deadline": 2}
            ),
            FollowUpTemplate(
                id="task_followup",
                name="Task Follow-up",
                type=FollowUpType.TASK_FOLLOWUP,
                template_text="Hi {recipient_name},\n\nFollowing up on the task '{subject}' that we discussed. Could you please provide an update on the progress?\n\n{task_details}\n\nThank you for your attention to this matter.\n\nBest regards,\n{sender_name}",
                variables=["recipient_name", "subject", "task_details", "sender_name"],
                conditions={"importance_threshold": 0.6, "days_since_last_update": 3}
            )
        ]

        for template in templates:
            self.templates[template.id] = template

    async def analyze_and_schedule_followups(
        self,
        emails: List[Dict[str, Any]],
        analysis_results: Optional[List[EmailAnalysis]] = None
    ) -> List[FollowUpItem]:
        """
        Analyze emails and schedule appropriate follow-ups.

        Args:
            emails: List of email data
            analysis_results: Optional email analysis results

        Returns:
            List of scheduled follow-up items
        """
        scheduled_followups = []

        for email in emails:
            followups = await self._analyze_single_email(email, analysis_results)
            scheduled_followups.extend(followups)

        self.logger.info(f"Scheduled {len(scheduled_followups)} follow-ups from {len(emails)} emails")
        return scheduled_followups

    async def _analyze_single_email(
        self,
        email: Dict[str, Any],
        analysis_results: Optional[List[EmailAnalysis]] = None
    ) -> List[FollowUpItem]:
        """Analyze a single email for follow-up opportunities."""
        followups = []

        # Get analysis result for this email
        analysis = None
        if analysis_results:
            email_id = email.get("message_id", "")
            for result in analysis_results:
                if result.email_id == email_id:
                    analysis = result
                    break

        # Check various follow-up triggers
        followup_types = await self._identify_followup_triggers(email, analysis)

        for followup_type in followup_types:
            followup = await self._create_followup(email, followup_type, analysis)
            if followup:
                followups.append(followup)

        return followups

    async def _identify_followup_triggers(
        self,
        email: Dict[str, Any],
        analysis: Optional[EmailAnalysis] = None
    ) -> List[FollowUpType]:
        """Identify which types of follow-ups are needed for an email."""
        triggers = []
        content = f"{email.get('subject', '')} {email.get('content', '')}".lower()

        # Response reminder triggers
        if await self._needs_response_reminder(email, analysis):
            triggers.append(FollowUpType.RESPONSE_REMINDER)

        # Meeting follow-up triggers
        if self._contains_meeting_keywords(content):
            triggers.append(FollowUpType.MEETING_FOLLOWUP)

        # Deadline follow-up triggers
        if self._contains_deadline_keywords(content):
            triggers.append(FollowUpType.DEADLINE_FOLLOWUP)

        # Task follow-up triggers
        if self._contains_task_keywords(content):
            triggers.append(FollowUpType.TASK_FOLLOWUP)

        # Information request triggers
        if self._contains_question_keywords(content):
            triggers.append(FollowUpType.INFORMATION_REQUEST)

        return triggers

    async def _needs_response_reminder(
        self,
        email: Dict[str, Any],
        analysis: Optional[EmailAnalysis] = None
    ) -> bool:
        """Determine if an email needs a response reminder."""
        # Check if email requires action
        if analysis and analysis.action_required:
            return True

        # Check for question marks or request keywords
        content = f"{email.get('subject', '')} {email.get('content', '')}".lower()
        question_indicators = ["?", "please", "could you", "can you", "would you", "let me know"]

        if any(indicator in content for indicator in question_indicators):
            return True

        # Check importance score
        if analysis and analysis.importance_score > 0.7:
            return True

        return False

    def _contains_meeting_keywords(self, content: str) -> bool:
        """Check if content contains meeting-related keywords."""
        meeting_keywords = [
            "meeting", "call", "discussion", "sync", "catch up",
            "schedule", "calendar", "appointment", "conference"
        ]
        return any(keyword in content for keyword in meeting_keywords)

    def _contains_deadline_keywords(self, content: str) -> bool:
        """Check if content contains deadline-related keywords."""
        deadline_keywords = [
            "deadline", "due date", "due by", "by end of",
            "target date", "completion date", "final date"
        ]
        return any(keyword in content for keyword in deadline_keywords)

    def _contains_task_keywords(self, content: str) -> bool:
        """Check if content contains task-related keywords."""
        task_keywords = [
            "task", "action item", "todo", "follow up", "next step",
            "responsible", "assign", "complete", "deliverable"
        ]
        return any(keyword in content for keyword in task_keywords)

    def _contains_question_keywords(self, content: str) -> bool:
        """Check if content contains question or request keywords."""
        question_keywords = [
            "?", "please", "could you", "can you", "would you",
            "let me know", "please advise", "please confirm"
        ]
        return any(keyword in content for keyword in question_keywords)

    async def _create_followup(
        self,
        email: Dict[str, Any],
        followup_type: FollowUpType,
        analysis: Optional[EmailAnalysis] = None
    ) -> Optional[FollowUpItem]:
        """Create a follow-up item for an email."""
        import uuid

        # Calculate scheduled time based on type
        scheduled_time = self._calculate_scheduled_time(email, followup_type)

        # Determine priority
        priority = self._calculate_followup_priority(email, followup_type, analysis)

        # Generate follow-up content
        followup_content = await self._generate_followup_content(email, followup_type, analysis)

        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id=email.get("message_id", ""),
            follow_up_type=followup_type,
            priority=priority,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=scheduled_time,
            created_time=datetime.now(),
            subject=email.get("subject", ""),
            recipient=email.get("sender", ""),  # Follow up with the sender
            content_preview=email.get("content", "")[:200] + "..." if len(email.get("content", "")) > 200 else email.get("content", ""),
            trigger_reason=self._get_trigger_reason(followup_type),
            follow_up_content=followup_content
        )

        # Store the follow-up
        self.follow_ups[followup.id] = followup

        return followup

    def _calculate_scheduled_time(self, email: Dict[str, Any], followup_type: FollowUpType) -> datetime:
        """Calculate when the follow-up should be sent."""
        base_time = datetime.now()
        interval_hours = self.default_intervals.get(followup_type, 24)

        # Adjust based on email content
        content = f"{email.get('subject', '')} {email.get('content', '')}".lower()

        # Urgent content gets faster follow-up
        if any(word in content for word in ["urgent", "asap", "critical", "emergency"]):
            interval_hours = max(1, interval_hours // 2)

        # Meeting-related gets very quick follow-up
        if followup_type == FollowUpType.MEETING_FOLLOWUP:
            interval_hours = 2

        return base_time + timedelta(hours=interval_hours)

    def _calculate_followup_priority(
        self,
        email: Dict[str, Any],
        followup_type: FollowUpType,
        analysis: Optional[EmailAnalysis] = None
    ) -> FollowUpPriority:
        """Calculate the priority of a follow-up."""
        # Base priority on analysis importance
        if analysis:
            if analysis.importance_score > 0.8:
                return FollowUpPriority.URGENT
            elif analysis.importance_score > 0.6:
                return FollowUpPriority.HIGH
            elif analysis.importance_score > 0.4:
                return FollowUpPriority.MEDIUM

        # Check for urgent keywords
        content = f"{email.get('subject', '')} {email.get('content', '')}".lower()
        if any(word in content for word in ["urgent", "asap", "critical", "emergency"]):
            return FollowUpPriority.URGENT

        # Meeting follow-ups are high priority
        if followup_type == FollowUpType.MEETING_FOLLOWUP:
            return FollowUpPriority.HIGH

        return FollowUpPriority.MEDIUM

    async def _generate_followup_content(
        self,
        email: Dict[str, Any],
        followup_type: FollowUpType,
        analysis: Optional[EmailAnalysis] = None
    ) -> Optional[str]:
        """Generate content for the follow-up email."""
        template = self.templates.get(followup_type.value)
        if not template:
            return None

        # Extract variables from email and analysis
        variables = {
            "recipient_name": self._extract_recipient_name(email.get("sender", "")),
            "subject": email.get("subject", ""),
            "sender_name": "System",  # This would be configurable
        }

        # Add analysis-specific variables
        if analysis:
            variables.update({
                "action_items": "\n".join(analysis.suggested_actions) if analysis.suggested_actions else "",
                "task_details": analysis.content_summary if analysis.content_summary else "",
            })

        # Add deadline-specific variables
        if followup_type == FollowUpType.DEADLINE_FOLLOWUP:
            deadline = self._extract_deadline(email)
            variables["deadline_date"] = deadline.strftime("%Y-%m-%d") if deadline else "TBD"

        # Fill template
        content = template.template_text
        for var, value in variables.items():
            content = content.replace(f"{{{var}}}", str(value))

        return content

    def _extract_recipient_name(self, sender: str) -> str:
        """Extract a readable name from the sender field."""
        # Try to extract name from "Name <email>" format
        name_match = re.search(r'^([^<]+)', sender)
        if name_match:
            return name_match.group(1).strip()

        # Extract from email address
        email_match = re.search(r'([^@]+)@', sender)
        if email_match:
            return email_match.group(1).replace('.', ' ').title()

        return "Recipient"

    def _extract_deadline(self, email: Dict[str, Any]) -> Optional[datetime]:
        """Extract deadline from email content."""
        content = f"{email.get('subject', '')} {email.get('content', '')}"

        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2} \w+ \d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    date_str = match.group(1)
                    # This is a simplified implementation
                    # In production, you'd want more robust date parsing
                    return datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    continue

        return None

    def _get_trigger_reason(self, followup_type: FollowUpType) -> str:
        """Get human-readable reason for the follow-up trigger."""
        reasons = {
            FollowUpType.RESPONSE_REMINDER: "Email requires response but none received",
            FollowUpType.DEADLINE_FOLLOWUP: "Upcoming deadline detected",
            FollowUpType.MEETING_FOLLOWUP: "Meeting discussion requires follow-up",
            FollowUpType.TASK_FOLLOWUP: "Task requires progress update",
            FollowUpType.INFORMATION_REQUEST: "Information request pending",
            FollowUpType.CUSTOM_FOLLOWUP: "Custom follow-up scheduled"
        }
        return reasons.get(followup_type, "Automated follow-up")

    async def process_pending_followups(self) -> List[FollowUpItem]:
        """Process and send pending follow-ups that are due."""
        now = datetime.now()
        due_followups = []

        for followup in self.follow_ups.values():
            if (followup.status == FollowUpStatus.SCHEDULED and
                followup.scheduled_time <= now):

                # Mark as sent (in real implementation, this would send the email)
                followup.status = FollowUpStatus.SENT
                followup.completed_time = now
                due_followups.append(followup)

                self.logger.info(f"Processed follow-up {followup.id} for email {followup.email_id}")

        return due_followups

    def get_pending_followups(self) -> List[FollowUpItem]:
        """Get all pending follow-ups."""
        return [f for f in self.follow_ups.values() if f.status in [FollowUpStatus.PENDING, FollowUpStatus.SCHEDULED]]

    def get_overdue_followups(self) -> List[FollowUpItem]:
        """Get follow-ups that are overdue."""
        now = datetime.now()
        return [f for f in self.follow_ups.values()
                if f.status == FollowUpStatus.SCHEDULED and f.scheduled_time < now]

    def cancel_followup(self, followup_id: str) -> bool:
        """Cancel a scheduled follow-up."""
        if followup_id in self.follow_ups:
            self.follow_ups[followup_id].status = FollowUpStatus.CANCELLED
            return True
        return False

    def get_followup_stats(self) -> Dict[str, Any]:
        """Get follow-up service statistics."""
        total = len(self.follow_ups)
        if total == 0:
            return {"total_followups": 0}

        status_counts = {}
        for status in FollowUpStatus:
            status_counts[status.value] = len([f for f in self.follow_ups.values() if f.status == status])

        type_counts = {}
        for followup_type in FollowUpType:
            type_counts[followup_type.value] = len([f for f in self.follow_ups.values() if f.follow_up_type == followup_type])

        return {
            "total_followups": total,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "pending_count": status_counts.get("pending", 0) + status_counts.get("scheduled", 0),
            "completed_count": status_counts.get("completed", 0) + status_counts.get("sent", 0),
            "overdue_count": len(self.get_overdue_followups())
        }


# Global instance
automated_followups_service = AutomatedFollowupsService()