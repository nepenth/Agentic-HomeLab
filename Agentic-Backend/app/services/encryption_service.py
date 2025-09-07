from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("encryption_service")


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet symmetric encryption."""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize encryption service with a secret key.

        Args:
            secret_key: Base64-encoded secret key. If None, uses settings.secret_key
        """
        if secret_key:
            self._key = secret_key.encode()
        else:
            self._key = settings.secret_key.encode()

        # Ensure the key is properly formatted for Fernet (32 bytes base64 encoded)
        if len(self._key) != 44:  # Fernet keys are 32 bytes base64 encoded = 44 chars
            # If it's not the right length, derive a proper key from it
            self._key = self._derive_key(self._key)

        self._fernet = Fernet(self._key)
        logger.info("Encryption service initialized")

    def _derive_key(self, input_key: bytes) -> bytes:
        """Derive a proper Fernet key from input key using PBKDF2."""
        salt = b"agentic_backend_salt"  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(input_key))
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        try:
            if not plaintext:
                return ""

            encrypted_data = self._fernet.encrypt(plaintext.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        try:
            if not encrypted_text:
                return ""

            decrypted_data = self._fernet.decrypt(encrypted_text.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """Generate a new random Fernet key.

        Returns:
            Base64-encoded key string
        """
        return Fernet.generate_key().decode()


# Global encryption service instance
encryption_service = EncryptionService()