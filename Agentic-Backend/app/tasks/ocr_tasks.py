"""
Celery tasks for OCR workflow processing.
"""

from celery import Task
from typing import Dict, Any, List
from uuid import UUID
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.celery_app import celery_app
from app.db.database import get_session_context
from app.services.ollama_client import ollama_client
from app.db.models.ocr_workflow import OCRWorkflow, OCRBatch, OCRImage, OCRWorkflowLog
from app.utils.logging import get_logger
from app.services.pubsub_service import pubsub_service
from app.db.models.notification import Notification
import base64
import os
from pathlib import Path
import io
from PIL import Image
import markdown2

logger = get_logger("ocr_tasks")


class OCRTask(Task):
    """Base class for OCR tasks with enhanced error handling and logging."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"OCR Task {task_id} failed: {exc}")
        
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"OCR Task {task_id} completed successfully")


@celery_app.task(base=OCRTask, bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_workflow_task(self, workflow_id: str, ocr_model: str, image_paths: List[str], batch_name: str = "Default Batch"):
    """Celery task for processing OCR workflow."""
    return asyncio.run(_process_ocr_workflow_async(self, workflow_id, ocr_model, image_paths, batch_name))


async def _process_ocr_workflow_async(
    task: OCRTask,
    workflow_id: str,
    ocr_model: str,
    image_paths: List[str],
    batch_name: str
) -> Dict[str, Any]:
    """Async implementation of OCR workflow processing."""
    workflow_uuid = UUID(workflow_id)
    
    async with get_session_context() as session:
        # Get or create workflow
        workflow = await session.get(OCRWorkflow, workflow_uuid)
        if not workflow:
            workflow = OCRWorkflow(
                id=workflow_uuid,
                user_id="current_user",  # TODO: Get from context
                workflow_name="OCR Workflow",
                ocr_model=ocr_model,
                status="running"
            )
            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)
        
        workflow.status = "running"
        workflow.started_at = datetime.utcnow()
        await session.commit()
        
        # Create batch
        batch = OCRBatch(
            workflow_id=workflow_uuid,
            batch_name=batch_name,
            total_images=len(image_paths),
            status="processing"
        )
        session.add(batch)
        await session.commit()
        await session.refresh(batch)
        
        # Process images
        combined_markdown = ""
        processed_count = 0
        
        for i, image_path in enumerate(image_paths):
            try:
                # Load image
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                # OCR with Ollama
                prompt = "Extract all text from this image and format it as clean markdown. Preserve structure, tables, and formatting as much as possible."
                
                response = await ollama_client.generate(
                    prompt=prompt,
                    model=ocr_model,
                    options={
                        "images": [image_data],
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                )
                
                ocr_text = response.get('response', '').strip()
                
                # Create image record
                image_record