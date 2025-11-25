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


@celery_app.task(base=OCRTask, bind=True, max_retries=3, default_retry_delay=60, time_limit=600, soft_time_limit=540)
def process_ocr_workflow_task(self, workflow_id: str, ocr_model: str, image_paths: List[str], batch_name: str = "Default Batch", user_id: str = "system"):
    """Celery task for processing OCR workflow."""
    logger.info(f"OCR task called with workflow_id={workflow_id}, user_id={user_id}, model={ocr_model}, images={len(image_paths)}")
    return asyncio.run(_process_ocr_workflow_async(self, workflow_id, ocr_model, image_paths, batch_name, user_id))


async def _process_ocr_workflow_async(
    task: OCRTask,
    workflow_id: str,
    ocr_model: str,
    image_paths: List[str],
    batch_name: str,
    user_id: str
) -> Dict[str, Any]:
    """Async implementation of OCR workflow processing."""
    logger.info(f"Starting OCR workflow processing for workflow {workflow_id}, user {user_id}, model {ocr_model}, {len(image_paths)} images")
    workflow_uuid = UUID(workflow_id)

    async with get_session_context() as session:
        # Get or create workflow
        workflow = await session.get(OCRWorkflow, workflow_uuid)
        if not workflow:
            logger.info(f"Creating new workflow {workflow_id}")
            workflow = OCRWorkflow(
                id=workflow_uuid,
                user_id=user_id,
                workflow_name="OCR Workflow",
                ocr_model=ocr_model,
                status="running"
            )
            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)
        else:
            logger.info(f"Found existing workflow {workflow_id}")

        workflow.status = "running"
        workflow.started_at = datetime.utcnow()
        workflow.total_images = len(image_paths)  # Set total images for progress tracking
        await session.commit()

        # Create initial log
        await _log_workflow_progress(session, workflow_uuid, None, None,
                                   f"Started OCR processing for {len(image_paths)} images", "info", user_id)

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
                # Update progress
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i,
                        'total': len(image_paths),
                        'message': f'Processing image {i+1}/{len(image_paths)}'
                    }
                )

                # Load image
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                # OCR with Ollama
                prompt = "Extract all text from this image and format it as clean markdown. Preserve structure, tables, and formatting as much as possible."

                logger.info(f"Sending OCR request to Ollama model {ocr_model} for image {os.path.basename(image_path)}")

                try:
                    response = await ollama_client.generate(
                        prompt=prompt,
                        model=ocr_model,
                        options={
                            "images": [image_data],
                            "temperature": 0.1,
                            "top_p": 0.9
                        }
                    )

                    logger.info(f"Received OCR response from Ollama: {response}")

                    ocr_text = response.get('response', '').strip()

                    if not ocr_text:
                        logger.warning(f"Empty OCR response for image {os.path.basename(image_path)}")
                        ocr_text = f"[No text extracted from {os.path.basename(image_path)}]"

                except Exception as ocr_error:
                    logger.error(f"OCR API call failed for image {os.path.basename(image_path)}: {ocr_error}")
                    ocr_text = f"[OCR failed for {os.path.basename(image_path)}: {str(ocr_error)}]"

                # Create image record
                image_record = OCRImage(
                    batch_id=batch.id,
                    workflow_id=workflow_uuid,
                    original_filename=os.path.basename(image_path),
                    file_path=image_path,
                    status="completed",
                    processing_order=i,
                    ocr_model_used=ocr_model,
                    raw_markdown=ocr_text,
                    processed_markdown=ocr_text,  # For now, same as raw
                    confidence_score=0.8,  # TODO: Extract from Ollama response if available
                    processed_at=datetime.utcnow()
                )

                session.add(image_record)
                combined_markdown += f"\n\n--- Page {i+1} ---\n\n"
                combined_markdown += ocr_text
                processed_count += 1

                # Update batch and workflow progress
                batch.processed_images = processed_count
                workflow.processed_images = processed_count
                await session.commit()

                # Log progress
                await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                           f"Processed image {i+1}/{len(image_paths)}", "info", user_id)

            except Exception as e:
                logger.error(f"Failed to process image {image_path}: {e}")

                # Create failed image record
                image_record = OCRImage(
                    batch_id=batch.id,
                    workflow_id=workflow_uuid,
                    original_filename=os.path.basename(image_path),
                    file_path=image_path,
                    status="failed",
                    processing_order=i,
                    error_message=str(e)
                )
                session.add(image_record)

                await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                           f"Failed to process image {os.path.basename(image_path)}: {e}", "error", user_id)

        # Update batch completion
        batch.status = "completed"
        batch.combined_markdown = combined_markdown.strip()
        batch.page_count = processed_count
        batch.completed_at = datetime.utcnow()
        await session.commit()

        # Update workflow completion - aggregate stats from all batches
        workflow.status = "completed"
        workflow.total_images = len(image_paths)
        workflow.processed_images = processed_count
        workflow.total_pages = processed_count
        workflow.completed_at = datetime.utcnow()
        await session.commit()

        # Log completion
        await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                   f"OCR workflow completed: {processed_count} images processed", "info", user_id)

        # Send notification
        await _send_completion_notification(session, workflow.user_id, workflow_uuid, batch.id, processed_count)

        # Clean up uploaded images after processing to prevent storage accumulation
        # Note: Only the processed results (markdown) are stored in the database
        try:
            for image_path in image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Cleaned up temporary image file: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up some image files: {e}")

        return {
            "workflow_id": str(workflow_uuid),
            "batch_id": str(batch.id),
            "status": "completed",
            "processed_images": processed_count,
            "total_images": len(image_paths),
            "combined_markdown": combined_markdown.strip()
        }


async def _log_workflow_progress(
    session: AsyncSession,
    workflow_id: UUID,
    batch_id: UUID = None,
    image_id: UUID = None,
    message: str = "",
    level: str = "info",
    user_id: str = "system"
):
    """Log workflow progress."""
    log_entry = OCRWorkflowLog(
        workflow_id=workflow_id,
        batch_id=batch_id,
        image_id=image_id,
        user_id=user_id,
        level=level,
        message=message,
        workflow_phase="processing"
    )
    session.add(log_entry)
    await session.commit()


async def _send_completion_notification(
    session: AsyncSession,
    user_id: str,
    workflow_id: UUID,
    batch_id: UUID,
    processed_count: int
) -> None:
    """Send completion notification."""
    try:
        notification = Notification(
            user_id=user_id,
            title="OCR Processing Complete",
            message=f"Your OCR workflow has completed processing {processed_count} images.",
            notification_type="ocr_complete",
            metadata={
                "workflow_id": str(workflow_id),
                "batch_id": str(batch_id),
                "processed_count": processed_count
            }
        )
        session.add(notification)
        await session.commit()

        # Publish to pubsub for real-time updates
        await pubsub_service.publish(
            f"user:{user_id}:ocr",
            {
                "type": "ocr_complete",
                "workflow_id": str(workflow_id),
                "batch_id": str(batch_id),
                "processed_count": processed_count
            }
        )

    except Exception as e:
        logger.error(f"Failed to send OCR completion notification: {e}")