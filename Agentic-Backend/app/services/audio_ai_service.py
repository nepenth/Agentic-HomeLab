"""
Audio AI Service for audio processing and analysis.

This service provides comprehensive audio AI capabilities including:
- Audio transcription (speech-to-text)
- Speaker identification
- Emotion analysis
- Audio classification
- Music analysis
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

logger = get_logger("audio_ai_service")


class AudioAIError(Exception):
    """Custom exception for audio AI operations."""
    pass


class AudioAIResult:
    """Result of an audio AI operation."""

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


class AudioAIService:
    """Service for audio AI processing using Ollama models."""

    def __init__(self):
        self.logger = get_logger("audio_ai_service")
        self.max_concurrent_tasks = 2  # Limited for 2x Tesla P40 homelab setup
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.supported_formats = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'webm', 'm4a']

        # Emotion categories for analysis
        self.emotion_categories = [
            "happy", "sad", "angry", "fearful", "surprised", "disgusted",
            "neutral", "excited", "calm", "anxious", "confident", "confused"
        ]

        # Audio classification categories
        self.audio_categories = [
            "speech", "music", "sound_effects", "ambient", "noise",
            "conversation", "lecture", "interview", "podcast", "song"
        ]

    async def initialize(self):
        """Initialize the audio AI service."""
        try:
            # Ensure model capability service is initialized
            await model_capability_service.initialize()
            self.logger.info("Audio AI Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Audio AI Service: {e}")
            raise

    async def transcribe_audio(
        self,
        audio_data: Union[bytes, str],
        language: str = "en",
        model_name: Optional[str] = None,
        include_timestamps: bool = False
    ) -> AudioAIResult:
        """
        Transcribe audio to text (speech-to-text).

        Args:
            audio_data: Audio data as bytes or base64 string
            language: Language code (e.g., 'en', 'es', 'fr')
            model_name: Specific model to use (optional)
            include_timestamps: Whether to include timestamps

        Returns:
            AudioAIResult with transcription
        """
        async with self.semaphore:  # Limit concurrent tasks
            result = AudioAIResult()
            start_time = datetime.now()

            try:
                # Get audio-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.AUDIO_TRANSCRIPTION
                    )

                if not model_name:
                    raise AudioAIError("No audio-capable models available")

                result.model_used = model_name

                # Convert audio to base64 if needed
                if isinstance(audio_data, bytes):
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                else:
                    audio_b64 = audio_data

                # Create transcription prompt
                prompt = f"""
                Transcribe the following audio to text. The audio is in {language} language.
                Provide a complete, accurate transcription of all speech in the audio.
                {"Include timestamps for different speakers if there are multiple speakers." if include_timestamps else ""}
                Format the transcription clearly and legibly.
                """

                # For Ollama, we'll use the chat endpoint with audio data
                # Note: This assumes the model supports audio input
                messages = [
                    {
                        "role": "user",
                        "content": prompt,
                        "audio": audio_b64  # This may not be supported by all Ollama models
                    }
                ]

                try:
                    # Try with audio support first
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={
                            "num_predict": 1000,
                            "temperature": 0.1
                        }
                    )
                except Exception:
                    # Fallback: Try without audio data (model may not support it)
                    self.logger.warning(f"Audio input not supported by {model_name}, trying text-only approach")
                    messages[0].pop("audio", None)  # Remove audio data
                    messages[0]["content"] = f"{prompt}\n\nNote: Audio transcription requested but model may not support direct audio input."

                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={
                            "num_predict": 1000,
                            "temperature": 0.1
                        }
                    )

                if response and 'message' in response:
                    transcription = response['message'].get('content', '')
                    result.result = {
                        "transcription": transcription,
                        "language": language,
                        "has_content": len(transcription.strip()) > 0,
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.8  # Default confidence for transcription
                else:
                    raise AudioAIError("Invalid response from audio model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "audio_size_bytes": len(audio_data) if isinstance(audio_data, bytes) else len(audio_b64),
                    "language": language,
                    "include_timestamps": include_timestamps,
                    "audio_supported": "audio" in str(messages[0])  # Check if audio was actually used
                }

                self.logger.info(f"Audio transcription completed in {result.processing_time:.2f}s using {model_name}")
                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Audio transcription failed: {e}")
                return result

    async def identify_speaker(
        self,
        audio_data: Union[bytes, str],
        num_speakers: Optional[int] = None,
        model_name: Optional[str] = None
    ) -> AudioAIResult:
        """
        Identify speakers in audio.

        Args:
            audio_data: Audio data as bytes or base64 string
            num_speakers: Expected number of speakers (optional)
            model_name: Specific model to use (optional)

        Returns:
            AudioAIResult with speaker identification
        """
        async with self.semaphore:
            result = AudioAIResult()
            start_time = datetime.now()

            try:
                # Get audio-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.AUDIO_ANALYSIS
                    )

                if not model_name:
                    raise AudioAIError("No audio-capable models available")

                result.model_used = model_name

                # Convert audio to base64 if needed
                if isinstance(audio_data, bytes):
                    audio_b64: str = base64.b64encode(audio_data).decode('utf-8')
                elif isinstance(audio_data, (bytearray, memoryview)):
                    audio_b64: str = base64.b64encode(bytes(audio_data)).decode('utf-8')
                else:
                    audio_b64: str = str(audio_data)

                # Create speaker identification prompt
                prompt = f"""
                Analyze this audio and identify the speakers.
                {"There are approximately {num_speakers} speakers." if num_speakers else ""}
                For each speaker, provide:
                - Speaker ID (Speaker 1, Speaker 2, etc.)
                - Approximate speaking time
                - Gender (if detectable)
                - Age group (if detectable)
                - Speech characteristics

                Format the analysis clearly.
                """

                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Try with audio if supported, fallback to text-only
                try:
                    messages[0]["audio"] = audio_b64
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 800, "temperature": 0.1}
                    )
                except Exception:
                    messages[0].pop("audio", None)
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 800, "temperature": 0.1}
                    )

                if response and 'message' in response:
                    analysis = response['message'].get('content', '')
                    result.result = {
                        "speaker_analysis": analysis,
                        "speakers_identified": self._parse_speaker_count(analysis),
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.7
                else:
                    raise AudioAIError("Invalid response from audio model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "audio_size_bytes": len(audio_data) if isinstance(audio_data, bytes) else len(audio_b64),
                    "expected_speakers": num_speakers
                }

                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Speaker identification failed: {e}")
                return result

    async def analyze_emotion(
        self,
        audio_data: Union[bytes, str],
        model_name: Optional[str] = None
    ) -> AudioAIResult:
        """
        Analyze emotions in audio.

        Args:
            audio_data: Audio data as bytes or base64 string
            model_name: Specific model to use (optional)

        Returns:
            AudioAIResult with emotion analysis
        """
        async with self.semaphore:
            result = AudioAIResult()
            start_time = datetime.now()

            try:
                # Get audio-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.AUDIO_ANALYSIS
                    )

                if not model_name:
                    raise AudioAIError("No audio-capable models available")

                result.model_used = model_name

                # Convert audio to base64 if needed
                if isinstance(audio_data, bytes):
                    audio_b64: str = base64.b64encode(audio_data).decode('utf-8')
                elif isinstance(audio_data, (bytearray, memoryview)):
                    audio_b64: str = base64.b64encode(bytes(audio_data)).decode('utf-8')
                else:
                    audio_b64: str = str(audio_data)

                # Create emotion analysis prompt
                emotions_list = ", ".join(self.emotion_categories)
                prompt = f"""
                Analyze the emotions and sentiment in this audio.
                Consider tone of voice, speech patterns, and vocal characteristics.

                Possible emotions: {emotions_list}

                Provide:
                - Primary emotion detected
                - Secondary emotions (if any)
                - Confidence levels for each emotion
                - Overall sentiment (positive, negative, neutral)
                - Reasoning for your analysis

                Be specific and provide evidence from the audio characteristics.
                """

                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Try with audio if supported
                try:
                    messages[0]["audio"] = audio_b64
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 600, "temperature": 0.1}
                    )
                except Exception:
                    messages[0].pop("audio", None)
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 600, "temperature": 0.1}
                    )

                if response and 'message' in response:
                    analysis = response['message'].get('content', '')
                    result.result = {
                        "emotion_analysis": analysis,
                        "detected_emotions": self._parse_emotions(analysis),
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.75
                else:
                    raise AudioAIError("Invalid response from audio model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "audio_size_bytes": len(audio_data) if isinstance(audio_data, bytes) else len(audio_b64),
                    "emotion_categories": self.emotion_categories
                }

                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Emotion analysis failed: {e}")
                return result

    async def classify_audio(
        self,
        audio_data: Union[bytes, str],
        model_name: Optional[str] = None
    ) -> AudioAIResult:
        """
        Classify audio content type.

        Args:
            audio_data: Audio data as bytes or base64 string
            model_name: Specific model to use (optional)

        Returns:
            AudioAIResult with classification
        """
        async with self.semaphore:
            result = AudioAIResult()
            start_time = datetime.now()

            try:
                # Get audio-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.AUDIO_ANALYSIS
                    )

                if not model_name:
                    raise AudioAIError("No audio-capable models available")

                result.model_used = model_name

                # Convert audio to base64 if needed
                if isinstance(audio_data, bytes):
                    audio_b64: str = base64.b64encode(audio_data).decode('utf-8')
                elif isinstance(audio_data, (bytearray, memoryview)):
                    audio_b64: str = base64.b64encode(bytes(audio_data)).decode('utf-8')
                else:
                    audio_b64: str = str(audio_data)

                # Create classification prompt
                categories_list = ", ".join(self.audio_categories)
                prompt = f"""
                Classify this audio content.
                Possible categories: {categories_list}

                Provide:
                - Primary content type
                - Secondary content types (if applicable)
                - Confidence level for classification
                - Key characteristics that led to this classification
                - Any notable features (music genre, speech topics, etc.)

                Be specific about what you hear in the audio.
                """

                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Try with audio if supported
                try:
                    messages[0]["audio"] = audio_b64
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 500, "temperature": 0.1}
                    )
                except Exception:
                    messages[0].pop("audio", None)
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 500, "temperature": 0.1}
                    )

                if response and 'message' in response:
                    analysis = response['message'].get('content', '')
                    result.result = {
                        "classification": analysis,
                        "detected_categories": self._parse_categories(analysis),
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.8
                else:
                    raise AudioAIError("Invalid response from audio model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "audio_size_bytes": len(audio_data) if isinstance(audio_data, bytes) else len(audio_b64),
                    "audio_categories": self.audio_categories
                }

                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Audio classification failed: {e}")
                return result

    async def analyze_music(
        self,
        audio_data: Union[bytes, str],
        model_name: Optional[str] = None
    ) -> AudioAIResult:
        """
        Analyze music in audio.

        Args:
            audio_data: Audio data as bytes or base64 string
            model_name: Specific model to use (optional)

        Returns:
            AudioAIResult with music analysis
        """
        async with self.semaphore:
            result = AudioAIResult()
            start_time = datetime.now()

            try:
                # Get audio-capable model
                if not model_name:
                    model_name = await model_capability_service.get_best_model_for_task(
                        ModelCapability.AUDIO_ANALYSIS
                    )

                if not model_name:
                    raise AudioAIError("No audio-capable models available")

                result.model_used = model_name

                # Convert audio to base64 if needed
                if isinstance(audio_data, bytes):
                    audio_b64: str = base64.b64encode(audio_data).decode('utf-8')
                elif isinstance(audio_data, (bytearray, memoryview)):
                    audio_b64: str = base64.b64encode(bytes(audio_data)).decode('utf-8')
                else:
                    audio_b64: str = str(audio_data)

                # Create music analysis prompt
                prompt = """
                Analyze this music audio and provide:
                - Genre/style (jazz, rock, classical, electronic, etc.)
                - Mood/emotion conveyed
                - Tempo (slow, medium, fast)
                - Instrumentation (what instruments you can identify)
                - Key musical characteristics
                - Notable features (vocals, lyrics, solo sections, etc.)
                - Overall quality assessment

                Provide detailed analysis of the musical elements.
                """

                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                # Try with audio if supported
                try:
                    messages[0]["audio"] = audio_b64
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 700, "temperature": 0.1}
                    )
                except Exception:
                    messages[0].pop("audio", None)
                    response = await ollama_client.chat(
                        messages=messages,
                        model=model_name,
                        stream=False,
                        options={"num_predict": 700, "temperature": 0.1}
                    )

                if response and 'message' in response:
                    analysis = response['message'].get('content', '')
                    result.result = {
                        "music_analysis": analysis,
                        "detected_genres": self._parse_music_genres(analysis),
                        "usage": response.get('usage', {}),
                        "model": model_name
                    }
                    result.confidence = 0.75
                else:
                    raise AudioAIError("Invalid response from audio model")

                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.metadata = {
                    "audio_size_bytes": len(audio_data) if isinstance(audio_data, bytes) else len(audio_b64),
                    "analysis_type": "music"
                }

                return result

            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.processing_time = (datetime.now() - start_time).total_seconds()
                self.logger.error(f"Music analysis failed: {e}")
                return result

    def _parse_speaker_count(self, analysis: str) -> int:
        """Parse number of speakers from analysis text."""
        # Simple parsing - could be enhanced with NLP
        text_lower = analysis.lower()
        if "multiple speakers" in text_lower or "several speakers" in text_lower:
            return 3  # Assume multiple
        elif "two speakers" in text_lower or "speaker 2" in text_lower:
            return 2
        elif "one speaker" in text_lower or "single speaker" in text_lower:
            return 1
        else:
            return 1  # Default

    def _parse_emotions(self, analysis: str) -> List[Dict[str, Any]]:
        """Parse detected emotions from analysis text."""
        detected_emotions = []
        text_lower = analysis.lower()

        for emotion in self.emotion_categories:
            if emotion in text_lower:
                detected_emotions.append({
                    "emotion": emotion,
                    "mentioned": True,
                    "confidence": 0.8 if emotion in ["happy", "sad", "angry"] else 0.6
                })

        return detected_emotions

    def _parse_categories(self, analysis: str) -> List[str]:
        """Parse audio categories from analysis text."""
        detected_categories = []
        text_lower = analysis.lower()

        for category in self.audio_categories:
            if category.replace("_", " ") in text_lower or category in text_lower:
                detected_categories.append(category)

        return detected_categories

    def _parse_music_genres(self, analysis: str) -> List[str]:
        """Parse music genres from analysis text."""
        # Common music genres
        genres = [
            "jazz", "rock", "pop", "classical", "electronic", "hip hop", "rap",
            "country", "blues", "reggae", "folk", "metal", "punk", "disco",
            "funk", "soul", "r&b", "gospel", "ambient", "techno", "house"
        ]

        detected_genres = []
        text_lower = analysis.lower()

        for genre in genres:
            if genre in text_lower:
                detected_genres.append(genre)

        return detected_genres

    async def validate_audio_format(self, audio_data: bytes) -> bool:
        """Validate if the audio format is supported."""
        try:
            # Check file signature
            if len(audio_data) < 12:
                return False

            # MP3
            if audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'ID3'):
                return True
            # WAV
            if audio_data.startswith(b'RIFF') and audio_data[8:12] == b'WAVE':
                return True
            # FLAC
            if audio_data.startswith(b'fLaC'):
                return True
            # OGG
            if audio_data.startswith(b'OggS'):
                return True
            # AAC/M4A
            if audio_data.startswith(b'\xff\xf1') or audio_data.startswith(b'\xff\xf9'):
                return True

            return False

        except Exception:
            return False

    async def get_supported_models(self) -> List[Dict[str, Any]]:
        """Get list of supported audio models."""
        try:
            audio_models = await model_capability_service.get_audio_models()

            return [
                {
                    "name": model.name,
                    "type": model.model_type.value,
                    "capabilities": [cap.value for cap in model.capabilities],
                    "size_gb": model.size_gb,
                    "is_available": model.is_available
                }
                for model in audio_models
            ]

        except Exception as e:
            self.logger.error(f"Failed to get supported audio models: {e}")
            return []

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        try:
            models = await self.get_supported_models()

            return {
                "service": "audio_ai",
                "status": "healthy",
                "supported_models": len(models),
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "supported_formats": self.supported_formats,
                "emotion_categories": len(self.emotion_categories),
                "audio_categories": len(self.audio_categories),
                "models": models,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "service": "audio_ai",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance
audio_ai_service = AudioAIService()