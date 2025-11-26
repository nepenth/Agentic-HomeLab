"""
OCR Workflow API Routes.

This module provides REST API endpoints for OCR workflow management including:
- Image upload and batch creation
- OCR processing workflow execution
- Result retrieval and export
- Model selection and configuration
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from typing import List, Optional
from uuid import UUID, uuid4
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from app.api.dependencies import get_db_session, get_current_user
from app.db.models.user import User
from app.db.models.ocr_workflow import (
    OCRWorkflow,
    OCRBatch,
    OCRImage,
    OCRDocument,
    OCRWorkflowLog,
    OCRWorkflowStatus,
    OCRBatchStatus
)
from app.tasks.ocr_tasks import process_ocr_workflow_task
from app.services.ollama_client import ollama_client
from app.services.pubsub_service import pubsub_service
from app.utils.logging import get_logger
from pydantic import BaseModel

logger = get_logger("ocr_workflow")

router = APIRouter()

# Pydantic models for request/response
class OCRWorkflowCreate(BaseModel):
    workflow_name: Optional[str] = None
    ocr_model: str = "deepseek-ocr:3b"
    processing_options: Optional[dict] = None

class OCRBatchCreate(BaseModel):
    batch_name: Optional[str] = None

class OCRWorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str

class OCRBatchResponse(BaseModel):
    batch_id: str
    workflow_id: str
    status: str
    message: str

class OCRModelInfo(BaseModel):
    name: str
    display_name: str
    description: str
    capabilities: List[str]
    recommended: bool
    size: Optional[str] = None

class OCRModelsResponse(BaseModel):
    models: List[OCRModelInfo]
    total_count: int

@router.get("/models", response_model=OCRModelsResponse)
async def get_ocr_models(
    current_user: User = Depends(get_current_user)
) -> OCRModelsResponse:
    """
    Get available OCR models from the global models endpoint, filtered to vision-capable models.
    """
    try:
        # Use the same model detection logic as the global endpoint
        from app.services.ollama_client import ollama_client

        # Get all available models from Ollama
        ollama_response = await ollama_client.list_models()

        # Filter for vision-capable models (same logic as global endpoint)
        vision_models = []
        for model in ollama_response.get("models", []):
            model_name = model.get("name", "")
            model_details = model.get("details", {})
            model_family = model_details.get("family", "").lower()
            model_families_list = model_details.get("families", [])

            # Check for vision capabilities (same logic as global endpoint)
            is_vision_capable = (
                # Known vision model families
                any(family in ['mllama', 'llava', 'qwen25vl', 'deepseekocr'] for family in [model_family] + model_families_list) or
                # Models with vision in name
                'vision' in model_name.lower() or 'ocr' in model_name.lower() or
                # Specific known vision models
                any(vision_model in model_name.lower() for vision_model in [
                    'llama3.2-vision', 'qwen2.5vl', 'llava', 'deepseek-ocr'
                ])
            )

            if is_vision_capable:
                vision_models.append({
                    "name": model_name,
                    "display_name": model_name.replace('-', ' ').title(),
                    "description": f"Vision-capable OCR model: {model_name}",
                    "capabilities": ["vision", "ocr", "image-analysis"],
                    "recommended": "deepseek-ocr" in model_name or "llama3.2-vision" in model_name,
                    "size": model.get("size", "Unknown")
                })

        # Sort by recommended status first, then by name
        vision_models.sort(key=lambda x: (not x["recommended"], x["name"]))

        # Use the vision models directly
        ocr_models = vision_models

        return OCRModelsResponse(
            models=ocr_models,
            total_count=len(ocr_models)
        )

    except Exception as e:
        logger.error(f"Failed to get OCR models: {e}")
        # Return default models if service is unavailable
        return OCRModelsResponse(
            models=[
                {
                    "name": "deepseek-ocr:3b",
                    "display_name": "DeepSeek OCR:3B",
                    "description": "Advanced OCR model optimized for document text extraction",
                    "capabilities": ["vision", "ocr", "image-analysis"],
                    "recommended": True,
                    "size": "Unknown"
                }
            ],
            total_count=1
        )

@router.post("/workflows", response_model=OCRWorkflowResponse)
async def create_ocr_workflow(
    workflow_data: OCRWorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> OCRWorkflowResponse:
    """
    Create a new OCR workflow.
    """
    try:
        workflow = OCRWorkflow(
            user_id=current_user.username,
            workflow_name=workflow_data.workflow_name or f"OCR Workflow {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            ocr_model=workflow_data.ocr_model,
            status="pending",
            processing_options=workflow_data.processing_options
        )

        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        logger.info(f"Created OCR workflow {workflow.id} for user {current_user.username}")

        return OCRWorkflowResponse(
            workflow_id=str(workflow.id),
            status="created",
            message="OCR workflow created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to create OCR workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OCR workflow"
        )

@router.post("/workflows/{workflow_id}/batches", response_model=OCRBatchResponse)
async def create_ocr_batch(
    workflow_id: str,
    batch_name: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> OCRBatchResponse:
    """
    Create a new OCR batch with uploaded images.
    """
    try:
        # Validate workflow exists and belongs to user
        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)
        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Create batch
        batch = OCRBatch(
            workflow_id=workflow_uuid,
            batch_name=batch_name or f"Batch {datetime.utcnow().strftime('%H:%M:%S')}",
            total_images=len(images),
            status="pending"
        )

        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        # Save uploaded images
        media_dir = os.path.join("media", "ocr")
        os.makedirs(media_dir, exist_ok=True)

        for i, image in enumerate(images):
            # Validate file type
            if not image.content_type.startswith('image/'):
                continue

            # Generate unique filename
            file_extension = os.path.splitext(image.filename or 'image.jpg')[1]
            unique_filename = f"{batch.id}_{i}{file_extension}"
            file_path = os.path.join(media_dir, unique_filename)

            # Save file
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)

            # Create image record
            image_record = OCRImage(
                batch_id=batch.id,
                workflow_id=workflow_uuid,
                original_filename=image.filename or f"image_{i}{file_extension}",
                file_path=file_path,
                file_size=len(content),
                mime_type=image.content_type,
                processing_order=i,
                status="pending"
            )

            db.add(image_record)

        await db.commit()

        logger.info(f"Created OCR batch {batch.id} with {len(images)} images")

        return OCRBatchResponse(
            batch_id=str(batch.id),
            workflow_id=workflow_id,
            status="created",
            message=f"Batch created with {len(images)} images"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create OCR batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OCR batch"
        )

@router.post("/workflows/{workflow_id}/process")
async def process_ocr_workflow(
    workflow_id: str,
    batch_id: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Start OCR processing for a workflow batch.
    """
    try:
        # Validate workflow and batch exist and belong to user
        workflow_uuid = UUID(workflow_id)
        batch_uuid = UUID(batch_id)

        workflow = await db.get(OCRWorkflow, workflow_uuid)
        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        batch = await db.get(OCRBatch, batch_uuid)
        if not batch or batch.workflow_id != workflow_uuid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch not found"
            )

        # Get image paths for processing
        images_result = await db.execute(
            select(OCRImage.file_path).where(
                and_(
                    OCRImage.batch_id == batch_uuid,
                    OCRImage.status == "pending"
                )
            ).order_by(OCRImage.processing_order)
        )
        image_paths = [row[0] for row in images_result.fetchall()]

        if not image_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No images to process"
            )

        # Update workflow and batch status
        workflow.status = "running"
        workflow.started_at = datetime.utcnow()
        batch.status = "processing"
        batch.started_at = datetime.utcnow()

        await db.commit()

        # Start background processing
        background_tasks.add_task(
            process_ocr_workflow_task.delay,
            workflow_id,
            workflow.ocr_model,
            image_paths,
            batch.batch_name,
            current_user.username
        )

        logger.info(f"Started OCR processing for workflow {workflow_id}, batch {batch_id}")

        return {
            "message": "OCR processing started",
            "workflow_id": workflow_id,
            "batch_id": batch_id,
            "task_id": None  # Could return Celery task ID if needed
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start OCR processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start OCR processing"
        )

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get the current status of an OCR workflow.
    """
    try:
        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)

        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Get batch information
        batches_result = await db.execute(
            select(OCRBatch).where(OCRBatch.workflow_id == workflow_uuid)
        )
        batches = batches_result.scalars().all()

        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "progress": {
                "total_images": workflow.total_images,
                "processed_images": workflow.processed_images,
                "total_pages": workflow.total_pages
            },
            "batches": [
                {
                    "batch_id": str(batch.id),
                    "batch_name": batch.batch_name,
                    "status": batch.status,
                    "total_images": batch.total_images,
                    "processed_images": batch.processed_images,
                    "page_count": batch.page_count
                }
                for batch in batches
            ],
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow status"
        )

@router.get("/workflows/{workflow_id}/results")
async def get_workflow_results(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get the results of a completed OCR workflow.
    """
    try:
        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)

        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if workflow.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is not completed yet"
            )

        # Get combined results from batches
        batches_result = await db.execute(
            select(OCRBatch).where(
                and_(
                    OCRBatch.workflow_id == workflow_uuid,
                    OCRBatch.status == "completed"
                )
            )
        )
        batches = batches_result.scalars().all()

        combined_markdown = ""
        for batch in batches:
            if batch.combined_markdown:
                combined_markdown += f"\n\n--- {batch.batch_name} ---\n\n"
                combined_markdown += batch.combined_markdown

        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "combined_markdown": combined_markdown.strip(),
            "total_pages": sum(batch.page_count for batch in batches),
            "batches_count": len(batches)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow results"
        )

@router.get("/workflows/{workflow_id}/logs")
async def get_workflow_logs(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
    offset: int = 0
):
    """
    Get OCR workflow logs from database.
    """
    try:
        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)

        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Get logs from database - also include logs without workflow_id but with matching user_id
        logs_result = await db.execute(
            select(OCRWorkflowLog).where(
                (OCRWorkflowLog.workflow_id == workflow_uuid) |
                ((OCRWorkflowLog.workflow_id.is_(None)) & (OCRWorkflowLog.user_id == current_user.username))
            ).order_by(OCRWorkflowLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = logs_result.scalars().all()

        logger.info(f"Found {len(logs)} logs for workflow {workflow_id} and user {current_user.username}")

        return {
            "workflow_id": workflow_id,
            "logs": [log.to_dict() for log in logs],
            "total_count": len(logs),
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow logs"
        )

@router.post("/workflows/{workflow_id}/export")
async def export_workflow_results(
    workflow_id: str,
    format: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export OCR workflow results to PDF or DOCX format.
    """
    try:
        if format not in ["pdf", "docx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export format. Supported: pdf, docx"
            )

        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)

        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Get workflow results
        results_response = await get_workflow_results(workflow_id, current_user, db)
        content = results_response["combined_markdown"]

        # TODO: Implement actual PDF/DOCX generation
        # For now, return placeholder response
        return {
            "message": f"Export to {format.upper()} would be implemented here",
            "workflow_id": workflow_id,
            "format": format,
            "content_length": len(content),
            "download_url": f"/api/v1/ocr/workflows/{workflow_id}/download/{format}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export workflow results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export workflow results"
        )

# Queue Management Endpoints

@router.get("/queue/status")
async def get_ocr_queue_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get OCR queue status and active workflows.
    """
    try:
        # Get active workflows for the user
        workflows_result = await db.execute(
            select(OCRWorkflow).where(
                and_(
                    OCRWorkflow.user_id == current_user.username,
                    OCRWorkflow.status.in_(["pending", "running"])
                )
            ).order_by(OCRWorkflow.created_at.desc())
        )
        workflows = workflows_result.scalars().all()

        # Get workflow details with batch info
        queue_items = []
        for workflow in workflows:
            batches_result = await db.execute(
                select(OCRBatch).where(OCRBatch.workflow_id == workflow.id)
            )
            batches = batches_result.scalars().all()

            queue_items.append({
                "workflow_id": str(workflow.id),
                "workflow_name": workflow.workflow_name,
                "status": workflow.status,
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
                "total_images": workflow.total_images,
                "processed_images": workflow.processed_images,
                "ocr_model": workflow.ocr_model,
                "batches": [
                    {
                        "batch_id": str(batch.id),
                        "batch_name": batch.batch_name,
                        "status": batch.status,
                        "total_images": batch.total_images,
                        "processed_images": batch.processed_images,
                        "created_at": batch.created_at.isoformat() if batch.created_at else None,
                    }
                    for batch in batches
                ]
            })

        return {
            "queue_items": queue_items,
            "total_count": len(queue_items),
            "user_id": current_user.username
        }

    except Exception as e:
        logger.error(f"Failed to get OCR queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue status"
        )

@router.delete("/workflows/{workflow_id}")
async def cancel_ocr_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel an OCR workflow and remove it from queue.
    """
    try:
        workflow_uuid = UUID(workflow_id)
        workflow = await db.get(OCRWorkflow, workflow_uuid)

        if not workflow or workflow.user_id != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Update workflow status
        workflow.status = "cancelled"
        workflow.completed_at = datetime.utcnow()
        workflow.error_message = "Cancelled by user"

        # Update associated batches
        await db.execute(
            update(OCRBatch).where(OCRBatch.workflow_id == workflow_uuid)
            .values(status="cancelled", completed_at=datetime.utcnow())
        )

        await db.commit()

        logger.info(f"Cancelled OCR workflow {workflow_id} for user {current_user.username}")

        return {
            "message": "Workflow cancelled successfully",
            "workflow_id": workflow_id,
            "status": "cancelled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel OCR workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel workflow"
        )

@router.delete("/queue/clear-all")
async def clear_all_ocr_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel all active OCR workflows for the current user.
    """
    try:
        # Get all active workflows for the user
        workflows_result = await db.execute(
            select(OCRWorkflow.id).where(
                and_(
                    OCRWorkflow.user_id == current_user.username,
                    OCRWorkflow.status.in_(["pending", "running"])
                )
            )
        )
        workflow_ids = [row[0] for row in workflows_result.fetchall()]

        if not workflow_ids:
            return {
                "message": "No active workflows to cancel",
                "cancelled_count": 0
            }

        # Update workflows
        await db.execute(
            update(OCRWorkflow).where(
                and_(
                    OCRWorkflow.user_id == current_user.username,
                    OCRWorkflow.status.in_(["pending", "running"])
                )
            ).values(
                status="cancelled",
                completed_at=datetime.utcnow(),
                error_message="Cancelled by user - clear all"
            )
        )

        # Update associated batches
        await db.execute(
            update(OCRBatch).where(
                OCRBatch.workflow_id.in_(workflow_ids)
            ).values(
                status="cancelled",
                completed_at=datetime.utcnow()
            )
        )

        await db.commit()

        logger.info(f"Cancelled {len(workflow_ids)} OCR workflows for user {current_user.username}")

        return {
            "message": f"Cancelled {len(workflow_ids)} workflows successfully",
            "cancelled_count": len(workflow_ids),
            "cancelled_workflows": [str(wid) for wid in workflow_ids]
        }

    except Exception as e:
        logger.error(f"Failed to clear all OCR workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear workflows"
        )