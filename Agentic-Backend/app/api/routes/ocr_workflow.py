"""
OCR Workflow API Routes.

This module provides REST API endpoints for OCR workflow management including:
- Image upload and batch creation
- OCR processing workflow execution
- Result retrieval and export
- Model selection and configuration
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Optional
from uuid import uuid4
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db_session, get_current_user
from app.db.database import get_session_context
from app.db.models.ocr_workflow import OCRWorkflow, OCRBatch, OCRImage, OCRDocument
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger
from app.tasks.ocr_tasks import process_ocr_workflow_task

logger = get_logger("ocr_workflow_api")
router = APIRouter(prefix="/ocr", tags=["OCR Workflow"])


@router.post("/models")
async def get_available_ocr_models():
    """Get available OCR models from Ollama."""
    try:
        models = await ollama_client.list_models()
        # Filter for vision/OCR models
        ocr_models = [m for m in models.get("models", []) if "ocr" in m["name"].lower() or "vision" in m["name"].lower()]
        return {"models": ocr_models}
    except Exception as e:
        logger.error(f"Failed to get OCR models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")


@router.post("/workflows")
async def create_ocr_workflow(
    workflow_name: str = Form(...),
    ocr_model: str = Form(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new OCR workflow."""
    workflow = OCRWorkflow(
        id=uuid4(),
        user_id="current_user",  # TODO: from current_user
        workflow_name=workflow_name,
        ocr_model=ocr_model,
        status="pending"
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return {"workflow_id": str(workflow.id)}


@router.post("/workflows/{workflow_id}/batches")
async def create_ocr_batch(
    workflow_id: str,
    batch_name: str = Form("Default Batch"),
    images: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a batch and upload images for OCR processing."""
    workflow = await db.get(OCRWorkflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
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
    
    # Save images
    image_paths = []
    media_dir = "media/ocr"
    os.makedirs(media_dir, exist_ok=True)
    
    for i, image in enumerate(images):
        filename = f"{batch.id}_{i}_{image.filename}"
        file_path = os.path.join(media_dir, filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        # Create image record
        image_record