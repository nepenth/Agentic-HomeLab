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

                # Get image metadata
                try:
                    with Image.open(image_path) as img:
                        image_width, image_height = img.size
                        image_dpi = img.info.get('dpi', (72, 72))[0] if img.info.get('dpi') else 72
                except Exception as e:
                    logger.warning(f"Failed to get image metadata for {image_path}: {e}")
                    image_width = image_height = image_dpi = None

                # Create image record
                image_record = OCRImage(
                    batch_id=batch.id,
                    workflow_id=workflow_uuid,
                    original_filename=os.path.basename(image_path),
                    file_path=image_path,
                    file_size=os.path.getsize(image_path) if os.path.exists(image_path) else None,
                    mime_type="image/jpeg",  # TODO: Detect actual mime type
                    status="completed",
                    processing_order=i,
                    ocr_model_used=ocr_model,
                    raw_markdown=ocr_text,
                    processed_markdown=ocr_text,  # For now, same as raw
                    confidence_score=0.8,  # TODO: Extract from Ollama response if available
                    image_width=image_width,
                    image_height=image_height,
                    image_dpi=image_dpi,
                    processed_at=datetime.utcnow()
                )
                session.add(image_record)

                # Add to combined markdown
                if ocr_text:
                    combined_markdown += f"\n\n## Page {i + 1}\n\n{ocr_text}"
                    processed_count += 1

                # Log progress
                log_entry = OCRWorkflowLog()
                log_entry.workflow_id = workflow_uuid
                log_entry.batch_id = batch.id
                log_entry.image_id = image_record.id
                log_entry.user_id = workflow.user_id
                log_entry.level = "info"
                log_entry.message = f"Processed image {i + 1}/{len(image_paths)}: {os.path.basename(image_path)}"
                log_entry.context = {
                    "image_path": image_path,
                    "ocr_model": ocr_model,
                    "confidence_score": image_record.confidence_score,
                    "text_length": len(ocr_text)
                }
                log_entry.workflow_phase = "processing_images"
                session.add(log_entry)

                # Update progress
                workflow.processed_images = processed_count
                batch.processed_images = processed_count
                await session.commit()

            except Exception as e:
                logger.error(f"Failed to process image {image_path}: {e}")

                # Create failed image record
                failed_image = OCRImage()
                failed_image.batch_id = batch.id
                failed_image.workflow_id = workflow_uuid
                failed_image.original_filename = os.path.basename(image_path)
                failed_image.file_path = image_path
                failed_image.status = "failed"
                failed_image.processing_order = i
                failed_image.error_message = str(e)
                failed_image.processed_at = datetime.utcnow()
                session.add(failed_image)

                # Log error
                error_log = OCRWorkflowLog()
                error_log.workflow_id = workflow_uuid
                error_log.batch_id = batch.id
                error_log.user_id = workflow.user_id
                error_log.level = "error"
                error_log.message = f"Failed to process image {os.path.basename(image_path)}"
                error_log.context = {"error": str(e), "image_path": image_path}
                error_log.workflow_phase = "processing_images"
                session.add(error_log)

                await session.commit()

        # Update batch with results
        batch.combined_markdown = combined_markdown.strip()
        batch.page_count = processed_count
        batch.completed_at = datetime.utcnow()
        batch.status = "completed" if processed_count > 0 else "failed"

        # Update workflow
        workflow.total_images = len(image_paths)
        workflow.processed_images = processed_count
        workflow.total_pages = processed_count
        workflow.completed_at = datetime.utcnow()
        workflow.status = "completed" if processed_count > 0 else "failed"

        await session.commit()

        # Log completion
        completion_log = OCRWorkflowLog()
        completion_log.workflow_id = workflow_uuid
        completion_log.batch_id = batch.id
        completion_log.user_id = workflow.user_id
        completion_log.level = "info"
        completion_log.message = f"OCR workflow completed: {processed_count}/{len(image_paths)} images processed"
        completion_log.context = {
            "total_images": len(image_paths),
            "processed_images": processed_count,
            "batch_name": batch_name,
            "ocr_model": ocr_model
        }
        completion_log.workflow_phase = "completed"
        session.add(completion_log)

        # Send notification
        try:
            notification = Notification()
            notification.user_id = workflow.user_id
            notification.type = "ocr_workflow_completed"
            notification.message = f"OCR workflow '{batch_name}' completed. Processed {processed_count} images."
            notification.related_id = str(workflow_uuid)
            session.add(notification)
            await session.commit()
        except Exception as e:
            logger.warning(f"Failed to create notification: {e}")

        # Publish to pubsub for real-time updates
        try:
            await pubsub_service.publish_log({
                "type": "workflow_completed",
                "workflow_id": str(workflow_uuid),
                "batch_id": str(batch.id),
                "status": workflow.status,
                "processed_images": processed_count,
                "total_images": len(image_paths),
                "user_id": workflow.user_id
            })
        except Exception as e:
            logger.warning(f"Failed to publish to pubsub: {e}")

        return {
            "workflow_id": str(workflow_uuid),
            "batch_id": str(batch.id),
            "status": workflow.status,
            "processed_images": processed_count,
            "total_images": len(image_paths),
            "combined_markdown": combined_markdown.strip()
        }