"""
Vision AI Service for image analysis and processing.

This service provides comprehensive vision AI capabilities including:
- Image analysis and description
- Object detection
- OCR (Optical Character Recognition)
- Image search and similarity
- Batch processing with resource management for homelab setup
"""

import asyncio
import base64
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import aiofiles

from app.services.ollama_client import ollama_client
from app.services.model_capability_service import model_capability_service, ModelCapability
from app.utils.logging import get_logger

logger = get_logger("vision_ai_service")


class VisionAIError(Exception):
    """Custom exception for vision AI operations."""
    pass


class VisionAIResult:
    """Result of a vision AI operation."""

    def __init__(self):
        self.success = True
        self.model_used = ""
        self.processing_time = 0.0
        self.result = {}
        self.confidence = 0.0
        self.error_message = ""
        self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "model_used": self.model_used,
            "processing_time": self.processing_time,
            "result": self.result,
            "confidence": self.confidence,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class VisionAIService:
    """Service for vision AI processing using Ollama models."""

    def __init__(self):
        self.logger = get_logger("vision_ai_service")
        self.max_concurrent_tasks = 2  # Limited for 2x Tesla P40 homelab setup
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.supported_formats = ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp']

    async def initialize(self):
        """Initialize the vision AI service."""
        try:
            # Ensure model capability service is initialized
            await model_capability_service.initialize()
            self.logger.info("Vision AI Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vision AI Service: {e}")
            raise

    async def analyze_image(
        self,
        image_data: Union[bytes, str],
        prompt: str = "Describe this image in detail",
        model_name: Optional[str] = None,
        max_tokens: int = 500
    ) -> VisionAIResult:
        """
        Analyze an image using vision-capable model.

        Args:
            image_data: Image data as bytes or base64 string
            prompt: Analysis prompt
            model_name: Specific model to use (optional)
            max_tokens: Maximum tokens in response

        Returns:
            VisionAIResult with analysis
        """
        async with self.semaphore:  # Limit concurrent tasks
            result = VisionAIResult()
            start_time = datetime.now()

            try:
                # Get vision-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.VISION_ANALYSIS
                    )

                if not model_name:
                    raise VisionAIError("No vision-capable models available")

                result.model_used = model_name

                # Convert image to base64 if needed
                if isinstance(image_data, bytes):
                    image_b64 = base64.b64encode(image_data).decode('utf-8')
                else:
                    image_b64 = image_data

                # For Ollama vision models, we need to use the chat endpoint with image data
                # Create a message with the image
                messages = [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_b64]
                    }
                ]

                # Make request to Ollama using chat endpoint
                response = await ollama_client.chat(
                    messages=messages,
                    model=model_name,
                    stream=False,
                    options={
                        "num_predict": max_tokens,
                        "temperature": 0.1  # Lower temperature for more accurate analysis
                    }
                )

                if response and 'response' in response:
                    result.result = {
                        "description": response['response'],
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.8  # Default confidence for vision analysis
                else:
                    raise VisionAIError("Invalid response from vision model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "image_size_bytes": len(image_data) if isinstance(image_data, bytes) else len(image_b64),
                    "prompt": prompt,
                    "max_tokens": max_tokens
                }

                self.logger.info(f"Image analysis completed in {result.processing_time:.2f}s using {model_name}")
                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Image analysis failed: {e}")
                return result

    async def detect_objects(
        self,
        image_data: Union[bytes, str],
        model_name: Optional[str] = None
    ) -> VisionAIResult:
        """
        Detect objects in an image.

        Args:
            image_data: Image data as bytes or base64 string
            model_name: Specific model to use (optional)

        Returns:
            VisionAIResult with detected objects
        """
        prompt = """
        Analyze this image and list all objects, people, animals, and significant items you can see.
        For each item, provide:
        - Name of the object/item
        - Approximate location (top-left, center, bottom-right, etc.)
        - Confidence level (high, medium, low)
        - Any notable characteristics

        Format the response as a structured list.
        """

        result = await self.analyze_image(image_data, prompt, model_name)

        if result.success:
            # Parse the response to extract structured object data
            result.result["objects"] = self._parse_object_detection(result.result.get("description", ""))

        return result

    async def extract_text(
        self,
        image_data: Union[bytes, str],
        model_name: Optional[str] = None
    ) -> VisionAIResult:
        """
        Extract text from an image (OCR).

        Args:
            image_data: Image data as bytes or base64 string
            model_name: Specific model to use (optional)

        Returns:
            VisionAIResult with extracted text
        """
        prompt = """
        Extract all visible text from this image. Include:
        - Main text content
        - Any labels, signs, or captions
        - Numbers, dates, or other structured text
        - Text in different languages if present

        Provide the extracted text in a clear, readable format.
        If no text is found, clearly state that.
        """

        result = await self.analyze_image(image_data, prompt, model_name)

        if result.success:
            extracted_text = result.result.get("description", "")
            result.result["extracted_text"] = extracted_text
            result.result["has_text"] = len(extracted_text.strip()) > 0

        return result

    async def search_similar_images(
        self,
        query_image: Union[bytes, str],
        search_prompt: str = "Find images with similar content",
        model_name: Optional[str] = None
    ) -> VisionAIResult:
        """
        Search for images similar to the query image.

        Args:
            query_image: Query image data
            search_prompt: Search description
            model_name: Specific model to use (optional)

        Returns:
            VisionAIResult with search results
        """
        prompt = f"""
        Based on this image, {search_prompt}.
        Describe the key visual elements, style, composition, and content that would help find similar images.
        Focus on:
        - Main subjects and objects
        - Color scheme and lighting
        - Composition and style
        - Mood and atmosphere
        - Unique identifying features
        """

        result = await self.analyze_image(query_image, prompt, model_name)

        if result.success:
            result.result["search_criteria"] = self._extract_search_criteria(result.result.get("description", ""))

        return result

    async def batch_process_images(
        self,
        images: List[Dict[str, Any]],
        operation: str = "analyze",
        model_name: Optional[str] = None
    ) -> List[VisionAIResult]:
        """
        Process multiple images in batch with resource management.

        Args:
            images: List of image data dictionaries
            operation: Type of operation (analyze, detect_objects, extract_text)
            model_name: Specific model to use (optional)

        Returns:
            List of VisionAIResult objects
        """
        async def process_single_image(image_data: Dict[str, Any]) -> VisionAIResult:
            """Process a single image with error handling."""
            try:
                img_data = image_data.get("data")
                img_id = image_data.get("id", "unknown")

                # Validate image data
                if not img_data or not isinstance(img_data, (bytes, str)):
                    result = VisionAIResult()
                    result.success = False
                    result.error_message = f"Invalid image data for image {img_id}"
                    return result

                if operation == "analyze":
                    prompt = image_data.get("prompt", "Describe this image in detail")
                    return await self.analyze_image(img_data, prompt, model_name)
                elif operation == "detect_objects":
                    return await self.detect_objects(img_data, model_name)
                elif operation == "extract_text":
                    return await self.extract_text(img_data, model_name)
                else:
                    result = VisionAIResult()
                    result.success = False
                    result.error_message = f"Unknown operation: {operation}"
                    return result

            except Exception as e:
                result = VisionAIResult()
                result.success = False
                result.error_message = f"Batch processing failed: {str(e)}"
                return result

        # Process images with controlled concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def limited_process(image_data):
            async with semaphore:
                return await process_single_image(image_data)

        # Create tasks for all images
        tasks = [limited_process(img) for img in images]

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = VisionAIResult()
                error_result.success = False
                error_result.error_message = f"Task failed: {str(result)}"
                final_results.append(error_result)
            else:
                final_results.append(result)

        self.logger.info(f"Batch processed {len(images)} images with operation '{operation}'")
        return final_results

    def _parse_object_detection(self, description: str) -> List[Dict[str, Any]]:
        """Parse object detection results from model response."""
        # This is a simple parser - in production, you might want more sophisticated parsing
        objects = []

        lines = description.split('\n')
        current_object = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_object:
                    objects.append(current_object)
                    current_object = {}
                continue

            # Try to extract object information
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()

                if 'name' in key or 'object' in key:
                    current_object['name'] = value
                elif 'location' in key or 'position' in key:
                    current_object['location'] = value
                elif 'confidence' in key:
                    current_object['confidence'] = value

        if current_object:
            objects.append(current_object)

        return objects

    def _extract_search_criteria(self, description: str) -> Dict[str, Any]:
        """Extract search criteria from model response."""
        criteria = {
            "subjects": [],
            "colors": [],
            "style": "",
            "composition": "",
            "mood": ""
        }

        # Simple keyword extraction - could be enhanced with NLP
        description_lower = description.lower()

        # Extract subjects
        subject_keywords = ["person", "people", "animal", "car", "building", "landscape", "portrait"]
        for keyword in subject_keywords:
            if keyword in description_lower:
                criteria["subjects"].append(keyword.title())

        # Extract colors
        color_keywords = ["red", "blue", "green", "yellow", "black", "white", "gray", "brown"]
        for color in color_keywords:
            if color in description_lower:
                criteria["colors"].append(color.title())

        return criteria

    async def get_supported_models(self) -> List[Dict[str, Any]]:
        """Get list of supported vision models."""
        try:
            vision_models = await model_capability_service.get_vision_models()

            return [
                {
                    "name": model.name,
                    "type": model.model_type.value,
                    "capabilities": [cap.value for cap in model.capabilities],
                    "size_gb": model.size_gb,
                    "is_available": model.is_available
                }
                for model in vision_models
            ]

        except Exception as e:
            self.logger.error(f"Failed to get supported vision models: {e}")
            return []

    async def validate_image_format(self, image_data: bytes) -> bool:
        """Validate if the image format is supported."""
        try:
            # Check file signature
            if len(image_data) < 8:
                return False

            # JPEG
            if image_data.startswith(b'\xff\xd8'):
                return True
            # PNG
            if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            # GIF
            if image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
                return True
            # WebP
            if image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
                return True
            # BMP
            if image_data.startswith(b'BM'):
                return True

            return False

        except Exception:
            return False

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        try:
            models = await self.get_supported_models()

            return {
                "service": "vision_ai",
                "status": "healthy",
                "supported_models": len(models),
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "supported_formats": self.supported_formats,
                "models": models,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "service": "vision_ai",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance
vision_ai_service = VisionAIService()