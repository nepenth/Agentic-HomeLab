"""
Model Benchmark Data Model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from app.db.database import Base


class ModelBenchmark(Base):
    """Stores benchmark data for AI models from various sources."""
    __tablename__ = "model_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False, index=True)
    source = Column(String(100), nullable=False, default="huggingface")  # huggingface, custom, etc.

    # Benchmark scores
    average_score = Column(Float, nullable=True)
    mmlu_score = Column(Float, nullable=True)
    gpqa_score = Column(Float, nullable=True)
    math_score = Column(Float, nullable=True)
    humaneval_score = Column(Float, nullable=True)
    bbh_score = Column(Float, nullable=True)

    # Metadata
    raw_data = Column(Text, nullable=True)  # JSON string of full benchmark data
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_model_benchmarks_name_source', 'model_name', 'source'),
        Index('idx_model_benchmarks_updated', 'last_updated'),
    )

    def __repr__(self):
        return f"<ModelBenchmark(model_name='{self.model_name}', source='{self.source}', average_score={self.average_score})>"