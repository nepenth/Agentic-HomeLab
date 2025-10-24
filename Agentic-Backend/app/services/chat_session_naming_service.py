"""
Chat Session Naming Service

Generates concise, descriptive names for chat sessions based on the initial message
using a small, fast LLM model.
"""

from app.services.ollama_client import ollama_client
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("chat_session_naming_service")


class ChatSessionNamingService:
    """Service for generating chat session names using LLM."""

    def __init__(self):
        self.logger = get_logger("chat_session_naming_service")
        self.naming_model = settings.chat_session_naming_model
        self.max_name_length = 50  # Maximum characters for session name

    async def generate_session_name(self, initial_message: str) -> str:
        """
        Generate a concise, descriptive name for a chat session based on the initial message.

        Args:
            initial_message: The first message sent in the chat session

        Returns:
            A short, descriptive session name (max 50 characters)
        """
        try:
            # Create a prompt for the naming model
            prompt = f"""Based on this user message, create a very short, concise title (maximum 6 words) for this conversation.

User message: "{initial_message}"

Requirements:
- Maximum 6 words
- No quotes or punctuation at start/end
- Descriptive and specific
- Use title case

Examples:
- "What are my recent emails?" → "Recent Email Summary"
- "Find tracking numbers from Amazon" → "Amazon Tracking Numbers"
- "Help me organize my inbox" → "Inbox Organization Help"

Title:"""

            # Generate the name using the small model with a short timeout
            response = await ollama_client.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.naming_model,
                timeout_ms=20000  # 20 second timeout for naming
            )

            # Extract the generated name
            if isinstance(response, dict) and "message" in response:
                generated_name = response["message"].get("content", "").strip()
            elif isinstance(response, str):
                generated_name = response.strip()
            else:
                generated_name = ""

            # Clean up the generated name
            generated_name = self._clean_session_name(generated_name)

            # Validate and truncate if needed
            if not generated_name or len(generated_name) < 3:
                # Fallback to truncated message if generation failed
                generated_name = self._fallback_name(initial_message)

            # Ensure max length
            if len(generated_name) > self.max_name_length:
                generated_name = generated_name[:self.max_name_length].rsplit(' ', 1)[0] + "..."

            self.logger.info(f"Generated session name: '{generated_name}' from message: '{initial_message[:50]}...'")
            return generated_name

        except Exception as e:
            self.logger.warning(f"Failed to generate session name, using fallback: {e}")
            return self._fallback_name(initial_message)

    def _clean_session_name(self, name: str) -> str:
        """Clean up generated session name."""
        # Remove common prefixes/suffixes from LLM responses
        name = name.strip()

        # Remove quotes
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        if name.startswith("'") and name.endswith("'"):
            name = name[1:-1]

        # Remove "Title:" prefix if present
        if name.lower().startswith("title:"):
            name = name[6:].strip()

        # Remove trailing punctuation
        while name and name[-1] in '.!?,;:':
            name = name[:-1]

        return name.strip()

    def _fallback_name(self, message: str) -> str:
        """Generate a fallback name from the message if LLM generation fails."""
        # Take first 40 characters and clean up
        name = message.strip()[:40]

        # Break at last space to avoid cutting words
        if len(message) > 40:
            name = name.rsplit(' ', 1)[0] + "..."

        return name or "New Chat"


# Singleton instance
chat_session_naming_service = ChatSessionNamingService()
