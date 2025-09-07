"""
Knowledge Base Presenter API Routes

Frontend-facing API endpoints for browsing, editing, and managing the knowledge base.
Provides comprehensive access to processed knowledge base items with filtering,
search, and management capabilities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update, insert
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models.knowledge_base import (
    KnowledgeBaseItem,
    KnowledgeBaseCategory,
    KnowledgeBaseMedia,
    KnowledgeBaseAnalysis,
    KnowledgeBaseProcessingPhase,
    KnowledgeBaseSearchLog,
    KnowledgeBaseWorkflowSettings
)
from app.services.knowledge_base_workflow_service import KnowledgeBaseWorkflowService
from app.utils.logging import get_logger

# TODO: Implement proper authentication
async def get_current_user():
    """Placeholder for authentication - returns dummy user for now"""
    return {"id": "system", "username": "system"}

logger = get_logger("knowledge_base_presenter")

router = APIRouter(prefix="/knowledge", tags=["knowledge-base"])


# Dependency to get workflow service
async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> KnowledgeBaseWorkflowService:
    """Get knowledge base workflow service instance."""
    # Import here to avoid circular imports
    from app.services.ollama_client import ollama_client
    from app.services.vision_ai_service import vision_ai_service
    from app.services.semantic_processing_service import semantic_processing_service
    from app.services.media_download_service import media_download_service
    from app.connectors.social_media import TwitterConnector
    from app.config import settings

    # Initialize services if needed
    await semantic_processing_service.initialize()
    await vision_ai_service.initialize()

    from app.connectors.base import ConnectorConfig
    from app.connectors.base import ConnectorType

    # Use actual X API credentials from settings
    credentials = {}
    if settings.x_bearer_token:
        credentials["bearer_token"] = settings.x_bearer_token
    if settings.x_api_key and settings.x_api_secret:
        credentials["api_key"] = settings.x_api_key
        credentials["api_secret"] = settings.x_api_secret

    config = ConnectorConfig(
        name="twitter_connector",
        connector_type=ConnectorType.SOCIAL_MEDIA,
        source_config={},
        credentials=credentials
    )
    twitter_connector = TwitterConnector(config)

    service = KnowledgeBaseWorkflowService(
        db_session=db,
        ollama_client=ollama_client,
        vision_service=vision_ai_service,
        semantic_service=semantic_processing_service,
        twitter_connector=twitter_connector,
        media_download_service=media_download_service
    )

    return service


@router.get("/items")
async def list_knowledge_items(
    db: AsyncSession = Depends(get_db),
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    # Sorting parameters
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    # User authentication
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List processed knowledge base items with pagination and sorting.

    Returns a paginated list of knowledge base items that have been processed
    through the workflow pipeline. Excludes raw bookmarks that haven't been
    processed into knowledge base items.
    """
    try:
        # Build base query - exclude raw bookmarks and only include processed items
        query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                # Exclude raw bookmarks - only include items that have been processed
                KnowledgeBaseItem.source_type.not_in([
                    "twitter_bookmark",  # Raw bookmarks not processed
                    "twitter_bookmark_auto"  # Auto-discovered bookmarks not processed
                ]),
                # Only include items that have completed processing or are being processed
                or_(
                    KnowledgeBaseItem.processing_phase != "not_started",
                    KnowledgeBaseItem.processed_at.isnot(None)
                )
            )
        )

        # Apply sorting
        sort_column = getattr(KnowledgeBaseItem, sort_by, KnowledgeBaseItem.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Get total count for pagination
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        # Format results
        items_list = []
        for item in items:
            item_dict = item.to_dict()
            items_list.append(item_dict)

        return {
            "items": items_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if total_count > 0 else 0
            },
            "total_count": total_count,
            "filter_note": "Excludes raw bookmarks - only shows processed knowledge base items"
        }

    except Exception as e:
        logger.error(f"Error listing knowledge items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge items: {str(e)}")


@router.post("/items")
async def create_knowledge_item(
    item_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new knowledge base item.

    Supports creating items from various sources including Twitter bookmarks.
    """
    try:
        # Validate required fields
        required_fields = ["source_type", "content_type"]
        for field in required_fields:
            if field not in item_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field missing: {field}"
                )

        # Generate UUID for new item
        item_id = str(uuid.uuid4())

        # Prepare item data
        now = datetime.utcnow()
        item_dict = {
            "id": item_id,
            "source_type": item_data["source_type"],
            "content_type": item_data["content_type"],
            "title": item_data.get("title"),
            "summary": item_data.get("summary"),
            "full_content": item_data.get("full_content"),
            "item_metadata": item_data.get("item_metadata", {}),
            "created_at": now,
            "updated_at": now,
            "processed_at": None,
            "is_active": True,
            "processing_phase": "not_started",
            "phase_started_at": None,
            "phase_completed_at": None,
            "last_successful_phase": None,
            "needs_reprocessing": False,
            "reprocessing_reason": None
        }

        # Insert new item
        await db.execute(
            insert(KnowledgeBaseItem).values(**item_dict)
        )

        await db.commit()

        logger.info(f"Created knowledge base item {item_id} by user {current_user.get('id')}")

        return {
            "message": "Knowledge base item created successfully",
            "item_id": item_id,
            "item": item_dict
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge item: {str(e)}")


@router.post("/items/twitter-bookmark")
async def create_twitter_bookmark_item(
    bookmark_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a knowledge base item from a Twitter bookmark.

    Specialized endpoint for Twitter bookmark processing with automatic metadata extraction.
    """
    try:
        # Validate required fields
        required_fields = ["bookmark_url"]
        for field in required_fields:
            if field not in bookmark_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field missing: {field}"
                )

        # Generate UUID for new item
        item_id = str(uuid.uuid4())

        # Extract tweet ID from URL if possible
        bookmark_url = bookmark_data["bookmark_url"]
        tweet_id = None
        if "status/" in bookmark_url:
            try:
                tweet_id = bookmark_url.split("status/")[1].split("?")[0].split("/")[0]
            except:
                pass

        # Prepare item data
        now = datetime.utcnow()
        item_dict = {
            "id": item_id,
            "source_type": "twitter_bookmark",
            "content_type": "text",
            "title": bookmark_data.get("title", f"Twitter Bookmark - {tweet_id or 'Unknown'}"),
            "summary": bookmark_data.get("summary"),
            "full_content": bookmark_data.get("content"),
            "item_metadata": {
                "bookmark_url": bookmark_url,
                "tweet_id": tweet_id,
                "bookmarked_at": bookmark_data.get("bookmarked_at"),
                "tags": bookmark_data.get("tags", []),
                **bookmark_data.get("metadata", {})
            },
            "created_at": now,
            "updated_at": now,
            "processed_at": None,
            "is_active": True,
            "processing_phase": "not_started",
            "phase_started_at": None,
            "phase_completed_at": None,
            "last_successful_phase": None,
            "needs_reprocessing": False,
            "reprocessing_reason": None
        }

        # Insert new item
        await db.execute(
            insert(KnowledgeBaseItem).values(**item_dict)
        )

        await db.commit()

        logger.info(f"Created Twitter bookmark item {item_id} by user {current_user.get('id')}")

        return {
            "message": "Twitter bookmark item created successfully",
            "item_id": item_id,
            "item": item_dict,
            "tweet_id": tweet_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Twitter bookmark item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create Twitter bookmark item: {str(e)}")


@router.post("/fetch-twitter-bookmarks")
async def fetch_twitter_bookmarks(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetch Twitter bookmarks from a bookmark folder URL and process them through the knowledge base workflow.

    This endpoint automatically discovers and processes Twitter bookmarks from a user's bookmark collection.

    For development/testing, you can use:
    - bookmark_url: "mock://bookmarks" to use mock data instead of real Twitter API
    - use_mock_data: true parameter for any URL
    """
    """
    Fetch Twitter bookmarks from a bookmark folder URL and process them through the knowledge base workflow.

    This endpoint automatically discovers and processes Twitter bookmarks from a user's bookmark collection.
    """
    try:
        # Validate required fields
        required_fields = ["bookmark_url"]
        for field in required_fields:
            if field not in request:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field missing: {field}"
                )

        bookmark_url = request["bookmark_url"]
        max_results = request.get("max_results", 50)
        process_items = request.get("process_items", True)
        workflow_settings_id = request.get("workflow_settings_id")

        # Load workflow settings if specified
        if workflow_settings_id:
            await workflow_service.load_workflow_settings(workflow_settings_id)

        # Use Playwright by default (configured in settings)
        # Extract user information from bookmark URL if possible
        # Twitter bookmark URLs are typically: https://twitter.com/i/bookmarks or https://twitter.com/username/bookmarks
        user_id = None
        username = None

        if "bookmarks" in bookmark_url:
            # Try to extract username from URL
            if "/i/bookmarks" in bookmark_url:
                # This is the current user's bookmarks - we'll need to get user_id from auth
                pass  # Will use current authenticated user
            else:
                # Extract username from URL like https://twitter.com/username/bookmarks
                try:
                    username = bookmark_url.split("/bookmarks")[0].split("/")[-1]
                except:
                    pass

        # Use Twitter connector to fetch bookmarks
        # The connector expects source_config with query_type and params
        source_config = {
            "query_type": "bookmarks",
            "query_params": {
                "max_results": min(max_results, 100),  # Twitter API limit
                "user_id": user_id,
                "username": username
            }
        }

        # Get Twitter connector from workflow service
        twitter_connector = workflow_service.twitter

        # Discover bookmarks using Playwright (configured in settings)
        logger.info(f"Fetching Twitter bookmarks for user {current_user.get('id')} using Playwright")
        bookmark_items = await twitter_connector.discover(source_config)

        if not bookmark_items:
            return {
                "message": "No bookmarks found or unable to access bookmark folder",
                "bookmarks_found": 0,
                "processed_items": 0,
                "items": []
            }

        processed_items = []
        created_items = []

        for bookmark_item in bookmark_items:
            try:
                # Create knowledge base item from bookmark
                item_id = str(uuid.uuid4())
                now = datetime.utcnow()

                # Extract tweet ID from bookmark URL
                tweet_id = None
                if bookmark_item.url:
                    try:
                        tweet_id = bookmark_item.url.split("status/")[1].split("?")[0].split("/")[0]
                    except:
                        pass

                item_dict = {
                    "id": item_id,
                    "source_type": "twitter_bookmark_auto",
                    "content_type": "text",
                    "title": bookmark_item.title or f"Twitter Bookmark - {tweet_id or 'Unknown'}",
                    "summary": bookmark_item.description,
                    "full_content": bookmark_item.description,
                    "item_metadata": {
                        "bookmark_url": bookmark_item.url,
                        "tweet_id": tweet_id,
                        "author_username": bookmark_item.metadata.get("author_username"),
                        "author_name": bookmark_item.metadata.get("author_name"),
                        "likes": bookmark_item.metadata.get("likes", 0),
                        "retweets": bookmark_item.metadata.get("retweets", 0),
                        "replies": bookmark_item.metadata.get("replies", 0),
                        "hashtags": bookmark_item.metadata.get("hashtags", []),
                        "mentions": bookmark_item.metadata.get("mentions", []),
                        "bookmarked_at": now.isoformat(),
                        "auto_discovered": True,
                        **bookmark_item.metadata
                    },
                    "created_at": now,
                    "updated_at": now,
                    "processed_at": None,
                    "is_active": True,
                    "processing_phase": "not_started",
                    "phase_started_at": None,
                    "phase_completed_at": None,
                    "last_successful_phase": None,
                    "needs_reprocessing": False,
                    "reprocessing_reason": None
                }

                # Insert new item
                await db.execute(
                    insert(KnowledgeBaseItem).values(**item_dict)
                )

                created_items.append(item_dict)

                # Process through workflow if requested
                if process_items:
                    try:
                        result = await workflow_service.process_item(item_id)
                        processed_items.append({
                            "item_id": item_id,
                            "processing_result": result
                        })
                        logger.info(f"Successfully processed Twitter bookmark {item_id}")
                    except Exception as process_error:
                        logger.error(f"Failed to process Twitter bookmark {item_id}: {process_error}")
                        processed_items.append({
                            "item_id": item_id,
                            "processing_error": str(process_error)
                        })

            except Exception as item_error:
                logger.error(f"Failed to create knowledge base item from bookmark: {item_error}")
                continue

        await db.commit()

        return {
            "message": f"Successfully fetched {len(bookmark_items)} Twitter bookmarks using Playwright",
            "bookmarks_found": len(bookmark_items),
            "items_created": len(created_items),
            "items_processed": len(processed_items),
            "bookmark_url": bookmark_url,
            "fetch_method": "playwright",
            "processed_items": processed_items,
            "created_items": created_items
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Twitter bookmarks: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to fetch Twitter bookmarks: {str(e)}")


@router.get("/browse")
async def browse_knowledge_base(
    db: AsyncSession = Depends(get_db),
    # Filtering parameters
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    processing_status: Optional[str] = Query(None, description="Filter by processing status"),
    has_media: Optional[bool] = Query(None, description="Filter by media presence"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    # Search parameters
    search_query: Optional[str] = Query(None, description="Search in title and content"),
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    # Sorting parameters
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    # User authentication
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Browse knowledge base with advanced filtering and search capabilities.

    Returns paginated list of knowledge base items with their current processing status,
    categories, and basic metadata.
    """
    try:
        # Build base query
        query = select(KnowledgeBaseItem).where(KnowledgeBaseItem.is_active == True)

        # Apply filters
        if category:
            query = query.join(KnowledgeBaseCategory).where(
                KnowledgeBaseCategory.category == category
            )

        if subcategory:
            query = query.join(KnowledgeBaseCategory).where(
                KnowledgeBaseCategory.sub_category == subcategory
            )

        if processing_status:
            query = query.where(KnowledgeBaseItem.processing_phase == processing_status)

        if has_media is not None:
            if has_media:
                query = query.where(
                    select(func.count()).select_from(KnowledgeBaseMedia)
                    .where(KnowledgeBaseMedia.item_id == KnowledgeBaseItem.id)
                    .correlate(KnowledgeBaseItem).scalar_subquery() > 0
                )
            else:
                query = query.where(
                    select(func.count()).select_from(KnowledgeBaseMedia)
                    .where(KnowledgeBaseMedia.item_id == KnowledgeBaseItem.id)
                    .correlate(KnowledgeBaseItem).scalar_subquery() == 0
                )

        if source_type:
            query = query.where(KnowledgeBaseItem.source_type == source_type)

        if search_query:
            search_filter = f"%{search_query}%"
            query = query.where(
                or_(
                    KnowledgeBaseItem.title.ilike(search_filter),
                    KnowledgeBaseItem.summary.ilike(search_filter),
                    KnowledgeBaseItem.full_content.ilike(search_filter)
                )
            )

        # Apply sorting
        sort_column = getattr(KnowledgeBaseItem, sort_by, KnowledgeBaseItem.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Get total count for pagination
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        # Get categories for each item
        items_with_categories = []
        for item in items:
            # Get categories
            cat_query = select(KnowledgeBaseCategory).where(
                KnowledgeBaseCategory.item_id == item.id
            )
            cat_result = await db.execute(cat_query)
            categories = cat_result.scalars().all()

            # Get media count
            media_query = select(func.count()).select_from(KnowledgeBaseMedia).where(
                KnowledgeBaseMedia.item_id == item.id
            )
            media_result = await db.execute(media_query)
            media_count = media_result.scalar() or 0

            # Get latest processing phase
            phase_query = select(KnowledgeBaseProcessingPhase).where(
                KnowledgeBaseProcessingPhase.item_id == item.id
            ).order_by(desc(KnowledgeBaseProcessingPhase.created_at)).limit(1)
            phase_result = await db.execute(phase_query)
            latest_phase = phase_result.scalar_one_or_none()

            item_dict = item.to_dict()
            item_dict.update({
                "categories": [{"category": c.category, "subcategory": c.sub_category} for c in categories],
                "media_count": media_count,
                "latest_phase": latest_phase.to_dict() if latest_phase else None
            })
            items_with_categories.append(item_dict)

        return {
            "items": items_with_categories,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if total_count > 0 else 0
            },
            "filters_applied": {
                "category": category,
                "subcategory": subcategory,
                "processing_status": processing_status,
                "has_media": has_media,
                "source_type": source_type,
                "search_query": search_query
            }
        }

    except Exception as e:
        logger.error(f"Error browsing knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to browse knowledge base: {str(e)}")


@router.get("/items/{item_id}/details")
async def get_item_details(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get complete details for a specific knowledge base item.

    Includes processing history, categories, media assets, and analysis results.
    """
    try:
        # Get main item with relationships
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Get processing phases
        phases_query = select(KnowledgeBaseProcessingPhase).where(
            KnowledgeBaseProcessingPhase.item_id == item_id
        ).order_by(desc(KnowledgeBaseProcessingPhase.created_at))
        phases_result = await db.execute(phases_query)
        phases = phases_result.scalars().all()

        # Get categories
        categories_query = select(KnowledgeBaseCategory).where(
            KnowledgeBaseCategory.item_id == item_id
        )
        categories_result = await db.execute(categories_query)
        categories = categories_result.scalars().all()

        # Get media assets
        media_query = select(KnowledgeBaseMedia).where(
            KnowledgeBaseMedia.item_id == item_id
        )
        media_result = await db.execute(media_query)
        media_assets = media_result.scalars().all()

        # Get analysis results
        analysis_query = select(KnowledgeBaseAnalysis).where(
            KnowledgeBaseAnalysis.item_id == item_id
        ).order_by(desc(KnowledgeBaseAnalysis.created_at))
        analysis_result = await db.execute(analysis_query)
        analysis_results = analysis_result.scalars().all()

        return {
            "item": item.to_dict(),
            "processing_phases": [phase.to_dict() for phase in phases],
            "categories": [cat.to_dict() for cat in categories],
            "media_assets": [media.to_dict() for media in media_assets],
            "analysis_results": [analysis.to_dict() for analysis in analysis_results]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get item details: {str(e)}")


@router.put("/items/{item_id}/edit")
async def edit_knowledge_item(
    item_id: str,
    updates: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Edit knowledge base item content and metadata.

    Allows updating title, summary, content, and metadata.
    """
    try:
        # Validate allowed fields
        allowed_fields = {"title", "summary", "full_content", "item_metadata"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fields for update: {invalid_fields}"
            )

        # Check if item exists
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Update item
        update_data = updates.copy()
        update_data["updated_at"] = datetime.utcnow()

        await db.execute(
            update(KnowledgeBaseItem)
            .where(KnowledgeBaseItem.id == item_id)
            .values(**update_data)
        )

        await db.commit()

        # Log the edit
        logger.info(f"Item {item_id} edited by user {current_user.get('id')}")

        return {
            "message": "Knowledge base item updated successfully",
            "item_id": item_id,
            "updated_fields": list(updates.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing knowledge item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to edit knowledge item: {str(e)}")


@router.post("/items/{item_id}/reprocess")
async def flag_for_reprocessing(
    item_id: str,
    reprocess_request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Flag knowledge base item for reprocessing specific phases.

    Allows selective reprocessing of workflow phases with reason tracking.
    Supports custom workflow settings for reprocessing.
    """
    try:
        phases = reprocess_request.get("phases", [])
        reason = reprocess_request.get("reason", "User requested reprocessing")
        start_immediately = reprocess_request.get("start_immediately", False)
        workflow_settings_id = reprocess_request.get("workflow_settings_id")

        if not phases:
            raise HTTPException(status_code=400, detail="At least one phase must be specified")

        # Validate phases
        valid_phases = {
            "fetch_bookmarks", "cache_content", "cache_media", "interpret_media",
            "categorize_content", "holistic_understanding", "synthesized_learning", "embeddings"
        }
        invalid_phases = set(phases) - valid_phases
        if invalid_phases:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phases: {invalid_phases}"
            )

        # Check if item exists
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Load workflow settings if specified
        if workflow_settings_id:
            await workflow_service.load_workflow_settings(workflow_settings_id)

        # Flag for reprocessing
        await workflow_service.flag_for_reprocessing(item_id, phases, reason)

        # Start reprocessing if requested
        if start_immediately:
            background_tasks.add_task(
                workflow_service.process_item,
                item_id,
                phases[0]  # Start with first phase
            )

        logger.info(f"Item {item_id} flagged for reprocessing phases {phases}")

        return {
            "message": f"Item {item_id} flagged for reprocessing",
            "phases": phases,
            "reason": reason,
            "started_immediately": start_immediately,
            "workflow_settings_used": workflow_settings_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error flagging item for reprocessing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to flag for reprocessing: {str(e)}")


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all available categories and subcategories in the knowledge base.

    Returns hierarchical structure of categories with item counts.
    """
    try:
        # Get all categories with counts
        query = select(
            KnowledgeBaseCategory.category,
            KnowledgeBaseCategory.sub_category,
            func.count(KnowledgeBaseCategory.id).label("item_count")
        ).group_by(
            KnowledgeBaseCategory.category,
            KnowledgeBaseCategory.sub_category
        ).order_by(
            KnowledgeBaseCategory.category,
            KnowledgeBaseCategory.sub_category
        )

        result = await db.execute(query)
        category_data = result.all()

        # Organize into hierarchical structure
        categories = {}
        for category, subcategory, count in category_data:
            if category not in categories:
                categories[category] = {
                    "name": category,
                    "total_items": 0,
                    "subcategories": {}
                }

            categories[category]["total_items"] += count

            if subcategory:
                categories[category]["subcategories"][subcategory] = {
                    "name": subcategory,
                    "item_count": count
                }

        return {
            "categories": list(categories.values()),
            "total_categories": len(categories)
        }

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/stats")
async def get_knowledge_base_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comprehensive statistics about the knowledge base.

    Includes counts by status, category, processing phase, etc.
    """
    try:
        stats = {}

        # Total items
        total_query = select(func.count()).select_from(KnowledgeBaseItem).where(
            KnowledgeBaseItem.is_active == True
        )
        total_result = await db.execute(total_query)
        stats["total_items"] = total_result.scalar()

        # Items by processing status
        status_query = select(
            KnowledgeBaseItem.processing_phase,
            func.count(KnowledgeBaseItem.id)
        ).where(KnowledgeBaseItem.is_active == True).group_by(KnowledgeBaseItem.processing_phase)

        status_result = await db.execute(status_query)
        stats["processing_status"] = {status: count for status, count in status_result.all()}

        # Items by source type
        source_query = select(
            KnowledgeBaseItem.source_type,
            func.count(KnowledgeBaseItem.id)
        ).where(KnowledgeBaseItem.is_active == True).group_by(KnowledgeBaseItem.source_type)

        source_result = await db.execute(source_query)
        stats["source_types"] = {source: count for source, count in source_result.all()}

        # Items with media
        media_query = select(func.count(func.distinct(KnowledgeBaseMedia.item_id))).select_from(
            KnowledgeBaseMedia
        ).join(KnowledgeBaseItem).where(KnowledgeBaseItem.is_active == True)

        media_result = await db.execute(media_query)
        stats["items_with_media"] = media_result.scalar()

        # Total media assets
        total_media_query = select(func.count()).select_from(KnowledgeBaseMedia).join(
            KnowledgeBaseItem
        ).where(KnowledgeBaseItem.is_active == True)

        total_media_result = await db.execute(total_media_query)
        stats["total_media_assets"] = total_media_result.scalar()

        # Recent processing activity
        recent_phases_query = select(func.count()).select_from(KnowledgeBaseProcessingPhase).where(
            KnowledgeBaseProcessingPhase.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        )
        recent_result = await db.execute(recent_phases_query)
        stats["processing_phases_today"] = recent_result.scalar()

        return stats

    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/search")
async def search_knowledge_base(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Search knowledge base using semantic search capabilities.

    Supports natural language queries with optional category filtering.
    """
    try:
        # Log search query
        await db.execute(
            insert(KnowledgeBaseSearchLog).values(
                user_id=current_user.get("id"),
                query=query,
                search_type="semantic",
                created_at=datetime.utcnow()
            )
        )

        # For now, implement basic text search
        # TODO: Integrate with semantic search service
        search_filter = f"%{query}%"

        search_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                or_(
                    KnowledgeBaseItem.title.ilike(search_filter),
                    KnowledgeBaseItem.summary.ilike(search_filter),
                    KnowledgeBaseItem.full_content.ilike(search_filter)
                )
            )
        )

        # Apply category filters
        if category:
            search_query = search_query.join(KnowledgeBaseCategory).where(
                KnowledgeBaseCategory.category == category
            )

        if subcategory:
            search_query = search_query.join(KnowledgeBaseCategory).where(
                KnowledgeBaseCategory.sub_category == subcategory
            )

        search_query = search_query.limit(limit)

        result = await db.execute(search_query)
        items = result.scalars().all()

        # Format results
        search_results = []
        for item in items:
            # Safely get created_at
            created_at_str = None
            if hasattr(item, 'created_at') and getattr(item, 'created_at', None):
                created_at = getattr(item, 'created_at')
                if hasattr(created_at, 'isoformat'):
                    created_at_str = created_at.isoformat()

            search_results.append({
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "source_type": item.source_type,
                "processing_phase": item.processing_phase,
                "created_at": created_at_str
            })

        return {
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.delete("/items/{item_id}")
async def delete_knowledge_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Soft delete a knowledge base item.

    Marks item as inactive rather than physically deleting it.
    """
    try:
        # Check if item exists
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Soft delete
        await db.execute(
            update(KnowledgeBaseItem)
            .where(KnowledgeBaseItem.id == item_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
        )

        await db.commit()

        logger.info(f"Item {item_id} soft deleted by user {current_user.get('id')}")

        return {
            "message": "Knowledge base item deleted successfully",
            "item_id": item_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge item: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge item: {str(e)}")


@router.get("/items/{item_id}/progress")
async def get_item_progress(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comprehensive processing progress for a specific knowledge base item.

    Returns detailed progress information including:
    - Overall progress percentage
    - Current phase and its progress
    - Processing time estimates
    - Rich status messages
    - Phase-by-phase breakdown
    """
    try:
        # Check if item exists
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Get progress from workflow service
        progress = await workflow_service.get_processing_progress(item_id)

        return progress

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get item progress: {str(e)}")


@router.get("/progress/batch")
async def get_batch_progress(
    item_ids: List[str] = Query(..., description="List of item IDs to get progress for"),
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get processing progress for multiple knowledge base items.

    Useful for monitoring batch processing operations.
    """
    try:
        progress_results = []

        for item_id in item_ids:
            try:
                # Check if item exists
                item_query = select(KnowledgeBaseItem).where(
                    and_(
                        KnowledgeBaseItem.id == item_id,
                        KnowledgeBaseItem.is_active == True
                    )
                )
                item_result = await db.execute(item_query)
                item = item_result.scalar_one_or_none()

                if item:
                    progress = await workflow_service.get_processing_progress(item_id)
                    progress_results.append(progress)
                else:
                    progress_results.append({
                        "item_id": item_id,
                        "error": "Item not found"
                    })

            except Exception as item_error:
                logger.error(f"Error getting progress for item {item_id}: {item_error}")
                progress_results.append({
                    "item_id": item_id,
                    "error": str(item_error)
                })

        return {
            "batch_progress": progress_results,
            "total_items": len(item_ids),
            "successful_queries": len([p for p in progress_results if "error" not in p])
        }

    except Exception as e:
        logger.error(f"Error getting batch progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch progress: {str(e)}")


@router.get("/progress/active")
async def get_active_processing_progress(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of active items to return"),
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get progress for all currently active processing items.

    Returns items that are currently being processed, ordered by most recent activity.
    """
    try:
        # Get items with active processing phases
        active_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.processing_phase != "completed",
                KnowledgeBaseItem.processing_phase != "not_started"
            )
        ).order_by(desc(KnowledgeBaseItem.phase_started_at)).limit(limit)

        active_result = await db.execute(active_query)
        active_items = active_result.scalars().all()

        active_progress = []
        for item in active_items:
            try:
                progress = await workflow_service.get_processing_progress(str(item.id))
                active_progress.append(progress)
            except Exception as progress_error:
                logger.error(f"Error getting progress for active item {item.id}: {progress_error}")
                continue

        return {
            "active_processing": active_progress,
            "total_active": len(active_progress),
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting active processing progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active processing progress: {str(e)}")


@router.get("/progress/summary")
async def get_processing_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a summary of processing progress across all knowledge base items.

    Provides high-level statistics about processing status and performance.
    """
    try:
        summary = {}

        # Total items count
        total_query = select(func.count()).select_from(KnowledgeBaseItem).where(
            KnowledgeBaseItem.is_active == True
        )
        total_result = await db.execute(total_query)
        summary["total_items"] = total_result.scalar() or 0

        # Processing status breakdown
        status_query = select(
            KnowledgeBaseItem.processing_phase,
            func.count(KnowledgeBaseItem.id)
        ).where(KnowledgeBaseItem.is_active == True).group_by(KnowledgeBaseItem.processing_phase)

        status_result = await db.execute(status_query)
        summary["processing_status_breakdown"] = {status: count for status, count in status_result.all()}

        # Active processing count
        active_query = select(func.count()).select_from(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.processing_phase != "completed",
                KnowledgeBaseItem.processing_phase != "not_started"
            )
        )
        active_result = await db.execute(active_query)
        summary["currently_processing"] = active_result.scalar() or 0

        # Average processing times by phase
        avg_time_query = select(
            KnowledgeBaseProcessingPhase.phase_name,
            func.avg(KnowledgeBaseProcessingPhase.processing_duration_ms),
            func.count(KnowledgeBaseProcessingPhase.id)
        ).where(
            and_(
                KnowledgeBaseProcessingPhase.processing_duration_ms.isnot(None),
                KnowledgeBaseProcessingPhase.status == "completed"
            )
        ).group_by(KnowledgeBaseProcessingPhase.phase_name)

        avg_time_result = await db.execute(avg_time_query)
        summary["average_processing_times_ms"] = {
            phase: {"avg_time_ms": float(avg_time) if avg_time else None, "sample_count": count}
            for phase, avg_time, count in avg_time_result.all()
        }

        # Recent processing activity (last 24 hours)
        from datetime import timedelta
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_query = select(func.count()).select_from(KnowledgeBaseProcessingPhase).where(
            KnowledgeBaseProcessingPhase.created_at >= twenty_four_hours_ago
        )
        recent_result = await db.execute(recent_query)
        summary["processing_phases_last_24h"] = recent_result.scalar() or 0

        # Overall completion rate
        completed_query = select(func.count()).select_from(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.processing_phase == "completed"
            )
        )
        completed_result = await db.execute(completed_query)
        completed_count = completed_result.scalar() or 0

        if summary["total_items"] > 0:
            summary["overall_completion_rate"] = (completed_count / summary["total_items"]) * 100.0
        else:
            summary["overall_completion_rate"] = 0.0

        return summary

    except Exception as e:
        logger.error(f"Error getting processing summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing summary: {str(e)}")


# Workflow Settings Endpoints

# Workflow Settings Endpoints

@router.get("/workflow-settings/defaults")
async def get_default_workflow_settings(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get default workflow settings.

    Returns system defaults if no user defaults are set.
    """
    try:
        # Try to get user default first (only if user_id is a valid UUID)
        user_id = current_user.get("id")
        if user_id and len(user_id) >= 32:  # Check if it's a valid UUID-like string
            try:
                user_default_query = select(KnowledgeBaseWorkflowSettings).where(
                    and_(
                        KnowledgeBaseWorkflowSettings.user_id == user_id,
                        KnowledgeBaseWorkflowSettings.is_default == True
                    )
                )
                user_result = await db.execute(user_default_query)
                user_default = user_result.scalar_one_or_none()

                if user_default:
                    return user_default.to_dict()
            except Exception as user_query_error:
                logger.warning(f"Error querying user defaults for {user_id}: {user_query_error}")
                # Continue to system defaults

        # Fall back to system default
        system_default_query = select(KnowledgeBaseWorkflowSettings).where(
            KnowledgeBaseWorkflowSettings.is_system_default == True
        )
        system_result = await db.execute(system_default_query)
        system_default = system_result.scalar_one_or_none()

        if system_default:
            return system_default.to_dict()

        # Return hardcoded defaults if no database defaults exist
        return {
            "phase_models": KnowledgeBaseWorkflowSettings.get_default_phase_models(),
            "phase_settings": KnowledgeBaseWorkflowSettings.get_default_phase_settings(),
            "global_settings": KnowledgeBaseWorkflowSettings.get_default_global_settings()
        }

    except Exception as e:
        logger.error(f"Error getting default workflow settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get default workflow settings: {str(e)}")


@router.get("/workflow-settings")
async def list_workflow_settings(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all workflow settings profiles.

    Returns both user-specific and system-wide settings.
    """
    try:
        # Get all settings (user-specific and system)
        query = select(KnowledgeBaseWorkflowSettings).order_by(
            desc(KnowledgeBaseWorkflowSettings.is_default),
            desc(KnowledgeBaseWorkflowSettings.is_system_default),
            desc(KnowledgeBaseWorkflowSettings.updated_at)
        )

        result = await db.execute(query)
        settings_list = result.scalars().all()

        return {
            "settings": [settings.to_dict() for settings in settings_list],
            "total": len(settings_list)
        }

    except Exception as e:
        logger.error(f"Error listing workflow settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflow settings: {str(e)}")


@router.post("/workflow-settings")
async def create_workflow_settings(
    settings_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create new workflow settings profile.

    Supports creating user-specific or system-wide settings.
    """
    try:
        # Validate required fields
        required_fields = ["settings_name"]
        for field in required_fields:
            if field not in settings_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field missing: {field}"
                )

        # Generate UUID for new settings
        settings_id = str(uuid.uuid4())

        # Prepare settings data with defaults
        now = datetime.utcnow()
        settings_dict = {
            "id": settings_id,
            "user_id": settings_data.get("user_id"),
            "settings_name": settings_data["settings_name"],
            "is_default": settings_data.get("is_default", False),
            "is_system_default": settings_data.get("is_system_default", False),
            "phase_models": settings_data.get("phase_models", KnowledgeBaseWorkflowSettings.get_default_phase_models()),
            "phase_settings": settings_data.get("phase_settings", KnowledgeBaseWorkflowSettings.get_default_phase_settings()),
            "global_settings": settings_data.get("global_settings", KnowledgeBaseWorkflowSettings.get_default_global_settings()),
            "usage_count": 0,
            "last_used_at": None,
            "created_at": now,
            "updated_at": now
        }

        # If this is set as default, unset other defaults for this user
        if settings_dict["is_default"] and settings_dict["user_id"]:
            await db.execute(
                update(KnowledgeBaseWorkflowSettings).where(
                    and_(
                        KnowledgeBaseWorkflowSettings.user_id == settings_dict["user_id"],
                        KnowledgeBaseWorkflowSettings.is_default == True
                    )
                ).values(is_default=False)
            )

        # If this is set as system default, unset other system defaults
        if settings_dict["is_system_default"]:
            await db.execute(
                update(KnowledgeBaseWorkflowSettings).where(
                    KnowledgeBaseWorkflowSettings.is_system_default == True
                ).values(is_system_default=False)
            )

        # Insert new settings
        await db.execute(
            insert(KnowledgeBaseWorkflowSettings).values(**settings_dict)
        )

        await db.commit()

        logger.info(f"Created workflow settings {settings_id} by user {current_user.get('id')}")

        return {
            "message": "Workflow settings created successfully",
            "settings_id": settings_id,
            "settings": settings_dict
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create workflow settings: {str(e)}")


@router.get("/workflow-settings/{settings_id}")
async def get_workflow_settings(
    settings_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get specific workflow settings profile by ID.
    """
    try:
        query = select(KnowledgeBaseWorkflowSettings).where(
            KnowledgeBaseWorkflowSettings.id == settings_id
        )

        result = await db.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            raise HTTPException(status_code=404, detail="Workflow settings not found")

        return settings.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow settings: {str(e)}")


@router.put("/workflow-settings/{settings_id}")
async def update_workflow_settings(
    settings_id: str,
    updates: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update workflow settings profile.

    Allows updating phase models, phase settings, and global settings.
    """
    try:
        # Check if settings exist
        query = select(KnowledgeBaseWorkflowSettings).where(
            KnowledgeBaseWorkflowSettings.id == settings_id
        )
        result = await db.execute(query)
        existing_settings = result.scalar_one_or_none()

        if not existing_settings:
            raise HTTPException(status_code=404, detail="Workflow settings not found")

        # Prepare update data
        update_data = updates.copy()
        update_data["updated_at"] = datetime.utcnow()

        # If setting as default, unset other defaults for this user
        if update_data.get("is_default") and existing_settings.user_id:
            await db.execute(
                update(KnowledgeBaseWorkflowSettings).where(
                    and_(
                        KnowledgeBaseWorkflowSettings.user_id == existing_settings.user_id,
                        KnowledgeBaseWorkflowSettings.id != settings_id,
                        KnowledgeBaseWorkflowSettings.is_default == True
                    )
                ).values(is_default=False)
            )

        # If setting as system default, unset other system defaults
        if update_data.get("is_system_default"):
            await db.execute(
                update(KnowledgeBaseWorkflowSettings).where(
                    and_(
                        KnowledgeBaseWorkflowSettings.id != settings_id,
                        KnowledgeBaseWorkflowSettings.is_system_default == True
                    )
                ).values(is_system_default=False)
            )

        # Update settings
        await db.execute(
            update(KnowledgeBaseWorkflowSettings)
            .where(KnowledgeBaseWorkflowSettings.id == settings_id)
            .values(**update_data)
        )

        await db.commit()

        logger.info(f"Updated workflow settings {settings_id} by user {current_user.get('id')}")

        return {
            "message": "Workflow settings updated successfully",
            "settings_id": settings_id,
            "updated_fields": list(updates.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update workflow settings: {str(e)}")


@router.delete("/workflow-settings/{settings_id}")
async def delete_workflow_settings(
    settings_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete workflow settings profile.

    Cannot delete system default settings.
    """
    try:
        # Check if settings exist
        query = select(KnowledgeBaseWorkflowSettings).where(
            KnowledgeBaseWorkflowSettings.id == settings_id
        )
        result = await db.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            raise HTTPException(status_code=404, detail="Workflow settings not found")

        # Prevent deletion of system default settings
        if settings.is_system_default:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete system default settings"
            )

        # Delete settings
        await db.execute(
            update(KnowledgeBaseWorkflowSettings)
            .where(KnowledgeBaseWorkflowSettings.id == settings_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )

        await db.commit()

        logger.info(f"Deleted workflow settings {settings_id} by user {current_user.get('id')}")

        return {
            "message": "Workflow settings deleted successfully",
            "settings_id": settings_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete workflow settings: {str(e)}")


@router.post("/workflow-settings/{settings_id}/activate")
async def activate_workflow_settings(
    settings_id: str,
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Activate workflow settings for the current session.

    This loads the specified settings into the workflow service for immediate use.
    """
    try:
        # Load settings from database
        await workflow_service.load_workflow_settings(settings_id)

        # Update usage count
        await db.execute(
            update(KnowledgeBaseWorkflowSettings)
            .where(KnowledgeBaseWorkflowSettings.id == settings_id)
            .values(
                usage_count=KnowledgeBaseWorkflowSettings.usage_count + 1,
                last_used_at=datetime.utcnow()
            )
        )

        await db.commit()

        logger.info(f"Activated workflow settings {settings_id} by user {current_user.get('id')}")

        return {
            "message": "Workflow settings activated successfully",
            "settings_id": settings_id,
            "current_settings": {
                "phase_models": workflow_service.phase_models,
                "phase_settings": workflow_service.phase_settings,
                "global_settings": workflow_service.global_settings
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating workflow settings: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to activate workflow settings: {str(e)}")


@router.delete("/items/{item_id}/cancel")
async def cancel_item_processing(
    item_id: str,
    reason: str = Query("Cancelled by user", description="Reason for cancellation"),
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cancel processing for a knowledge base item.

    This endpoint allows users to cancel ongoing processing of a knowledge base item.
    The cancellation will be detected by the running workflow and processing will stop gracefully.
    """
    try:
        # Check if item exists
        item_query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Knowledge base item not found")

        # Check current processing status
        if item.processing_phase in ["completed", "cancelled"]:
            return {
                "message": f"Item processing is already {item.processing_phase}",
                "item_id": item_id,
                "current_status": item.processing_phase,
                "cancelled_at": item.phase_completed_at.isoformat() if item.phase_completed_at else None
            }

        if item.processing_phase == "not_started":
            raise HTTPException(
                status_code=400,
                detail="Item processing has not started yet"
            )

        # Get current processing phase details for better feedback
        phase_query = select(KnowledgeBaseProcessingPhase).where(
            and_(
                KnowledgeBaseProcessingPhase.item_id == item_id,
                KnowledgeBaseProcessingPhase.status == "running"
            )
        ).order_by(desc(KnowledgeBaseProcessingPhase.started_at))
        phase_result = await db.execute(phase_query)
        current_phase = phase_result.scalar_one_or_none()

        # Cancel processing in workflow service
        await workflow_service.cancel_item_processing(item_id, reason)

        # Update item status in database
        await db.execute(
            update(KnowledgeBaseItem)
            .where(KnowledgeBaseItem.id == item_id)
            .values(
                processing_phase="cancelled",
                phase_completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                reprocessing_reason=reason
            )
        )

        await db.commit()

        logger.info(f"Item {item_id} processing cancelled by user {current_user.get('id')}: {reason}")

        return {
            "message": "Item processing cancelled successfully",
            "item_id": item_id,
            "reason": reason,
            "cancelled_at": datetime.utcnow().isoformat(),
            "previous_phase": item.processing_phase,
            "current_phase_details": {
                "phase_name": current_phase.phase_name if current_phase else None,
                "progress_percentage": current_phase.progress_percentage if current_phase else None,
                "started_at": current_phase.started_at.isoformat() if current_phase and current_phase.started_at else None
            } if current_phase else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling item processing: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel processing: {str(e)}")


@router.delete("/processing/batch")
async def cancel_batch_processing(
    item_ids: List[str] = Query(..., description="List of item IDs to cancel"),
    reason: str = Query("Batch cancellation by user", description="Reason for cancellation"),
    db: AsyncSession = Depends(get_db),
    workflow_service: KnowledgeBaseWorkflowService = Depends(get_workflow_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cancel processing for multiple knowledge base items.

    This endpoint allows batch cancellation of multiple processing items.
    Returns detailed results for each item.
    """
    try:
        if not item_ids:
            raise HTTPException(status_code=400, detail="No item IDs provided")

        if len(item_ids) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 items can be cancelled at once")

        cancelled_items = []
        failed_items = []
        already_cancelled = []

        for item_id in item_ids:
            try:
                # Check if item exists
                item_query = select(KnowledgeBaseItem).where(
                    and_(
                        KnowledgeBaseItem.id == item_id,
                        KnowledgeBaseItem.is_active == True
                    )
                )
                item_result = await db.execute(item_query)
                item = item_result.scalar_one_or_none()

                if not item:
                    failed_items.append({"item_id": item_id, "error": "Item not found"})
                    continue

                # Check current processing status
                if item.processing_phase == "cancelled":
                    already_cancelled.append({
                        "item_id": item_id,
                        "status": "already_cancelled",
                        "cancelled_at": item.phase_completed_at.isoformat() if item.phase_completed_at else None
                    })
                    continue

                if item.processing_phase == "completed":
                    failed_items.append({
                        "item_id": item_id,
                        "error": "Item processing already completed"
                    })
                    continue

                if item.processing_phase == "not_started":
                    failed_items.append({
                        "item_id": item_id,
                        "error": "Item processing has not started yet"
                    })
                    continue

                # Get current processing phase details
                phase_query = select(KnowledgeBaseProcessingPhase).where(
                    and_(
                        KnowledgeBaseProcessingPhase.item_id == item_id,
                        KnowledgeBaseProcessingPhase.status == "running"
                    )
                ).order_by(desc(KnowledgeBaseProcessingPhase.started_at))
                phase_result = await db.execute(phase_query)
                current_phase = phase_result.scalar_one_or_none()

                # Cancel processing
                await workflow_service.cancel_item_processing(item_id, reason)

                # Update item status
                await db.execute(
                    update(KnowledgeBaseItem)
                    .where(KnowledgeBaseItem.id == item_id)
                    .values(
                        processing_phase="cancelled",
                        phase_completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        reprocessing_reason=reason
                    )
                )

                cancelled_items.append({
                    "item_id": item_id,
                    "previous_phase": item.processing_phase,
                    "current_phase_details": {
                        "phase_name": current_phase.phase_name if current_phase else None,
                        "progress_percentage": current_phase.progress_percentage if current_phase else None,
                        "started_at": current_phase.started_at.isoformat() if current_phase and current_phase.started_at else None
                    } if current_phase else None
                })

            except Exception as item_error:
                logger.error(f"Error cancelling item {item_id}: {item_error}")
                failed_items.append({"item_id": item_id, "error": str(item_error)})

        await db.commit()

        logger.info(f"Batch cancellation completed by user {current_user.get('id')}: {len(cancelled_items)} cancelled, {len(failed_items)} failed, {len(already_cancelled)} already cancelled")

        return {
            "message": f"Batch cancellation completed: {len(cancelled_items)} cancelled, {len(failed_items)} failed, {len(already_cancelled)} already cancelled",
            "cancelled_items": cancelled_items,
            "failed_items": failed_items,
            "already_cancelled_items": already_cancelled,
            "total_requested": len(item_ids),
            "reason": reason,
            "cancelled_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch cancellation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch processing: {str(e)}")


# Bookmarks-specific endpoints

@router.get("/bookmarks")
async def list_bookmarks(
    db: AsyncSession = Depends(get_db),
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    # Sorting parameters
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    # Filtering parameters
    has_been_processed: Optional[bool] = Query(None, description="Filter by processing status"),
    # User authentication
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List raw bookmark data with pagination and sorting.

    Returns a paginated list of bookmark items that may or may not have been
    processed into knowledge base items. This endpoint provides access to the
    underlying bookmark data including URLs, tweet IDs, and metadata.
    """
    try:
        # Build base query for bookmarks
        query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.source_type.in_([
                    "twitter_bookmark",  # Raw bookmarks
                    "twitter_bookmark_auto"  # Auto-discovered bookmarks
                ])
            )
        )

        # Apply processing status filter
        if has_been_processed is not None:
            if has_been_processed:
                # Only show bookmarks that have been processed
                query = query.where(
                    and_(
                        KnowledgeBaseItem.processing_phase != "not_started",
                        KnowledgeBaseItem.processed_at.isnot(None)
                    )
                )
            else:
                # Only show bookmarks that haven't been processed
                query = query.where(
                    or_(
                        KnowledgeBaseItem.processing_phase == "not_started",
                        KnowledgeBaseItem.processed_at.is_(None)
                    )
                )

        # Apply sorting
        sort_column = getattr(KnowledgeBaseItem, sort_by, KnowledgeBaseItem.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Get total count for pagination
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * limit).limit(limit)

        # Execute query
        result = await db.execute(query)
        bookmarks = result.scalars().all()

        # Format results with bookmark-specific data
        bookmarks_list = []
        for bookmark in bookmarks:
            bookmark_dict = bookmark.to_dict()

            # Add bookmark-specific fields
            bookmark_metadata = bookmark_dict.get("metadata", {})
            bookmark_dict.update({
                "bookmark_url": bookmark_metadata.get("bookmark_url"),
                "tweet_id": bookmark_metadata.get("tweet_id"),
                "author_username": bookmark_metadata.get("author_username"),
                "author_name": bookmark_metadata.get("author_name"),
                "likes": bookmark_metadata.get("likes", 0),
                "retweets": bookmark_metadata.get("retweets", 0),
                "replies": bookmark_metadata.get("replies", 0),
                "hashtags": bookmark_metadata.get("hashtags", []),
                "mentions": bookmark_metadata.get("mentions", []),
                "bookmarked_at": bookmark_metadata.get("bookmarked_at"),
                "auto_discovered": bookmark_metadata.get("auto_discovered", False),
                "is_thread": bookmark_metadata.get("is_thread", False),
                "thread_root_id": bookmark_metadata.get("thread_root_id"),
                "thread_position": bookmark_metadata.get("thread_position")
            })

            bookmarks_list.append(bookmark_dict)

        return {
            "bookmarks": bookmarks_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if total_count > 0 else 0
            },
            "total_count": total_count,
            "filters_applied": {
                "has_been_processed": has_been_processed
            }
        }

    except Exception as e:
        logger.error(f"Error listing bookmarks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list bookmarks: {str(e)}")


@router.get("/bookmarks/{item_id}")
async def get_bookmark_details(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed information for a specific bookmark.

    Includes all bookmark metadata, processing status, and any associated
    knowledge base item data if the bookmark has been processed.
    """
    try:
        # Get bookmark item
        query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.source_type.in_([
                    "twitter_bookmark",
                    "twitter_bookmark_auto"
                ])
            )
        )
        result = await db.execute(query)
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")

        # Get processing phases if any
        phases_query = select(KnowledgeBaseProcessingPhase).where(
            KnowledgeBaseProcessingPhase.item_id == item_id
        ).order_by(desc(KnowledgeBaseProcessingPhase.created_at))
        phases_result = await db.execute(phases_query)
        phases = phases_result.scalars().all()

        # Get categories if processed
        categories_query = select(KnowledgeBaseCategory).where(
            KnowledgeBaseCategory.item_id == item_id
        )
        categories_result = await db.execute(categories_query)
        categories = categories_result.scalars().all()

        # Get media assets if any
        media_query = select(KnowledgeBaseMedia).where(
            KnowledgeBaseMedia.item_id == item_id
        )
        media_result = await db.execute(media_query)
        media_assets = media_result.scalars().all()

        # Format bookmark data
        bookmark_dict = bookmark.to_dict()
        bookmark_metadata = bookmark_dict.get("metadata", {})

        detailed_bookmark = {
            "id": bookmark_dict["id"],
            "source_type": bookmark_dict["source_type"],
            "content_type": bookmark_dict["content_type"],
            "title": bookmark_dict["title"],
            "summary": bookmark_dict["summary"],
            "full_content": bookmark_dict["full_content"],
            "created_at": bookmark_dict["created_at"],
            "updated_at": bookmark_dict["updated_at"],
            "processed_at": bookmark_dict["processed_at"],
            "processing_phase": bookmark_dict["processing_phase"],
            "is_active": bookmark_dict["is_active"],

            # Bookmark-specific data
            "bookmark_url": bookmark_metadata.get("bookmark_url"),
            "tweet_id": bookmark_metadata.get("tweet_id"),
            "author_username": bookmark_metadata.get("author_username"),
            "author_name": bookmark_metadata.get("author_name"),
            "likes": bookmark_metadata.get("likes", 0),
            "retweets": bookmark_metadata.get("retweets", 0),
            "replies": bookmark_metadata.get("replies", 0),
            "hashtags": bookmark_metadata.get("hashtags", []),
            "mentions": bookmark_metadata.get("mentions", []),
            "bookmarked_at": bookmark_metadata.get("bookmarked_at"),
            "auto_discovered": bookmark_metadata.get("auto_discovered", False),
            "is_thread": bookmark_metadata.get("is_thread", False),
            "thread_root_id": bookmark_metadata.get("thread_root_id"),
            "thread_position": bookmark_metadata.get("thread_position"),

            # Processing information
            "processing_phases": [phase.to_dict() for phase in phases],
            "categories": [cat.to_dict() for cat in categories],
            "media_assets": [media.to_dict() for media in media_assets],
            "has_been_processed": bookmark_dict["processing_phase"] != "not_started" and bookmark_dict["processed_at"] is not None
        }

        return detailed_bookmark

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bookmark details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bookmark details: {str(e)}")


@router.post("/bookmarks/{item_id}/process")
async def process_bookmark(
    item_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process a bookmark into a knowledge base item.

    This endpoint triggers the knowledge base workflow for a specific bookmark,
    converting it from raw bookmark data into a processed knowledge base item.
    """
    try:
        # Check if bookmark exists
        query = select(KnowledgeBaseItem).where(
            and_(
                KnowledgeBaseItem.id == item_id,
                KnowledgeBaseItem.is_active == True,
                KnowledgeBaseItem.source_type.in_([
                    "twitter_bookmark",
                    "twitter_bookmark_auto"
                ])
            )
        )
        result = await db.execute(query)
        bookmark = result.scalar_one_or_none()

        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")

        # Check if already processed
        if bookmark.processing_phase != "not_started":
            return {
                "message": f"Bookmark is already being processed or has been processed",
                "current_phase": bookmark.processing_phase,
                "processed_at": bookmark.processed_at.isoformat() if bookmark.processed_at else None
            }

        # Create a new workflow service instance for the background task
        # This avoids the async context issue by creating a fresh service
        from app.services.knowledge_base_workflow_service import KnowledgeBaseWorkflowService
        from app.services.ollama_client import ollama_client
        from app.services.vision_ai_service import vision_ai_service
        from app.services.semantic_processing_service import semantic_processing_service
        from app.services.media_download_service import media_download_service
        from app.connectors.social_media import TwitterConnector
        from app.config import settings

        # Initialize services if needed
        await semantic_processing_service.initialize()
        await vision_ai_service.initialize()

        from app.connectors.base import ConnectorConfig
        from app.connectors.base import ConnectorType

        # Use actual X API credentials from settings
        credentials = {}
        if settings.x_bearer_token:
            credentials["bearer_token"] = settings.x_bearer_token
        if settings.x_api_key and settings.x_api_secret:
            credentials["api_key"] = settings.x_api_key
            credentials["api_secret"] = settings.x_api_secret

        config = ConnectorConfig(
            name="twitter_connector",
            connector_type=ConnectorType.SOCIAL_MEDIA,
            source_config={},
            credentials=credentials
        )
        twitter_connector = TwitterConnector(config)

        # Create workflow service with fresh database session
        workflow_service = KnowledgeBaseWorkflowService(
            db_session=None,  # Will create its own session
            ollama_client=ollama_client,
            vision_service=vision_ai_service,
            semantic_service=semantic_processing_service,
            twitter_connector=twitter_connector,
            media_download_service=media_download_service
        )

        # Start processing in background with the new service instance
        background_tasks.add_task(workflow_service.process_item, item_id)

        # Update bookmark status to indicate processing has started
        await db.execute(
            update(KnowledgeBaseItem)
            .where(KnowledgeBaseItem.id == item_id)
            .values(
                processing_phase="fetch_bookmarks",  # Start with first phase
                phase_started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )

        await db.commit()

        logger.info(f"Started processing bookmark {item_id} by user {current_user.get('id')}")

        return {
            "message": "Bookmark processing started successfully",
            "item_id": item_id,
            "processing_started_at": datetime.utcnow().isoformat(),
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing bookmark: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process bookmark: {str(e)}")