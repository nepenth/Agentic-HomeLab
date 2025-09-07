"""
Performance Optimization Service for automated model selection and routing.

This service provides intelligent performance optimization capabilities including:
- Automated model selection based on task requirements
- Performance monitoring and analytics
- Load balancing across models
- Resource-aware routing
- Cost optimization
- Real-time performance adaptation
- Model performance benchmarking
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

from app.config import settings
from app.services.ollama_client import ollama_client
from app.utils.logging import get_logger

logger = get_logger("performance_optimization_service")


class PerformanceOptimizationError(Exception):
    """Raised when performance optimization fails."""
    pass


class ModelPerformanceMetrics:
    """Performance metrics for a model."""

    def __init__(
        self,
        model_name: str,
        task_type: str,
        avg_response_time: float = None,
        avg_tokens_per_second: float = None,
        success_rate: float = None,
        total_requests: int = None,
        error_count: int = None,
        last_updated: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        self.model_name = model_name
        self.task_type = task_type
        self.avg_response_time = avg_response_time
        self.avg_tokens_per_second = avg_tokens_per_second
        self.success_rate = success_rate
        self.total_requests = total_requests or 0
        self.error_count = error_count or 0
        self.last_updated = last_updated or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "model_name": self.model_name,
            "task_type": self.task_type,
            "avg_response_time": self.avg_response_time,
            "avg_tokens_per_second": self.avg_tokens_per_second,
            "success_rate": self.success_rate,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata
        }


class OptimizationResult:
    """Result of performance optimization analysis."""

    def __init__(
        self,
        optimization_id: str,
        recommended_models: Dict[str, str],
        performance_improvements: Dict[str, float],
        cost_savings: float = None,
        processing_time_ms: float = None,
        recommendations: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.optimization_id = optimization_id
        self.recommended_models = recommended_models
        self.performance_improvements = performance_improvements
        self.cost_savings = cost_savings
        self.processing_time_ms = processing_time_ms
        self.recommendations = recommendations or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "optimization_id": self.optimization_id,
            "recommended_models": self.recommended_models,
            "performance_improvements": self.performance_improvements,
            "cost_savings": self.cost_savings,
            "processing_time_ms": self.processing_time_ms,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class PerformanceOptimizationService:
    """Service for optimizing AI model performance and selection."""

    def __init__(self):
        self.default_model = getattr(settings, 'performance_optimization_default_model', 'llama2:13b')
        self.processing_timeout = getattr(settings, 'performance_optimization_timeout_seconds', 300)

        # Performance tracking
        self.model_metrics: Dict[str, Dict[str, ModelPerformanceMetrics]] = defaultdict(dict)
        self.request_history: List[Dict[str, Any]] = []

        # Optimization thresholds
        self.performance_thresholds = {
            "max_response_time": 30.0,  # seconds
            "min_success_rate": 0.95,   # 95%
            "min_tokens_per_second": 10.0,
            "max_error_rate": 0.05      # 5%
        }

        # Model capabilities and costs (example data)
        self.model_profiles = {
            "llama2:7b": {
                "capabilities": ["text_generation", "classification"],
                "performance_score": 0.7,
                "cost_per_token": 0.001,
                "max_tokens": 4096
            },
            "llama2:13b": {
                "capabilities": ["text_generation", "classification", "analysis"],
                "performance_score": 0.85,
                "cost_per_token": 0.002,
                "max_tokens": 4096
            },
            "codellama:7b": {
                "capabilities": ["code_generation", "code_analysis"],
                "performance_score": 0.8,
                "cost_per_token": 0.0015,
                "max_tokens": 2048
            },
            "llava:7b": {
                "capabilities": ["vision", "image_captioning"],
                "performance_score": 0.75,
                "cost_per_token": 0.0025,
                "max_tokens": 512
            }
        }

    async def select_optimal_model(
        self,
        task_type: str,
        content_data: Dict[str, Any],
        constraints: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """
        Select the optimal model for a given task and content.

        Args:
            task_type: Type of task (text_generation, classification, vision, etc.)
            content_data: Content data for analysis
            constraints: Performance and cost constraints
            **kwargs: Additional selection parameters

        Returns:
            Optimal model name
        """
        try:
            constraints = constraints or {}

            # Get available models for task type
            available_models = await self._get_available_models_for_task(task_type)

            if not available_models:
                logger.warning(f"No models available for task type: {task_type}")
                return self.default_model

            # Score models based on performance and constraints
            model_scores = {}

            for model_name in available_models:
                score = await self._score_model_for_task(
                    model_name, task_type, content_data, constraints, **kwargs
                )
                model_scores[model_name] = score

            # Select best model
            if model_scores:
                best_model = max(model_scores.keys(), key=lambda x: model_scores[x])
                logger.info(f"Selected optimal model: {best_model} for task {task_type} with score {model_scores[best_model]:.3f}")
                return best_model
            else:
                return self.default_model

        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            return self.default_model

    async def _get_available_models_for_task(self, task_type: str) -> List[str]:
        """Get models available for a specific task type."""
        try:
            # Get available models from Ollama
            models_response = await ollama_client.list_models()
            available_models = []

            if "models" in models_response:
                for model_info in models_response["models"]:
                    model_name = model_info.get("name", "")

                    # Check if model supports the task type
                    if model_name in self.model_profiles:
                        capabilities = self.model_profiles[model_name].get("capabilities", [])
                        if task_type in capabilities:
                            available_models.append(model_name)
                    else:
                        # If model not in profiles, assume it can handle general tasks
                        if task_type in ["text_generation", "classification"]:
                            available_models.append(model_name)

            return available_models

        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return [self.default_model]

    async def _score_model_for_task(
        self,
        model_name: str,
        task_type: str,
        content_data: Dict[str, Any],
        constraints: Dict[str, Any],
        **kwargs
    ) -> float:
        """Score a model for a specific task."""
        try:
            score = 0.0
            weights = {
                "performance": 0.4,
                "cost": 0.2,
                "capability": 0.2,
                "availability": 0.2
            }

            # Performance score
            perf_metrics = self.model_metrics.get(model_name, {}).get(task_type)
            if perf_metrics:
                perf_score = self._calculate_performance_score(perf_metrics, constraints)
                score += perf_score * weights["performance"]
            else:
                # Default performance score
                score += 0.5 * weights["performance"]

            # Cost score (lower cost is better)
            model_profile = self.model_profiles.get(model_name, {})
            cost_per_token = model_profile.get("cost_per_token", 0.002)
            max_cost = constraints.get("max_cost_per_token", 0.005)
            cost_score = max(0, 1 - (cost_per_token / max_cost))
            score += cost_score * weights["cost"]

            # Capability score
            capabilities = model_profile.get("capabilities", [])
            capability_score = 1.0 if task_type in capabilities else 0.3
            score += capability_score * weights["capability"]

            # Availability score (simplified)
            availability_score = 1.0  # Assume all models are available
            score += availability_score * weights["availability"]

            return score

        except Exception as e:
            logger.error(f"Model scoring failed: {e}")
            return 0.5

    def _calculate_performance_score(
        self,
        metrics: ModelPerformanceMetrics,
        constraints: Dict[str, Any]
    ) -> float:
        """Calculate performance score based on metrics and constraints."""
        try:
            score = 0.0
            factors = 0

            # Response time score
            if metrics.avg_response_time is not None:
                max_time = constraints.get("max_response_time", self.performance_thresholds["max_response_time"])
                time_score = max(0, 1 - (metrics.avg_response_time / max_time))
                score += time_score
                factors += 1

            # Success rate score
            if metrics.success_rate is not None:
                success_score = metrics.success_rate
                score += success_score
                factors += 1

            # Tokens per second score
            if metrics.avg_tokens_per_second is not None:
                min_tps = constraints.get("min_tokens_per_second", self.performance_thresholds["min_tokens_per_second"])
                tps_score = min(1.0, metrics.avg_tokens_per_second / min_tps)
                score += tps_score
                factors += 1

            return score / factors if factors > 0 else 0.5

        except Exception as e:
            logger.error(f"Performance score calculation failed: {e}")
            return 0.5

    async def record_model_performance(
        self,
        model_name: str,
        task_type: str,
        response_time: float,
        tokens_generated: int,
        success: bool,
        error_type: str = None,
        **kwargs
    ):
        """
        Record model performance metrics.

        Args:
            model_name: Name of the model
            task_type: Type of task performed
            response_time: Response time in seconds
            tokens_generated: Number of tokens generated
            success: Whether the request was successful
            error_type: Type of error if any
            **kwargs: Additional metadata
        """
        try:
            # Get or create metrics
            if model_name not in self.model_metrics:
                self.model_metrics[model_name] = {}

            if task_type not in self.model_metrics[model_name]:
                self.model_metrics[model_name][task_type] = ModelPerformanceMetrics(
                    model_name=model_name,
                    task_type=task_type
                )

            metrics = self.model_metrics[model_name][task_type]

            # Update metrics
            total_requests = metrics.total_requests + 1
            metrics.total_requests = total_requests

            if success:
                # Update response time (rolling average)
                if metrics.avg_response_time is None:
                    metrics.avg_response_time = response_time
                else:
                    metrics.avg_response_time = (
                        metrics.avg_response_time * (total_requests - 1) + response_time
                    ) / total_requests

                # Update tokens per second
                if response_time > 0 and tokens_generated > 0:
                    tokens_per_second = tokens_generated / response_time
                    if metrics.avg_tokens_per_second is None:
                        metrics.avg_tokens_per_second = tokens_per_second
                    else:
                        metrics.avg_tokens_per_second = (
                            metrics.avg_tokens_per_second * (total_requests - 1) + tokens_per_second
                        ) / total_requests

                # Update success rate
                successful_requests = total_requests - metrics.error_count
                metrics.success_rate = successful_requests / total_requests

            else:
                metrics.error_count += 1
                metrics.success_rate = (total_requests - metrics.error_count) / total_requests

            metrics.last_updated = datetime.now()

            # Store request history
            self.request_history.append({
                "model_name": model_name,
                "task_type": task_type,
                "response_time": response_time,
                "tokens_generated": tokens_generated,
                "success": success,
                "error_type": error_type,
                "timestamp": datetime.now(),
                **kwargs
            })

            # Keep only recent history
            if len(self.request_history) > 10000:
                self.request_history = self.request_history[-5000:]

        except Exception as e:
            logger.error(f"Performance recording failed: {e}")

    async def optimize_model_selection(
        self,
        workload_analysis: Dict[str, Any] = None,
        **kwargs
    ) -> OptimizationResult:
        """
        Perform comprehensive optimization of model selection.

        Args:
            workload_analysis: Analysis of expected workload
            **kwargs: Additional optimization parameters

        Returns:
            OptimizationResult with recommendations
        """
        start_time = datetime.now()
        optimization_id = f"opt_{int(datetime.now().timestamp())}"

        try:
            # Analyze current performance
            current_performance = await self._analyze_current_performance()

            # Generate recommendations
            recommended_models = {}
            performance_improvements = {}

            # Analyze each task type
            task_types = set()
            for model_metrics in self.model_metrics.values():
                task_types.update(model_metrics.keys())

            for task_type in task_types:
                # Find best model for this task type
                best_model = await self._find_best_model_for_task_type(task_type)
                if best_model:
                    recommended_models[task_type] = best_model

                    # Estimate performance improvement
                    current_avg_time = current_performance.get(f"{task_type}_avg_time", 10.0)
                    improvement = await self._estimate_performance_improvement(
                        task_type, best_model, current_avg_time
                    )
                    performance_improvements[task_type] = improvement

            # Calculate cost savings
            cost_savings = await self._calculate_cost_savings(recommended_models)

            # Generate recommendations
            recommendations = await self._generate_optimization_recommendations(
                recommended_models, performance_improvements, cost_savings
            )

            result = OptimizationResult(
                optimization_id=optimization_id,
                recommended_models=recommended_models,
                performance_improvements=performance_improvements,
                cost_savings=cost_savings,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                recommendations=recommendations
            )

            logger.info(f"Performance optimization completed: {len(recommended_models)} recommendations generated")
            return result

        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            raise PerformanceOptimizationError(f"Performance optimization failed: {str(e)}")

    async def _analyze_current_performance(self) -> Dict[str, Any]:
        """Analyze current system performance."""
        try:
            analysis = {}

            # Aggregate metrics by task type
            task_metrics = defaultdict(list)

            for model_name, model_data in self.model_metrics.items():
                for task_type, metrics in model_data.items():
                    task_metrics[task_type].append(metrics)

            # Calculate averages
            for task_type, metrics_list in task_metrics.items():
                if metrics_list:
                    avg_response_time = statistics.mean(
                        [m.avg_response_time for m in metrics_list if m.avg_response_time]
                    )
                    avg_success_rate = statistics.mean(
                        [m.success_rate for m in metrics_list if m.success_rate]
                    )

                    analysis[f"{task_type}_avg_time"] = avg_response_time
                    analysis[f"{task_type}_avg_success"] = avg_success_rate

            return analysis

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {}

    async def _find_best_model_for_task_type(self, task_type: str) -> Optional[str]:
        """Find the best performing model for a task type."""
        try:
            best_model = None
            best_score = -1

            for model_name, model_data in self.model_metrics.items():
                if task_type in model_data:
                    metrics = model_data[task_type]
                    score = self._calculate_performance_score(metrics, {})
                    if score > best_score:
                        best_score = score
                        best_model = model_name

            return best_model

        except Exception as e:
            logger.error(f"Best model finding failed: {e}")
            return None

    async def _estimate_performance_improvement(
        self,
        task_type: str,
        model_name: str,
        current_avg_time: float
    ) -> float:
        """Estimate performance improvement for a model."""
        try:
            metrics = self.model_metrics.get(model_name, {}).get(task_type)
            if metrics and metrics.avg_response_time:
                improvement = (current_avg_time - metrics.avg_response_time) / current_avg_time
                return max(0, improvement)
            else:
                return 0.1  # Assume 10% improvement if no data

        except Exception as e:
            logger.error(f"Performance improvement estimation failed: {e}")
            return 0.0

    async def _calculate_cost_savings(self, recommended_models: Dict[str, str]) -> float:
        """Calculate potential cost savings from optimization."""
        try:
            # Simplified cost calculation
            total_savings = 0.0

            for task_type, model_name in recommended_models.items():
                model_profile = self.model_profiles.get(model_name, {})
                cost_per_token = model_profile.get("cost_per_token", 0.002)

                # Estimate monthly usage (simplified)
                estimated_tokens_per_month = 100000  # Example
                savings_per_task = cost_per_token * estimated_tokens_per_month * 0.1  # 10% savings
                total_savings += savings_per_task

            return total_savings

        except Exception as e:
            logger.error(f"Cost savings calculation failed: {e}")
            return 0.0

    async def _generate_optimization_recommendations(
        self,
        recommended_models: Dict[str, str],
        performance_improvements: Dict[str, float],
        cost_savings: float
    ) -> List[str]:
        """Generate optimization recommendations."""
        try:
            recommendations = []

            # Model recommendations
            if recommended_models:
                recommendations.append(f"Implement model routing for {len(recommended_models)} task types")

            # Performance recommendations
            significant_improvements = [
                task for task, improvement in performance_improvements.items()
                if improvement > 0.2
            ]
            if significant_improvements:
                recommendations.append(f"Expected >20% performance improvement for: {', '.join(significant_improvements)}")

            # Cost recommendations
            if cost_savings > 100:
                recommendations.append(".2f")

            # Monitoring recommendations
            recommendations.append("Set up continuous performance monitoring")
            recommendations.append("Implement automatic model switching based on performance")

            return recommendations

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Continue monitoring performance and implement gradual optimizations"]

    def get_performance_metrics(
        self,
        model_name: str = None,
        task_type: str = None
    ) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            if model_name and task_type:
                metrics = self.model_metrics.get(model_name, {}).get(task_type)
                return metrics.to_dict() if metrics else {}
            elif model_name:
                return {
                    task: metrics.to_dict()
                    for task, metrics in self.model_metrics.get(model_name, {}).items()
                }
            elif task_type:
                # Aggregate across models
                task_metrics = {}
                for model_name, model_data in self.model_metrics.items():
                    if task_type in model_data:
                        task_metrics[model_name] = model_data[task_type].to_dict()
                return task_metrics
            else:
                # Return all metrics
                return {
                    model_name: {
                        task: metrics.to_dict()
                        for task, metrics in model_data.items()
                    }
                    for model_name, model_data in self.model_metrics.items()
                }

        except Exception as e:
            logger.error(f"Metrics retrieval failed: {e}")
            return {"error": str(e)}

    async def benchmark_models(
        self,
        models: List[str],
        test_tasks: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Benchmark multiple models on test tasks.

        Args:
            models: List of model names to benchmark
            test_tasks: List of test tasks
            **kwargs: Additional benchmarking parameters

        Returns:
            Benchmarking results
        """
        try:
            results = {}

            for model_name in models:
                model_results = []

                for task in test_tasks:
                    start_time = time.time()

                    try:
                        # Execute task with model
                        response = await ollama_client.generate(
                            model=model_name,
                            prompt=task.get("prompt", ""),
                            options={
                                "temperature": kwargs.get("temperature", 0.1),
                                "num_predict": kwargs.get("max_tokens", 100)
                            }
                        )

                        response_time = time.time() - start_time
                        tokens_generated = len(response.get("response", "").split())

                        model_results.append({
                            "task_id": task.get("id", ""),
                            "response_time": response_time,
                            "tokens_generated": tokens_generated,
                            "success": True
                        })

                        # Record performance
                        await self.record_model_performance(
                            model_name=model_name,
                            task_type=task.get("type", "benchmark"),
                            response_time=response_time,
                            tokens_generated=tokens_generated,
                            success=True
                        )

                    except Exception as e:
                        response_time = time.time() - start_time
                        model_results.append({
                            "task_id": task.get("id", ""),
                            "response_time": response_time,
                            "error": str(e),
                            "success": False
                        })

                        # Record error
                        await self.record_model_performance(
                            model_name=model_name,
                            task_type=task.get("type", "benchmark"),
                            response_time=response_time,
                            tokens_generated=0,
                            success=False,
                            error_type=str(e)
                        )

                # Calculate aggregate metrics
                successful_tasks = [r for r in model_results if r["success"]]
                if successful_tasks:
                    avg_response_time = statistics.mean([r["response_time"] for r in successful_tasks])
                    avg_tokens_per_second = statistics.mean([
                        r["tokens_generated"] / r["response_time"] for r in successful_tasks
                        if r["response_time"] > 0
                    ])
                    success_rate = len(successful_tasks) / len(model_results)

                    results[model_name] = {
                        "avg_response_time": avg_response_time,
                        "avg_tokens_per_second": avg_tokens_per_second,
                        "success_rate": success_rate,
                        "total_tasks": len(model_results),
                        "successful_tasks": len(successful_tasks)
                    }
                else:
                    results[model_name] = {
                        "error": "No successful tasks",
                        "total_tasks": len(model_results),
                        "successful_tasks": 0
                    }

            return results

        except Exception as e:
            logger.error(f"Model benchmarking failed: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the performance optimization service."""
        try:
            # Test basic Ollama connectivity
            health = await ollama_client.health_check()

            metrics_count = sum(len(model_data) for model_data in self.model_metrics.values())
            history_count = len(self.request_history)

            return {
                "service": "performance_optimization",
                "status": "healthy" if health.get("status") == "healthy" else "degraded",
                "ollama_status": health.get("status"),
                "tracked_models": len(self.model_metrics),
                "total_metrics": metrics_count,
                "request_history_size": history_count,
                "default_model": self.default_model
            }

        except Exception as e:
            return {
                "service": "performance_optimization",
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
performance_optimization_service = PerformanceOptimizationService()