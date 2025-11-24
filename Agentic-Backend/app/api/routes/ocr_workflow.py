
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
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.api.dependencies import get_db_session, get_current_user
from app.db.models.user import User
from app.db.models.ocr_workflow import (
    OCRWorkflow, OCRBatch, OCRImage, OCRDocument, OCRWorkflowLog,
    OCRWorkflowStatus, OCRBatchStatus
)
from app.services.ollama_client import ollama_client
from app.tasks.ocr_tasks import process_ocr_workflow_task
from app.utils.logging import get_logger
import shutil
from pathlib import Path

logger = get_logger("ocr_workflow_api")
router = APIRouter()

# Create OCR media directory
OCR_MEDIA_DIR = Path("media/ocr")
OCR_MEDIA_DIR.mkdir(parents=True, exist_ok=True)


class OCRWorkflowCreateRequest(BaseModel):
    """Request to create a new OCR workflow."""
    workflow_name: str = "OCR Workflow"
    ocr_model: str = "deepseek-ocr"
    processing_options: dict = {}


class OCRBatchCreateRequest(BaseModel):
    """Request to create a batch of images."""
    batch_name: str = "New Batch"


class OCRProcessRequest(BaseModel):
    """Request to process an OCR batch."""
    batch_id: str


class OCRExportRequest(BaseModel):
    """Request to export OCR results."""
    format: str = "markdown"  # markdown, pdf, docx


class OCRWorkflowResponse(BaseModel):
    """Response for workflow operations."""
    workflow_id: str
    status: str
    message: str


class OCRBatchResponse(BaseModel):
    """Response for batch operations."""
    batch_id: str
    workflow_id: str
    status: str
    message: str


class OCRStatusResponse(BaseModel):
    """Response for status queries."""
    workflow_id: str
    status: str
    progress: dict
    created_at: str
    updated_at: str


class OCRResultsResponse(BaseModel):
    """Response for OCR results."""
    workflow_id: str
    batch_id: str
    combined_markdown: str
    processed_images: int
    total_images: int
    status: str


class OCROllamaModel(BaseModel):
    """OCR model information from Ollama."""
    name: str
    size: int
    modified_at: str


@router.get("/models", response_model=List[OCROllamaModel])
async def get_available_ocr_models():
    """Get list of available OCR models from Ollama."""
    try:
        models_response = await ollama_client.list_models()
        models = models_response.get("models", [])

        # Filter for OCR-related models (you might want to adjust this filter)
        ocr_models = [
            model for model in models
            if any(keyword in model.get("name", "").lower() for keyword in ["ocr", "vision", "llava"])
        ]

        # If no OCR-specific models, return all models
        if not ocr_models:
            ocr_models = models

        return [
            OCROllamaModel(
                name=model["name"],
                size=model.get("size", 0),
                modified_at=model.get("modified_at", "")
            )
            for model in ocr_models
        ]
    except Exception as e:
        logger.error(f"Failed to get OCR models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OCR models"
        )


@router.post("/workflows", response_model=OCRWorkflowResponse)
async def create_ocr_workflow(
    request: OCRWorkflowCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new OCR workflow."""
    try:
        workflow = OCRWorkflow(
            user_id=str(current_user.id),
            workflow_name=request.workflow_name,
            ocr_model=request.ocr_model,
            processing_options=request.processing_options,
            status="pending"
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
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create OCR workflow"
        )


@router.post("/workflows/{workflow_id}/batches", response_model=OCRBatchResponse)
async def upload_ocr_batch(
    workflow_id: UUID,
    batch_name: str = Form(...),
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Upload a batch of images for OCR processing."""
    try:
        # Verify workflow exists and belongs to user
        workflow = await db.get(OCRWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Create batch
        batch = OCRBatch(
            workflow_id=workflow_id,
            batch_name=batch_name,
            total_images=len(images),
            status="pending"
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        # Save uploaded images
        saved_paths = []
        for i, image in enumerate(images):
            if not image.filename:
                continue

            # Generate unique filename
            file_extension = Path(image.filename).suffix
            unique_filename = f"{workflow_id}_{batch.id}_{i}{file_extension}"
            file_path = OCR_MEDIA_DIR / unique_filename

            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            saved_paths.append(str(file_path))

            # Create image record
            image_record = OCRImage(
                batch_id=batch.id,
                workflow_id=workflow_id,
                original_filename=image.filename,
                file_path=str(file_path),
                file_size=file_path.stat().st_size if file_path.exists() else None,
                mime_type=image.content_type,
                status="uploaded",
                processing_order=i
            )
            db.add(image_record)

        await db.commit()

        logger.info(f"Uploaded {len(saved_paths)} images for batch {batch.id}")

        return OCRBatchResponse(
            batch_id=str(batch.id),
            workflow_id=str(workflow_id),
            status="uploaded",
            message=f"Successfully uploaded {len(saved_paths)} images"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload OCR batch: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload images"
        )


@router.post("/workflows/{workflow_id}/process", response_model=dict)
async def process_ocr_workflow(
    workflow_id: UUID,
    request: OCRProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start OCR processing for a workflow batch."""
    try:
        # Verify workflow exists and belongs to user
        workflow = await db.get(OCRWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Get batch
        batch_id = UUID(request.batch_id)
        batch = await db.get(OCRBatch, batch_id)
        if not batch or batch.workflow_id != workflow_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

        # Get image paths
        images_query = select(OCRImage.file_path).where(
            and_(OCRImage.batch_id == batch_id, OCRImage.status == "uploaded")
        )
        result = await db.execute(images_query)
        image_paths = [row[0] for row in result.fetchall()]

        if not image_paths:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images to process")

        # Start Celery task
        task = process_ocr_workflow_task.delay(
            workflow_id=str(workflow_id),
            ocr_model=workflow.ocr_model,
            image_paths=image_paths,
            batch_name=batch.batch_name
        )

        logger.info(f"Started OCR processing task {task.id} for workflow {workflow_id}")

        return {
            "task_id": task.id,
            "status": "processing",
            "message": "OCR processing started",
            "workflow_id": str(workflow_id),
            "batch_id": str(batch_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start OCR processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start OCR processing"
        )


@router.get("/workflows/{workflow_id}/status", response_model=OCRStatusResponse)
async def get_ocr_workflow_status(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the status of an OCR workflow."""
    try:
        # Verify workflow exists and belongs to user
        workflow = await db.get(OCRWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Get batch information
        batches_query = select(OCRBatch).where(OCRBatch.workflow_id == workflow_id)
        result = await db.execute(batches_query)
        batches = result.scalars().all()

        progress = {
            "total_batches": len(batches),
            "completed_batches": len([b for b in batches if b.status == "completed"]),
            "total_images": sum(b.total_images for b in batches),
            "processed_images": sum(b.processed_images for b in batches)
        }

        return OCRStatusResponse(
            workflow_id=str(workflow_id),
            status=workflow.status,
            progress=progress,
            created_at=workflow.created_at.isoformat() if workflow.created_at else "",
            updated_at=workflow.updated_at.isoformat() if workflow.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow status"
        )


@router.get("/workflows/{workflow_id}/results", response_model=OCRResultsResponse)
async def get_ocr_workflow_results(
    workflow_id: UUID,
    batch_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the results of an OCR workflow."""
    try:
        # Verify workflow exists and belongs to user
        workflow = await db.get(OCRWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Get batch (use first batch if not specified)
        if batch_id:
            batch_uuid = UUID(batch_id)
            batch = await db.get(OCRBatch, batch_uuid)
            if not batch or batch.workflow_id != workflow_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        else:
            # Get the first completed batch
            batches_query = select(OCRBatch).where(
                and_(OCRBatch.workflow_id == workflow_id, OCRBatch.status == "completed")
            ).order_by(OCRBatch.created_at.desc())
            result = await db.execute(batches_query)
            batch = result.scalar_one_or_none()
            if not batch:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No completed batches found")

        return OCRResultsResponse(
            workflow_id=str(workflow_id),
            batch_id=str(batch.id),
            combined_markdown=batch.combined_markdown or "",
            processed_images=batch.processed_images,
            total_images=batch.total_images,
            status=batch.status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow results"
        )


@router.post("/workflows/{workflow_id}/export", response_model=dict)
async def export_ocr_results(
    workflow_id: UUID,
    request: OCRExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Export OCR results in the specified format."""
    try:
        # Verify workflow exists and belongs to user
        workflow = await db.get(OCRWorkflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if workflow.user_id != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Get completed batch
        batches_query = select(OCRBatch).where(
            and_(OCRBatch.workflow_id == workflow_id, OCRBatch.status == "completed")
        ).order_by(OCRBatch.created_at.desc())
        result = await db.execute(batches_query)
        batch = result.scalar_one_or_none()
        if not batch or not batch.combined_markdown:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No completed results to export")

        # For now, just return the markdown content
        # In a full implementation, you'd generate PDF/DOCX files
        if request.format == "markdown":
            return {
                "format": "markdown",
                "content": batch.combined_markdown,
                "filename": f"ocr_results_{workflow_id}.md"
            }
        else:
            # Placeholder for PDF/DOCX export
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Export format '{request.format}' not yet implemented"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export OCR results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export results"
        )