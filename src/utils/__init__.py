"""Shared utility functions."""

from .parsing import parse_count, extract_numbers, clean_text
from .security import (
    mask_credential,
    mask_email,
    mask_url_credentials,
    mask_dict_secrets,
    SensitiveFilter,
    setup_secure_logging,
)
from .html_debug_logger import (
    HTMLDebugLogger,
    get_debug_logger,
    set_debug_client,
    save_debug_html,
)
from .output_paths import (
    OutputPathManager,
    get_export_path,
    ensure_export_dir,
)
from .structured_logging import (
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    correlation_context,
    StructuredFormatter,
    CorrelationFormatter,
    ContextLogger,
    get_logger,
    log_operation,
    log_scraping_activity,
    log_storage_operation,
    setup_structured_logging,
)
from .credential_manager import (
    CredentialManager,
    CredentialEntry,
    get_credential_manager,
    reset_credential_manager,
)

__all__ = [
    # Parsing
    "parse_count",
    "extract_numbers",
    "clean_text",
    # Security
    "mask_credential",
    "mask_email",
    "mask_url_credentials",
    "mask_dict_secrets",
    "SensitiveFilter",
    "setup_secure_logging",
    # Debug logging
    "HTMLDebugLogger",
    "get_debug_logger",
    "set_debug_client",
    "save_debug_html",
    # Output paths
    "OutputPathManager",
    "get_export_path",
    "ensure_export_dir",
    # Structured logging
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "correlation_context",
    "StructuredFormatter",
    "CorrelationFormatter",
    "ContextLogger",
    "get_logger",
    "log_operation",
    "log_scraping_activity",
    "log_storage_operation",
    "setup_structured_logging",
    # Credential management
    "CredentialManager",
    "CredentialEntry",
    "get_credential_manager",
    "reset_credential_manager",
]
