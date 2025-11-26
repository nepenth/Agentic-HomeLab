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
                # Specialized prompt for DeepSeek-OCR / Vision models
                prompt = """
                Perform high-quality OCR on this image. 
                1. Extract ALL text exactly as it appears.
                2. Preserve formatting (headers, lists, tables) using Markdown.
                3. If there are tables, format them as Markdown tables.
                4. Do not add conversational filler (like "Here is the text"). Just provide the Markdown content.
                """

                logger.info(f"Sending OCR request to Ollama model {ocr_model} for image {os.path.basename(image_path)}")
                await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                           f"Sending image {i+1} to {ocr_model}...", "info", user_id)

                try:
                    # First check if the model is available
                    try:
                        models_response = await ollama_client.list_models()
                        available_models = [model.get('name', '') for model in models_response.get('models', [])]

                        # Check if specific version exists or if we need to pull it
                        # More flexible matching: check if the requested model matches any available model
                        model_available = any(
                            available_model.startswith(ocr_model) or
                            available_model == ocr_model or
                            (ocr_model in available_model and ':' in available_model)
                            for available_model in available_models
                        )

                        if not model_available:
                            logger.warning(f"Model {ocr_model} not available locally. Available: {available_models}")

                            # Try to pull it if it's a known model
                            if 'deepseek-ocr' in ocr_model or 'llama3.2-vision' in ocr_model:
                                try:
                                    await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                                               f"Pulling model {ocr_model}...", "info", user_id)
                                    await ollama_client.pull_model(ocr_model)
                                    logger.info(f"Successfully pulled model {ocr_model}")
                                except Exception as pull_error:
                                    logger.error(f"Failed to pull model {ocr_model}: {pull_error}")
                                    # Fallback logic continues below

                            # Re-check availability or find fallback
                            models_response = await ollama_client.list_models()
                            available_models = [model.get('name', '') for model in models_response.get('models', [])]

                            # Check again with flexible matching
                            model_available = any(
                                available_model.startswith(ocr_model) or
                                available_model == ocr_model or
                                (ocr_model in available_model and ':' in available_model)
                                for available_model in available_models
                            )

                            if not model_available:
                                # Try to find a suitable vision-capable model
                                vision_models = [m for m in available_models if any(keyword in m.lower() for keyword in ['vision', 'vl', 'llava', 'qwen2.5vl', 'llama3.2-vision', 'deepseek-ocr'])]
                                if vision_models:
                                    # Prefer llama3.2-vision or deepseek-ocr as primary fallback
                                    preferred_models = [m for m in vision_models if 'deepseek-ocr' in m or 'llama3.2-vision' in m]
                                    fallback_model = preferred_models[0] if preferred_models else vision_models[0]
                                    logger.info(f"Using fallback vision model: {fallback_model}")
                                    await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                                               f"Model {ocr_model} unavailable, using fallback: {fallback_model}", "warning", user_id)
                                    ocr_model = fallback_model
                                else:
                                    raise Exception(f"Model {ocr_model} not available and no suitable vision-capable fallback found.")

                        # Log the model being used
                        logger.info(f"Starting OCR processing with model: {ocr_model}")
                    except Exception as model_check_error:
                        logger.warning(f"Could not check available models: {model_check_error}")

                    response = await ollama_client.generate(
                        prompt=prompt,
                        model=ocr_model,
                        options={
                            "images": [image_data],
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "num_ctx": 4096  # Ensure enough context for full page
                        }
                    )

                    logger.info(f"Received OCR response from Ollama")

                    ocr_text = response.get('response', '').strip()

                    if not ocr_text:
                        logger.warning(f"Empty OCR response for image {os.path.basename(image_path)}")
                        ocr_text = f"[No text extracted from {os.path.basename(image_path)}]"
                        await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                                   f"Warning: No text extracted from image {i+1}", "warning", user_id)

                except Exception as ocr_error:
                    logger.error(f"OCR API call failed for image {os.path.basename(image_path)}: {ocr_error}")
                    ocr_text = f"[OCR failed for {os.path.basename(image_path)}: {str(ocr_error)}]"
                    await _log_workflow_progress(session, workflow_uuid, batch.id, None,
                                               f"OCR API failed for image {i+1}: {str(ocr_error)}", "error", user_id)

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
                                           f"Successfully processed image {i+1}/{len(image_paths)}", "success", user_id)

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
                await session.commit() # Commit failure record

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