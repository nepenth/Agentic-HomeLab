from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.api.dependencies import get_db_session, verify_api_key
from app.services.secrets_service import SecretsService
from app.utils.logging import get_logger

logger = get_logger("secrets_api")
router = APIRouter()


class SecretCreate(BaseModel):
    secret_key: str = Field(..., min_length=1, max_length=255, description="The secret key (e.g., 'imap_password')")
    secret_value: str = Field(..., min_length=1, description="The plaintext secret value")
    description: Optional[str] = Field(None, description="Optional description of the secret")


class SecretUpdate(BaseModel):
    secret_value: Optional[str] = Field(None, min_length=1, description="New secret value")
    description: Optional[str] = Field(None, description="New description")
    is_active: Optional[bool] = Field(None, description="Whether the secret is active")


class SecretResponse(BaseModel):
    id: str
    agent_id: str
    secret_key: str
    description: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class SecretDetailResponse(BaseModel):
    id: str
    agent_id: str
    secret_key: str
    encrypted_value: str
    description: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    decrypted_value: Optional[str] = None
    decryption_error: Optional[str] = None


@router.post("/agents/{agent_id}/secrets", response_model=SecretResponse, dependencies=[Depends(verify_api_key)])
async def create_secret(
    agent_id: UUID,
    secret_data: SecretCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new secret for an agent."""
    try:
        secrets_service = SecretsService(db)
        secret = await secrets_service.create_secret(
            agent_id=agent_id,
            secret_key=secret_data.secret_key,
            secret_value=secret_data.secret_value,
            description=secret_data.description
        )

        return SecretResponse(**secret.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create secret for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create secret"
        )


@router.get("/agents/{agent_id}/secrets", response_model=List[SecretResponse])
async def list_agent_secrets(
    agent_id: UUID,
    include_inactive: bool = Query(False, description="Include inactive secrets"),
    db: AsyncSession = Depends(get_db_session)
):
    """List all secrets for an agent."""
    try:
        secrets_service = SecretsService(db)
        secrets = await secrets_service.get_agent_secrets(
            agent_id=agent_id,
            include_inactive=include_inactive,
            decrypt=False
        )

        return [SecretResponse(**secret) for secret in secrets]

    except Exception as e:
        logger.error(f"Failed to list secrets for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent secrets"
        )


@router.get("/agents/{agent_id}/secrets/{secret_id}", response_model=SecretDetailResponse, dependencies=[Depends(verify_api_key)])
async def get_secret(
    agent_id: UUID,
    secret_id: UUID,
    decrypt: bool = Query(False, description="Whether to include decrypted value"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific secret by ID."""
    try:
        secrets_service = SecretsService(db)
        secret = await secrets_service.get_secret(
            secret_id=secret_id,
            decrypt=decrypt
        )

        # Verify the secret belongs to the specified agent
        if secret["agent_id"] != str(agent_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found for this agent"
            )

        return SecretDetailResponse(**secret)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve secret"
        )


@router.put("/agents/{agent_id}/secrets/{secret_id}", response_model=SecretResponse, dependencies=[Depends(verify_api_key)])
async def update_secret(
    agent_id: UUID,
    secret_id: UUID,
    secret_data: SecretUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a secret."""
    try:
        secrets_service = SecretsService(db)

        # First verify the secret belongs to the agent
        secret_info = await secrets_service.get_secret(secret_id, decrypt=False)
        if secret_info["agent_id"] != str(agent_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found for this agent"
            )

        secret = await secrets_service.update_secret(
            secret_id=secret_id,
            secret_value=secret_data.secret_value,
            description=secret_data.description,
            is_active=secret_data.is_active
        )

        return SecretResponse(**secret.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update secret"
        )


@router.delete("/agents/{agent_id}/secrets/{secret_id}", dependencies=[Depends(verify_api_key)])
async def delete_secret(
    agent_id: UUID,
    secret_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a secret (soft delete)."""
    try:
        secrets_service = SecretsService(db)

        # First verify the secret belongs to the agent
        secret_info = await secrets_service.get_secret(secret_id, decrypt=False)
        if secret_info["agent_id"] != str(agent_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Secret not found for this agent"
            )

        await secrets_service.delete_secret(secret_id)

        return {"message": "Secret deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete secret {secret_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete secret"
        )


@router.get("/agents/{agent_id}/secrets/{secret_key}/value", dependencies=[Depends(verify_api_key)])
async def get_secret_value(
    agent_id: UUID,
    secret_key: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get the decrypted value of a secret by key (for internal use by agents)."""
    try:
        secrets_service = SecretsService(db)
        value = await secrets_service.get_secret_value(agent_id, secret_key)

        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Secret '{secret_key}' not found for this agent"
            )

        return {"secret_key": secret_key, "value": value}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get secret value for agent {agent_id}, key {secret_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve secret value"
        )