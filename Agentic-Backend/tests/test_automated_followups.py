"""
Tests for Automated Follow-ups service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.automated_followups import (
    AutomatedFollowupsService,
    FollowUpItem,
    FollowUpType,
    FollowUpPriority,
    FollowUpStatus
)


class TestAutomatedFollowupsService:
    """Test cases for the Automated Follow-ups service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AutomatedFollowupsService()

    def test_initialization(self):
        """Test service initialization."""
        assert self.service.follow_ups == {}
        assert len(self.service.templates) == 4  # Default templates
        assert self.service.default_intervals[FollowUpType.RESPONSE_REMINDER] == 24

    @pytest.mark.asyncio
    async def test_analyze_and_schedule_followups(self):
        """Test analyzing emails and scheduling follow-ups."""
        # Mock email data
        emails = [
            {
                "message_id": "email1",
                "subject": "Urgent: Please review the proposal",
                "content": "Can you please review this proposal by tomorrow?",
                "sender": "boss@company.com"
            },
            {
                "message_id": "email2",
                "subject": "Meeting tomorrow at 2 PM",
                "content": "Let's discuss the project status in our meeting tomorrow.",
                "sender": "colleague@company.com"
            }
        ]

        # Schedule follow-ups
        followups = await self.service.analyze_and_schedule_followups(emails)

        # Verify follow-ups were created
        assert len(followups) > 0
        assert len(self.service.follow_ups) == len(followups)

        # Check first follow-up
        followup = followups[0]
        assert isinstance(followup, FollowUpItem)
        assert followup.status == FollowUpStatus.SCHEDULED
        assert followup.email_id in ["email1", "email2"]

    def test_create_followup(self):
        """Test creating a follow-up item."""
        import uuid

        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id="test_email",
            follow_up_type=FollowUpType.RESPONSE_REMINDER,
            priority=FollowUpPriority.HIGH,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=datetime.now() + timedelta(hours=24),
            created_time=datetime.now(),
            subject="Test Subject",
            recipient="test@example.com",
            content_preview="Test content",
            trigger_reason="Test trigger"
        )

        assert followup.id is not None
        assert followup.status == FollowUpStatus.SCHEDULED
        assert followup.priority == FollowUpPriority.HIGH

    def test_calculate_scheduled_time(self):
        """Test calculating scheduled time for follow-ups."""
        email = {
            "subject": "Urgent meeting request",
            "content": "This is urgent, please respond ASAP"
        }

        # Test urgent content gets faster follow-up
        scheduled_time = self.service._calculate_scheduled_time(email, FollowUpType.RESPONSE_REMINDER)
        expected_time = datetime.now() + timedelta(hours=12)  # Should be faster than default 24h

        # Allow some tolerance for timing
        time_diff = abs((scheduled_time - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_calculate_followup_priority(self):
        """Test calculating follow-up priority."""
        # Test urgent email
        urgent_email = {
            "subject": "URGENT: Critical issue",
            "content": "This is extremely urgent"
        }

        priority = self.service._calculate_followup_priority(
            urgent_email,
            FollowUpType.RESPONSE_REMINDER,
            None
        )
        assert priority == FollowUpPriority.URGENT

        # Test normal email
        normal_email = {
            "subject": "Regular update",
            "content": "Just a regular update"
        }

        priority = self.service._calculate_followup_priority(
            normal_email,
            FollowUpType.RESPONSE_REMINDER,
            None
        )
        assert priority in [FollowUpPriority.MEDIUM, FollowUpPriority.LOW]

    def test_get_pending_followups(self):
        """Test getting pending follow-ups."""
        # Initially should be empty
        pending = self.service.get_pending_followups()
        assert len(pending) == 0

        # Add a pending follow-up
        import uuid
        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id="test_email",
            follow_up_type=FollowUpType.RESPONSE_REMINDER,
            priority=FollowUpPriority.MEDIUM,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=datetime.now() + timedelta(hours=1),
            created_time=datetime.now(),
            subject="Test",
            recipient="test@example.com",
            content_preview="Test",
            trigger_reason="Test"
        )

        self.service.follow_ups[followup.id] = followup

        # Should now have 1 pending follow-up
        pending = self.service.get_pending_followups()
        assert len(pending) == 1
        assert pending[0].id == followup.id

    def test_get_overdue_followups(self):
        """Test getting overdue follow-ups."""
        # Add an overdue follow-up
        import uuid
        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id="test_email",
            follow_up_type=FollowUpType.RESPONSE_REMINDER,
            priority=FollowUpPriority.MEDIUM,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=datetime.now() - timedelta(hours=1),  # Already past
            created_time=datetime.now() - timedelta(hours=2),
            subject="Test",
            recipient="test@example.com",
            content_preview="Test",
            trigger_reason="Test"
        )

        self.service.follow_ups[followup.id] = followup

        # Should have 1 overdue follow-up
        overdue = self.service.get_overdue_followups()
        assert len(overdue) == 1
        assert overdue[0].id == followup.id

    def test_cancel_followup(self):
        """Test cancelling a follow-up."""
        import uuid

        # Add a follow-up
        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id="test_email",
            follow_up_type=FollowUpType.RESPONSE_REMINDER,
            priority=FollowUpPriority.MEDIUM,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=datetime.now() + timedelta(hours=1),
            created_time=datetime.now(),
            subject="Test",
            recipient="test@example.com",
            content_preview="Test",
            trigger_reason="Test"
        )

        self.service.follow_ups[followup.id] = followup

        # Cancel it
        success = self.service.cancel_followup(followup.id)
        assert success

        # Verify it's cancelled
        cancelled_followup = self.service.follow_ups[followup.id]
        assert cancelled_followup.status == FollowUpStatus.CANCELLED

        # Try to cancel non-existent follow-up
        success = self.service.cancel_followup("non-existent-id")
        assert not success

    def test_get_followup_stats(self):
        """Test getting follow-up statistics."""
        # Initially empty
        stats = self.service.get_followup_stats()
        assert stats["total_followups"] == 0

        # Add some follow-ups
        import uuid

        statuses = [FollowUpStatus.SCHEDULED, FollowUpStatus.COMPLETED, FollowUpStatus.CANCELLED]
        types = [FollowUpType.RESPONSE_REMINDER, FollowUpType.MEETING_FOLLOWUP]

        for i, (status, followup_type) in enumerate(zip(statuses, types)):
            followup = FollowUpItem(
                id=str(uuid.uuid4()),
                email_id=f"test_email_{i}",
                follow_up_type=followup_type,
                priority=FollowUpPriority.MEDIUM,
                status=status,
                scheduled_time=datetime.now() + timedelta(hours=1),
                created_time=datetime.now(),
                subject=f"Test {i}",
                recipient="test@example.com",
                content_preview="Test",
                trigger_reason="Test"
            )
            self.service.follow_ups[followup.id] = followup

        # Get stats
        stats = self.service.get_followup_stats()
        assert stats["total_followups"] == 3
        assert stats["status_breakdown"]["scheduled"] == 1
        assert stats["status_breakdown"]["completed"] == 1
        assert stats["status_breakdown"]["cancelled"] == 1
        assert stats["type_breakdown"]["response_reminder"] == 1
        assert stats["type_breakdown"]["meeting_followup"] == 1

    def test_keyword_detection(self):
        """Test keyword detection methods."""
        # Test meeting keywords
        meeting_content = "Let's schedule a meeting tomorrow at 2 PM"
        assert self.service._contains_meeting_keywords(meeting_content)

        non_meeting_content = "Please review this document"
        assert not self.service._contains_meeting_keywords(non_meeting_content)

        # Test deadline keywords
        deadline_content = "The deadline is approaching, please submit by Friday"
        assert self.service._contains_deadline_keywords(deadline_content)

        non_deadline_content = "Let's discuss this later"
        assert not self.service._contains_deadline_keywords(non_deadline_content)

        # Test task keywords
        task_content = "Please complete this task by next week"
        assert self.service._contains_task_keywords(task_content)

        non_task_content = "How are you doing?"
        assert not self.service._contains_task_keywords(non_task_content)

        # Test question keywords
        question_content = "Could you please review this?"
        assert self.service._contains_question_keywords(question_content)

        non_question_content = "This is a statement."
        assert not self.service._contains_question_keywords(non_question_content)

    def test_recipient_name_extraction(self):
        """Test extracting recipient names from email addresses."""
        # Test various email formats
        assert self.service._extract_recipient_name("john.doe@example.com") == "John Doe"
        assert self.service._extract_recipient_name("Jane Smith <jane.smith@example.com>") == "Jane Smith"
        assert self.service._extract_recipient_name("support@company.com") == "Support"

    @pytest.mark.asyncio
    async def test_process_pending_followups(self):
        """Test processing pending follow-ups."""
        import uuid

        # Add a follow-up that's due
        followup = FollowUpItem(
            id=str(uuid.uuid4()),
            email_id="test_email",
            follow_up_type=FollowUpType.RESPONSE_REMINDER,
            priority=FollowUpPriority.MEDIUM,
            status=FollowUpStatus.SCHEDULED,
            scheduled_time=datetime.now() - timedelta(minutes=1),  # Already due
            created_time=datetime.now() - timedelta(hours=1),
            subject="Test",
            recipient="test@example.com",
            content_preview="Test",
            trigger_reason="Test"
        )

        self.service.follow_ups[followup.id] = followup

        # Process pending follow-ups
        processed = await self.service.process_pending_followups()

        # Verify it was processed
        assert len(processed) == 1
        assert processed[0].status == FollowUpStatus.SENT
        assert processed[0].completed_time is not None

        # Verify it was updated in the service
        updated_followup = self.service.follow_ups[followup.id]
        assert updated_followup.status == FollowUpStatus.SENT