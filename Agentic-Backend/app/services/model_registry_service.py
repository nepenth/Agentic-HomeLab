"""
Enhanced Model Registry Service with Database-Backed Benchmark Integration
"""
import asyncio
import pandas as pd
from datasets import load_dataset
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, or_
from sqlalchemy.sql import func
import json

from app.utils.logging import get_logger
from app.db.models import ModelBenchmark
from app.db.database import get_db

logger = get_logger("model_registry_service")


class ModelRegistryService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.memory_cache = {}  # In-memory cache for performance
        self.cache_expiry = timedelta(hours=24)  # Cache for 24 hours
        self.last_cache_update = None

    async def get_db_session(self) -> AsyncSession:
        """Get database session, creating one if needed."""
        if self.db is not None:
            return self.db

        # Create new session if none exists
        async for session in get_db():
            return session

        raise RuntimeError("Could not create database session")

    async def get_model_benchmarks(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """Fetch and cache model benchmarks from Hugging Face Open LLM Leaderboard."""
        now = datetime.now()

        # Check memory cache first
        if not force_refresh and self.last_cache_update:
            # Ensure both datetimes are timezone-aware for comparison
            if isinstance(self.last_cache_update, datetime) and isinstance(now, datetime):
                try:
                    if now - self.last_cache_update < self.cache_expiry:
                        return self.memory_cache
                except TypeError:
                    # Handle naive vs aware datetime comparison
                    logger.warning("Datetime comparison issue, forcing refresh")
                    pass

        # Load from database
        session = await self.get_db_session()
        try:
            # Check if we need to refresh from source
            should_refresh = force_refresh
            if not should_refresh:
                # Check last update time
                result = await session.execute(
                    select(func.max(ModelBenchmark.last_updated))
                )
                last_update = result.scalar()
                if last_update and (now - last_update) < self.cache_expiry:
                    # Load from database cache
                    return await self._load_benchmarks_from_db(session)
                else:
                    should_refresh = True

            if should_refresh:
                try:
                    await self._fetch_and_store_benchmarks(session)
                except Exception as e:
                    logger.warning(f"Primary benchmark fetch failed, using fallback: {e}")
                    # Ensure fallback data is available
                    await self._ensure_fallback_data(session)

            # Load fresh data from database
            benchmarks = await self._load_benchmarks_from_db(session)
            self.memory_cache = benchmarks
            self.last_cache_update = now

            return benchmarks

        except Exception as e:
            logger.warning(f"Failed to get benchmarks: {e}")
            # Try to ensure fallback data is available
            try:
                session = await self.get_db_session()
                await self._ensure_fallback_data(session)
                # Try loading again
                benchmarks = await self._load_benchmarks_from_db(session)
                self.memory_cache = benchmarks
                self.last_cache_update = now
                return benchmarks
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                # Return memory cache if available
                return self.memory_cache if self.memory_cache else {}

    async def _fetch_and_store_benchmarks(self, session: AsyncSession):
        """Fetch benchmark data from Hugging Face and store in database."""
        try:
            logger.info("Fetching benchmark data from Hugging Face Open LLM Leaderboard")

            # Load benchmark data from Hugging Face
            ds = load_dataset("open-llm-leaderboard/results", split="train")
            df = pd.DataFrame(ds)

            # Clear old data for this source
            await session.execute(
                delete(ModelBenchmark).where(ModelBenchmark.source == "huggingface")
            )

            # Process and store benchmark data
            benchmark_records = []
            for _, row in df.iterrows():
                model_name = self._normalize_model_name(str(row['model_name']))

                benchmark_records.append({
                    'model_name': model_name,
                    'source': 'huggingface',
                    'average_score': float(row.get('Average ⬆️', 0) or 0),
                    'mmlu_score': float(row.get('MMLU-PRO', 0) or 0),
                    'gpqa_score': float(row.get('GPQA', 0) or 0),
                    'math_score': float(row.get('MATH', 0) or 0),
                    'humaneval_score': float(row.get('HumanEval', 0) or 0),
                    'bbh_score': float(row.get('BBH', 0) or 0),
                    'raw_data': json.dumps(dict(row)),
                    'last_updated': datetime.now()
                })

            # Bulk insert
            if benchmark_records:
                await session.execute(insert(ModelBenchmark), benchmark_records)
                await session.commit()

            logger.info(f"Successfully stored benchmarks for {len(benchmark_records)} models")

        except Exception as e:
            logger.warning(f"Failed to fetch Hugging Face benchmarks: {e}")
            # Fallback to static benchmark data for immediate functionality
            await self._store_fallback_benchmarks(session)

    async def _load_benchmarks_from_db(self, session: AsyncSession) -> Dict[str, Dict]:
        """Load benchmark data from database."""
        result = await session.execute(
            select(ModelBenchmark).where(
                or_(
                    ModelBenchmark.source == "huggingface",
                    ModelBenchmark.source == "fallback"
                )
            )
        )
        benchmarks = {}

        for benchmark in result.scalars():
            benchmarks[benchmark.model_name] = {
                'average_score': benchmark.average_score or 0,
                'mmlu': benchmark.mmlu_score or 0,
                'gpqa': benchmark.gpqa_score or 0,
                'math': benchmark.math_score or 0,
                'humaneval': benchmark.humaneval_score or 0,
                'bbh': benchmark.bbh_score or 0,
                'last_updated': benchmark.last_updated.isoformat() if benchmark.last_updated else None
            }

        return benchmarks

    async def cleanup_old_benchmarks(self, days_old: int = 30):
        """Clean up benchmark data older than specified days."""
        session = await self.get_db_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)

            result = await session.execute(
                delete(ModelBenchmark).where(
                    and_(
                        ModelBenchmark.source == "huggingface",
                        ModelBenchmark.last_updated < cutoff_date
                    )
                )
            )

            deleted_count = result.rowcount
            await session.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old benchmark records")

        except Exception as e:
            logger.error(f"Failed to cleanup old benchmarks: {e}")
            await session.rollback()

    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model names to match Ollama naming conventions."""
        # Remove organization prefixes, convert to lowercase
        name = model_name.lower()
        name = name.replace('meta-llama/', '').replace('microsoft/', '')

        # Handle common variations
        replacements = {
            'llama-3.1': 'llama3.1',
            'llama-3': 'llama3',
            'qwen2.5': 'qwen2.5',
            'deepseek-coder-v2': 'deepseek-coder'
        }

        for old, new in replacements.items():
            name = name.replace(old, new)

        return name

    async def get_model_ranking_score(self, model_name: str) -> float:
        """Calculate comprehensive ranking score for a model."""
        benchmarks = await self.get_model_benchmarks()

        # Base score from static intelligence
        base_score = self._get_base_model_score(model_name)

        # Benchmark bonus
        benchmark_bonus = 0
        model_benchmarks = benchmarks.get(model_name, {})
        if model_benchmarks:
            avg_score = model_benchmarks.get('average_score', 0)
            benchmark_bonus = min(avg_score * 0.5, 50)  # Max 50 points from benchmarks

        # Size optimization bonus
        size_bonus = self._calculate_size_bonus(model_name)

        # Recommendation bonus
        rec_bonus = 20 if self._is_recommended_model(model_name) else 0

        total_score = base_score + benchmark_bonus + size_bonus + rec_bonus
        return min(total_score, 100)  # Cap at 100

    def _get_base_model_score(self, model_name: str) -> float:
        """Get base score from static model intelligence."""
        # Extract base name for lookup
        base_name = model_name.split(':')[0].lower()

        # Base scores for known models
        base_scores = {
            'qwen3': 85,
            'qwen2.5': 75,
            'deepseek-r1': 80,
            'phi4': 70,
            'mistral-small3.1': 65,
            'codellama': 60,
            'llama3.3': 55,
            'granite4': 70,
            'openthinker': 75,
            'cogito': 75,
            'magistral': 70
        }

        return base_scores.get(base_name, 50)  # Default score

    def _calculate_size_bonus(self, model_name: str) -> float:
        """Calculate bonus based on model size (sweet spot 7B-30B)."""
        # Extract size from model name or runtime data
        size_gb = self._extract_model_size_gb(model_name)

        if 7 <= size_gb <= 30:
            return 15
        elif size_gb > 30:
            return 10
        else:
            return 5

    def _extract_model_size_gb(self, model_name: str) -> float:
        """Extract model size in GB from name."""
        import re

        # Look for size patterns like 7b, 13b, 30b, etc.
        match = re.search(r'(\d+(?:\.\d+)?)[bB]', model_name)
        if match:
            size_b = float(match.group(1))
            # Convert B (billions) to GB approximation
            return size_b * 1.2  # Rough conversion

        return 7  # Default assumption

    def _is_recommended_model(self, model_name: str) -> bool:
        """Check if model is recommended based on various criteria."""
        recommended_patterns = [
            'thinking', 'reasoning', 'r1', 'qwen3', 'deepseek-r1',
            'phi4', 'mistral-small3.1', 'granite4'
        ]
        return any(pattern in model_name.lower() for pattern in recommended_patterns)

    async def _store_fallback_benchmarks(self, session: AsyncSession):
        """Store fallback benchmark data when Hugging Face fetch fails."""
        try:
            logger.info("Using fallback benchmark data")

            # Clear old data for this source
            await session.execute(
                delete(ModelBenchmark).where(ModelBenchmark.source == "fallback")
            )

            # Static benchmark data based on known model performance
            # Include both base names and specific variants
            fallback_data = [
                # Base model names
                {
                    'model_name': 'qwen3',
                    'source': 'fallback',
                    'average_score': 85.0,
                    'mmlu_score': 82.0,
                    'gpqa_score': 78.0,
                    'math_score': 75.0,
                    'humaneval_score': 70.0,
                    'bbh_score': 68.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                # Specific Qwen3 variants
                {
                    'model_name': 'qwen3:30b',
                    'source': 'fallback',
                    'average_score': 85.0,
                    'mmlu_score': 82.0,
                    'gpqa_score': 78.0,
                    'math_score': 75.0,
                    'humaneval_score': 70.0,
                    'bbh_score': 68.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'qwen3:30b-a3b-instruct-2507-q8_0',
                    'source': 'fallback',
                    'average_score': 84.0,
                    'mmlu_score': 81.0,
                    'gpqa_score': 77.0,
                    'math_score': 74.0,
                    'humaneval_score': 69.0,
                    'bbh_score': 67.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'qwen3:30b-a3b-thinking-2507-q8_0',
                    'source': 'fallback',
                    'average_score': 86.0,
                    'mmlu_score': 83.0,
                    'gpqa_score': 79.0,
                    'math_score': 76.0,
                    'humaneval_score': 71.0,
                    'bbh_score': 69.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'qwen3:32b',
                    'source': 'fallback',
                    'average_score': 85.5,
                    'mmlu_score': 82.5,
                    'gpqa_score': 78.5,
                    'math_score': 75.5,
                    'humaneval_score': 70.5,
                    'bbh_score': 68.5,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'qwen3:8b',
                    'source': 'fallback',
                    'average_score': 80.0,
                    'mmlu_score': 77.0,
                    'gpqa_score': 73.0,
                    'math_score': 70.0,
                    'humaneval_score': 65.0,
                    'bbh_score': 63.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                # DeepSeek variants
                {
                    'model_name': 'deepseek-r1',
                    'source': 'fallback',
                    'average_score': 80.0,
                    'mmlu_score': 78.0,
                    'gpqa_score': 75.0,
                    'math_score': 85.0,
                    'humaneval_score': 72.0,
                    'bbh_score': 70.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'deepseek-r1:1.5b',
                    'source': 'fallback',
                    'average_score': 75.0,
                    'mmlu_score': 73.0,
                    'gpqa_score': 70.0,
                    'math_score': 80.0,
                    'humaneval_score': 67.0,
                    'bbh_score': 65.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'deepseek-r1:8b',
                    'source': 'fallback',
                    'average_score': 79.0,
                    'mmlu_score': 77.0,
                    'gpqa_score': 74.0,
                    'math_score': 84.0,
                    'humaneval_score': 71.0,
                    'bbh_score': 69.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'deepseek-r1:32b',
                    'source': 'fallback',
                    'average_score': 81.0,
                    'mmlu_score': 79.0,
                    'gpqa_score': 76.0,
                    'math_score': 86.0,
                    'humaneval_score': 73.0,
                    'bbh_score': 71.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'qwen2.5',
                    'source': 'fallback',
                    'average_score': 75.0,
                    'mmlu_score': 72.0,
                    'gpqa_score': 68.0,
                    'math_score': 70.0,
                    'humaneval_score': 65.0,
                    'bbh_score': 62.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'deepseek-r1',
                    'source': 'fallback',
                    'average_score': 80.0,
                    'mmlu_score': 78.0,
                    'gpqa_score': 75.0,
                    'math_score': 85.0,
                    'humaneval_score': 72.0,
                    'bbh_score': 70.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'phi4',
                    'source': 'fallback',
                    'average_score': 70.0,
                    'mmlu_score': 68.0,
                    'gpqa_score': 65.0,
                    'math_score': 72.0,
                    'humaneval_score': 75.0,
                    'bbh_score': 68.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'mistral-small3.1',
                    'source': 'fallback',
                    'average_score': 65.0,
                    'mmlu_score': 63.0,
                    'gpqa_score': 60.0,
                    'math_score': 68.0,
                    'humaneval_score': 62.0,
                    'bbh_score': 58.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'codellama',
                    'source': 'fallback',
                    'average_score': 60.0,
                    'mmlu_score': 58.0,
                    'gpqa_score': 55.0,
                    'math_score': 65.0,
                    'humaneval_score': 78.0,
                    'bbh_score': 52.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                },
                {
                    'model_name': 'llama3.3',
                    'source': 'fallback',
                    'average_score': 55.0,
                    'mmlu_score': 53.0,
                    'gpqa_score': 50.0,
                    'math_score': 58.0,
                    'humaneval_score': 52.0,
                    'bbh_score': 48.0,
                    'raw_data': json.dumps({'source': 'static_fallback'}),
                    'last_updated': datetime.now()
                }
            ]

            # Insert fallback data
            await session.execute(insert(ModelBenchmark), fallback_data)
            await session.commit()

            logger.info(f"Stored {len(fallback_data)} fallback benchmark records")

        except Exception as e:
            logger.error(f"Failed to store fallback benchmarks: {e}")
            await session.rollback()

    async def _ensure_fallback_data(self, session: AsyncSession):
        """Ensure fallback benchmark data exists in database."""
        try:
            # Check if fallback data already exists
            result = await session.execute(
                select(func.count()).select_from(ModelBenchmark).where(
                    ModelBenchmark.source == "fallback"
                )
            )
            count = result.scalar()

            if count == 0:
                logger.info("No fallback data found, creating it...")
                await self._store_fallback_benchmarks(session)
            else:
                logger.info(f"Found {count} existing fallback records")

        except Exception as e:
            logger.error(f"Failed to ensure fallback data: {e}")


# Global instance - temporarily disabled to avoid initialization issues
# model_registry_service = ModelRegistryService()