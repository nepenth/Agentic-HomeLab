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