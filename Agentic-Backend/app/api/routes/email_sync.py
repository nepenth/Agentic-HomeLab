"""
Email Synchronization API Routes

Provides REST API endpoints for managing email account synchronization,
monitoring sync status, and controlling email data ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException, status as status_codes, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.api.dependencies import get_db_session, get_current_user
from app.services.email_sync_service import email_sync_service
from app.services.email_connectors.base_connector import SyncType
from app.services.email_embedding_service import email_embedding_service
from app.utils.logging import get_logger
from app.db.models.user import User

logger = get_logger("email_sync_api")
router = APIRouter()


@router.get("/defaults")
async def get_sync_defaults():
    """
    Get default sync configuration options and presets.

    Returns system defaults, available options, and recommended configurations
    for different use cases. These can be customized per email account.
    """
    from app.config import settings

    return {
        "system_defaults": {
            "sync_days_back": settings.email_sync_default_days_back,
            "max_emails_limit": settings.email_sync_default_max_emails,
            "batch_size": settings.email_sync_batch_size
        },
        "configuration_options": {
            "sync_days_back": {
                "options": [
                    {"value": 30, "label": "1 Month", "description": "Recent emails only"},
                    {"value": 90, "label": "3 Months", "description": "Quarterly view"},
                    {"value": 180, "label": "6 Months", "description": "Semi-annual"},
                    {"value": 365, "label": "1 Year", "description": "Annual (recommended)"},
                    {"value": 730, "label": "2 Years", "description": "Extended history"},
                    {"value": None, "label": "All Time", "description": "Complete mailbox"}
                ],
                "description": "How far back to sync emails from today"
            },
            "max_emails_limit": {
                "options": [
                    {"value": 500, "label": "500 emails", "description": "Minimal sync"},
                    {"value": 1000, "label": "1,000 emails", "description": "Light usage"},
                    {"value": 2500, "label": "2,500 emails", "description": "Moderate usage"},
                    {"value": 5000, "label": "5,000 emails", "description": "Standard (recommended)"},
                    {"value": 10000, "label": "10,000 emails", "description": "Heavy usage"},
                    {"value": None, "label": "Unlimited", "description": "No email limit"}
                ],
                "description": "Maximum number of emails to sync"
            }
        },
        "presets": {
            "quick_start": {
                "name": "Quick Start",
                "sync_days_back": 90,
                "max_emails_limit": 1000,
                "description": "Fast setup with recent emails",
                "estimated_time": "5-10 minutes",
                "use_case": "Testing or immediate productivity"
            },
            "balanced": {
                "name": "Balanced (Recommended)",
                "sync_days_back": 365,
                "max_emails_limit": 5000,
                "description": "Good balance of coverage and performance",
                "estimated_time": "15-30 minutes",
                "use_case": "Most users and typical workflows"
            },
            "comprehensive": {
                "name": "Comprehensive",
                "sync_days_back": 730,
                "max_emails_limit": 10000,
                "description": "Extensive email history",
                "estimated_time": "30-60 minutes",
                "use_case": "Research, compliance, or complete archive"
            },
            "unlimited": {
                "name": "Complete Archive",
                "sync_days_back": None,
                "max_emails_limit": None,
                "description": "Sync entire mailbox",
                "estimated_time": "1-3 hours",
                "use_case": "Full historical analysis or migration"
            }
        }
    }


class EmailAccountRequest(BaseModel):
    """Request for creating/updating an email account."""
    account_type: str = Field(..., description="Email provider type (gmail, outlook, imap)")
    email_address: str = Field(..., description="Email address")
    display_name: Optional[str] = Field(None, description="Display name for account")
    auth_credentials: Dict[str, Any] = Field(..., description="Authentication credentials")

    # Per-account sync configuration
    sync_interval_minutes: int = Field(15, description="Sync interval in minutes")
    auto_sync_enabled: bool = Field(True, description="Enable automatic synchronization")
    sync_days_back: Optional[int] = Field(None, description="Days back to sync (None = use system default)")
    max_emails_limit: Optional[int] = Field(None, description="Maximum emails to sync (None = use system default)")

    # Additional sync settings (folders, filters, etc.)
    sync_settings: Dict[str, Any] = Field(default_factory=dict, description="Additional sync configuration")


class SyncRequest(BaseModel):
    """Request for manual email synchronization."""
    account_ids: Optional[List[str]] = Field(None, description="Specific accounts to sync (None = all)")
    sync_type: str = Field("incremental", description="Type of sync (full, incremental)")
    force_sync: bool = Field(False, description="Force sync even if recently synced")
    # Sync limits for this request
    sync_days_back: Optional[int] = Field(None, description="Days back to sync (overrides account default)")
    max_emails_limit: Optional[int] = Field(None, description="Maximum emails to sync (overrides account default)")


class EmailAccountUpdateRequest(BaseModel):
    """Request for updating an email account."""
    display_name: Optional[str] = Field(None, description="Display name for account")
    sync_interval_minutes: Optional[int] = Field(None, description="Sync interval in minutes")
    auto_sync_enabled: Optional[bool] = Field(None, description="Enable automatic synchronization")
    sync_days_back: Optional[int] = Field(None, description="Days back to sync")
    max_emails_limit: Optional[int] = Field(None, description="Maximum emails to sync")
    sync_settings: Optional[Dict[str, Any]] = Field(None, description="Additional sync configuration")


class EmbeddingRequest(BaseModel):
    """Request for generating email embeddings."""
    user_id: Optional[int] = Field(None, description="Process embeddings for specific user")
    force_regenerate: bool = Field(False, description="Regenerate existing embeddings")


@router.post("/accounts")
async def create_email_account(
    request: EmailAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new email account for synchronization.

    This endpoint allows users to add email accounts from various providers
    with their authentication credentials and sync preferences.
    """
    try:
        # Import here to avoid circular imports
        from app.db.models.email import EmailAccount

        # Import settings to get system defaults
        from app.config import settings

        # Build comprehensive sync settings combining user preferences with system defaults
        sync_settings = {
            # Per-account configurable limits
            "sync_days_back": request.sync_days_back or settings.email_sync_default_days_back,
            "max_emails_limit": request.max_emails_limit or settings.email_sync_default_max_emails,

            # System settings (not user-configurable)
            "batch_size": settings.email_sync_batch_size,

            # Default sync preferences
            "folders_to_sync": ["INBOX"],
            "sync_attachments": True,
            "max_attachment_size_mb": 25,
            "include_spam": False,
            "include_trash": False,

            # Merge any additional settings from request
            **request.sync_settings
        }

        # Create email account
        account = EmailAccount(
            user_id=current_user.id,
            account_type=request.account_type,
            email_address=request.email_address,
            display_name=request.display_name or request.email_address,
            auth_type=request.auth_credentials.get("auth_type", "oauth2"),
            auth_credentials=request.auth_credentials,
            sync_settings=sync_settings,
            sync_interval_minutes=request.sync_interval_minutes,
            auto_sync_enabled=request.auto_sync_enabled
        )

        db.add(account)
        await db.commit()
        await db.refresh(account)

        logger.info(f"Created email account {account.id} for user {current_user.id}")

        return {
            "account_id": str(account.id),
            "email_address": account.email_address,
            "account_type": account.account_type,
            "sync_status": account.sync_status,
            "auto_sync_enabled": account.auto_sync_enabled,
            "created_at": account.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create email account: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email account"
        )


@router.get("/accounts")
async def get_email_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all email accounts for the current user.

    Returns a list of configured email accounts with their sync status
    and configuration details.
    """
    try:
        from sqlalchemy import select
        from app.db.models.email import EmailAccount

        query = select(EmailAccount).where(EmailAccount.user_id == current_user.id)
        result = await db.execute(query)
        accounts = result.scalars().all()

        account_list = []
        for account in accounts:
            sync_settings = account.sync_settings or {}
            account_data = {
                "account_id": str(account.id),
                "email_address": account.email_address,
                "display_name": account.display_name,
                "account_type": account.account_type,
                "sync_status": account.sync_status,
                "auto_sync_enabled": account.auto_sync_enabled,
                "sync_interval_minutes": account.sync_interval_minutes,
                "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
                "next_sync_at": account.next_sync_at.isoformat() if account.next_sync_at else None,
                "total_emails_synced": account.total_emails_synced or 0,
                "last_error": account.last_error,
                "created_at": account.created_at.isoformat(),

                # Per-account sync configuration
                "sync_configuration": {
                    "sync_days_back": sync_settings.get("sync_days_back"),
                    "max_emails_limit": sync_settings.get("max_emails_limit"),
                    "folders_to_sync": sync_settings.get("folders_to_sync", ["INBOX"]),
                    "sync_attachments": sync_settings.get("sync_attachments", True),
                    "include_spam": sync_settings.get("include_spam", False),
                    "include_trash": sync_settings.get("include_trash", False)
                }
            }
            account_list.append(account_data)

        return {"accounts": account_list, "total": len(account_list)}

    except Exception as e:
        logger.error(f"Failed to get email accounts: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email accounts"
        )


@router.delete("/accounts/{account_id}")
async def delete_email_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete an email account and all associated data.

    This will remove the account configuration and all synced emails,
    embeddings, and tasks associated with the account.
    """
    try:
        from sqlalchemy import select, delete
        from app.db.models.email import EmailAccount

        # Verify account ownership
        query = select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id
        )
        result = await db.execute(query)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )

        # Delete account (cascading deletes will handle emails, etc.)
        await db.delete(account)
        await db.commit()

        logger.info(f"Deleted email account {account_id} for user {current_user.id}")
        return {"message": "Email account deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete email account: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email account"
        )


@router.put("/accounts/{account_id}")
async def update_email_account(
    account_id: str,
    request: EmailAccountUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an email account configuration.

    Allows updating display name, sync settings, auto sync toggle, and sync interval.
    """
    try:
        from sqlalchemy import select, update
        from app.db.models.email import EmailAccount

        # Verify account exists and belongs to user
        account_query = select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.user_id == current_user.id
        )
        result = await db.execute(account_query)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )

        # Build update data
        update_data = {}
        if request.display_name is not None:
            update_data["display_name"] = request.display_name
        if request.sync_interval_minutes is not None:
            update_data["sync_interval_minutes"] = request.sync_interval_minutes
        if request.auto_sync_enabled is not None:
            update_data["auto_sync_enabled"] = request.auto_sync_enabled

        # Handle sync settings updates (merge with existing settings)
        if any(field is not None for field in [request.sync_days_back, request.max_emails_limit, request.sync_settings]):
            current_settings = account.sync_settings or {}

            # Update specific sync limit fields
            if request.sync_days_back is not None:
                current_settings["sync_days_back"] = request.sync_days_back
            if request.max_emails_limit is not None:
                current_settings["max_emails_limit"] = request.max_emails_limit

            # Merge any additional sync settings
            if request.sync_settings is not None:
                current_settings.update(request.sync_settings)

            update_data["sync_settings"] = current_settings

        if update_data:
            update_data["updated_at"] = datetime.now()

            await db.execute(
                update(EmailAccount)
                .where(EmailAccount.id == account_id)
                .values(**update_data)
            )
            await db.commit()

        logger.info(f"Updated email account {account_id} for user {current_user.id}")
        return {"message": "Email account updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update email account: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email account"
        )


@router.post("/sync")
async def trigger_email_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Trigger manual email synchronization.

    Initiates email sync for specified accounts or all user accounts.
    Sync operations run in the background and can be monitored via status endpoints.
    """
    try:
        # Convert sync type string to enum
        sync_type = SyncType.FULL if request.sync_type.lower() == "full" else SyncType.INCREMENTAL

        # Schedule sync operation in background
        if request.account_ids:
            # Sync specific accounts
            for account_id in request.account_ids:
                background_tasks.add_task(
                    email_sync_service.sync_account,
                    db, account_id, sync_type, request.force_sync
                )
        else:
            # Sync all user accounts
            background_tasks.add_task(
                email_sync_service.sync_all_accounts,
                db, current_user.id, sync_type
            )

        logger.info(f"Triggered email sync for user {current_user.id}")

        return {
            "message": "Email synchronization started",
            "sync_type": request.sync_type,
            "account_ids": request.account_ids,
            "initiated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to trigger email sync: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start email synchronization"
        )


@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get synchronization status for user's email accounts.

    Returns detailed status information including sync history,
    statistics, and any error conditions.
    """
    try:
        status = await email_sync_service.get_sync_status(db, current_user.id)
        return status

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync status"
        )


@router.post("/embeddings/generate")
async def generate_embeddings(
    request: EmbeddingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate embeddings for synced emails.

    Creates vector embeddings for email content to enable semantic search
    and intelligent email conversations.
    """
    try:
        # Determine user ID for processing
        user_id = request.user_id if request.user_id else current_user.id

        # Only allow users to generate embeddings for themselves unless admin
        if user_id != current_user.id:
            # Add admin check here if needed
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Can only generate embeddings for your own emails"
            )

        # Schedule embedding generation in background
        background_tasks.add_task(
            email_embedding_service.process_pending_emails,
            db, user_id, request.force_regenerate
        )

        logger.info(f"Triggered embedding generation for user {user_id}")

        return {
            "message": "Embedding generation started",
            "user_id": user_id,
            "force_regenerate": request.force_regenerate,
            "initiated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start embedding generation"
        )


@router.get("/emails")
async def get_synced_emails(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sender: Optional[str] = None,
    days_back: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get synced emails with filtering and pagination.

    Returns a paginated list of synced emails with optional filtering
    by search terms, category, sender, and date range.
    """
    try:
        from sqlalchemy import select, and_, desc, func
        from sqlalchemy.orm import selectinload
        from app.db.models.email import Email
        from datetime import timedelta

        # Build query
        query = select(Email).options(
            selectinload(Email.embeddings),
            selectinload(Email.attachments)
        ).where(Email.user_id == current_user.id)

        # Apply filters
        if days_back > 0:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            query = query.where(Email.received_at >= cutoff_date)

        if category:
            query = query.where(Email.category == category)

        if sender:
            query = query.where(Email.sender_email.ilike(f"%{sender}%"))

        if search:
            # Simple text search - could be enhanced with full-text search
            search_filter = and_(
                Email.subject.ilike(f"%{search}%"),
                Email.body_text.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        # Get total count
        count_query = select(func.count(Email.id)).where(query.whereclause)
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(desc(Email.received_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        emails = result.scalars().all()

        # Format response
        email_list = []
        for email in emails:
            email_list.append({
                "email_id": str(email.id),
                "subject": email.subject,
                "sender_email": email.sender_email,
                "sender_name": email.sender_name,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "category": email.category,
                "importance_score": email.importance_score,
                "is_read": email.is_read,
                "is_flagged": email.is_flagged,
                "has_attachments": email.has_attachments,
                "attachment_count": email.attachment_count,
                "snippet": email.snippet,
                "folder_path": email.folder_path,
                "labels": email.labels,
                "embeddings_generated": email.embeddings_generated,
                "tasks_generated": email.tasks_generated
            })

        return {
            "emails": email_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + limit < total_count
            },
            "filters": {
                "search": search,
                "category": category,
                "sender": sender,
                "days_back": days_back
            }
        }

    except Exception as e:
        logger.error(f"Failed to get synced emails: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve synced emails"
        )

@router.get("/models/embedding")
async def get_available_embedding_models():
    """
    Get list of available embedding models from Ollama.
    
    Returns available models with metadata including dimensions,
    performance characteristics, and the current system default.
    """
    try:
        from app.services.model_capability_service import model_capability_service
        from app.config import settings
        
        # Initialize model capability service
        await model_capability_service.initialize()
        
        # Get embedding models
        embedding_models = await model_capability_service.get_embedding_models()
        
        models_list = []
        for model in embedding_models:
            models_list.append({
                "name": model.name,
                "display_name": model.display_name or model.name,
                "description": f"Embedding model with {model.context_length} dimensions",
                "dimensions": model.context_length,
                "capabilities": model.capabilities,
                "parameter_size": getattr(model, 'parameter_size', None),
                "is_available": True
            })
        
        return {
            "models": models_list,
            "system_default": settings.default_embedding_model,
            "total_count": len(models_list)
        }
    
    except Exception as e:
        logger.error(f"Failed to get embedding models: {e}")
        # Return fallback response
        return {
            "models": [
                {
                    "name": settings.default_embedding_model,
                    "display_name": settings.default_embedding_model,
                    "description": "Default embedding model",
                    "dimensions": 1024,
                    "capabilities": [],
                    "parameter_size": None,
                    "is_available": True
                }
            ],
            "system_default": settings.default_embedding_model,
            "total_count": 1,
            "error": "Failed to fetch models from Ollama"
        }


class EmbeddingModelUpdateRequest(BaseModel):
    """Request to update embedding model for an account."""
    model_name: Optional[str] = Field(None, description="Model name (null for system default)")
    regenerate_embeddings: bool = Field(False, description="Regenerate existing embeddings")


@router.patch("/accounts/{account_id}/embedding-model")
async def update_account_embedding_model(
    account_id: UUID,
    request: EmbeddingModelUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update the embedding model for a specific email account.
    
    Allows per-account embedding model configuration. Setting model_name to null
    will use the system default model.
    """
    try:
        from app.db.models.email import EmailAccount
        from sqlalchemy import select
        
        # Get account
        result = await db.execute(
            select(EmailAccount).where(EmailAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )
        
        # Check ownership
        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this account"
            )
        
        # Update embedding model
        account.embedding_model = request.model_name
        await db.commit()
        
        logger.info(
            f"Updated embedding model for account {account_id} to "
            f"{request.model_name or 'system default'}"
        )
        
        # Optionally trigger re-embedding
        regenerate_task_id = None
        if request.regenerate_embeddings:
            from app.tasks.email_sync_tasks import regenerate_account_embeddings
            task = regenerate_account_embeddings.delay(
                str(account_id),
                request.model_name
            )
            regenerate_task_id = task.id
            logger.info(f"Scheduled re-embedding for account {account_id} with task {task.id}")

        return {
            "message": "Embedding model updated successfully",
            "account_id": str(account_id),
            "embedding_model": request.model_name or "system_default",
            "regenerate_scheduled": request.regenerate_embeddings,
            "regenerate_task_id": regenerate_task_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update embedding model: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update embedding model"
        )


@router.get("/emails/{email_id}")
async def get_email_detail(
    email_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get full email details including content, attachments, and thread context.
    
    This endpoint provides complete email information for display in the UI,
    including the ability to view full email body, download attachments,
    and see related emails in the thread.
    """
    try:
        from app.db.models.email import Email, EmailTask
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        # Get email with related data
        result = await db.execute(
            select(Email)
            .options(selectinload(Email.attachments))
            .where(Email.id == email_id)
        )
        email = result.scalar_one_or_none()
        
        if not email:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # Check ownership
        if email.user_id != current_user.id:
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this email"
            )
        
        # Get related tasks
        tasks_result = await db.execute(
            select(EmailTask).where(EmailTask.email_id == email_id)
        )
        related_tasks = tasks_result.scalars().all()
        
        # Get thread emails if thread_id exists
        thread_emails = []
        if email.thread_id:
            thread_result = await db.execute(
                select(Email)
                .where(Email.thread_id == email.thread_id)
                .order_by(Email.sent_at)
            )
            thread_emails_raw = thread_result.scalars().all()
            thread_emails = [
                {
                    "id": str(e.id),
                    "subject": e.subject,
                    "sender_email": e.sender_email,
                    "sent_at": e.sent_at.isoformat() if e.sent_at else None,
                    "is_current": e.id == email_id
                }
                for e in thread_emails_raw
            ]
        
        return {
            "email": {
                "id": str(email.id),
                "message_id": email.message_id,
                "thread_id": email.thread_id,
                "subject": email.subject,
                "sender_email": email.sender_email,
                "sender_name": email.sender_name,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "folder_path": email.folder_path,
                "labels": email.labels,
                "is_read": email.is_read,
                "is_flagged": email.is_flagged,
                "is_important": email.is_important,
                "importance_score": email.importance_score,
                "category": email.category,
                "has_attachments": email.has_attachments,
                "attachments": [
                    {
                        "id": str(att.id),
                        "filename": att.filename,
                        "content_type": att.content_type,
                        "size_bytes": att.size_bytes,
                        "is_inline": att.is_inline
                    }
                    for att in (email.attachments or [])
                ]
            },
            "thread": {
                "emails": thread_emails,
                "total_count": len(thread_emails)
            } if thread_emails else None,
            "related_tasks": [
                {
                    "id": str(task.id),
                    "description": task.description,
                    "status": task.status.value if hasattr(task.status, 'value') else task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None
                }
                for task in related_tasks
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email detail: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email details"
        )


@router.get("/accounts/{account_id}/embedding-stats")
async def get_account_embedding_stats(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get embedding statistics for a specific email account.

    Returns:
    - Total emails for account
    - Emails with embeddings
    - Emails without embeddings
    - Breakdown by embedding model used
    - Embedding types generated
    """
    try:
        from app.db.models.email import EmailAccount, Email, EmailEmbedding
        from sqlalchemy import select, func

        # Verify account belongs to user
        result = await db.execute(
            select(EmailAccount).where(EmailAccount.id == account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )

        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this account"
            )

        # Get total emails
        total_emails_result = await db.execute(
            select(func.count(Email.id)).where(Email.account_id == account_id)
        )
        total_emails = total_emails_result.scalar() or 0

        # Get emails with embeddings
        emails_with_embeddings_result = await db.execute(
            select(func.count(Email.id)).where(
                Email.account_id == account_id,
                Email.embeddings_generated == True
            )
        )
        emails_with_embeddings = emails_with_embeddings_result.scalar() or 0

        # Get embedding breakdown by model
        model_breakdown_result = await db.execute(
            select(
                EmailEmbedding.model_name,
                EmailEmbedding.embedding_type,
                func.count(EmailEmbedding.id).label('count')
            ).join(Email, Email.id == EmailEmbedding.email_id)
            .where(Email.account_id == account_id)
            .group_by(EmailEmbedding.model_name, EmailEmbedding.embedding_type)
        )

        model_breakdown = []
        for row in model_breakdown_result:
            model_breakdown.append({
                "model_name": row.model_name,
                "embedding_type": row.embedding_type,
                "count": row.count
            })

        return {
            "account_id": str(account_id),
            "email_address": account.email_address,
            "current_embedding_model": account.embedding_model,
            "total_emails": total_emails,
            "emails_with_embeddings": emails_with_embeddings,
            "emails_without_embeddings": total_emails - emails_with_embeddings,
            "embedding_coverage_percent": round((emails_with_embeddings / total_emails * 100), 2) if total_emails > 0 else 0,
            "model_breakdown": model_breakdown
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve embedding statistics"
        )


class RegenerateEmbeddingsRequest(BaseModel):
    """Request to regenerate embeddings."""
    model_name: Optional[str] = Field(None, description="Target model (null = use account default)")
    filter_by_current_model: Optional[str] = Field(None, description="Only regenerate embeddings from this model")
    email_ids: Optional[List[UUID]] = Field(None, description="Specific emails to regenerate (null = all)")
    embedding_types: Optional[List[str]] = Field(None, description="Specific embedding types to regenerate")
    delete_existing: bool = Field(True, description="Delete existing embeddings before regenerating")


@router.post("/accounts/{account_id}/regenerate-embeddings")
async def regenerate_account_embeddings_endpoint(
    account_id: UUID,
    request: RegenerateEmbeddingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Regenerate embeddings for emails in an account.

    Supports:
    - Regenerating all embeddings
    - Regenerating only embeddings from specific models
    - Regenerating specific emails
    - Regenerating specific embedding types
    - Optionally preserving old embeddings
    """
    try:
        from app.db.models.email import EmailAccount
        from app.tasks.email_sync_tasks import regenerate_account_embeddings
        from sqlalchemy import select

        # Verify account belongs to user
        result = await db.execute(
            select(EmailAccount).where(EmailAccount.id == account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )

        if account.user_id != current_user.id:
            raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this account"
            )

        # Trigger regeneration task
        task = regenerate_account_embeddings.delay(
            str(account_id),
            request.model_name,
            request.filter_by_current_model,
            [str(eid) for eid in request.email_ids] if request.email_ids else None,
            request.embedding_types,
            request.delete_existing
        )

        logger.info(
            f"Scheduled embedding regeneration for account {account_id} "
            f"with task {task.id}"
        )

        return {
            "message": "Embedding regeneration scheduled successfully",
            "task_id": task.id,
            "account_id": str(account_id),
            "target_model": request.model_name or account.embedding_model or "system_default",
            "filter_by_model": request.filter_by_current_model,
            "email_count": len(request.email_ids) if request.email_ids else "all"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule embedding regeneration: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule embedding regeneration"
        )


@router.get("/embedding-models/comparison")
async def get_embedding_models_comparison(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get comparison of embedding models used across all user's accounts.

    Useful for understanding which models are in use and making migration decisions.
    """
    try:
        from app.db.models.email import EmailAccount, Email, EmailEmbedding
        from sqlalchemy import select, func

        # Get user's accounts
        accounts_result = await db.execute(
            select(EmailAccount).where(EmailAccount.user_id == current_user.id)
        )
        accounts = accounts_result.scalars().all()

        account_summaries = []
        for account in accounts:
            # Get embedding model breakdown for this account
            model_stats_result = await db.execute(
                select(
                    EmailEmbedding.model_name,
                    func.count(EmailEmbedding.id).label('count')
                ).join(Email, Email.id == EmailEmbedding.email_id)
                .where(Email.account_id == account.id)
                .group_by(EmailEmbedding.model_name)
            )

            model_stats = {}
            for row in model_stats_result:
                model_stats[row.model_name or "unknown"] = row.count

            # Get total emails
            total_emails_result = await db.execute(
                select(func.count(Email.id)).where(Email.account_id == account.id)
            )
            total_emails = total_emails_result.scalar() or 0

            account_summaries.append({
                "account_id": str(account.id),
                "email_address": account.email_address,
                "configured_model": account.embedding_model,
                "total_emails": total_emails,
                "models_in_use": model_stats
            })

        return {
            "accounts": account_summaries,
            "total_accounts": len(accounts)
        }

    except Exception as e:
        logger.error(f"Failed to get model comparison: {e}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model comparison"
        )
