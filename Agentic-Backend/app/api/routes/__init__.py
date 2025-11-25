from fastapi import APIRouter
from .agents import router as agents_router
from .tasks import router as tasks_router
from .logs import router as logs_router
from .health import router as health_router
from .websocket import router as websocket_router
from .auth import router as auth_router
from .security import router as security_router
from .system_metrics import router as system_metrics_router
from .ollama import router as ollama_router
from .secrets import router as secrets_router
from .chat import router as chat_router
from .agent_builder import router as agent_builder_router
from .http_client import router as http_client_router
from .model_selection import router as model_selection_router
from .content_framework import router as content_framework_router
from .semantic_processing import router as semantic_processing_router
from .content import router as content_router
from .analytics import router as analytics_router
from .personalization import router as personalization_router
from .trends import router as trends_router
from .search_analytics import router as search_analytics_router

# Phase 2 Content Connectors
from .connectors import router as connectors_router

# Phase 3 AI Features
from .vision import router as vision_router
from .audio import router as audio_router
from .semantic import router as semantic_router

# Phase 5 Orchestration & Automation
from .workflow_automation import router as workflow_automation_router
from .integration_layer import router as integration_layer_router

# Phase 4 Advanced Features
from .automated_followups import router as automated_followups_router
from .performance_cache import router as performance_cache_router
from .security_service import router as security_service_router
from .advanced_analytics import router as advanced_analytics_router

# Knowledge Base Workflow System
from .knowledge_base_presenter import router as knowledge_base_router

# Email Workflow System
from .email_workflow import router as email_workflow_router
from .email_chat import router as email_chat_router
from .email_search import router as email_search_router
from .email_assistant import router as email_assistant_router
from .email_sync import router as email_sync_router

# OCR Workflow System
from .ocr_workflow import router as ocr_workflow_router

# Phase 3: Monitoring & Observability
from .monitoring import router as monitoring_router

# Global routes (shared across workflows)
from .shared import router as global_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(security_router, prefix="/security", tags=["security"])
api_router.include_router(system_metrics_router, tags=["system"])
api_router.include_router(ollama_router, prefix="/ollama", tags=["ollama"])
api_router.include_router(secrets_router, tags=["secrets"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(agent_builder_router, prefix="/agent-builder", tags=["agent-builder"])

# Phase 1 New Services
api_router.include_router(http_client_router, tags=["HTTP Client"])
api_router.include_router(model_selection_router, tags=["Model Selection"])
api_router.include_router(content_framework_router, tags=["Content Framework"])
api_router.include_router(semantic_processing_router, tags=["Semantic Processing"])

# Phase 2 Content Connectors
api_router.include_router(content_router, tags=["Content Connectors"])
api_router.include_router(connectors_router, prefix="/connectors", tags=["Content Connectors"])

# Phase 4 Analytics & Intelligence
api_router.include_router(analytics_router, tags=["Analytics & Insights"])
api_router.include_router(personalization_router, tags=["Personalization"])
api_router.include_router(trends_router, tags=["Trend Detection & Analytics"])
api_router.include_router(search_analytics_router, tags=["Search Analytics"])
api_router.include_router(automated_followups_router, tags=["Automated Follow-ups"])
api_router.include_router(performance_cache_router, tags=["Performance Cache"])
api_router.include_router(security_service_router, tags=["Security Service"])
api_router.include_router(advanced_analytics_router, tags=["Advanced Analytics"])

# Phase 3 AI Features
api_router.include_router(vision_router, prefix="/vision", tags=["Vision AI"])
api_router.include_router(audio_router, prefix="/audio", tags=["Audio AI"])
api_router.include_router(semantic_router, prefix="/semantic", tags=["Semantic Processing"])

# Phase 5 Orchestration & Automation
api_router.include_router(workflow_automation_router, prefix="/workflows", tags=["Workflow Automation"])
api_router.include_router(integration_layer_router, tags=["Integration Layer"])

# Knowledge Base Workflow System
api_router.include_router(knowledge_base_router, tags=["Knowledge Base"])

# Email Workflow System
api_router.include_router(email_workflow_router, prefix="/email", tags=["Email Workflow"])
api_router.include_router(email_chat_router, prefix="/email", tags=["Email Chat"])
api_router.include_router(email_search_router, prefix="/email", tags=["Email Search"])
api_router.include_router(email_assistant_router, prefix="/email-assistant", tags=["Email Assistant"])
api_router.include_router(email_sync_router, prefix="/email-sync", tags=["Email Synchronization"])

# Global routes (shared across workflows)
api_router.include_router(global_router, prefix="/global", tags=["Global"])

# OCR Workflow System
api_router.include_router(ocr_workflow_router, prefix="/ocr", tags=["OCR Workflow"])

# Phase 3: Monitoring & Observability
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring & Observability"])


# WebSocket routes don't use /api/v1 prefix
ws_router = APIRouter()
ws_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])

__all__ = ["api_router", "ws_router"]