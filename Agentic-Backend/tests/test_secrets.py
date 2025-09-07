"""Tests for secrets management functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.secrets_service import SecretsService
from app.services.encryption_service import EncryptionService
from app.db.models.secret import AgentSecret
from uuid import uuid4


class TestEncryptionService:
    """Test the encryption service."""

    def test_encrypt_decrypt(self):
        """Test basic encryption and decryption."""
        service = EncryptionService("test-key-for-testing-purposes")

        plaintext = "my-secret-password"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        service = EncryptionService("test-key")

        encrypted = service.encrypt("")
        decrypted = service.decrypt(encrypted)

        assert decrypted == ""

    def test_generate_key(self):
        """Test key generation."""
        key = EncryptionService.generate_key()

        # Fernet keys are 44 characters (32 bytes base64 encoded)
        assert len(key) == 44
        assert isinstance(key, str)


class TestSecretsService:
    """Test the secrets service."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def secrets_service(self, mock_db):
        """Create secrets service with mocked DB."""
        return SecretsService(mock_db)

    @pytest.fixture
    def sample_agent_id(self):
        """Sample agent ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_secret(self, sample_agent_id):
        """Sample secret for testing."""
        return AgentSecret(
            agent_id=sample_agent_id,
            secret_key="test_key",
            encrypted_value="encrypted_value",
            description="Test secret",
            is_active=True
        )

    def test_initialization(self, secrets_service, mock_db):
        """Test service initialization."""
        assert secrets_service.db == mock_db

    @pytest.mark.asyncio
    async def test_create_secret_success(self, secrets_service, mock_db, sample_agent_id):
        """Test successful secret creation."""
        # Mock agent existence check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=sample_agent_id)
        mock_db.execute.return_value = mock_result

        # Mock secret creation
        mock_secret = MagicMock()
        mock_secret.to_dict.return_value = {
            "id": str(uuid4()),
            "agent_id": str(sample_agent_id),
            "secret_key": "test_key",
            "description": "Test secret",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = await secrets_service.create_secret(
            agent_id=sample_agent_id,
            secret_key="test_key",
            secret_value="test_value",
            description="Test secret"
        )

        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_secret_agent_not_found(self, secrets_service, mock_db, sample_agent_id):
        """Test secret creation with non-existent agent."""
        # Mock agent not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(Exception):  # Should raise HTTPException
            await secrets_service.create_secret(
                agent_id=sample_agent_id,
                secret_key="test_key",
                secret_value="test_value"
            )

    @pytest.mark.asyncio
    async def test_create_secret_key_conflict(self, secrets_service, mock_db, sample_agent_id):
        """Test secret creation with conflicting key."""
        # Mock agent exists
        mock_agent_result = MagicMock()
        mock_agent_result.scalar_one_or_none.return_value = MagicMock(id=sample_agent_id)
        mock_db.execute.return_value = mock_agent_result

        # Mock existing secret with same key
        mock_conflict_result = MagicMock()
        mock_conflict_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.side_effect = [mock_agent_result, mock_conflict_result]

        with pytest.raises(Exception):  # Should raise HTTPException
            await secrets_service.create_secret(
                agent_id=sample_agent_id,
                secret_key="existing_key",
                secret_value="test_value"
            )

    @pytest.mark.asyncio
    async def test_get_secret_value_success(self, secrets_service, mock_db, sample_agent_id):
        """Test successful secret value retrieval."""
        # Mock secret exists
        mock_result = MagicMock()
        mock_secret = MagicMock()
        mock_secret.encrypted_value = "encrypted_test_value"
        mock_result.scalar_one_or_none.return_value = mock_secret
        mock_db.execute.return_value = mock_result

        result = await secrets_service.get_secret_value(sample_agent_id, "test_key")

        assert result == "test_value"  # Should be decrypted

    @pytest.mark.asyncio
    async def test_get_secret_value_not_found(self, secrets_service, mock_db, sample_agent_id):
        """Test secret value retrieval for non-existent secret."""
        # Mock secret not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await secrets_service.get_secret_value(sample_agent_id, "nonexistent_key")

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])