"""
Integration test for schema management functionality.
"""
import pytest
from app.services.schema_manager import SchemaManager
from app.schemas.agent_schema import AgentSchema
from unittest.mock import AsyncMock


@pytest.fixture
def valid_email_analyzer_schema():
    """A complete, valid email analyzer schema for testing."""
    return {
        "agent_type": "email_analyzer",
        "metadata": {
            "name": "Email Analyzer",
            "description": "Analyzes emails for importance and categorization",
            "category": "productivity",
            "version": "1.0.0",
            "author": "Test User"
        },
        "data_models": {
            "email_analysis": {
                "table_name": "email_analysis_results",
                "description": "Results of email analysis",
                "fields": {
                    "email_id": {
                        "type": "string",
                        "required": True,
                        "max_length": 255,
                        "description": "Unique identifier for the email"
                    },
                    "importance_score": {
                        "type": "float",
                        "required": False,
                        "range": [0.0, 1.0],
                        "default": 0.5,
                        "description": "Calculated importance score"
                    },
                    "categories": {
                        "type": "array",
                        "items": "string",
                        "required": False,
                        "description": "Assigned categories"
                    },
                    "is_urgent": {
                        "type": "boolean",
                        "required": False,
                        "default": False,
                        "description": "Whether the email is marked as urgent"
                    },
                    "sender_reputation": {
                        "type": "enum",
                        "values": ["trusted", "neutral", "suspicious"],
                        "required": False,
                        "default": "neutral",
                        "description": "Reputation of the sender"
                    }
                },
                "indexes": [
                    {
                        "name": "idx_email_id",
                        "fields": ["email_id"],
                        "unique": True
                    },
                    {
                        "name": "idx_importance_score",
                        "fields": ["importance_score"],
                        "unique": False
                    }
                ]
            }
        },
        "processing_pipeline": {
            "steps": [
                {
                    "name": "extract_email_content",
                    "tool": "email_extractor",
                    "description": "Extract email content and metadata",
                    "config": {
                        "include_attachments": False,
                        "parse_html": True
                    }
                },
                {
                    "name": "analyze_importance",
                    "tool": "importance_analyzer",
                    "description": "Calculate importance score",
                    "depends_on": ["extract_email_content"],
                    "config": {
                        "model": "importance_v2",
                        "threshold": 0.7
                    }
                },
                {
                    "name": "categorize_email",
                    "tool": "email_categorizer",
                    "description": "Assign categories to email",
                    "depends_on": ["extract_email_content"],
                    "config": {
                        "max_categories": 3
                    }
                },
                {
                    "name": "store_results",
                    "tool": "database_writer",
                    "description": "Store analysis results",
                    "depends_on": ["analyze_importance", "categorize_email"],
                    "config": {
                        "table": "email_analysis_results"
                    }
                }
            ],
            "parallel_execution": False,
            "max_retries": 3,
            "timeout": 300
        },
        "tools": {
            "email_extractor": {
                "type": "email_connector",
                "description": "Connects to email services to extract content",
                "config": {
                    "service": "imap",
                    "timeout": 30
                },
                "auth_config": {
                    "type": "oauth2",
                    "config": {
                        "scope": "read"
                    }
                },
                "rate_limit": "100/hour"
            },
            "importance_analyzer": {
                "type": "ml_classifier",
                "description": "ML model for importance scoring",
                "config": {
                    "model_path": "models/importance_v2.pkl",
                    "confidence_threshold": 0.8
                },
                "timeout": 60
            },
            "email_categorizer": {
                "type": "text_classifier",
                "description": "Categorizes emails based on content",
                "config": {
                    "categories": ["work", "personal", "newsletter", "spam"],
                    "multi_label": True
                },
                "timeout": 30
            },
            "database_writer": {
                "type": "database",
                "description": "Writes results to database",
                "config": {
                    "batch_size": 100,
                    "upsert": True
                },
                "auth_config": {
                    "type": "none",
                    "config": {}
                },
                "rate_limit": "1000/hour",
                "timeout": 120
            }
        },
        "input_schema": {
            "email_source": {
                "type": "string",
                "required": True,
                "description": "Email source identifier (e.g., folder, account)"
            },
            "date_range": {
                "type": "string",
                "required": False,
                "default": "7d",
                "pattern": "^\\d+[dwmy]$",
                "description": "Date range for analysis (e.g., '7d', '1w', '1m')"
            },
            "filters": {
                "type": "array",
                "items": "string",
                "required": False,
                "description": "Additional filters to apply"
            }
        },
        "output_schema": {
            "processed_count": {
                "type": "integer",
                "required": True,
                "description": "Number of emails processed"
            },
            "results": {
                "type": "array",
                "items": "email_analysis",
                "description": "Analysis results for each email"
            },
            "summary": {
                "type": "json",
                "required": False,
                "description": "Summary statistics"
            }
        },
        "max_execution_time": 1800,  # 30 minutes
        "max_memory_usage": 512,     # 512 MB
        "allowed_domains": [
            "https://api.gmail.com",
            "https://outlook.office365.com"
        ]
    }


class TestSchemaIntegration:
    """Integration tests for schema management."""
    
    @pytest.mark.asyncio
    async def test_complete_schema_validation(self, valid_email_analyzer_schema):
        """Test validation of a complete, realistic schema."""
        mock_db = AsyncMock()
        schema_manager = SchemaManager(mock_db)
        
        result = await schema_manager.validate_schema(valid_email_analyzer_schema)
        
        assert result.is_valid, f"Schema validation failed: {result.errors}"
        assert result.schema_hash is not None
        assert len(result.schema_hash) == 64  # SHA-256 hash
        
        # Should have some warnings but no errors
        assert len(result.errors) == 0
        # Might have warnings about best practices
        print(f"Validation warnings: {result.warnings}")
    
    @pytest.mark.asyncio
    async def test_pydantic_schema_creation(self, valid_email_analyzer_schema):
        """Test that the schema can be converted to Pydantic model."""
        # This tests that our Pydantic model definitions work correctly
        agent_schema = AgentSchema(**valid_email_analyzer_schema)
        
        assert agent_schema.agent_type == "email_analyzer"
        assert agent_schema.metadata.name == "Email Analyzer"
        assert len(agent_schema.data_models) == 1
        assert "email_analysis" in agent_schema.data_models
        assert len(agent_schema.processing_pipeline.steps) == 4
        assert len(agent_schema.tools) == 4
        
        # Test field validation
        email_analysis_model = agent_schema.data_models["email_analysis"]
        assert email_analysis_model.table_name == "email_analysis_results"
        assert "email_id" in email_analysis_model.fields
        assert email_analysis_model.fields["email_id"].required is True
        assert email_analysis_model.fields["importance_score"].range == [0.0, 1.0]
    
    @pytest.mark.asyncio
    async def test_schema_hash_consistency(self, valid_email_analyzer_schema):
        """Test that schema hashing is consistent."""
        mock_db = AsyncMock()
        schema_manager = SchemaManager(mock_db)
        
        # Validate same schema multiple times
        result1 = await schema_manager.validate_schema(valid_email_analyzer_schema)
        result2 = await schema_manager.validate_schema(valid_email_analyzer_schema)
        
        assert result1.is_valid and result2.is_valid
        assert result1.schema_hash == result2.schema_hash
    
    @pytest.mark.asyncio
    async def test_schema_modification_detection(self, valid_email_analyzer_schema):
        """Test that schema modifications are detected via hash changes."""
        mock_db = AsyncMock()
        schema_manager = SchemaManager(mock_db)
        
        # Get hash of original schema
        result1 = await schema_manager.validate_schema(valid_email_analyzer_schema)
        original_hash = result1.schema_hash
        
        # Modify schema slightly
        modified_schema = valid_email_analyzer_schema.copy()
        modified_schema["metadata"]["version"] = "1.0.1"
        
        result2 = await schema_manager.validate_schema(modified_schema)
        modified_hash = result2.schema_hash
        
        assert result1.is_valid and result2.is_valid
        assert original_hash != modified_hash
    
    @pytest.mark.asyncio
    async def test_invalid_schema_detection(self):
        """Test that various invalid schemas are properly detected."""
        mock_db = AsyncMock()
        schema_manager = SchemaManager(mock_db)
        
        # Test missing required fields
        invalid_schema = {
            "agent_type": "incomplete_agent",
            "metadata": {
                "name": "Incomplete Agent"
                # Missing required fields
            }
            # Missing other required sections
        }
        
        result = await schema_manager.validate_schema(invalid_schema)
        assert not result.is_valid
        assert len(result.errors) > 0
        
        # Test invalid field types
        invalid_field_schema = {
            "agent_type": "invalid_field_agent",
            "metadata": {
                "name": "Invalid Field Agent",
                "description": "Test agent",
                "category": "test",
                "version": "1.0.0"
            },
            "data_models": {
                "test_model": {
                    "table_name": "test_table",
                    "fields": {
                        "invalid_field": {
                            "type": "nonexistent_type",  # Invalid type
                            "required": True
                        }
                    }
                }
            },
            "processing_pipeline": {
                "steps": [
                    {
                        "name": "test_step",
                        "tool": "test_tool"
                    }
                ]
            },
            "tools": {
                "test_tool": {
                    "type": "test",
                    "config": {}
                }
            },
            "input_schema": {
                "test_input": {
                    "type": "string",
                    "required": True
                }
            },
            "output_schema": {
                "test_output": {
                    "type": "string",
                    "required": True
                }
            }
        }
        
        result = await schema_manager.validate_schema(invalid_field_schema)
        assert not result.is_valid
        # Should detect the invalid field type
        assert any("type" in error.lower() for error in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])