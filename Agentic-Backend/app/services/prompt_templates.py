"""
XML-based prompt templates for LLM interactions.

This module provides structured prompt templates using XML format for consistent
and maintainable prompt engineering across different chat scenarios.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from app.utils.logging import get_logger

logger = get_logger("prompt_templates")


@dataclass
class PromptTemplate:
    """Container for prompt template data."""
    name: str
    description: str
    template_xml: str
    variables: Dict[str, str]
    system_prompt: Optional[str] = None


class PromptTemplateManager:
    """Manager for XML-based prompt templates."""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default prompt templates."""

        # Agent Creation Assistant Template
        agent_creation_template = """
<prompt_template name="agent_creation_assistant" version="1.0">
    <description>Interactive assistant for creating agents with validation and guidance</description>

    <system_prompt>
You are an AI assistant specialized in helping users create intelligent agents for their Agentic Backend system.
Your role is to guide users through the agent creation process, validate their inputs, suggest improvements,
and ensure they create effective and secure agents.

Key responsibilities:
1. Understand user requirements and translate them into agent configurations
2. Validate agent parameters and suggest optimal settings
3. Provide security guidance for sensitive operations
4. Help with tool selection and configuration
5. Explain technical concepts in user-friendly terms
6. Suggest best practices for agent development

Always be helpful, patient, and thorough in your explanations.
    </system_prompt>

    <conversation_flow>
        <step id="initial_greeting" order="1">
            <trigger>new_session</trigger>
            <response_template>
Hello! I'm your AI assistant for creating intelligent agents. I'll help you design and configure
an agent that meets your specific needs.

To get started, could you tell me:
1. What kind of task should this agent perform?
2. What data or systems will it need to access?
3. Any specific requirements or constraints?

Feel free to describe your use case in natural language, and I'll guide you through the setup process.
            </response_template>
        </step>

        <step id="analyze_requirements" order="2">
            <trigger>user_describes_task</trigger>
            <response_template>
Based on your description of: "{user_input}"

I understand you want to create an agent for: {task_summary}

Recommended configuration:
- **Agent Type**: {suggested_agent_type}
- **Model**: {suggested_model}
- **Tools Needed**: {suggested_tools}

Does this align with your vision? Would you like me to explain any of these recommendations or make adjustments?
            </response_template>
        </step>

        <step id="validate_configuration" order="3">
            <trigger>configuration_proposed</trigger>
            <response_template>
Let me validate your proposed configuration:

✅ **Valid Configuration Elements:**
{valid_items}

⚠️ **Items Needing Attention:**
{attention_items}

❌ **Invalid or Missing Elements:**
{invalid_items}

**Security Considerations:**
{security_notes}

**Performance Recommendations:**
{performance_tips}

Would you like me to help fix any issues or proceed with creating the agent?
            </response_template>
        </step>
    </conversation_flow>

    <validation_rules>
        <rule name="model_compatibility">
            <condition>model_selected</condition>
            <check>Ensure selected model is available and compatible with task</check>
            <error_message>Selected model '{model}' is not available. Available models: {available_models}</error_message>
        </rule>

        <rule name="security_validation">
            <condition>secrets_configured</condition>
            <check>Validate secret keys and access patterns</check>
            <warning_message>Consider using secrets for sensitive data like API keys</warning_message>
        </rule>

        <rule name="resource_limits">
            <condition>resource_intensive_task</condition>
            <check>Ensure resource requirements are within system limits</check>
            <warning_message>Task may require significant resources. Consider resource limits.</warning_message>
        </rule>
    </validation_rules>

    <error_handling>
        <error type="validation_error">
            <message>I found some issues with your configuration:</message>
            <suggestions>
                <suggestion>Check required fields are provided</suggestion>
                <suggestion>Verify model availability</suggestion>
                <suggestion>Review security settings</suggestion>
            </suggestions>
        </error>

        <error type="permission_error">
            <message>You don't have permission to perform this action.</message>
            <suggestions>
                <suggestion>Check your authentication token</suggestion>
                <suggestion>Verify your user permissions</suggestion>
            </suggestions>
        </error>
    </error_handling>
</prompt_template>
        """.strip()

        # Workflow Creation Assistant Template
        workflow_creation_template = """
<prompt_template name="workflow_creation_assistant" version="1.0">
    <description>Interactive assistant for creating complex workflows with multiple agents</description>

    <system_prompt>
You are a workflow orchestration specialist helping users design complex multi-agent workflows.
Your expertise includes:
1. Breaking down complex tasks into manageable agent steps
2. Designing data flow between agents
3. Optimizing workflow performance and reliability
4. Implementing error handling and retry logic
5. Ensuring workflow security and monitoring

Guide users through creating efficient, maintainable workflows that leverage multiple agents effectively.
    </system_prompt>

    <conversation_flow>
        <step id="workflow_analysis" order="1">
            <trigger>workflow_description</trigger>
            <response_template>
I'll help you design a workflow for: "{user_input}"

**Workflow Analysis:**
- **Complexity Level**: {complexity_level}
- **Estimated Steps**: {estimated_steps}
- **Required Agent Types**: {required_agent_types}

**Recommended Architecture:**
{workflow_architecture}

Would you like me to elaborate on any part of this design or modify the approach?
            </response_template>
        </step>

        <step id="step_design" order="2">
            <trigger>step_details_requested</trigger>
            <response_template>
Let's design the workflow steps:

**Step {step_number}: {step_name}**
- **Agent Type**: {agent_type}
- **Purpose**: {step_purpose}
- **Input Data**: {input_requirements}
- **Output Format**: {output_format}
- **Error Handling**: {error_handling}

**Dependencies:**
{step_dependencies}

**Configuration:**
{step_config}

Does this step design meet your requirements?
            </response_template>
        </step>
    </conversation_flow>
</prompt_template>
        """.strip()

        # General Chat Template
        general_chat_template = """
<prompt_template name="general_assistant" version="1.0">
    <description>General-purpose AI assistant for various interactions</description>

    <system_prompt>
You are a helpful AI assistant with expertise in AI agents, workflows, and backend systems.
Provide clear, accurate information and practical guidance for users working with the Agentic Backend.
    </system_prompt>

    <conversation_flow>
        <step id="general_response" order="1">
            <trigger>any_input</trigger>
            <response_template>
{assistant_response}

How else can I help you with your agent or workflow development?
            </response_template>
        </step>
    </conversation_flow>
</prompt_template>
        """.strip()

        # Register templates
        self.templates["agent_creation"] = PromptTemplate(
            name="agent_creation",
            description="Interactive agent creation assistant",
            template_xml=agent_creation_template,
            variables={
                "user_input": "",
                "task_summary": "",
                "suggested_agent_type": "",
                "suggested_model": "",
                "suggested_tools": "",
                "valid_items": "",
                "attention_items": "",
                "invalid_items": "",
                "security_notes": "",
                "performance_tips": "",
                "model": "",
                "available_models": ""
            },
            system_prompt="You are an AI assistant specialized in helping users create intelligent agents..."
        )

        self.templates["workflow_creation"] = PromptTemplate(
            name="workflow_creation",
            description="Interactive workflow creation assistant",
            template_xml=workflow_creation_template,
            variables={
                "user_input": "",
                "complexity_level": "",
                "estimated_steps": "",
                "required_agent_types": "",
                "workflow_architecture": "",
                "step_number": "",
                "step_name": "",
                "agent_type": "",
                "step_purpose": "",
                "input_requirements": "",
                "output_format": "",
                "error_handling": "",
                "step_dependencies": "",
                "step_config": ""
            },
            system_prompt="You are a workflow orchestration specialist..."
        )

        self.templates["general"] = PromptTemplate(
            name="general",
            description="General-purpose AI assistant",
            template_xml=general_chat_template,
            variables={
                "assistant_response": ""
            },
            system_prompt="You are a helpful AI assistant..."
        )

    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name."""
        return self.templates.get(template_name)

    def list_templates(self) -> Dict[str, str]:
        """List available templates with descriptions."""
        return {name: template.description for name, template in self.templates.items()}

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render a template with provided variables."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Simple variable substitution for now
        # In a more advanced implementation, this could parse the XML and use proper templating
        result = template.template_xml

        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result

    def get_system_prompt(self, template_name: str) -> Optional[str]:
        """Get the system prompt for a template."""
        template = self.get_template(template_name)
        return template.system_prompt if template else None

    def validate_template_variables(self, template_name: str, variables: Dict[str, Any]) -> bool:
        """Validate that all required template variables are provided."""
        template = self.get_template(template_name)
        if not template:
            return False

        required_vars = set(template.variables.keys())
        provided_vars = set(variables.keys())

        return required_vars.issubset(provided_vars)


# Global instance
prompt_manager = PromptTemplateManager()