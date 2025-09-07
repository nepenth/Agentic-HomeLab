"""
Agent Creation Wizard - Guides users through creating agents with LLM assistance.

This service provides intelligent guidance for agent creation, including:
- Requirements analysis
- Configuration suggestions
- Validation and error checking
- Best practices recommendations
- Integration with secrets management
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import json
import re

from app.services.chat_service import ChatService
from app.services.ollama_client import ollama_client
from app.services.prompt_templates import prompt_manager
from app.utils.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("agent_creation_wizard")


class AgentCreationWizard:
    """Wizard for guiding agent creation with LLM assistance."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_service = ChatService(db)

    async def analyze_user_requirements(self, user_input: str, session_id: UUID) -> Dict[str, Any]:
        """Analyze user requirements and suggest agent configuration."""
        try:
            # Use LLM to analyze the user's requirements
            analysis_prompt = f"""
You are an expert AI agent designer. Analyze the following user requirements and suggest an appropriate agent configuration:

User Requirements: "{user_input}"

Please provide a JSON response with the following structure:
{{
    "task_type": "classification|generation|analysis|automation|other",
    "complexity": "simple|moderate|complex",
    "suggested_model": "llama2|codellama|mistral|other",
    "required_tools": ["tool1", "tool2"],
    "estimated_resources": {{
        "memory_mb": 512,
        "cpu_cores": 1
    }},
    "security_requirements": ["secrets", "validation", "isolation"],
    "recommendations": ["recommendation1", "recommendation2"],
    "potential_issues": ["issue1", "issue2"],
    "confidence_score": 0.0-1.0
}}

Be specific and practical in your suggestions.
"""

            response = await ollama_client.generate(
                prompt=analysis_prompt,
                model="llama2",  # Use a reliable model for analysis
                format="json"
            )

            try:
                analysis = json.loads(response.get("response", "{}"))
            except json.JSONDecodeError:
                # Fallback analysis if JSON parsing fails
                analysis = self._fallback_analysis(user_input)

            # Store analysis in session metadata
            await self.chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=f"Analysis complete! Here's what I understand from your requirements:\n\n{json.dumps(analysis, indent=2)}",
                message_type="analysis_result",
                metadata={"analysis": analysis}
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing requirements: {e}")
            return self._fallback_analysis(user_input)

    def _fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """Fallback analysis when LLM analysis fails."""
        return {
            "task_type": "other",
            "complexity": "moderate",
            "suggested_model": "llama2",
            "required_tools": [],
            "estimated_resources": {
                "memory_mb": 512,
                "cpu_cores": 1
            },
            "security_requirements": ["validation"],
            "recommendations": ["Review configuration before deployment"],
            "potential_issues": ["May need additional tools or resources"],
            "confidence_score": 0.5
        }

    async def generate_agent_config(
        self,
        analysis: Dict[str, Any],
        user_preferences: Dict[str, Any],
        session_id: UUID
    ) -> Dict[str, Any]:
        """Generate a complete agent configuration based on analysis and user preferences."""

        # Build configuration based on analysis
        config = {
            "name": user_preferences.get("name", f"Agent-{analysis.get('task_type', 'general')}"),
            "model_name": user_preferences.get("model_name", analysis.get("suggested_model", "llama2")),
            "description": user_preferences.get("description", ""),
            "config": {
                "temperature": user_preferences.get("temperature", 0.7),
                "max_tokens": user_preferences.get("max_tokens", 2048),
                "system_prompt": self._generate_system_prompt(analysis, user_preferences)
            },
            "estimated_resources": analysis.get("estimated_resources", {}),
            "required_tools": analysis.get("required_tools", []),
            "security_requirements": analysis.get("security_requirements", [])
        }

        # Add secrets configuration if needed
        if "secrets" in analysis.get("security_requirements", []):
            config["secrets"] = self._suggest_secrets_config(analysis)

        # Store generated config in session
        await self.chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=f"Here's the generated agent configuration:\n\n```json\n{json.dumps(config, indent=2)}\n```",
            message_type="generated_config",
            metadata={"generated_config": config}
        )

        return config

    def _generate_system_prompt(self, analysis: Dict[str, Any], user_preferences: Dict[str, Any]) -> str:
        """Generate an appropriate system prompt based on analysis."""
        task_type = analysis.get("task_type", "general")
        complexity = analysis.get("complexity", "moderate")

        base_prompts = {
            "classification": "You are an expert at classifying and categorizing information. Analyze the given content and provide accurate classifications with confidence scores.",
            "generation": "You are a creative AI assistant specialized in generating high-quality content. Create engaging, well-structured responses that meet the user's requirements.",
            "analysis": "You are an analytical AI expert. Provide thorough, evidence-based analysis with clear reasoning and actionable insights.",
            "automation": "You are an automation specialist. Help users streamline processes and create efficient automated workflows.",
            "other": "You are a helpful AI assistant. Provide accurate, useful responses to user queries."
        }

        prompt = base_prompts.get(task_type, base_prompts["other"])

        if complexity == "complex":
            prompt += " Take extra care with detailed analysis and comprehensive responses."
        elif complexity == "simple":
            prompt += " Keep responses clear and concise."

        return prompt

    def _suggest_secrets_config(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Suggest secrets configuration based on analysis."""
        secrets = []

        task_type = analysis.get("task_type", "")
        required_tools = analysis.get("required_tools", [])

        # Suggest common secrets based on task type and tools
        if task_type in ["automation", "analysis"] or "email" in str(required_tools).lower():
            secrets.append({
                "key": "email_password",
                "value": "",  # To be filled by user
                "description": "Email account password for automated email processing"
            })

        if "api" in str(required_tools).lower():
            secrets.append({
                "key": "api_key",
                "value": "",
                "description": "API key for external service integration"
            })

        if "database" in str(required_tools).lower():
            secrets.append({
                "key": "db_password",
                "value": "",
                "description": "Database connection password"
            })

        return secrets

    async def validate_configuration(self, config: Dict[str, Any], session_id: UUID) -> Tuple[bool, List[str]]:
        """Validate the generated agent configuration."""
        issues = []
        warnings = []

        # Basic validation
        if not config.get("name"):
            issues.append("Agent name is required")

        if not config.get("model_name"):
            issues.append("Model name is required")

        # Check model availability (would need actual model list)
        # For now, just check if it's a reasonable model name
        valid_models = ["llama2", "codellama", "mistral", "qwen", "phi"]
        if config.get("model_name") and not any(model in config["model_name"].lower() for model in valid_models):
            warnings.append(f"Model '{config['model_name']}' may not be available")

        # Check resource requirements
        resources = config.get("estimated_resources", {})
        if resources.get("memory_mb", 0) > 2048:
            warnings.append("High memory requirement - ensure sufficient resources")

        # Check secrets configuration
        secrets = config.get("secrets", [])
        for secret in secrets:
            if not secret.get("key"):
                issues.append("Secret key is required")
            if not secret.get("value") and secret.get("key"):
                warnings.append(f"Secret '{secret['key']}' has no value set")

        # Store validation results
        validation_result = {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "recommendations": self._generate_recommendations(issues, warnings)
        }

        await self.chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=self._format_validation_message(validation_result),
            message_type="validation_result",
            metadata={"validation": validation_result}
        )

        return validation_result["is_valid"], issues + warnings

    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if issues:
            recommendations.append("Address critical issues before proceeding")

        if warnings:
            recommendations.append("Review warnings to optimize configuration")

        if not issues and not warnings:
            recommendations.append("Configuration looks good! Ready for deployment")

        return recommendations

    def _format_validation_message(self, validation: Dict[str, Any]) -> str:
        """Format validation results into a user-friendly message."""
        message = "Configuration Validation Results:\n\n"

        if validation["issues"]:
            message += "❌ Critical Issues:\n"
            for issue in validation["issues"]:
                message += f"  • {issue}\n"
            message += "\n"

        if validation["warnings"]:
            message += "⚠️ Warnings:\n"
            for warning in validation["warnings"]:
                message += f"  • {warning}\n"
            message += "\n"

        if validation["recommendations"]:
            message += "💡 Recommendations:\n"
            for rec in validation["recommendations"]:
                message += f"  • {rec}\n"

        return message

    async def finalize_agent_creation(
        self,
        config: Dict[str, Any],
        session_id: UUID
    ) -> Dict[str, Any]:
        """Finalize agent creation with deployment-ready configuration."""

        # Generate deployment-ready configuration
        deployment_config = {
            "agent_config": {
                "name": config["name"],
                "model_name": config["model_name"],
                "description": config.get("description", ""),
                "config": config["config"],
                "is_active": True
            },
            "secrets": config.get("secrets", []),
            "deployment_notes": self._generate_deployment_notes(config),
            "monitoring_setup": self._suggest_monitoring_config(config)
        }

        await self.chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=f"🎉 Agent creation complete! Here's your deployment-ready configuration:\n\n```json\n{json.dumps(deployment_config, indent=2)}\n```\n\nYou can now create this agent using the API!",
            message_type="final_config",
            metadata={"final_config": deployment_config}
        )

        return deployment_config

    def _generate_deployment_notes(self, config: Dict[str, Any]) -> List[str]:
        """Generate deployment notes and best practices."""
        notes = [
            "Test the agent with sample inputs before production use",
            "Monitor resource usage during initial deployment",
            "Set up appropriate logging and error handling"
        ]

        if config.get("secrets"):
            notes.append("Ensure all required secrets are properly configured")

        resources = config.get("estimated_resources", {})
        if resources.get("memory_mb", 0) > 1024:
            notes.append("Monitor memory usage closely due to high requirements")

        return notes

    def _suggest_monitoring_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest monitoring configuration for the agent."""
        return {
            "metrics_enabled": True,
            "log_level": "INFO",
            "performance_monitoring": True,
            "error_alerts": True,
            "resource_limits": config.get("estimated_resources", {})
        }