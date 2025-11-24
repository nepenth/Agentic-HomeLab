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
    OCRWorkflowStatus,
    OCRBatchStatus
)
from app.tasks.ocr_tasks import process_ocr_workflow_task
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger
from pydantic import BaseModel

logger = get_logger("ocr_workflow")

router = APIRouter()

# Pydantic models for request/response
class OCRWorkflowCreate(BaseModel):
    workflow_name: Optional[str] = None
    ocr_model: str = "deepseek-ocr"
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
    Get available OCR models from Ollama, filtered to vision-capable models.
    """
    try:
        # Get all available models from Ollama
        ollama_response = await ollama_client.list_models()

        # Filter for vision-capable models (models that support image processing)
        vision_models = []
        for model in ollama_response.get("models", []):
            model_name = model.get("name", "")

            # Check if model supports vision capabilities
            # Vision-capable models typically include keywords like 'vision', 'vl', 'visual', etc.
            is_vision_capable = any(keyword in model_name.lower() for keyword in [
                'vision', 'vl', 'visual', 'llava', 'bakllava', 'moondream',
                'deepseek-ocr', 'qwen2.5vl', 'llama3.2-vision'
            ])

            if is_vision_capable:
                vision_models.append({
                    "name": model_name,
                    "display_name": model_name.replace('-', ' ').title(),
                    "description": f"Vision-capable OCR model: {model_name}",
                    "capabilities": ["vision", "ocr", "image-analysis"],
                    "recommended": "deepseek-ocr" in model_name or "qwen2.5vl" in model_name,
                    "size": model.get("size", "Unknown")
                })

        # Add some default OCR models if not found in Ollama
        default_models = [
            {
                "name": "deepseek-ocr",
                "display_name": "DeepSeek OCR",
                "description": "Advanced OCR model optimized for document text extraction",
                "capabilities": ["ocr", "document-processing", "text-extraction"],
                "recommended": True,
                "size": "Unknown"
            }
        ]

        # Combine Ollama vision models with defaults
        all_models = vision_models + default_models

        # Remove duplicates
        seen_names = set()
        unique_models = []
        for model in all_models:
            if model["name"] not in seen_names:
                seen_names.add(model["name"])
                unique_models.append(model)

        return OCRModelsResponse(
            models=unique_models,
            total_count=len(unique_models)
        )

    except Exception as e:
        logger.error(f"Failed to get OCR models: {e}")
        # Return default models if Ollama is unavailable
        return OCRModelsResponse(
            models=[
                {
                    "name": "deepseek-ocr",
                    "display_name": "DeepSeek OCR",
                    "description": "Advanced OCR model optimized for document text extraction",
                    "capabilities": ["ocr", "document-processing", "text-extraction"],
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