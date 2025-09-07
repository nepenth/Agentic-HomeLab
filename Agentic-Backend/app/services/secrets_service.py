from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional, Dict, Any
from uuid import UUID
from app.db.models.secret import AgentSecret
from app.db.models.agent import Agent
from app.services.encryption_service import encryption_service
from app.utils.logging import get_logger
from fastapi import HTTPException
from http import HTTPStatus as status

logger = get_logger("secrets_service")


class SecretsService:
    """Service for managing agent secrets with encryption."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_secret(
        self,
        agent_id: UUID,
        secret_key: str,
        secret_value: str,
        description: Optional[str] = None
    ) -> AgentSecret:
        """Create a new secret for an agent.

        Args:
            agent_id: The agent ID
            secret_key: The secret key (e.g., "imap_password")
            secret_value: The plaintext secret value
            description: Optional description

        Returns:
            The created AgentSecret instance
        """
        try:
            # Verify agent exists
            agent_result = await self.db.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = agent_result.scalar_one_or_none()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent {agent_id} not found"
                )

            # Check if secret key already exists for this agent
            existing_result = await self.db.execute(
                select(AgentSecret).where(
                    AgentSecret.agent_id == agent_id,
                    AgentSecret.secret_key == secret_key,
                    AgentSecret.is_active == True
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Secret key '{secret_key}' already exists for this agent"
                )

            # Encrypt the secret value
            encrypted_value = encryption_service.encrypt(secret_value)

            # Create the secret
            secret = AgentSecret(
                agent_id=agent_id,
                secret_key=secret_key,
                encrypted_value=encrypted_value,
                description=description
            )

            self.db.add(secret)
            await self.db.commit()
            await self.db.refresh(secret)

            logger.info(f"Created secret '{secret_key}' for agent {agent_id}")
            return secret

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create secret: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create secret"
            )

    async def get_secret(self, secret_id: UUID, decrypt: bool = False) -> Dict[str, Any]:
        """Get a secret by ID.

        Args:
            secret_id: The secret ID
            decrypt: Whether to decrypt the value

        Returns:
            Secret data as dictionary
        """
        try:
            result = await self.db.execute(
                select(AgentSecret).where(AgentSecret.id == secret_id)
            )
            secret = result.scalar_one_or_none()

            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Secret not found"
                )

            secret_dict = secret.to_dict(include_encrypted_value=True)

            if decrypt:
                try:
                    secret_dict["decrypted_value"] = encryption_service.decrypt(secret.encrypted_value)
                except Exception as e:
                    logger.error(f"Failed to decrypt secret {secret_id}: {e}")
                    secret_dict["decrypted_value"] = None
                    secret_dict["decryption_error"] = str(e)

            return secret_dict

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get secret {secret_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve secret"
            )

    async def get_agent_secrets(
        self,
        agent_id: UUID,
        include_inactive: bool = False,
        decrypt: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all secrets for an agent.

        Args:
            agent_id: The agent ID
            include_inactive: Whether to include inactive secrets
            decrypt: Whether to decrypt values

        Returns:
            List of secret dictionaries
        """
        try:
            query = select(AgentSecret).where(AgentSecret.agent_id == agent_id)
            if not include_inactive:
                query = query.where(AgentSecret.is_active == True)

            result = await self.db.execute(query)
            secrets = result.scalars().all()

            secrets_list = []
            for secret in secrets:
                secret_dict = secret.to_dict(include_encrypted_value=True)

                if decrypt:
                    try:
                        secret_dict["decrypted_value"] = encryption_service.decrypt(secret.encrypted_value)
                    except Exception as e:
                        logger.error(f"Failed to decrypt secret {secret.id}: {e}")
                        secret_dict["decrypted_value"] = None
                        secret_dict["decryption_error"] = str(e)

                secrets_list.append(secret_dict)

            return secrets_list

        except Exception as e:
            logger.error(f"Failed to get secrets for agent {agent_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve agent secrets"
            )

    async def update_secret(
        self,
        secret_id: UUID,
        secret_value: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> AgentSecret:
        """Update a secret.

        Args:
            secret_id: The secret ID
            secret_value: New secret value (will be encrypted)
            description: New description
            is_active: New active status

        Returns:
            Updated AgentSecret instance
        """
        try:
            # Check if secret exists
            result = await self.db.execute(
                select(AgentSecret).where(AgentSecret.id == secret_id)
            )
            secret = result.scalar_one_or_none()

            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Secret not found"
                )

            update_data = {}

            if secret_value is not None:
                update_data["encrypted_value"] = encryption_service.encrypt(secret_value)

            if description is not None:
                update_data["description"] = description

            if is_active is not None:
                update_data["is_active"] = is_active

            if update_data:
                stmt = update(AgentSecret).where(AgentSecret.id == secret_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.commit()
                await self.db.refresh(secret)

            logger.info(f"Updated secret {secret_id}")
            return secret

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update secret"
            )

    async def delete_secret(self, secret_id: UUID) -> bool:
        """Delete a secret (soft delete by setting is_active=False).

        Args:
            secret_id: The secret ID

        Returns:
            True if deleted successfully
        """
        try:
            # Check if secret exists
            result = await self.db.execute(
                select(AgentSecret).where(AgentSecret.id == secret_id)
            )
            secret = result.scalar_one_or_none()

            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Secret not found"
                )

            # Soft delete
            stmt = update(AgentSecret).where(AgentSecret.id == secret_id).values(is_active=False)
            await self.db.execute(stmt)
            await self.db.commit()

            logger.info(f"Deleted secret {secret_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete secret"
            )

    async def get_secret_value(self, agent_id: UUID, secret_key: str) -> Optional[str]:
        """Get a decrypted secret value by agent ID and key.

        Args:
            agent_id: The agent ID
            secret_key: The secret key

        Returns:
            Decrypted secret value or None if not found
        """
        try:
            result = await self.db.execute(
                select(AgentSecret).where(
                    AgentSecret.agent_id == agent_id,
                    AgentSecret.secret_key == secret_key,
                    AgentSecret.is_active == True
                )
            )
            secret = result.scalar_one_or_none()

            if not secret:
                return None

            return encryption_service.decrypt(secret.encrypted_value)

        except Exception as e:
            logger.error(f"Failed to get secret value for agent {agent_id}, key {secret_key}: {e}")
            return None


# Global instance (will be initialized with database session when needed)
secrets_service = None