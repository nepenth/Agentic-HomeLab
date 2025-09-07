"""
Knowledge Base Workflow Service

This service orchestrates the complete knowledge base generation workflow,
managing all 8 phases with intelligent model selection, error recovery,
and comprehensive phase tracking.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, and_, or_

from app.db.models.knowledge_base import (
    KnowledgeBaseItem,
    KnowledgeBaseProcessingPhase,
    KnowledgeBaseCategory,
    KnowledgeBaseMedia,
    KnowledgeBaseAnalysis,
    KnowledgeBaseEmbedding,
    KnowledgeBaseWorkflowSettings
)
from app.services.ollama_client import OllamaClient
from app.services.vision_ai_service import VisionAIService
from app.services.semantic_processing_service import SemanticProcessingService
from app.services.media_download_service import MediaDownloadService
from app.connectors.social_media import TwitterConnector
from app.utils.logging import get_logger

logger = get_logger("knowledge_base_workflow")


class KnowledgeBaseWorkflowService:
    """Service for orchestrating knowledge base generation workflow"""

    def __init__(
        self,
        db_session: Optional[AsyncSession],
        ollama_client: OllamaClient,
        vision_service: VisionAIService,
        semantic_service: SemanticProcessingService,
        twitter_connector: TwitterConnector,
        media_download_service: MediaDownloadService,
        media_cache_dir: str = "/app/media_cache",
        workflow_settings: Optional[Dict[str, Any]] = None
    ):
        self.db = db_session
        self.db_session_provided = db_session is not None
        self.ollama = ollama_client
        self.vision = vision_service
        self.semantic = semantic_service
        self.twitter = twitter_connector
        self.media_download = media_download_service
        self.media_cache_dir = Path(media_cache_dir)
        self.media_cache_dir.mkdir(parents=True, exist_ok=True)

        # Load workflow settings
        self.workflow_settings = workflow_settings or self._load_default_workflow_settings()

        # Phase-to-model mapping from settings (with defaults as fallback)
        self.phase_models = self.workflow_settings.get("phase_models", self._get_default_phase_models())

        # Phase settings (skip, force reprocess, enabled)
        self.phase_settings = self.workflow_settings.get("phase_settings", self._get_default_phase_settings())

        # Global workflow settings
        self.global_settings = self.workflow_settings.get("global_settings", self._get_default_global_settings())

        # Define phase sequence and dependencies
        self.phase_sequence = [
            "fetch_bookmarks",
            "cache_content",
            "cache_media",
            "interpret_media",
            "categorize_content",
            "holistic_understanding",
            "synthesized_learning",
            "embeddings"
        ]

        # Phase dependencies
        self.phase_dependencies = {
            "fetch_bookmarks": [],
            "cache_content": ["fetch_bookmarks"],
            "cache_media": ["cache_content"],
            "interpret_media": ["cache_media"],
            "categorize_content": ["cache_content"],
            "holistic_understanding": ["categorize_content"],  # Can also depend on interpret_media if media exists
            "synthesized_learning": ["holistic_understanding"],
            "embeddings": ["holistic_understanding"]
        }

    async def _get_db_session(self) -> AsyncSession:
        """Get database session, creating one if not provided"""
        if self.db is not None:
            return self.db

        # Import here to avoid circular imports
        from app.db.database import async_session_factory
        session = async_session_factory()
        return session

    async def process_item(self, item_id: str, start_phase: Optional[str] = None) -> Dict[str, Any]:
        """
        Main orchestration method for processing a knowledge base item

        Args:
            item_id: UUID of the knowledge base item
            start_phase: Optional phase to start from (for resuming)

        Returns:
            Dict containing processing results and status
        """
        # Get database session
        db_session = await self._get_db_session()
        self.db = db_session  # Set for use in other methods

        try:
            item = await self._get_item(item_id)
            if not item:
                raise ValueError(f"Knowledge base item {item_id} not found")

            # Determine starting phase
            if start_phase:
                current_phase = start_phase
            else:
                current_phase = await self._determine_starting_phase(item)

            logger.info(f"Starting knowledge base processing for item {item_id} at phase: {current_phase}")

            results = {}
            processed_phases = []

            try:
                for phase_name in self.phase_sequence[self.phase_sequence.index(current_phase):]:
                    # Check for cancellation before starting each phase
                    if await self._is_item_cancelled(item_id):
                        logger.info(f"Processing cancelled for item {item_id} before phase {phase_name}")
                        await self._handle_workflow_cancellation(item, f"Cancelled before phase {phase_name}")
                        return {
                            "item_id": item_id,
                            "status": "cancelled",
                            "processed_phases": processed_phases,
                            "results": results,
                            "current_phase": "cancelled",
                            "cancelled_at_phase": phase_name
                        }

                    # Check if phase should be skipped based on settings
                    if self.should_skip_phase(phase_name):
                        logger.info(f"Skipping phase {phase_name} for item {item_id} - disabled in settings")
                        # Mark as skipped in processing phases
                        await self._record_phase_skipped(str(item.id), phase_name)
                        continue

                    if not await self._can_run_phase(item, phase_name):
                        logger.info(f"Skipping phase {phase_name} for item {item_id} - dependencies not met")
                        continue

                    # Select appropriate model for this phase
                    model = await self._select_model_for_phase(phase_name, item)

                    # Execute phase with error handling and retry logic
                    phase_result = await self._execute_phase_with_retry(
                        item, phase_name, model
                    )

                    results[phase_name] = phase_result
                    processed_phases.append(phase_name)

                    # Update item status
                    await self._update_item_phase_status(item, phase_name, "completed")

                    # Check for cancellation after phase completion
                    if await self._is_item_cancelled(item_id):
                        logger.info(f"Processing cancelled for item {item_id} after phase {phase_name}")
                        await self._handle_workflow_cancellation(item, f"Cancelled after phase {phase_name}")
                        return {
                            "item_id": item_id,
                            "status": "cancelled",
                            "processed_phases": processed_phases,
                            "results": results,
                            "current_phase": "cancelled",
                            "cancelled_at_phase": phase_name
                        }

                    # Check if we should continue to next phase
                    if not await self._should_continue_to_next_phase(item, phase_name):
                        break

                # Mark item as fully processed if all phases completed
                if len(processed_phases) == len(self.phase_sequence):
                    await self._mark_item_completed(item)

                return {
                    "item_id": item_id,
                    "status": "completed",
                    "processed_phases": processed_phases,
                    "results": results,
                    "current_phase": item.processing_phase
                }

            except Exception as e:
                logger.error(f"Workflow failed for item {item_id} at phase {current_phase}: {str(e)}")
                await self._handle_workflow_error(item, current_phase, str(e))
                raise
        finally:
            # Close session if we created it
            if not self.db_session_provided:
                await db_session.close()

    async def flag_for_reprocessing(self, item_id: str, phases: List[str], reason: str):
        """Flag item for reprocessing specific phases"""

        # Update item reprocessing flags
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item_id).values(
                needs_reprocessing=True,
                reprocessing_reason=reason
            )
        )

        # Reset specified phases and their dependencies
        for phase in phases:
            await self._reset_phase_status(item_id, phase)
            dependent_phases = self._get_dependent_phases(phase)
            for dep_phase in dependent_phases:
                await self._reset_phase_status(item_id, dep_phase)

        logger.info(f"Flagged item {item_id} for reprocessing phases: {phases}")

    async def update_workflow_settings(self, settings: Dict[str, Any]) -> None:
        """Update workflow settings for this service instance"""
        if "phase_models" in settings:
            self.phase_models = settings["phase_models"]
        if "phase_settings" in settings:
            self.phase_settings = settings["phase_settings"]
        if "global_settings" in settings:
            self.global_settings = settings["global_settings"]

        # Update the combined settings dict
        self.workflow_settings.update(settings)

    async def _execute_phase_with_retry(
        self,
        item: KnowledgeBaseItem,
        phase_name: str,
        model: Optional[str],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute a phase with retry logic and model fallback"""

        for attempt in range(max_retries + 1):
            # Check for cancellation before each attempt
            if await self._is_item_cancelled(str(item.id)):
                logger.info(f"Phase {phase_name} cancelled for item {item.id} before attempt {attempt + 1}")
                raise Exception(f"Phase {phase_name} cancelled by user")

            try:
                # Record phase start
                await self._record_phase_start(str(item.id), phase_name, model or "none")

                # Execute the specific phase
                result = await self._execute_phase(item, phase_name, model)

                # Record successful completion
                await self._record_phase_completion(str(item.id), phase_name, model or "none", result)

                return result

            except Exception as e:
                error_msg = f"Phase {phase_name} failed on attempt {attempt + 1}: {str(e)}"
                logger.warning(f"{error_msg} for item {item.id}")

                # Check if this is a cancellation exception
                if "cancelled by user" in str(e).lower():
                    raise e

                if attempt < max_retries and model is not None:
                    # Try fallback model if available
                    fallback_model = await self._get_fallback_model(phase_name, model)
                    if fallback_model and fallback_model != model:
                        logger.info(f"Trying fallback model {fallback_model} for phase {phase_name}")
                        model = fallback_model
                        continue

                # Record failure
                await self._record_phase_failure(str(item.id), phase_name, model or "none", error_msg)
                raise Exception(error_msg)

    async def _execute_phase(self, item: KnowledgeBaseItem, phase_name: str, model: Optional[str]) -> Dict[str, Any]:
        """Execute a specific processing phase"""

        phase_handlers = {
            "fetch_bookmarks": self._phase_fetch_bookmarks,
            "cache_content": self._phase_cache_content,
            "cache_media": self._phase_cache_media,
            "interpret_media": self._phase_interpret_media,
            "categorize_content": self._phase_categorize_content,
            "holistic_understanding": self._phase_holistic_understanding,
            "synthesized_learning": self._phase_synthesized_learning,
            "embeddings": self._phase_embeddings
        }

        handler = phase_handlers.get(phase_name)
        if not handler:
            raise ValueError(f"Unknown phase: {phase_name}")

        return await handler(item, model)

    # Phase implementation methods
    async def _phase_fetch_bookmarks(self, item: KnowledgeBaseItem, model: Optional[str] = None) -> Dict[str, Any]:
        """Phase 1: Fetch bookmarks from X.com API with thread detection and persistence"""
        if item.source_type not in ["twitter_bookmark", "twitter_bookmark_auto"]:
            raise ValueError("Item is not a Twitter bookmark")

        # Import settings to get X_BOOKMARK_URL
        from app.config import settings

        # Use the configured bookmark URL from settings
        bookmark_url = settings.x_bookmark_url
        if not bookmark_url:
            raise ValueError("X_BOOKMARK_URL not configured in settings")

        # Extract user ID from bookmark URL if it's a folder URL
        user_id = None
        if "folders/" in bookmark_url:
            try:
                # Extract user ID from URL like: https://api.x.com/2/users/{user_id}/bookmarks/folders/{folder_id}
                user_id = bookmark_url.split("/users/")[1].split("/")[0]
            except:
                pass

        # Use Twitter connector to fetch bookmarks with thread detection and persistence
        source_config = {
            "query_type": "bookmarks",
            "query_params": {
                "user_id": user_id,
                "max_results": 100,
                "use_playwright": True,  # Force Playwright for thread detection
                "db_session": self.db,  # Pass database session for persistence
                "incremental": True  # Enable incremental updates
            }
        }

        bookmarks = await self.twitter.discover(source_config)

        # Store fetched content with thread information
        tweets_data = []
        for bookmark in bookmarks:
            # Get thread information from metadata
            is_thread = bookmark.metadata.get("is_thread", False)
            thread_root_id = bookmark.metadata.get("thread_root_id")
            thread_position = bookmark.metadata.get("thread_position", 0)

            tweet_data = await self.twitter.fetch(bookmark)
            tweets_data.append({
                "tweet_id": tweet_data.item.id,
                "text": tweet_data.text_content,
                "author": tweet_data.item.metadata.get("author_username"),
                "created_at": tweet_data.item.last_modified.isoformat(),
                "media_urls": [],  # Will be populated in cache_media phase
                "is_thread": is_thread,
                "thread_root_id": thread_root_id,
                "thread_position": thread_position
            })

        return {
            "bookmarks_fetched": len(bookmarks),
            "tweets": tweets_data,
            "threads_detected": sum(1 for t in tweets_data if t.get("is_thread")),
            "unique_threads": len(set(t.get("thread_root_id") for t in tweets_data if t.get("thread_root_id")))
        }

    async def _phase_cache_content(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 2: Cache text content to database"""
        # Get tweets from previous phase
        tweets = item.item_metadata.get("tweets", [])

        cached_tweets = []
        for tweet in tweets:
            # Store tweet content in database
            await self.db.execute(
                insert(KnowledgeBaseAnalysis).values(
                    item_id=item.id,
                    analysis_type="cached_content",
                    content=json.dumps(tweet),
                    model_used="text_extraction",
                    created_at=datetime.utcnow()
                )
            )
            cached_tweets.append(tweet["tweet_id"])

        return {
            "tweets_cached": len(cached_tweets),
            "cached_ids": cached_tweets
        }

    async def _phase_cache_media(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 3: Cache media files to persistent storage with progress tracking"""
        tweets = item.item_metadata.get("tweets", [])

        cached_media = []
        download_tasks = []

        for tweet in tweets:
            # Check if tweet has media
            # This would need to be populated during fetch phase
            media_urls = tweet.get("media_urls", [])
            if not media_urls:
                continue

            for media_url in media_urls:
                # Prepare download task
                media_filename = f"{tweet['tweet_id']}_{Path(media_url).name}"
                download_tasks.append({
                    "url": media_url,
                    "filename": media_filename,
                    "tweet_id": tweet["tweet_id"]
                })

        # Download media files in batch
        if download_tasks:
            # Update progress to indicate download starting
            await self.update_phase_progress(
                str(item.id),
                "cache_media",
                0,
                len(download_tasks),
                f"Starting download of {len(download_tasks)} media files"
            )

            download_results = await self.media_download.batch_download_media(download_tasks)

            for i, result in enumerate(download_results):
                # Update progress for each download
                await self.update_phase_progress(
                    str(item.id),
                    "cache_media",
                    i + 1,
                    len(download_tasks),
                    f"Downloaded media file {i + 1} of {len(download_tasks)}"
                )

                if result.success:
                    task = download_tasks[i]

                    # Store media metadata
                    await self.db.execute(
                        insert(KnowledgeBaseMedia).values(
                            item_id=item.id,
                            media_type=self._get_media_type(task["url"]),
                            original_url=task["url"],
                            cached_path=result.file_path,
                            file_size=result.file_size,
                            content_type=result.content_type,
                            created_at=datetime.utcnow()
                        )
                    )

                    cached_media.append({
                        "tweet_id": task["tweet_id"],
                        "media_url": task["url"],
                        "cached_path": result.file_path,
                        "file_size": result.file_size,
                        "download_time": result.download_time
                    })

        return {
            "media_cached": len(cached_media),
            "total_download_tasks": len(download_tasks),
            "media_files": cached_media
        }

    async def _phase_interpret_media(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 4: Use Vision AI to interpret media content with progress tracking"""
        if not model:
            raise ValueError("Model is required for media interpretation phase")

        # Get cached media for this item
        media_query = select(KnowledgeBaseMedia).where(KnowledgeBaseMedia.item_id == item.id)
        media_result = await self.db.execute(media_query)
        media_files = media_result.scalars().all()

        interpretations = []
        total_media = len(media_files)

        for i, media in enumerate(media_files, 1):
            # Update progress
            await self.update_phase_progress(
                str(item.id),
                "interpret_media",
                i,
                total_media,
                f"Analyzing media {i} of {total_media} with Vision AI"
            )

            if not media.cached_path or not Path(media.cached_path).exists():
                continue

            # Use Vision AI to analyze media
            with open(media.cached_path, "rb") as f:
                media_data = f.read()

            analysis_result = await self.vision.analyze_image(
                image_data=media_data,
                model_name=model,
                tasks=["caption", "objects", "ocr"]
            )

            # Store interpretation
            interpretation = {
                "media_id": str(media.id),
                "caption": analysis_result.get("caption", ""),
                "objects": analysis_result.get("objects", []),
                "text_content": analysis_result.get("ocr", ""),
                "semantic_description": analysis_result.get("description", "")
            }

            await self.db.execute(
                update(KnowledgeBaseMedia).where(KnowledgeBaseMedia.id == media.id).values(
                    vision_analysis=json.dumps(interpretation)
                )
            )

            interpretations.append(interpretation)

        return {
            "media_interpreted": len(interpretations),
            "total_media_files": total_media,
            "interpretations": interpretations
        }

    async def _phase_categorize_content(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 5: Categorize content into domains and sub-categories"""
        if not model:
            raise ValueError("Model is required for content categorization phase")

        # Get cached content
        content_query = select(KnowledgeBaseAnalysis).where(
            and_(
                KnowledgeBaseAnalysis.item_id == item.id,
                KnowledgeBaseAnalysis.analysis_type == "cached_content"
            )
        )
        content_result = await self.db.execute(content_query)
        content_analysis = content_result.scalar_one_or_none()

        if not content_analysis:
            raise ValueError("No cached content found for categorization")

        tweets = json.loads(content_analysis.content)

        # Prepare content for categorization
        content_text = " ".join([tweet.get("text", "") for tweet in tweets])

        # Use LLM for categorization
        prompt = f"""
        Analyze the following content and categorize it into a domain and sub-category.
        Content: {content_text}

        Respond with JSON in this format:
        {{
            "domain": "technology|science|business|health|education|entertainment|other",
            "sub_category": "specific sub-category based on content",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        """

        categorization_result = await self.ollama.generate(
            model=model,
            prompt=prompt,
            format="json"
        )

        result_data = json.loads(categorization_result["response"])

        # Store categorization
        await self.db.execute(
            insert(KnowledgeBaseCategory).values(
                item_id=item.id,
                category=result_data["domain"],
                sub_category=result_data["sub_category"],
                confidence_score=result_data["confidence"],
                auto_generated=True,
                model_used=model,
                created_at=datetime.utcnow()
            )
        )

        return {
            "domain": result_data["domain"],
            "sub_category": result_data["sub_category"],
            "confidence": result_data["confidence"]
        }

    async def _phase_holistic_understanding(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 6: Create holistic understanding combining text and media"""
        if not model:
            raise ValueError("Model is required for holistic understanding phase")

        # Get text content
        content_query = select(KnowledgeBaseAnalysis).where(
            and_(
                KnowledgeBaseAnalysis.item_id == item.id,
                KnowledgeBaseAnalysis.analysis_type == "cached_content"
            )
        )
        content_result = await self.db.execute(content_query)
        content_analysis = content_result.scalar_one_or_none()

        # Get media interpretations
        media_query = select(KnowledgeBaseMedia).where(KnowledgeBaseMedia.item_id == item.id)
        media_result = await self.db.execute(media_query)
        media_files = media_result.scalars().all()

        # Combine text and media insights
        text_content = ""
        if content_analysis:
            tweets = json.loads(content_analysis.content)
            text_content = " ".join([tweet.get("text", "") for tweet in tweets])

        media_insights = []
        for media in media_files:
            if media.vision_analysis:
                media_insights.append(json.loads(media.vision_analysis))

        # Generate holistic understanding
        prompt = f"""
        Create a comprehensive understanding of the following content by combining text and visual information:

        TEXT CONTENT:
        {text_content}

        VISUAL INSIGHTS:
        {json.dumps(media_insights, indent=2)}

        Provide a holistic summary that explains:
        1. The main topic and context
        2. How visual elements support or enhance the text
        3. Key insights and takeaways
        4. Overall significance and relevance

        Respond with a detailed analysis.
        """

        understanding_result = await self.ollama.generate(
            model=model,
            prompt=prompt,
            options={"num_predict": 1000}
        )

        holistic_content = understanding_result["response"]

        # Store holistic understanding
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item.id).values(
                full_content=holistic_content,
                processed_at=datetime.utcnow()
            )
        )

        return {
            "holistic_content": holistic_content,
            "text_length": len(text_content),
            "media_insights_count": len(media_insights)
        }

    async def _phase_synthesized_learning(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 7: Generate synthesized learning for sub-category"""
        if not model:
            raise ValueError("Model is required for synthesized learning phase")

        # Get item category
        category_query = select(KnowledgeBaseCategory).where(KnowledgeBaseCategory.item_id == item.id)
        category_result = await self.db.execute(category_query)
        category = category_result.scalar_one_or_none()

        if not category:
            raise ValueError("No category found for synthesized learning")

        # Check if we have enough items in this sub-category
        subcategory_count_query = select(KnowledgeBaseCategory).where(
            and_(
                KnowledgeBaseCategory.category == category.category,
                KnowledgeBaseCategory.sub_category == category.sub_category
            )
        )
        count_result = await self.db.execute(subcategory_count_query)
        subcategory_items = count_result.scalars().all()

        if len(subcategory_items) < 3:
            return {
                "skipped": True,
                "reason": f"Only {len(subcategory_items)} items in sub-category, need 3+",
                "subcategory": category.sub_category
            }

        # Get all items in this sub-category
        item_ids = [str(item.item_id) for item in subcategory_items]
        items_query = select(KnowledgeBaseItem).where(KnowledgeBaseItem.id.in_(item_ids))
        items_result = await self.db.execute(items_query)
        related_items = items_result.scalars().all()

        # Combine content from all related items
        combined_content = []
        for related_item in related_items:
            if related_item.full_content:
                combined_content.append(related_item.full_content)

        # Generate synthesized learning
        prompt = f"""
        Based on the following collection of content from the {category.sub_category} sub-category,
        create a comprehensive synthesized learning document that:

        1. Identifies common themes and patterns
        2. Synthesizes key insights and learnings
        3. Provides actionable recommendations
        4. Highlights emerging trends or important developments

        CONTENT TO SYNTHESIZE:
        {"\\n\\n---\\n\\n".join(combined_content)}

        Create a well-structured learning document.
        """

        synthesis_result = await self.ollama.generate(
            model=model,
            prompt=prompt,
            options={"num_predict": 2000}
        )

        synthesized_content = synthesis_result["response"]

        # Store synthesized learning (this would be stored separately)
        # For now, we'll store it as analysis
        await self.db.execute(
            insert(KnowledgeBaseAnalysis).values(
                item_id=item.id,
                analysis_type="synthesized_learning",
                model_used=model,
                content=synthesized_content,
                created_at=datetime.utcnow()
            )
        )

        return {
            "synthesized": True,
            "subcategory": category.sub_category,
            "items_synthesized": len(related_items),
            "content_length": len(synthesized_content)
        }

    async def _phase_embeddings(self, item: KnowledgeBaseItem, model: Optional[str]) -> Dict[str, Any]:
        """Phase 8: Generate embeddings for semantic search"""
        if not model:
            raise ValueError("Model is required for embeddings phase")

        if not item.full_content:
            raise ValueError("No content available for embedding generation")

        # Generate embeddings using semantic service
        embedding = await self.semantic.generate_embedding(
            text=item.full_content,
            model_name=model
        )

        embedding_result = {
            "embeddings": [embedding]
        }

        # Store embeddings
        await self.db.execute(
            insert(KnowledgeBaseEmbedding).values(
                item_id=item.id,
                embedding_model=model,
                embedding_vector=json.dumps(embedding_result["embeddings"][0]),
                content_chunk=item.full_content,
                chunk_index=0,
                created_at=datetime.utcnow()
            )
        )

        return {
            "embeddings_generated": True,
            "model_used": model,
            "vector_dimensions": len(embedding_result["embeddings"][0])
        }

    # Helper methods
    async def _get_item(self, item_id: str) -> Optional[KnowledgeBaseItem]:
        """Get knowledge base item by ID"""
        query = select(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _determine_starting_phase(self, item: KnowledgeBaseItem) -> str:
        """Determine which phase to start processing from"""
        # Check if item is a Twitter bookmark from Playwright fetch
        if item.source_type == "twitter_bookmark_auto" and item.item_metadata:
            # Item is a single bookmark from Playwright fetch, skip fetch_bookmarks
            # Convert single bookmark to tweets format for processing
            tweet_data = {
                "tweet_id": item.item_metadata.get("tweet_id", ""),
                "text": item.full_content or item.summary or "",
                "author": item.item_metadata.get("author_username", ""),
                "created_at": item.created_at.isoformat(),
                "media_urls": [],  # Will be populated in cache_media phase
                "is_thread": item.item_metadata.get("is_thread", False),
                "thread_root_id": item.item_metadata.get("thread_root_id"),
                "thread_position": item.item_metadata.get("thread_position", 0)
            }
            # Update item metadata to include tweets array
            if not item.item_metadata:
                item.item_metadata = {}
            item.item_metadata["tweets"] = [tweet_data]
            return "cache_content"

        # Check if item already has bookmark data (from Playwright fetch)
        if item.item_metadata and item.item_metadata.get("tweets"):
            # Item already has bookmark data, skip fetch_bookmarks phase
            return "cache_content"

        # Standard phase determination logic
        if item.processing_phase == "not_started":
            return "fetch_bookmarks"
        elif item.processing_phase == "completed":
            return "fetch_bookmarks"  # Restart if needed
        else:
            return item.processing_phase

    async def _can_run_phase(self, item: KnowledgeBaseItem, phase_name: str) -> bool:
        """Check if a phase can be run based on dependencies and settings"""
        # Check if phase is force reprocessing
        if self.should_force_reprocess_phase(phase_name):
            return True

        dependencies = self.phase_dependencies.get(phase_name, [])

        for dep in dependencies:
            # Check if dependency phase was completed
            phase_query = select(KnowledgeBaseProcessingPhase).where(
                and_(
                    KnowledgeBaseProcessingPhase.item_id == item.id,
                    KnowledgeBaseProcessingPhase.phase_name == dep,
                    KnowledgeBaseProcessingPhase.status == "completed"
                )
            )
            dep_result = await self.db.execute(phase_query)
            dep_phase = dep_result.scalar_one_or_none()

            if not dep_phase:
                return False

        return True

    async def _select_model_for_phase(self, phase_name: str, item: KnowledgeBaseItem) -> Optional[str]:
        """Select the best model for a given phase based on workflow settings"""
        config = self.phase_models.get(phase_name, {})
        if not config:
            return "llama2"  # Default fallback

        # Check if phase needs a model
        configured_model = config.get("model")
        if configured_model is None:
            return None  # Phase doesn't need a model

        # Check model availability
        available_models = await self.ollama.list_models()
        available_names = [model["name"] for model in available_models.get("models", [])]

        # Try configured model first
        if configured_model and configured_model in available_names:
            return configured_model

        # Try fallback models from settings
        for fallback in config.get("fallback_models", []):
            if fallback in available_names:
                return fallback

        # Ultimate fallback
        return "llama2"

    async def _get_fallback_model(self, phase_name: str, current_model: str) -> Optional[str]:
        """Get a fallback model for a phase"""
        config = self.phase_models.get(phase_name, {})
        fallbacks = config.get("fallback_models", [])

        available_models = await self.ollama.list_models()
        available_names = [model["name"] for model in available_models.get("models", [])]

        for fallback in fallbacks:
            if fallback != current_model and fallback in available_names:
                return fallback

        return None

    async def _record_phase_start(self, item_id: str, phase_name: str, model: str, total_items: int = 1):
        """Record the start of a processing phase with progress tracking"""
        await self.db.execute(
            insert(KnowledgeBaseProcessingPhase).values(
                item_id=item_id,
                phase_name=phase_name,
                status="running",
                model_used=model,
                started_at=datetime.utcnow(),
                total_items=total_items,
                current_item_index=0,
                progress_percentage=0.0,
                status_message=f"Starting {phase_name} phase processing",
                created_at=datetime.utcnow()
            )
        )

        # Update item status
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item_id).values(
                processing_phase=phase_name,
                phase_started_at=datetime.utcnow()
            )
        )

    async def _record_phase_completion(self, item_id: str, phase_name: str, model: str, result: Dict[str, Any]):
        """Record successful completion of a phase with processing time calculation"""
        # Calculate processing duration
        phase_query = select(KnowledgeBaseProcessingPhase).where(
            and_(
                KnowledgeBaseProcessingPhase.item_id == item_id,
                KnowledgeBaseProcessingPhase.phase_name == phase_name
            )
        )
        phase_result = await self.db.execute(phase_query)
        phase_record = phase_result.scalar_one_or_none()

        processing_duration_ms = None
        if phase_record and phase_record.started_at:
            duration = datetime.utcnow() - phase_record.started_at
            processing_duration_ms = int(duration.total_seconds() * 1000)

        await self.db.execute(
            update(KnowledgeBaseProcessingPhase).where(
                and_(
                    KnowledgeBaseProcessingPhase.item_id == item_id,
                    KnowledgeBaseProcessingPhase.phase_name == phase_name
                )
            ).values(
                status="completed",
                completed_at=datetime.utcnow(),
                processing_duration_ms=processing_duration_ms,
                progress_percentage=100.0,
                status_message=f"Completed {phase_name} phase processing",
                processing_metadata=json.dumps(result)
            )
        )

    async def _record_phase_failure(self, item_id: str, phase_name: str, model: str, error_msg: str):
        """Record failure of a processing phase"""
        await self.db.execute(
            update(KnowledgeBaseProcessingPhase).where(
                and_(
                    KnowledgeBaseProcessingPhase.item_id == item_id,
                    KnowledgeBaseProcessingPhase.phase_name == phase_name
                )
            ).values(
                status="failed",
                completed_at=datetime.utcnow(),
                error_message=error_msg,
                status_message=f"Failed {phase_name} phase: {error_msg}"
            )
        )

    async def _record_phase_skipped(self, item_id: str, phase_name: str):
        """Record that a processing phase was skipped"""
        await self.db.execute(
            insert(KnowledgeBaseProcessingPhase).values(
                item_id=item_id,
                phase_name=phase_name,
                status="skipped",
                model_used="n/a",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                status_message=f"Skipped {phase_name} phase (disabled in settings)",
                created_at=datetime.utcnow()
            )
        )

    async def update_phase_progress(
        self,
        item_id: str,
        phase_name: str,
        current_item: int,
        total_items: int,
        status_message: Optional[str] = None
    ):
        """Update progress for a processing phase"""
        progress_percentage = (current_item / total_items) * 100.0 if total_items > 0 else 0.0

        # Calculate estimated time remaining based on current progress
        estimated_remaining_ms = None
        phase_query = select(KnowledgeBaseProcessingPhase).where(
            and_(
                KnowledgeBaseProcessingPhase.item_id == item_id,
                KnowledgeBaseProcessingPhase.phase_name == phase_name
            )
        )
        phase_result = await self.db.execute(phase_query)
        phase_record = phase_result.scalar_one_or_none()

        if phase_record and phase_record.started_at and current_item > 0:
            elapsed = datetime.utcnow() - phase_record.started_at
            elapsed_ms = elapsed.total_seconds() * 1000
            avg_time_per_item = elapsed_ms / current_item
            remaining_items = total_items - current_item
            estimated_remaining_ms = int(avg_time_per_item * remaining_items)

        # Default status message if not provided
        if not status_message:
            status_message = f"Processing item {current_item} of {total_items}"

        await self.db.execute(
            update(KnowledgeBaseProcessingPhase).where(
                and_(
                    KnowledgeBaseProcessingPhase.item_id == item_id,
                    KnowledgeBaseProcessingPhase.phase_name == phase_name
                )
            ).values(
                current_item_index=current_item,
                total_items=total_items,
                progress_percentage=progress_percentage,
                estimated_time_remaining_ms=estimated_remaining_ms,
                status_message=status_message,
                updated_at=datetime.utcnow()
            )
        )

    async def get_processing_progress(self, item_id: str) -> Dict[str, Any]:
        """Get comprehensive processing progress for an item"""
        # Get item details
        item = await self._get_item(item_id)
        if not item:
            raise ValueError(f"Knowledge base item {item_id} not found")

        # Get all processing phases
        phases_query = select(KnowledgeBaseProcessingPhase).where(
            KnowledgeBaseProcessingPhase.item_id == item_id
        ).order_by(KnowledgeBaseProcessingPhase.created_at)
        phases_result = await self.db.execute(phases_query)
        phases = phases_result.scalars().all()

        # Calculate overall progress
        total_phases = len(self.phase_sequence)
        completed_phases = sum(1 for phase in phases if phase.status == "completed")
        overall_progress = (completed_phases / total_phases) * 100.0 if total_phases > 0 else 0.0

        # Get current phase progress
        current_phase = None
        current_phase_progress = 0.0
        estimated_time_remaining = None

        for phase in phases:
            if phase.status == "running":
                current_phase = phase.phase_name
                current_phase_progress = phase.progress_percentage or 0.0
                estimated_time_remaining = phase.estimated_time_remaining_ms
                break

        # Calculate total processing time so far
        total_processing_time_ms = sum(
            phase.processing_duration_ms or 0
            for phase in phases
            if phase.processing_duration_ms
        )

        return {
            "item_id": item_id,
            "item_title": item.title,
            "overall_progress_percentage": overall_progress,
            "current_phase": current_phase,
            "current_phase_progress_percentage": current_phase_progress,
            "total_phases": total_phases,
            "completed_phases": completed_phases,
            "estimated_time_remaining_ms": estimated_time_remaining,
            "total_processing_time_ms": total_processing_time_ms,
            "processing_status": item.processing_phase,
            "phases": [
                {
                    "phase_name": phase.phase_name,
                    "status": phase.status,
                    "progress_percentage": phase.progress_percentage or 0.0,
                    "processing_duration_ms": phase.processing_duration_ms,
                    "status_message": phase.status_message,
                    "started_at": phase.started_at.isoformat() if phase.started_at else None,
                    "completed_at": phase.completed_at.isoformat() if phase.completed_at else None,
                    "model_used": phase.model_used
                }
                for phase in phases
            ]
        }

    async def _update_item_phase_status(self, item: KnowledgeBaseItem, phase_name: str, status: str):
        """Update the overall item processing status"""
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item.id).values(
                processing_phase=phase_name if status == "running" else "completed",
                phase_completed_at=datetime.utcnow() if status == "completed" else None,
                last_successful_phase=phase_name if status == "completed" else item.last_successful_phase
            )
        )

    async def _should_continue_to_next_phase(self, item: KnowledgeBaseItem, completed_phase: str) -> bool:
        """Determine if processing should continue to the next phase"""
        # For now, always continue unless there are specific conditions
        return True

    async def _mark_item_completed(self, item: KnowledgeBaseItem):
        """Mark an item as fully processed"""
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item.id).values(
                processing_phase="completed",
                phase_completed_at=datetime.utcnow()
            )
        )

    async def _handle_workflow_error(self, item: KnowledgeBaseItem, phase_name: str, error_msg: str):
        """Handle workflow-level errors"""
        await self.db.execute(
            update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item.id).values(
                processing_phase=f"failed_at_{phase_name}"
            )
        )

        logger.error(f"Workflow failed for item {item.id} at phase {phase_name}: {error_msg}")

    def _get_dependent_phases(self, phase_name: str) -> List[str]:
        """Get all phases that depend on the given phase"""
        dependents = []
        for phase, deps in self.phase_dependencies.items():
            if phase_name in deps:
                dependents.append(phase)
                # Recursively get dependents of dependents
                dependents.extend(self._get_dependent_phases(phase))
        return list(set(dependents))

    async def _reset_phase_status(self, item_id: str, phase_name: str):
        """Reset a phase status to allow reprocessing"""
        await self.db.execute(
            update(KnowledgeBaseProcessingPhase).where(
                and_(
                    KnowledgeBaseProcessingPhase.item_id == item_id,
                    KnowledgeBaseProcessingPhase.phase_name == phase_name
                )
            ).values(
                status="pending",
                retry_count=0,
                error_message=None,
                started_at=None,
                completed_at=None
            )
        )

    def _get_media_type(self, url: str) -> str:
        """Determine media type from URL"""
        if url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return "image"
        elif url.lower().endswith(('.mp4', '.avi', '.mov', '.wmv')):
            return "video"
        elif url.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
            return "audio"
        else:
            return "unknown"

    # Workflow Settings Methods
    def _load_default_workflow_settings(self) -> Dict[str, Any]:
        """Load default workflow settings from database or use hardcoded defaults"""
        # For now, return hardcoded defaults
        # TODO: Load from database based on user preferences
        return {
            "phase_models": self._get_default_phase_models(),
            "phase_settings": self._get_default_phase_settings(),
            "global_settings": self._get_default_global_settings()
        }

    def _get_default_phase_models(self) -> Dict[str, Any]:
        """Get default model configuration for all phases"""
        return {
            "fetch_bookmarks": {
                "model": None,  # No model needed for bookmark fetching
                "fallback_models": [],
                "task_type": "data_fetching"
            },
            "cache_content": {
                "model": "llama2",
                "fallback_models": ["mistral", "codellama"],
                "task_type": "text_processing"
            },
            "cache_media": {
                "model": "llama2",
                "fallback_models": ["mistral", "codellama"],
                "task_type": "general"
            },
            "interpret_media": {
                "model": "llava:13b",
                "fallback_models": ["llava:7b", "bakllava"],
                "task_type": "vision_analysis"
            },
            "categorize_content": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "mistral"],
                "task_type": "classification"
            },
            "holistic_understanding": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "codellama"],
                "task_type": "text_synthesis"
            },
            "synthesized_learning": {
                "model": "llama2:13b",
                "fallback_models": ["llama2:7b", "mistral"],
                "task_type": "content_synthesis"
            },
            "embeddings": {
                "model": "all-minilm",
                "fallback_models": ["paraphrase-multilingual", "sentence-transformers"],
                "task_type": "embedding"
            }
        }

    def _get_default_phase_settings(self) -> Dict[str, Any]:
        """Get default phase control settings"""
        return {
            "fetch_bookmarks": {"skip": False, "force_reprocess": False, "enabled": True},
            "cache_content": {"skip": False, "force_reprocess": False, "enabled": True},
            "cache_media": {"skip": False, "force_reprocess": False, "enabled": True},
            "interpret_media": {"skip": False, "force_reprocess": False, "enabled": True},
            "categorize_content": {"skip": False, "force_reprocess": False, "enabled": True},
            "holistic_understanding": {"skip": False, "force_reprocess": False, "enabled": True},
            "synthesized_learning": {"skip": False, "force_reprocess": False, "enabled": True},
            "embeddings": {"skip": False, "force_reprocess": False, "enabled": True}
        }

    def _get_default_global_settings(self) -> Dict[str, Any]:
        """Get default global workflow settings"""
        return {
            "max_concurrent_items": 5,
            "retry_attempts": 3,
            "timeout_seconds": 1800,
            "auto_start_processing": True,
            "enable_progress_tracking": True,
            "notification_settings": {
                "on_completion": True,
                "on_error": True,
                "progress_updates": False
            }
        }

    def should_skip_phase(self, phase_name: str) -> bool:
        """Check if a phase should be skipped based on settings"""
        phase_setting = self.phase_settings.get(phase_name, {})
        return phase_setting.get("skip", False) or not phase_setting.get("enabled", True)

    def should_force_reprocess_phase(self, phase_name: str) -> bool:
        """Check if a phase should be force reprocessed"""
        phase_setting = self.phase_settings.get(phase_name, {})
        return phase_setting.get("force_reprocess", False)

    async def load_workflow_settings(self, settings_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
        """Load workflow settings from database"""
        if settings_id:
            # Load specific settings profile
            query = select(KnowledgeBaseWorkflowSettings).where(
                KnowledgeBaseWorkflowSettings.id == settings_id
            )
            result = await self.db.execute(query)
            settings = result.scalar_one_or_none()
            if settings:
                self.workflow_settings = {
                    "phase_models": settings.phase_models,
                    "phase_settings": settings.phase_settings,
                    "global_settings": settings.global_settings
                }
                # Update instance variables
                self.phase_models = settings.phase_models
                self.phase_settings = settings.phase_settings
                self.global_settings = settings.global_settings

    async def cancel_item_processing(self, item_id: str, reason: str = "Cancelled by user"):
        """Cancel processing for a knowledge base item.

        This method stops any ongoing processing for the specified item and
        updates the database to reflect the cancellation.
        """
        try:
            # Get the item to check current status
            item = await self._get_item(item_id)
            if not item:
                raise ValueError(f"Knowledge base item {item_id} not found")

            # Check if item is currently processing
            if item.processing_phase in ["completed", "cancelled", "not_started"]:
                logger.warning(f"Item {item_id} is not currently processing (status: {item.processing_phase})")
                return

            # Update any running processing phases to cancelled status
            await self.db.execute(
                update(KnowledgeBaseProcessingPhase).where(
                    and_(
                        KnowledgeBaseProcessingPhase.item_id == item_id,
                        KnowledgeBaseProcessingPhase.status == "running"
                    )
                ).values(
                    status="cancelled",
                    completed_at=datetime.utcnow(),
                    error_message=f"Processing cancelled: {reason}",
                    status_message=f"Cancelled: {reason}",
                    updated_at=datetime.utcnow()
                )
            )

            # Update item status to cancelled
            await self.db.execute(
                update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item_id).values(
                    processing_phase="cancelled",
                    phase_completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    reprocessing_reason=reason
                )
            )

            await self.db.commit()

            logger.info(f"Successfully cancelled processing for item {item_id}: {reason}")

        except Exception as e:
            logger.error(f"Error cancelling item processing {item_id}: {e}")
            await self.db.rollback()
            raise

    async def _is_item_cancelled(self, item_id: str) -> bool:
        """Check if an item has been marked for cancellation."""
        try:
            # Query the database to check current status
            query = select(KnowledgeBaseItem.processing_phase).where(
                KnowledgeBaseItem.id == item_id
            )
            result = await self.db.execute(query)
            current_phase = result.scalar_one_or_none()

            return current_phase == "cancelled"
        except Exception as e:
            logger.error(f"Error checking cancellation status for item {item_id}: {e}")
            return False

    async def _handle_workflow_cancellation(self, item: KnowledgeBaseItem, reason: str):
        """Handle workflow cancellation by updating the item status."""
        try:
            await self.db.execute(
                update(KnowledgeBaseItem).where(KnowledgeBaseItem.id == item.id).values(
                    processing_phase="cancelled",
                    phase_completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    reprocessing_reason=reason
                )
            )

            await self.db.commit()

            logger.info(f"Workflow cancelled for item {item.id}: {reason}")
        except Exception as e:
            logger.error(f"Error handling workflow cancellation for item {item.id}: {e}")
            await self.db.rollback()
