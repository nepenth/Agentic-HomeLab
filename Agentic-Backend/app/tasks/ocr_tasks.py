"""
Celery tasks for OCR workflow processing.
"""

from celery import Task
from typing import Dict, Any, List
from uuid import UUID
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from app.celery_app import celery_app
from app.db.database import get_celery_db_session
from app.services.ollama_client import sync_ollama_client
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


def _post_process_deepseek_ocr_output(raw_output: str) -> str:
    """
    Post-process raw deepseek-ocr output to clean markdown.

    The deepseek-ocr model may include grounding tags, bounding box coordinates,
    and other artifacts that need to be cleaned up for proper markdown output.
    """
    if not raw_output:
        return ""

    try:
        import re
        cleaned = raw_output.strip()

        # Remove grounding tags like <|grounding|> or similar
        cleaned = re.sub(r'<\|[^>]+\|>', '', cleaned)

        # Remove bounding box coordinates like image[[x, y, w, h]] or table[[x, y, w, h]]
        cleaned = re.sub(r'(?:image|table|text)\[\[[^\]]+\]\]', '', cleaned)

        # Remove HTML table artifacts and empty table cells
        # Remove <table>, <tr>, <td> tags and their content if they're empty
        cleaned = re.sub(r'<table[^>]*>.*?</table>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<tr[^>]*>.*?</tr>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<td[^>]*>\s*</td>', '', cleaned, flags=re.IGNORECASE)

        # Remove any remaining HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        # Remove unwanted prefixes
        lines = cleaned.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            # Skip lines that are just artifacts
            if (line.startswith('# document:') or
                line.startswith('<|') or
                line.endswith('|>') or
                re.match(r'^\s*\[\[.*\]\]\s*$', line) or  # Lines that are just coordinates
                re.match(r'^\s*$', line)):  # Empty lines
                continue
            filtered_lines.append(line)

        cleaned = '\n'.join(filtered_lines).strip()

        # Clean up multiple consecutive empty lines
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)

        # Extract text from any remaining structured data
        # Look for patterns like "text content" within brackets or quotes
        text_matches = re.findall(r'"([^"]+)"|\'([^\']+)\'', cleaned)
        if text_matches and not cleaned.strip():
            # If we only found quoted text and no other content, use it
            extracted_text = []
            for match in text_matches:
                text = match[0] or match[1]
                if text.strip():
                    extracted_text.append(text.strip())
            if extracted_text:
                cleaned = '\n'.join(extracted_text)

        # Final cleanup - ensure we have meaningful content
        cleaned = cleaned.strip()

        # If content is too short or looks like coordinates/artifacts, return placeholder
        if (not cleaned or
            len(cleaned.strip()) < 10 or
            re.match(r'^[\[\]\d\s,]+$', cleaned.strip()) or  # Only coordinates
            cleaned.lower().strip() in ['image', 'table', 'text']):  # Only detection types
            return "[No readable text extracted from image - model returned layout detection data only]"

        return cleaned

    except Exception as e:
        logger.error(f"Error post-processing deepseek-ocr output: {e}")
        # Return the original output if post-processing fails
        return raw_output.strip() if raw_output else "[Error processing OCR output]"


class OCRTask(Task):
    """Base class for OCR tasks with enhanced error handling and logging."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"OCR Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"OCR Task {task_id} completed successfully")


@celery_app.task(base=OCRTask, bind=True, max_retries=3, default_retry_delay=60, time_limit=3600, soft_time_limit=3000)
def process_ocr_workflow_task(self, workflow_id: str, ocr_model: str, image_paths: List[str], batch_name: str = "Default Batch", user_id: str = "system"):
    """Celery task for processing OCR workflow."""
    logger.info(f"OCR task called with workflow_id={workflow_id}, user_id={user_id}, model={ocr_model}, images={len(image_paths)}")

    # Use synchronous database session for Celery tasks
    with get_celery_db_session() as db:
        return _process_ocr_workflow_sync(self, db, workflow_id, ocr_model, image_paths, batch_name, user_id)


def _process_ocr_workflow_sync(
    task: OCRTask,
    db,
    workflow_id: str,
    ocr_model: str,
    image_paths: List[str],
    batch_name: str,
    user_id: str
) -> Dict[str, Any]:
    """Synchronous implementation of OCR workflow processing."""
    logger.info(f"Starting OCR workflow processing for workflow {workflow_id}, user {user_id}, model {ocr_model}, {len(image_paths)} images")
    workflow_uuid = UUID(workflow_id)

    # Get or create workflow
    workflow = db.query(OCRWorkflow).filter(OCRWorkflow.id == workflow_uuid).first()
    if not workflow:
        logger.info(f"Creating new workflow {workflow_id}")
        workflow = OCRWorkflow(
            id=workflow_uuid,
            user_id=user_id,
            workflow_name="OCR Workflow",
            ocr_model=ocr_model,
            status="running"
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
    else:
        logger.info(f"Found existing workflow {workflow_id}")

    workflow.status = "running"
    workflow.started_at = datetime.utcnow()
    workflow.total_images = len(image_paths)  # Set total images for progress tracking
    db.commit()

    # Create initial log
    _log_workflow_progress_sync(db, workflow_uuid, None, None,
                               f"Started OCR processing for {len(image_paths)} images", "info", user_id)

    # Create batch
    batch = OCRBatch(
        workflow_id=workflow_uuid,
        batch_name=batch_name,
        total_images=len(image_paths),
        status="processing"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

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

            # OCR with Ollama - use the selected model directly
            # The intelligent model selection system handles availability
            selected_model = ocr_model

            # Use appropriate prompt based on model type
            if 'llama3.2-vision' in selected_model.lower():
                prompt = """
                Analyze this image and extract all visible text. Convert the text to clean, well-formatted Markdown.

                Instructions:
                - Extract ALL text from the image exactly as it appears
                - Use proper Markdown formatting for headers, lists, tables, etc.
                - For tables, use Markdown table syntax
                - Preserve the original structure and formatting as much as possible
                - Do not add any introductory text or explanations
                - Return only the extracted text in Markdown format
                """
            else:  # deepseek-ocr and other models
                prompt = """
                Perform high-quality OCR on this image.
                1. Extract ALL text exactly as it appears.
                2. Preserve formatting (headers, lists, tables) using Markdown.
                3. If there are tables, format them as Markdown tables.
                4. Do not add conversational filler (like "Here is the text"). Just provide the Markdown content.
                """

            logger.info(f"Sending OCR request to Ollama model {ocr_model} for image {os.path.basename(image_path)}")
            logger.info(f"Image size: {len(image_data)} bytes, base64 encoded length: {len(image_data)}")
            _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                       f"Sending image {i+1} to {ocr_model}...", "info", user_id)

            # Add detailed logging for timeout configuration
            logger.info(f"Current Celery task time limits - hard: {task.request.time_limit if hasattr(task.request, 'time_limit') else 'N/A'}, soft: {task.request.soft_time_limit if hasattr(task.request, 'soft_time_limit') else 'N/A'}")

            try:
                # Use shorter timeout for OCR operations (2 minutes total, 90 seconds read)
                logger.info(f"Making Ollama API call to {selected_model} with image size: {len(image_data)} chars")
                logger.info(f"Starting OCR processing at: {datetime.utcnow().isoformat()}")
                start_time = datetime.utcnow()

                # Add explicit timeout handling for Ollama client
                from app.services.ollama_client import ollama_client
                import asyncio

                # Set a generous timeout for OCR operations (30 minutes)
                try:
                    # Use the chat API endpoint for deepseek-ocr model as recommended
                    if 'deepseek-ocr' in selected_model.lower():
                        # Use chat API with proper prompt format for deepseek-ocr
                        logger.info(f"Using chat API endpoint for deepseek-ocr model")
                        response = sync_ollama_client.chat(
                            model=selected_model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": "# document: <image>\n<|grounding|>Convert the document to markdown.",
                                    "images": [image_data]
                                }
                            ],
                            options={
                                "temperature": 0.1,
                                "top_p": 0.9,
                                "num_ctx": 4096  # Ensure enough context for full page
                            },
                            timeout=1800  # 30 minutes timeout for OCR
                        )
                    else:
                        # Use generate API for other models
                        logger.info(f"Using generate API endpoint for {selected_model} model")
                        response = sync_ollama_client.generate(
                            prompt=prompt,
                            model=selected_model,
                            options={
                                "images": [image_data],
                                "temperature": 0.1,
                                "top_p": 0.9,
                                "num_ctx": 4096  # Ensure enough context for full page
                            },
                            timeout=1800  # 30 minutes timeout for OCR
                        )
                except Exception as e:
                    logger.error(f"Ollama client error with extended timeout: {str(e)}")
                    raise

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"Received OCR response from Ollama in {duration:.2f} seconds")
                logger.info(f"Response keys: {list(response.keys()) if response else 'None'}")
                logger.info(f"Response has 'response' key: {'response' in response if response else False}")

                # Log the actual response content for debugging
                if response:
                    if 'response' in response:
                        response_content = response['response']
                        logger.info(f"OCR response length: {len(response_content)} characters")
                        logger.info(f"OCR response preview: {response_content[:200] if len(response_content) > 200 else response_content}")
                        ocr_text = response_content.strip()
                    elif 'message' in response and 'content' in response['message']:
                        # Handle chat API response format
                        response_content = response['message']['content']
                        logger.info(f"OCR response length: {len(response_content)} characters")
                        logger.info(f"OCR response preview: {response_content[:200] if len(response_content) > 200 else response_content}")

                        # Post-process deepseek-ocr raw output to clean markdown
                        if 'deepseek-ocr' in selected_model.lower():
                            ocr_text = _post_process_deepseek_ocr_output(response_content)
                        else:
                            ocr_text = response_content.strip()
                    else:
                        logger.warning(f"Unexpected response format: {list(response.keys())}")
                        ocr_text = f"[Unexpected response format: {list(response.keys())}]"
                else:
                    logger.error("Empty response received from Ollama API")
                    ocr_text = "[Empty response received from Ollama API]"

                if not ocr_text:
                    logger.warning(f"Empty OCR response for image {os.path.basename(image_path)}")
                    ocr_text = f"[No text extracted from {os.path.basename(image_path)}]"
                    _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                               f"Warning: No text extracted from image {i+1}", "warning", user_id)

            except Exception as ocr_error:
                error_msg = str(ocr_error)
                logger.error(f"OCR API call failed for image {os.path.basename(image_path)}: {error_msg}")

                # Check if it's a timeout-related error
                if "timeout" in error_msg.lower() or "time" in error_msg.lower():
                    ocr_text = f"[OCR timed out for {os.path.basename(image_path)}: {error_msg}]"
                    _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                               f"OCR API timed out for image {i+1}: {error_msg}", "error", user_id)
                else:
                    ocr_text = f"[OCR failed for {os.path.basename(image_path)}: {error_msg}]"
                    _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                               f"OCR API failed for image {i+1}: {error_msg}", "error", user_id)

            # Create image record
            image_record = OCRImage(
                batch_id=batch.id,
                workflow_id=workflow_uuid,
                original_filename=os.path.basename(image_path),
                file_path=image_path,
                status="completed",
                processing_order=i,
                ocr_model_used=selected_model,
                raw_markdown=ocr_text,
                processed_markdown=ocr_text,  # For now, same as raw
                confidence_score=0.8,  # TODO: Extract from Ollama response if available
                processed_at=datetime.utcnow()
            )

            db.add(image_record)
            combined_markdown += f"\n\n--- Page {i+1} ---\n\n"
            combined_markdown += ocr_text
            processed_count += 1

            # Update batch and workflow progress
            batch.processed_images = processed_count
            workflow.processed_images = processed_count
            db.commit()

            # Log progress
            _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
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
            db.add(image_record)
            db.commit()  # Commit failure record

            _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                       f"Failed to process image {os.path.basename(image_path)}: {e}", "error", user_id)

    # Update batch completion
    batch.status = "completed"
    batch.combined_markdown = combined_markdown.strip()
    batch.page_count = processed_count
    batch.completed_at = datetime.utcnow()
    db.commit()

    # Determine workflow status based on processing results
    if processed_count == 0:
        # No images were processed successfully
        workflow.status = "failed"
        workflow.error_message = "No images were successfully processed"
        _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                   "OCR workflow failed: No images were successfully processed", "error", user_id)
    elif processed_count < len(image_paths):
        # Some images failed but some succeeded
        workflow.status = "completed"
        workflow.error_message = f"Partial success: {processed_count}/{len(image_paths)} images processed"
        _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                   f"OCR workflow completed with partial success: {processed_count}/{len(image_paths)} images processed", "warning", user_id)
    else:
        # All images processed successfully
        workflow.status = "completed"
        _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                                   f"OCR workflow completed successfully: {processed_count} images processed", "success", user_id)

    # Update workflow completion stats
    workflow.total_images = len(image_paths)
    workflow.processed_images = processed_count
    workflow.total_pages = processed_count
    workflow.completed_at = datetime.utcnow()

    # Log final completion details
    logger.info(f"OCR workflow completed - Total images: {len(image_paths)}, Processed: {processed_count}")
    logger.info(f"Final combined markdown length: {len(combined_markdown)} characters")
    logger.info(f"Final markdown preview: {combined_markdown[:500] if len(combined_markdown) > 500 else combined_markdown}")

    db.commit()

    # Broadcast WebSocket update for workflow completion
    _broadcast_workflow_update_sync(db, workflow_uuid, workflow.status, user_id)

    # Log completion
    _log_workflow_progress_sync(db, workflow_uuid, batch.id, None,
                               f"OCR workflow completed: {processed_count} images processed", "info", user_id)

    # Send notification
    _send_completion_notification_sync(db, workflow.user_id, workflow_uuid, batch.id, processed_count)

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


def _log_workflow_progress_sync(
    db,
    workflow_id: UUID,
    batch_id = None,
    image_id = None,
    message: str = "",
    level: str = "info",
    user_id: str = "system"
):
    """Log workflow progress synchronously."""
    from datetime import datetime

    # Use UTC timezone for all backend timestamps (best practice)
    current_time_utc = datetime.utcnow()

    log_entry = OCRWorkflowLog(
        workflow_id=workflow_id,
        batch_id=batch_id,
        image_id=image_id,
        user_id=user_id,
        level=level,
        message=message,
        workflow_phase="processing",
        timestamp=current_time_utc  # Use UTC timezone timestamp (backend standard)
    )
    db.add(log_entry)
    db.commit()


def _broadcast_workflow_update_sync(
    db,
    workflow_id: UUID,
    status: str,
    user_id: str
) -> None:
    """Broadcast OCR workflow status update via WebSocket synchronously."""
    try:
        from app.api.routes.websocket import manager
        from app.db.models.ocr_workflow import OCRBatch

        # Get updated workflow data
        workflow = db.query(OCRWorkflow).filter(OCRWorkflow.id == workflow_id).first()
        if not workflow:
            return

        # Get batch information
        batches = db.query(OCRBatch).filter(OCRBatch.workflow_id == workflow_id).all()

        # Broadcast to WebSocket connections
        message = {
            "type": "ocr_workflow_status",
            "workflow_id": str(workflow_id),
            "status": status,
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

        # Broadcast to all connections subscribed to this workflow
        # Fix async await issue
        import asyncio
        asyncio.run(manager.broadcast_workflow_update(message, user_id, str(workflow_id)))

    except Exception as e:
        logger.error(f"Failed to broadcast OCR workflow update: {e}")


def _send_completion_notification_sync(
    db,
    user_id: str,
    workflow_id: UUID,
    batch_id: UUID,
    processed_count: int
) -> None:
    """Send completion notification synchronously."""
    try:
        # Fix notification parameter names to match Notification model
        notification = Notification(
            user_id=user_id,
            notification_title="OCR Processing Complete",
            notification_message=f"Your OCR workflow has completed processing {processed_count} images.",
            notification_type="ocr_complete",
            metadata={
                "workflow_id": str(workflow_id),
                "batch_id": str(batch_id),
                "processed_count": processed_count
            }
        )
        db.add(notification)
        db.commit()

        # Publish to pubsub for real-time updates
        pubsub_service.publish(
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