"""Tests for credential manager."""

import os
import pytest
import tempfile
from pathlib import Path

from src.utils.credential_manager import (
    CredentialManager,
    get_credential_manager,
    reset_credential_manager,
    HAS_CRYPTOGRAPHY,
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_storage):
    """Create credential manager with temp storage."""
    reset_credential_manager()
    return CredentialManager(
        storage_path=temp_storage,
        use_keyring=False,
        master_password="test_master_password"
    )


@pytest.fixture
def env_vars():
    """Set up and tear down environment variables."""
    original = {}
    test_vars = {
        "EXTRACTOR_INSTAGRAM__USERNAME": "env_user",
        "EXTRACTOR_INSTAGRAM__PASSWORD": "env_pass",
        "EXTRACTOR_FACEBOOK__EMAIL": "env@email.com",
    }

    # Save original values and set test values
    for key, value in test_vars.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_vars

    # Restore original values
    for key in test_vars:
        if original[key] is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original[key]


class TestCredentialManager:
    """Tests for CredentialManager class."""

    def test_initialization(self, temp_storage):
        """Test manager initialization."""
        manager = CredentialManager(
            storage_path=temp_storage,
            use_keyring=False
        )
        assert manager.storage_path == temp_storage
        assert not manager.use_keyring

    def test_set_master_password(self, manager):
        """Test setting master password."""
        manager.set_master_password("new_password")
        assert manager._master_password == "new_password"
        assert manager._fernet is None  # Should reset fernet

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_store_and_get_encrypted(self, manager):
        """Test storing and retrieving encrypted credentials."""
        # Store credential
        success = manager.store_encrypted("instagram", "password", "secret123")
        assert success

        # Retrieve credential
        value = manager.get_encrypted("instagram", "password")
        assert value == "secret123"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_delete_encrypted(self, manager):
        """Test deleting encrypted credentials."""
        # Store credential
        manager.store_encrypted("instagram", "password", "secret123")

        # Delete credential
        success = manager.delete_encrypted("instagram", "password")
        assert success

        # Verify deleted
        value = manager.get_encrypted("instagram", "password")
        assert value is None

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_delete_nonexistent(self, manager):
        """Test deleting non-existent credential."""
        success = manager.delete_encrypted("nonexistent", "password")
        assert not success

    def test_get_from_env(self, env_vars):
        """Test getting credentials from environment variables."""
        manager = CredentialManager()

        # Test retrieval
        value = manager.get_from_env("instagram", "username")
        assert value == "env_user"

        value = manager.get_from_env("instagram", "password")
        assert value == "env_pass"

        value = manager.get_from_env("facebook", "email")
        assert value == "env@email.com"

        # Test non-existent
        value = manager.get_from_env("twitter", "password")
        assert value is None

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_get_priority(self, manager, env_vars):
        """Test that environment variables have priority."""
        # Store encrypted credential
        manager.store_encrypted("instagram", "username", "encrypted_user")

        # Get should return env var value
        value = manager.get("instagram", "username")
        assert value == "env_user"

        # Non-env var should return encrypted
        manager.store_encrypted("instagram", "token", "encrypted_token")
        value = manager.get("instagram", "token")
        assert value == "encrypted_token"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_list_credentials(self, manager):
        """Test listing stored credentials."""
        # Store some credentials
        manager.store_encrypted("instagram", "username", "user123")
        manager.store_encrypted("instagram", "password", "pass456")
        manager.store_encrypted("facebook", "email", "test@example.com")

        # List credentials
        creds = manager.list_credentials()
        assert len(creds) == 3
        assert "instagram_username" in creds
        assert "instagram_password" in creds
        assert "facebook_email" in creds

        # Values should be masked
        assert "***" in creds["instagram_password"]

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_has_credential(self, manager):
        """Test checking if credential exists."""
        # Use a unique platform name to avoid env var interference
        platform = "test_platform_unique"

        # Initially not present
        assert not manager.has_credential(platform, "password")

        # Store credential
        manager.store_encrypted(platform, "password", "secret")

        # Now present
        assert manager.has_credential(platform, "password")

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_store_platform_credentials(self, manager):
        """Test storing all platform credentials."""
        success = manager.store_platform_credentials(
            "instagram",
            username="myuser",
            password="mypass",
            email=None,
            token="mytoken"
        )
        assert success

        # Verify all stored
        assert manager.get_encrypted("instagram", "username") == "myuser"
        assert manager.get_encrypted("instagram", "password") == "mypass"
        assert manager.get_encrypted("instagram", "email") is None
        assert manager.get_encrypted("instagram", "token") == "mytoken"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_get_platform_credentials(self, manager):
        """Test getting all platform credentials."""
        # Use unique platform to avoid env var interference
        platform = "test_unique_platform"

        # Store some credentials
        manager.store_encrypted(platform, "username", "myuser")
        manager.store_encrypted(platform, "password", "mypass")

        # Get platform credentials
        creds = manager.get_platform_credentials(platform)
        assert creds["username"] == "myuser"
        assert creds["password"] == "mypass"
        assert creds["email"] is None
        assert creds["token"] is None

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_multiple_credentials_persistence(self, temp_storage):
        """Test that credentials persist across manager instances."""
        # Store with first manager
        manager1 = CredentialManager(
            storage_path=temp_storage,
            master_password="test_password"
        )
        manager1.store_encrypted("instagram", "password", "secret123")

        # Retrieve with new manager instance
        manager2 = CredentialManager(
            storage_path=temp_storage,
            master_password="test_password"
        )
        value = manager2.get_encrypted("instagram", "password")
        assert value == "secret123"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_wrong_master_password(self, temp_storage):
        """Test that wrong master password fails to decrypt."""
        # Store with one password
        manager1 = CredentialManager(
            storage_path=temp_storage,
            master_password="password1"
        )
        manager1.store_encrypted("instagram", "password", "secret123")

        # Try to retrieve with different password
        manager2 = CredentialManager(
            storage_path=temp_storage,
            master_password="password2"
        )
        # Should fail to decrypt
        value = manager2.get_encrypted("instagram", "password")
        assert value is None or value != "secret123"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_special_characters_in_credentials(self, manager):
        """Test credentials with special characters."""
        special_passwords = [
            "p@ssw0rd!#$%",
            "with spaces in it",
            "unicode: \u00e9\u00e0\u00fc",
            "quotes: \"'`",
            "newlines:\n\t",
        ]

        for i, password in enumerate(special_passwords):
            key = f"type{i}"
            manager.store_encrypted("test", key, password)
            retrieved = manager.get_encrypted("test", key)
            assert retrieved == password, f"Failed for: {password}"

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_empty_storage_list(self, manager):
        """Test listing empty storage."""
        creds = manager.list_credentials()
        assert creds == {}

    def test_no_master_password_error(self, temp_storage):
        """Test that operations fail without master password."""
        manager = CredentialManager(
            storage_path=temp_storage,
            use_keyring=False,
            master_password=None
        )

        if HAS_CRYPTOGRAPHY:
            # _get_fernet raises the error directly
            with pytest.raises(RuntimeError, match="Master password required"):
                manager._get_fernet()

            # store_encrypted catches and returns False
            success = manager.store_encrypted("test", "password", "secret")
            assert not success


class TestCredentialManagerSingleton:
    """Tests for singleton behavior."""

    def test_get_credential_manager_creates_instance(self, temp_storage):
        """Test singleton creation."""
        reset_credential_manager()

        manager1 = get_credential_manager(
            storage_path=temp_storage,
            master_password="test"
        )
        manager2 = get_credential_manager()

        assert manager1 is manager2

    def test_reset_credential_manager(self, temp_storage):
        """Test resetting singleton."""
        manager1 = get_credential_manager(
            storage_path=temp_storage,
            master_password="test"
        )

        reset_credential_manager()

        manager2 = get_credential_manager(
            storage_path=temp_storage,
            master_password="test"
        )

        assert manager1 is not manager2

    def test_update_master_password(self, temp_storage):
        """Test updating master password on existing instance."""
        reset_credential_manager()

        manager = get_credential_manager(
            storage_path=temp_storage,
            master_password="password1"
        )

        # Update password
        get_credential_manager(master_password="password2")

        assert manager._master_password == "password2"


class TestCredentialKey:
    """Tests for credential key generation."""

    def test_credential_key_format(self, manager):
        """Test credential key format."""
        key = manager._get_credential_key("instagram", "password")
        assert key == "instagram_password"

    def test_credential_key_case_sensitivity(self, manager):
        """Test that keys are case sensitive."""
        key1 = manager._get_credential_key("Instagram", "Password")
        key2 = manager._get_credential_key("instagram", "password")
        assert key1 != key2


class TestEnvironmentVariableIntegration:
    """Tests for environment variable integration."""

    def test_env_var_format(self, manager):
        """Test environment variable naming convention."""
        # The format should be EXTRACTOR_{PLATFORM}__{TYPE}
        os.environ["EXTRACTOR_TEST_PLATFORM__TEST_TYPE"] = "test_value"
        try:
            value = manager.get_from_env("test_platform", "test_type")
            assert value == "test_value"
        finally:
            del os.environ["EXTRACTOR_TEST_PLATFORM__TEST_TYPE"]

    def test_unified_get_prioritizes_env(self, manager, env_vars):
        """Test that unified get prioritizes environment variables."""
        if HAS_CRYPTOGRAPHY:
            # Store encrypted value
            manager.store_encrypted("instagram", "username", "stored_value")

        # Should return env var value
        value = manager.get("instagram", "username")
        assert value == "env_user"


# Integration tests
class TestIntegration:
    """Integration tests for credential manager."""

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
    def test_full_workflow(self, temp_storage):
        """Test complete credential management workflow."""
        reset_credential_manager()

        # Initialize manager
        manager = get_credential_manager(
            storage_path=temp_storage,
            master_password="secure_master_password"
        )

        # Store multiple platform credentials (use unique names to avoid env vars)
        platforms = {
            "test_insta": {"username": "insta_user", "password": "insta_pass"},
            "test_fb": {"email": "fb@example.com", "password": "fb_pass"},
            "test_tw": {"username": "tw_user", "password": "tw_pass"},
        }

        for platform, creds in platforms.items():
            for cred_type, value in creds.items():
                manager.store(platform, cred_type, value)

        # Verify all credentials
        for platform, creds in platforms.items():
            for cred_type, expected in creds.items():
                actual = manager.get(platform, cred_type)
                assert actual == expected

        # List should show all
        listed = manager.list_credentials()
        assert len(listed) == 6

        # Delete some
        manager.delete("test_tw", "username")
        manager.delete("test_tw", "password")

        # Verify deleted
        listed = manager.list_credentials()
        assert len(listed) == 4
        assert "test_tw_username" not in listed
        assert "test_tw_password" not in listed

        # Remaining should still work
        assert manager.get("test_insta", "username") == "insta_user"
        assert manager.get("test_fb", "email") == "fb@example.com"

        reset_credential_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
