"""Tests for email workflow functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.email_analysis_service import EmailAnalysisService, EmailAnalysis, EmailMetadata
from app.services.email_task_converter import EmailTaskConverter, TaskCreationRequest, TaskCreationResult
from app.db.models.task import Task, TaskStatus


class TestEmailAnalysisService:
    """Test the email analysis service."""

    @pytest.fixture
    def analysis_service(self):
        """Create email analysis service instance."""
        return EmailAnalysisService()

    @pytest.fixture
    def sample_email_content(self):
        """Sample email content for testing."""
        return """
        Subject: Urgent: Project Deadline Approaching

        Dear Team,

        I hope this email finds you well. I'm writing to remind you about the upcoming deadline for the Q4 project deliverables.

        As you know, we have several critical tasks that need to be completed by Friday:

        1. Complete the financial report
        2. Review and approve the marketing materials
        3. Finalize the project documentation

        Please let me know if you need any assistance or have questions about these deliverables.

        Best regards,
        John Smith
        Project Manager
        """

    @pytest.fixture
    def sample_email_metadata(self):
        """Sample email metadata for testing."""
        return {
            "subject": "Urgent: Project Deadline Approaching",
            "sender": "john.smith@company.com",
            "message_id": "<123456789@example.com>",
            "date": datetime.now().isoformat(),
            "content_length": 500,
            "has_attachments": False,
            "attachment_count": 0,
            "content_type": "text/plain"
        }

    def test_initialization(self, analysis_service):
        """Test service initialization."""
        assert analysis_service.importance_threshold == 0.7
        assert analysis_service.spam_threshold == 0.8
        assert isinstance(analysis_service.urgency_keywords, dict)
        assert isinstance(analysis_service.spam_keywords, list)

    def test_decode_header_value(self, analysis_service):
        """Test email header decoding."""
        # Test normal ASCII
        result = analysis_service._decode_header_value("Test Subject")
        assert result == "Test Subject"

        # Test empty value
        result = analysis_service._decode_header_value("")
        assert result == ""

        # Test None value
        result = analysis_service._decode_header_value(None)
        assert result == ""

    def test_parse_recipients(self, analysis_service):
        """Test recipient parsing."""
        # Test single recipient
        recipients = analysis_service._parse_recipients("user@example.com")
        assert recipients == ["user@example.com"]

        # Test multiple recipients
        recipients = analysis_service._parse_recipients("user1@example.com, user2@example.com")
        assert recipients == ["user1@example.com", "user2@example.com"]

        # Test empty string
        recipients = analysis_service._parse_recipients("")
        assert recipients == []

    def test_extract_metadata(self, analysis_service, sample_email_metadata):
        """Test metadata extraction."""
        metadata = analysis_service._extract_metadata(sample_email_metadata)

        assert metadata.subject == "Urgent: Project Deadline Approaching"
        assert metadata.sender == "john.smith@company.com"
        assert metadata.sender_domain == "company.com"
        assert metadata.message_id == "<123456789@example.com>"
        assert metadata.has_attachments == False
        assert metadata.attachment_count == 0

    def test_calculate_rule_based_importance(self, analysis_service, sample_email_content, sample_email_metadata):
        """Test rule-based importance calculation."""
        metadata = analysis_service._extract_metadata(sample_email_metadata)

        score = analysis_service._calculate_rule_based_importance(sample_email_content, metadata)

        # Should be high due to "urgent" keyword
        assert score > 0.5
        assert score <= 1.0

    def test_calculate_urgency_level(self, analysis_service):
        """Test urgency level calculation."""
        # High importance
        level = analysis_service._calculate_urgency_level(0.9, "urgent deadline", None)
        assert level == "urgent"

        # Medium importance
        level = analysis_service._calculate_urgency_level(0.6, "normal content", None)
        assert level == "medium"

        # Low importance
        level = analysis_service._calculate_urgency_level(0.2, "normal content", None)
        assert level == "low"

    def test_fallback_categorization(self, analysis_service, sample_email_content):
        """Test fallback categorization."""
        metadata = EmailMetadata(
            subject="Test Subject",
            sender="test@example.com",
            sender_domain="example.com",
            recipients=[],
            received_date=datetime.now(),
            content_length=100,
            has_attachments=False,
            attachment_count=0,
            content_type="text/plain",
            message_id="<test@example.com>"
        )

        categories = analysis_service._fallback_categorization(sample_email_content, metadata)
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_detect_spam(self, analysis_service):
        """Test spam detection."""
        # Clean content
        spam_score = analysis_service._detect_spam("This is a normal business email.", None)
        assert spam_score < 0.5

        # Spam content
        spam_content = "WINNER! You've won a lottery! Click here to claim your prize!"
        spam_score = analysis_service._detect_spam(spam_content, None)
        assert spam_score > 0.5

    def test_analyze_attachments(self, analysis_service):
        """Test attachment analysis."""
        attachments = [
            {"filename": "document.pdf", "content_type": "application/pdf", "size": 1000000},
            {"filename": "script.exe", "content_type": "application/x-msdownload", "size": 50000}
        ]

        result = analysis_service._analyze_attachments(attachments)

        assert result["has_attachments"] == True
        assert result["count"] == 2
        assert result["total_size_bytes"] == 1050000
        assert len(result["analysis"]) == 2

        # Check risk assessment
        exe_attachment = next(att for att in result["analysis"] if att["filename"] == "script.exe")
        assert exe_attachment["risk_level"] == "high"

    def test_generate_summary(self, analysis_service):
        """Test content summary generation."""
        content = "This is a test email about project deadlines and deliverables."

        # Mock the Ollama client
        with patch('app.services.email_analysis_service.ollama_client') as mock_client:
            mock_response = MagicMock()
            mock_response.get.return_value = "Test summary"
            mock_client.generate.return_value = {'response': 'Test summary'}

            summary = analysis_service._generate_summary(content)
            assert summary == "Test summary"

    def test_get_stats(self, analysis_service):
        """Test service statistics."""
        stats = analysis_service.get_stats()

        assert "sender_reputation_cache_size" in stats
        assert "importance_threshold" in stats
        assert "spam_threshold" in stats
        assert "urgency_keywords_count" in stats
        assert "spam_keywords_count" in stats


class TestEmailTaskConverter:
    """Test the email task converter service."""

    @pytest.fixture
    def task_converter(self):
        """Create email task converter instance."""
        return EmailTaskConverter()

    @pytest.fixture
    def sample_analysis(self):
        """Sample email analysis for testing."""
        return EmailAnalysis(
            email_id="<test@example.com>",
            importance_score=0.8,
            categories=["work/business", "urgent"],
            urgency_level="high",
            sender_reputation=0.9,
            content_summary="Urgent project deadline approaching",
            key_topics=["deadline", "project", "deliverables"],
            action_required=True,
            suggested_actions=["Review project status", "Respond to email"],
            processing_time_ms=150.0
        )

    @pytest.fixture
    def sample_request(self, sample_analysis):
        """Sample task creation request."""
        return TaskCreationRequest(
            email_analysis=sample_analysis,
            user_id="user123",
            email_content="Test email content about project deadline",
            email_metadata={
                "subject": "Urgent: Project Deadline",
                "sender": "boss@company.com",
                "message_id": "<test@example.com>"
            }
        )

    def test_initialization(self, task_converter):
        """Test service initialization."""
        assert len(task_converter.task_templates) > 0
        assert "urgent_response" in task_converter.task_templates
        assert "high_priority_review" in task_converter.task_templates

    def test_select_task_templates(self, task_converter, sample_analysis):
        """Test task template selection."""
        email_content = "Urgent deadline approaching for project deliverables"

        templates = task_converter._select_task_templates(sample_analysis, email_content)

        assert len(templates) > 0
        # Should include urgent template due to high importance and urgency
        template_names = [t.name for t in templates]
        assert any("urgent" in name.lower() for name in template_names)

    def test_calculate_due_date(self, task_converter):
        """Test due date calculation."""
        now = datetime.now()

        # Urgent priority
        due_date = task_converter._calculate_due_date("urgent", "urgent")
        expected = now + timedelta(hours=2)
        assert abs((due_date - expected).total_seconds()) < 60  # Within 1 minute

        # High priority
        due_date = task_converter._calculate_due_date("high", "high")
        expected = now + timedelta(hours=8)
        assert abs((due_date - expected).total_seconds()) < 60

        # Medium priority
        due_date = task_converter._calculate_due_date("medium", "medium")
        expected = now + timedelta(days=1)
        assert abs((due_date - expected).total_seconds()) < 3600  # Within 1 hour

    def test_calculate_follow_up_date(self, task_converter, sample_analysis):
        """Test follow-up date calculation."""
        templates = [
            task_converter.task_templates["urgent_response"],
            task_converter.task_templates["high_priority_review"]
        ]

        follow_up_date = task_converter._calculate_follow_up_date(sample_analysis, templates)

        now = datetime.now()
        # Should be within reasonable range (1-3 days for urgent)
        assert follow_up_date > now
        assert follow_up_date < now + timedelta(days=7)

    def test_generate_task_description(self, task_converter, sample_request, sample_analysis):
        """Test task description generation."""
        template = task_converter.task_templates["urgent_response"]

        description = task_converter._generate_task_description(template, sample_request, sample_analysis)

        assert "Urgent Email Response Required" in description
        assert "Urgent: Project Deadline" in description
        assert "boss@company.com" in description
        assert "0.8" in description  # importance score
        assert "high" in description  # urgency level

    def test_get_agent_id_for_task(self, task_converter):
        """Test agent ID determination for tasks."""
        template = task_converter.task_templates["urgent_response"]

        agent_id = task_converter._get_agent_id_for_task(template, None)

        assert agent_id == "email-responder-agent"

    def test_get_stats(self, task_converter):
        """Test service statistics."""
        stats = task_converter.get_stats()

        assert "task_templates_count" in stats
        assert "priority_mapping" in stats
        assert "supported_urgency_levels" in stats
        assert "supported_priorities" in stats

        assert stats["task_templates_count"] == len(task_converter.task_templates)
        assert "urgent" in stats["supported_priorities"]
        assert "low" in stats["supported_urgency_levels"]


class TestEmailAnalysis:
    """Test the EmailAnalysis dataclass."""

    def test_initialization(self):
        """Test EmailAnalysis initialization."""
        analysis = EmailAnalysis(
            email_id="<test@example.com>",
            importance_score=0.8,
            categories=["work", "urgent"],
            urgency_level="high",
            sender_reputation=0.9,
            content_summary="Test summary",
            key_topics=["test", "topic"],
            action_required=True,
            suggested_actions=["Respond immediately"],
            processing_time_ms=100.0
        )

        assert analysis.email_id == "<test@example.com>"
        assert analysis.importance_score == 0.8
        assert analysis.urgency_level == "high"
        assert analysis.action_required == True

    def test_to_dict(self):
        """Test EmailAnalysis to_dict method."""
        analysis = EmailAnalysis(
            email_id="<test@example.com>",
            importance_score=0.8,
            categories=["work"],
            urgency_level="high",
            sender_reputation=0.9,
            content_summary="Test summary",
            key_topics=["test"],
            action_required=True,
            suggested_actions=["Respond"],
            processing_time_ms=100.0
        )

        data = analysis.to_dict()

        assert data["email_id"] == "<test@example.com>"
        assert data["importance_score"] == 0.8
        assert data["urgency_level"] == "high"
        assert data["action_required"] == True
        assert "analyzed_at" in data
        assert "processing_time_ms" in data


class TestTaskCreationRequest:
    """Test the TaskCreationRequest dataclass."""

    def test_initialization(self):
        """Test TaskCreationRequest initialization."""
        analysis = EmailAnalysis(
            email_id="<test@example.com>",
            importance_score=0.8,
            categories=["work"],
            urgency_level="high",
            sender_reputation=0.9,
            content_summary="Test",
            key_topics=[],
            action_required=True,
            suggested_actions=[],
            processing_time_ms=100.0
        )

        request = TaskCreationRequest(
            email_analysis=analysis,
            user_id="user123",
            email_content="Test content",
            email_metadata={"subject": "Test"},
            priority_override="urgent"
        )

        assert request.user_id == "user123"
        assert request.priority_override == "urgent"
        assert request.email_analysis.email_id == "<test@example.com>"

    def test_to_dict(self):
        """Test TaskCreationRequest to_dict method."""
        analysis = EmailAnalysis(
            email_id="<test@example.com>",
            importance_score=0.8,
            categories=["work"],
            urgency_level="high",
            sender_reputation=0.9,
            content_summary="Test",
            key_topics=[],
            action_required=True,
            suggested_actions=[],
            processing_time_ms=100.0
        )

        request = TaskCreationRequest(
            email_analysis=analysis,
            user_id="user123",
            email_content="Test content",
            email_metadata={"subject": "Test"}
        )

        data = request.to_dict()

        assert data["user_id"] == "user123"
        assert data["email_content"] == "Test content"
        assert "email_analysis" in data


class TestTaskCreationResult:
    """Test the TaskCreationResult dataclass."""

    def test_initialization(self):
        """Test TaskCreationResult initialization."""
        tasks = [MagicMock(spec=Task)]
        result = TaskCreationResult(
            tasks_created=tasks,
            follow_up_scheduled=True,
            follow_up_date=datetime.now() + timedelta(days=1),
            processing_time_ms=200.0
        )

        assert len(result.tasks_created) == 1
        assert result.follow_up_scheduled == True
        assert result.processing_time_ms == 200.0

    def test_to_dict(self):
        """Test TaskCreationResult to_dict method."""
        tasks = [MagicMock(spec=Task)]
        tasks[0].to_dict.return_value = {"id": "task-123", "status": "pending"}

        follow_up_date = datetime.now() + timedelta(days=1)
        result = TaskCreationResult(
            tasks_created=tasks,
            follow_up_scheduled=True,
            follow_up_date=follow_up_date,
            processing_time_ms=200.0
        )

        data = result.to_dict()

        assert data["follow_up_scheduled"] == True
        assert data["processing_time_ms"] == 200.0
        assert "follow_up_date" in data
        assert "created_at" in data
        assert len(data["tasks_created"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])