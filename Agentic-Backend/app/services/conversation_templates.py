"""
Conversation templates and intelligent question generation for agent builder.
"""
from typing import List, Dict, Any, Optional
import re


class ConversationTemplate:
    """Template for guiding agent creation conversations."""

    def __init__(self, agent_type: str, keywords: List[str], questions: List[str], suggestions: List[str]):
        self.agent_type = agent_type
        self.keywords = keywords
        self.questions = questions
        self.suggestions = suggestions

    def matches(self, description: str) -> bool:
        """Check if this template matches the user description."""
        description_lower = description.lower()
        return any(keyword.lower() in description_lower for keyword in self.keywords)


class ConversationTemplateManager:
    """Manages conversation templates for different agent types."""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> List[ConversationTemplate]:
        """Load predefined conversation templates."""
        return [
            # Email Analysis Agent Template
            ConversationTemplate(
                agent_type="email_analyzer",
                keywords=["email", "mail", "inbox", "gmail", "outlook", "message", "analyze emails"],
                questions=[
                    "What email service do you use? (Gmail, Outlook, IMAP)",
                    "How do you define 'important' emails? (sender, keywords, urgency indicators)",
                    "What time range should it analyze? (last 30 days, all unread, etc.)",
                    "What actions should it suggest? (flag, categorize, create tasks, forward)",
                    "Should it process attachments or just email content?",
                    "Do you want it to learn from your manual classifications?"
                ],
                suggestions=[
                    "Email importance scoring (0-1 scale)",
                    "Category classification (urgent, important, normal, low)",
                    "Follow-up task generation",
                    "Sender reputation analysis",
                    "Keyword and phrase extraction",
                    "Attachment type detection",
                    "Automated email organization"
                ]
            ),

            # Knowledge Base Agent Template
            ConversationTemplate(
                agent_type="knowledge_base",
                keywords=["knowledge", "document", "file", "bookmark", "wiki", "database", "search", "index"],
                questions=[
                    "What types of documents will it process? (PDF, web pages, text files)",
                    "How should it organize the information? (categories, tags, relationships)",
                    "What search capabilities do you need? (keyword, semantic, fuzzy)",
                    "Should it extract metadata from documents?",
                    "Do you want it to suggest related content?",
                    "How should it handle updates to existing documents?"
                ],
                suggestions=[
                    "Document content extraction and indexing",
                    "Automatic categorization and tagging",
                    "Full-text search with relevance scoring",
                    "Metadata extraction (author, date, keywords)",
                    "Relationship mapping between documents",
                    "Content summarization",
                    "Bookmark and web page processing",
                    "Version control for document updates"
                ]
            ),

            # Data Processing Agent Template
            ConversationTemplate(
                agent_type="data_processor",
                keywords=["data", "process", "transform", "csv", "excel", "database", "etl", "pipeline"],
                questions=[
                    "What data formats will it handle? (CSV, JSON, XML, databases)",
                    "What transformations are needed? (filtering, aggregation, calculations)",
                    "Where should the processed data be stored?",
                    "How often should it run? (real-time, scheduled, on-demand)",
                    "What quality checks or validations are required?",
                    "Should it generate reports or notifications?"
                ],
                suggestions=[
                    "Multi-format data ingestion (CSV, JSON, XML, databases)",
                    "Data validation and cleaning",
                    "Complex transformations and calculations",
                    "Automated quality assurance checks",
                    "Real-time processing pipelines",
                    "Scheduled batch processing",
                    "Report generation and notifications",
                    "Data export to multiple formats"
                ]
            ),

            # API Integration Agent Template
            ConversationTemplate(
                agent_type="api_integrator",
                keywords=["api", "integration", "webhook", "sync", "external", "service", "rest", "graphql"],
                questions=[
                    "Which external services need to be integrated?",
                    "What data should be synchronized between systems?",
                    "How should authentication be handled?",
                    "What error handling and retry logic is needed?",
                    "Should it handle rate limiting automatically?",
                    "Do you need real-time or batch synchronization?"
                ],
                suggestions=[
                    "REST API and GraphQL integration",
                    "OAuth2 and API key authentication",
                    "Webhook processing and event handling",
                    "Bidirectional data synchronization",
                    "Rate limiting and quota management",
                    "Error recovery and retry mechanisms",
                    "Real-time and batch processing modes",
                    "API response caching and optimization"
                ]
            ),

            # Content Creation Agent Template
            ConversationTemplate(
                agent_type="content_creator",
                keywords=["content", "write", "generate", "create", "article", "blog", "social", "marketing"],
                questions=[
                    "What type of content should it create? (articles, social posts, emails)",
                    "What is the target audience and tone?",
                    "Should it use specific templates or styles?",
                    "How should it handle research or fact-checking?",
                    "Do you want it to generate multiple variations?",
                    "Should it optimize for SEO or engagement?"
                ],
                suggestions=[
                    "Multi-format content generation (text, markdown, HTML)",
                    "Template-based content creation",
                    "SEO optimization and keyword integration",
                    "Fact-checking and source verification",
                    "Content variation generation (A/B testing)",
                    "Social media post optimization",
                    "Automated content scheduling",
                    "Performance analytics integration"
                ]
            ),

            # Monitoring and Alert Agent Template
            ConversationTemplate(
                agent_type="monitor_alert",
                keywords=["monitor", "alert", "notification", "watch", "track", "detect", "anomaly"],
                questions=[
                    "What should it monitor? (logs, metrics, events, changes)",
                    "What conditions should trigger alerts?",
                    "How should alerts be delivered? (email, Slack, webhook)",
                    "What is the acceptable false positive rate?",
                    "Should it learn from acknowledged alerts?",
                    "Do you need escalation policies?"
                ],
                suggestions=[
                    "Real-time log and metric monitoring",
                    "Anomaly detection with machine learning",
                    "Multi-channel alert delivery",
                    "Escalation policies and on-call rotation",
                    "Alert correlation and deduplication",
                    "Historical trend analysis",
                    "Automated incident response",
                    "Performance and availability monitoring"
                ]
            )
        ]

    def find_matching_template(self, description: str) -> Optional[ConversationTemplate]:
        """Find the best matching template for a user description."""
        for template in self.templates:
            if template.matches(description):
                return template
        return None

    def get_all_templates(self) -> List[ConversationTemplate]:
        """Get all available templates."""
        return self.templates

    def get_template_by_type(self, agent_type: str) -> Optional[ConversationTemplate]:
        """Get a template by agent type."""
        for template in self.templates:
            if template.agent_type == agent_type:
                return template
        return None


class IntelligentQuestionGenerator:
    """Generates intelligent follow-up questions based on user responses."""

    def __init__(self):
        self.question_patterns = self._load_question_patterns()

    def _load_question_patterns(self) -> Dict[str, List[str]]:
        """Load question patterns for different scenarios."""
        return {
            "email_service": [
                "What specific folders should it monitor? (Inbox, Sent, Archive)",
                "Should it process email threads or individual messages?",
                "Do you want it to handle email attachments?",
                "What should happen to processed emails? (archive, label, delete)"
            ],
            "data_source": [
                "How frequently should it check for new data?",
                "What format is the data in? (JSON, CSV, XML, database)",
                "Is the data structured or unstructured?",
                "Should it validate data quality before processing?"
            ],
            "processing_complexity": [
                "How complex are the processing requirements?",
                "Do you need real-time or batch processing?",
                "Should it handle errors gracefully or stop on failures?",
                "Do you need detailed processing logs and metrics?"
            ],
            "output_requirements": [
                "What format should the output be in?",
                "Where should the results be stored?",
                "Do you need to trigger actions based on the results?",
                "Should it generate reports or notifications?"
            ],
            "security_concerns": [
                "Does the agent need to access sensitive data?",
                "What authentication methods are available?",
                "Should it encrypt data at rest and in transit?",
                "Do you need audit logging for all operations?"
            ]
        }

    def generate_followup_questions(self, user_input: str, current_requirements: Dict[str, Any]) -> List[str]:
        """Generate intelligent follow-up questions based on user input and current state."""
        questions = []

        # Analyze user input for keywords and context
        input_lower = user_input.lower()

        # Email-related questions
        if any(word in input_lower for word in ["gmail", "outlook", "email", "mail"]):
            questions.extend(self.question_patterns["email_service"][:2])

        # Data-related questions
        if any(word in input_lower for word in ["data", "database", "csv", "json", "api"]):
            questions.extend(self.question_patterns["data_source"][:2])

        # Processing complexity questions
        if any(word in input_lower for word in ["complex", "advanced", "multiple", "chain", "workflow"]):
            questions.extend(self.question_patterns["processing_complexity"][:2])

        # Output-related questions
        if any(word in input_lower for word in ["output", "result", "store", "save", "export"]):
            questions.extend(self.question_patterns["output_requirements"][:2])

        # Security-related questions
        if any(word in input_lower for word in ["secure", "private", "sensitive", "confidential"]):
            questions.extend(self.question_patterns["security_concerns"][:2])

        # Check what's missing from requirements
        if not current_requirements.get("data_sources"):
            questions.append("What data sources or inputs will your agent work with?")

        if not current_requirements.get("processing_steps"):
            questions.append("What processing or analysis should the agent perform?")

        if not current_requirements.get("output_format"):
            questions.append("What should be the output or result of the agent's work?")

        # Limit to top 3 most relevant questions
        return questions[:3]

    def assess_completeness(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how complete the requirements are."""
        required_fields = [
            "agent_type", "data_sources", "processing_steps",
            "output_format", "tools_needed"
        ]

        completeness = {}
        for field in required_fields:
            completeness[field] = field in requirements and bool(requirements[field])

        completeness_score = sum(completeness.values()) / len(required_fields)

        return {
            "completeness": completeness,
            "score": completeness_score,
            "ready_for_schema": completeness_score >= 0.8,
            "missing_fields": [field for field, present in completeness.items() if not present]
        }


class SchemaPreviewGenerator:
    """Generates schema previews during conversation."""

    def __init__(self):
        self.template_manager = ConversationTemplateManager()

    def generate_preview(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a schema preview based on current requirements."""
        agent_type = requirements.get("agent_type", "custom_agent")

        # Basic schema structure
        schema = {
            "agent_type": agent_type,
            "version": "1.0.0",
            "metadata": {
                "name": self._generate_name(requirements),
                "description": requirements.get("description", "Custom agent"),
                "category": self._determine_category(requirements)
            }
        }

        # Add data models if specified
        if requirements.get("data_sources"):
            schema["data_models"] = self._generate_data_models(requirements)

        # Add processing pipeline if specified
        if requirements.get("processing_steps"):
            schema["processing_pipeline"] = self._generate_processing_pipeline(requirements)

        # Add tools if specified
        if requirements.get("tools_needed"):
            schema["tools"] = self._generate_tools(requirements)

        # Add input/output schemas
        schema["input_schema"] = self._generate_input_schema(requirements)
        schema["output_schema"] = self._generate_output_schema(requirements)

        return schema

    def _generate_name(self, requirements: Dict[str, Any]) -> str:
        """Generate a human-readable name for the agent."""
        agent_type = requirements.get("agent_type", "custom")
        description = requirements.get("description", "")

        # Extract key words from description
        words = re.findall(r'\b\w+\b', description.lower())
        key_words = [word for word in words if len(word) > 3 and word not in ["that", "with", "from", "this", "will"]]

        if key_words:
            return f"{agent_type.replace('_', ' ').title()} for {key_words[0].title()}"
        else:
            return f"{agent_type.replace('_', ' ').title()} Agent"

    def _determine_category(self, requirements: Dict[str, Any]) -> str:
        """Determine the agent category based on requirements."""
        description = requirements.get("description", "").lower()

        if any(word in description for word in ["email", "mail", "inbox"]):
            return "productivity"
        elif any(word in description for word in ["data", "database", "process"]):
            return "data_processing"
        elif any(word in description for word in ["api", "integration", "sync"]):
            return "integration"
        elif any(word in description for word in ["content", "write", "generate"]):
            return "content_creation"
        elif any(word in description for word in ["monitor", "alert", "notification"]):
            return "monitoring"
        else:
            return "custom"

    def _generate_data_models(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data models based on requirements."""
        models = {}

        # Default results model
        models["results"] = {
            "table_name": f"{requirements.get('agent_type', 'custom')}_results",
            "fields": {
                "id": {"type": "uuid", "required": True},
                "data": {"type": "json", "required": True},
                "created_at": {"type": "datetime", "required": True}
            }
        }

        # Add specific models based on data sources
        data_sources = requirements.get("data_sources", [])
        if "email" in str(data_sources).lower():
            models["emails"] = {
                "table_name": "email_data",
                "fields": {
                    "email_id": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "sender": {"type": "string", "required": True},
                    "content": {"type": "text", "required": True}
                }
            }

        return models

    def _generate_processing_pipeline(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate processing pipeline based on requirements."""
        steps = []

        # Determine steps based on processing requirements
        processing_steps = requirements.get("processing_steps", [])

        if "analyze" in str(processing_steps).lower():
            steps.append({
                "name": "analyze",
                "tool": "llm_processor",
                "config": {"task": "analysis"}
            })

        if "store" in str(processing_steps).lower() or "save" in str(processing_steps).lower():
            steps.append({
                "name": "store",
                "tool": "database_writer",
                "config": {"table": "results"}
            })

        # Default processing step if none specified
        if not steps:
            steps.append({
                "name": "process",
                "tool": "llm_processor",
                "config": {}
            })

        return {"steps": steps}

    def _generate_tools(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tools configuration based on requirements."""
        tools = {}

        # Always include LLM processor as base
        tools["llm_processor"] = {
            "type": "llm",
            "config": {"model": "llama2"}
        }

        # Add database writer if storage is needed
        if requirements.get("needs_storage"):
            tools["database_writer"] = {
                "type": "database",
                "config": {"batch_size": 100}
            }

        # Add email connector if email processing is needed
        if "email" in str(requirements.get("data_sources", "")).lower():
            tools["email_connector"] = {
                "type": "email_service",
                "config": {"service": "imap"}
            }

        return tools

    def _generate_input_schema(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate input schema based on requirements."""
        schema = {}

        # Add input fields based on data sources
        data_sources = requirements.get("data_sources", [])
        if "email" in str(data_sources).lower():
            schema["email_source"] = {"type": "string", "required": True}
            schema["date_range"] = {"type": "string", "required": False}

        # Default input if nothing specific
        if not schema:
            schema["input"] = {"type": "string", "required": True}

        return schema

    def _generate_output_schema(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate output schema based on requirements."""
        schema = {}

        # Add output fields based on processing steps
        processing_steps = requirements.get("processing_steps", [])
        if "analyze" in str(processing_steps).lower():
            schema["analysis"] = {"type": "json", "required": True}

        if "count" in str(processing_steps).lower():
            schema["count"] = {"type": "integer", "required": True}

        # Default output
        if not schema:
            schema["result"] = {"type": "string", "required": True}

        return schema


# Global instances
template_manager = ConversationTemplateManager()
question_generator = IntelligentQuestionGenerator()
schema_preview_generator = SchemaPreviewGenerator()