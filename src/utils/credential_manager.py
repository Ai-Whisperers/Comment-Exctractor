"""Secure credential storage and encryption utilities.

This module provides encrypted storage for sensitive credentials like
passwords and API tokens. It supports:
- AES-256 encryption with key derivation from master password
- Optional keyring integration for OS-level secure storage
- Environment variable fallback for CI/CD environments
"""

import os
import json
import base64
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import cryptography for encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography package not installed. Encrypted storage disabled.")

# Try to import keyring for OS-level secure storage
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    logger.debug("keyring package not installed. Keyring storage disabled.")


# Constants
CREDENTIAL_FILE = "credentials.enc"
SALT_LENGTH = 16
KEY_ITERATIONS = 100000
SERVICE_NAME = "comment-extractor"


@dataclass
class CredentialEntry:
    """A single credential entry."""
    platform: str
    credential_type: str  # e.g., "password", "email", "token"
    value: str


class CredentialManager:
    """
    Secure credential storage manager.

    Supports multiple storage backends:
    1. Encrypted file storage (default)
    2. OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    3. Environment variables (for CI/CD)
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_keyring: bool = False,
        master_password: Optional[str] = None
    ):
        """
        Initialize credential manager.

        Args:
            storage_path: Directory for encrypted credential file
            use_keyring: Use OS keyring instead of encrypted file
            master_password: Master password for encryption (can be set later)
        """
        self.storage_path = storage_path or Path.home() / ".comment-extractor"
        self.use_keyring = use_keyring and HAS_KEYRING
        self._master_password = master_password
        self._fernet: Optional[Any] = None
        self._credentials_cache: Dict[str, str] = {}

        # Create storage directory if needed
        if not self.use_keyring:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def set_master_password(self, password: str) -> None:
        """
        Set the master password for encryption.

        Args:
            password: Master password
        """
        self._master_password = password
        self._fernet = None  # Reset fernet to regenerate key

    def _get_fernet(self) -> Any:
        """
        Get or create Fernet encryption instance.

        Returns:
            Fernet instance for encryption/decryption

        Raises:
            RuntimeError: If cryptography not installed or no master password
        """
        if not HAS_CRYPTOGRAPHY:
            raise RuntimeError(
                "Encrypted storage requires the 'cryptography' package. "
                "Install it with: pip install cryptography"
            )

        if not self._master_password:
            raise RuntimeError(
                "Master password required for encrypted storage. "
                "Call set_master_password() first."
            )

        if self._fernet is None:
            # Derive key from master password
            salt = self._get_or_create_salt()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=KEY_ITERATIONS,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(
                kdf.derive(self._master_password.encode())
            )
            self._fernet = Fernet(key)

        return self._fernet

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new one."""
        salt_file = self.storage_path / "salt"

        if salt_file.exists():
            return salt_file.read_bytes()

        # Generate new salt
        salt = os.urandom(SALT_LENGTH)
        salt_file.write_bytes(salt)
        return salt

    def _get_credential_key(self, platform: str, credential_type: str) -> str:
        """Generate a unique key for a credential."""
        return f"{platform}_{credential_type}"

    # Environment variable methods

    def get_from_env(self, platform: str, credential_type: str) -> Optional[str]:
        """
        Get credential from environment variable.

        Uses the format: EXTRACTOR_{PLATFORM}__{TYPE}
        e.g., EXTRACTOR_INSTAGRAM__PASSWORD

        Args:
            platform: Platform name
            credential_type: Credential type (password, email, etc.)

        Returns:
            Credential value or None
        """
        env_key = f"EXTRACTOR_{platform.upper()}__{credential_type.upper()}"
        return os.environ.get(env_key)

    # Keyring methods

    def store_in_keyring(self, platform: str, credential_type: str, value: str) -> bool:
        """
        Store credential in OS keyring.

        Args:
            platform: Platform name
            credential_type: Credential type
            value: Credential value

        Returns:
            True if stored successfully
        """
        if not HAS_KEYRING:
            logger.warning("Keyring not available")
            return False

        key = self._get_credential_key(platform, credential_type)
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            logger.debug(f"Stored {key} in keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to store in keyring: {e}")
            return False

    def get_from_keyring(self, platform: str, credential_type: str) -> Optional[str]:
        """
        Get credential from OS keyring.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            Credential value or None
        """
        if not HAS_KEYRING:
            return None

        key = self._get_credential_key(platform, credential_type)
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            if value:
                logger.debug(f"Retrieved {key} from keyring")
            return value
        except Exception as e:
            logger.error(f"Failed to get from keyring: {e}")
            return None

    def delete_from_keyring(self, platform: str, credential_type: str) -> bool:
        """
        Delete credential from OS keyring.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            True if deleted successfully
        """
        if not HAS_KEYRING:
            return False

        key = self._get_credential_key(platform, credential_type)
        try:
            keyring.delete_password(SERVICE_NAME, key)
            logger.debug(f"Deleted {key} from keyring")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from keyring: {e}")
            return False

    # Encrypted file methods

    def _get_credential_file(self) -> Path:
        """Get path to encrypted credentials file."""
        return self.storage_path / CREDENTIAL_FILE

    def _load_encrypted_credentials(self) -> Dict[str, str]:
        """Load and decrypt credentials from file."""
        cred_file = self._get_credential_file()

        if not cred_file.exists():
            return {}

        fernet = self._get_fernet()

        try:
            encrypted_data = cred_file.read_bytes()
            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return {}

    def _save_encrypted_credentials(self, credentials: Dict[str, str]) -> None:
        """Encrypt and save credentials to file."""
        cred_file = self._get_credential_file()
        fernet = self._get_fernet()

        # Encrypt and save
        json_data = json.dumps(credentials).encode()
        encrypted_data = fernet.encrypt(json_data)

        # Write with restrictive permissions
        cred_file.write_bytes(encrypted_data)

        # Set file permissions (Unix only)
        try:
            cred_file.chmod(0o600)
        except (AttributeError, OSError):
            pass  # Windows doesn't support Unix permissions

        logger.debug(f"Saved encrypted credentials to {cred_file}")

    def store_encrypted(self, platform: str, credential_type: str, value: str) -> bool:
        """
        Store credential in encrypted file.

        Args:
            platform: Platform name
            credential_type: Credential type
            value: Credential value

        Returns:
            True if stored successfully
        """
        try:
            credentials = self._load_encrypted_credentials()
            key = self._get_credential_key(platform, credential_type)
            credentials[key] = value
            self._save_encrypted_credentials(credentials)
            logger.debug(f"Stored {key} in encrypted file")
            return True
        except Exception as e:
            logger.error(f"Failed to store encrypted credential: {e}")
            return False

    def get_encrypted(self, platform: str, credential_type: str) -> Optional[str]:
        """
        Get credential from encrypted file.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            Credential value or None
        """
        try:
            credentials = self._load_encrypted_credentials()
            key = self._get_credential_key(platform, credential_type)
            value = credentials.get(key)
            if value:
                logger.debug(f"Retrieved {key} from encrypted file")
            return value
        except Exception as e:
            logger.error(f"Failed to get encrypted credential: {e}")
            return None

    def delete_encrypted(self, platform: str, credential_type: str) -> bool:
        """
        Delete credential from encrypted file.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            True if deleted successfully
        """
        try:
            credentials = self._load_encrypted_credentials()
            key = self._get_credential_key(platform, credential_type)
            if key in credentials:
                del credentials[key]
                self._save_encrypted_credentials(credentials)
                logger.debug(f"Deleted {key} from encrypted file")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete encrypted credential: {e}")
            return False

    # Unified interface

    def store(self, platform: str, credential_type: str, value: str) -> bool:
        """
        Store credential using configured backend.

        Args:
            platform: Platform name
            credential_type: Credential type
            value: Credential value

        Returns:
            True if stored successfully
        """
        if self.use_keyring:
            return self.store_in_keyring(platform, credential_type, value)
        return self.store_encrypted(platform, credential_type, value)

    def get(self, platform: str, credential_type: str) -> Optional[str]:
        """
        Get credential from available sources.

        Priority:
        1. Environment variables (for CI/CD)
        2. Keyring (if enabled)
        3. Encrypted file

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            Credential value or None
        """
        # 1. Check environment variables first
        value = self.get_from_env(platform, credential_type)
        if value:
            return value

        # 2. Check keyring if enabled
        if self.use_keyring:
            value = self.get_from_keyring(platform, credential_type)
            if value:
                return value

        # 3. Check encrypted file
        return self.get_encrypted(platform, credential_type)

    def delete(self, platform: str, credential_type: str) -> bool:
        """
        Delete credential from storage.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            True if deleted successfully
        """
        if self.use_keyring:
            return self.delete_from_keyring(platform, credential_type)
        return self.delete_encrypted(platform, credential_type)

    def list_credentials(self) -> Dict[str, str]:
        """
        List all stored credentials (keys only, not values).

        Returns:
            Dictionary mapping credential keys to masked values
        """
        from .security import mask_credential

        result = {}

        if self.use_keyring:
            # Keyring doesn't support listing, return empty
            logger.warning("Cannot list credentials from keyring")
            return result

        try:
            credentials = self._load_encrypted_credentials()
            for key, value in credentials.items():
                result[key] = mask_credential(value, 3)
            return result
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return result

    def has_credential(self, platform: str, credential_type: str) -> bool:
        """
        Check if a credential exists.

        Args:
            platform: Platform name
            credential_type: Credential type

        Returns:
            True if credential exists
        """
        return self.get(platform, credential_type) is not None

    def store_platform_credentials(
        self,
        platform: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        email: Optional[str] = None,
        token: Optional[str] = None
    ) -> bool:
        """
        Store all credentials for a platform.

        Args:
            platform: Platform name
            username: Username credential
            password: Password credential
            email: Email credential
            token: API token credential

        Returns:
            True if all stored successfully
        """
        success = True

        if username:
            success = self.store(platform, "username", username) and success
        if password:
            success = self.store(platform, "password", password) and success
        if email:
            success = self.store(platform, "email", email) and success
        if token:
            success = self.store(platform, "token", token) and success

        return success

    def get_platform_credentials(self, platform: str) -> Dict[str, Optional[str]]:
        """
        Get all credentials for a platform.

        Args:
            platform: Platform name

        Returns:
            Dictionary of credential types to values
        """
        return {
            "username": self.get(platform, "username"),
            "password": self.get(platform, "password"),
            "email": self.get(platform, "email"),
            "token": self.get(platform, "token"),
        }


# Singleton instance for easy access
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager(
    storage_path: Optional[Path] = None,
    use_keyring: bool = False,
    master_password: Optional[str] = None
) -> CredentialManager:
    """
    Get or create the credential manager singleton.

    Args:
        storage_path: Directory for encrypted credential file
        use_keyring: Use OS keyring instead of encrypted file
        master_password: Master password for encryption

    Returns:
        CredentialManager instance
    """
    global _credential_manager

    if _credential_manager is None:
        _credential_manager = CredentialManager(
            storage_path=storage_path,
            use_keyring=use_keyring,
            master_password=master_password
        )
    elif master_password:
        _credential_manager.set_master_password(master_password)

    return _credential_manager


def reset_credential_manager() -> None:
    """Reset the credential manager singleton (mainly for testing)."""
    global _credential_manager
    _credential_manager = None
