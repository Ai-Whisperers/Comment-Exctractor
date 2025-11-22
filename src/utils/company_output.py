"""Company-organized output path management."""

from pathlib import Path
from datetime import datetime
from typing import Optional

from src.core.models import Platform


class CompanyOutputManager:
    """Manages output paths organized by company and platform.

    Directory structure:
        data/exports/
        +-- {company_id}/
            +-- metadata.json
            +-- {platform}/
                +-- {identifier}/
                    +-- {timestamp}_posts.json
                    +-- {timestamp}_comments.json
                    +-- {timestamp}_profile.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize output manager.

        Args:
            base_dir: Base directory for exports. Defaults to data/exports
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "data" / "exports"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_company_dir(self, company_id: str) -> Path:
        """Get or create company directory."""
        company_dir = self.base_dir / company_id
        company_dir.mkdir(parents=True, exist_ok=True)
        return company_dir

    def get_platform_dir(self, company_id: str, platform: Platform) -> Path:
        """Get or create platform directory within company."""
        platform_dir = self.get_company_dir(company_id) / platform.value
        platform_dir.mkdir(parents=True, exist_ok=True)
        return platform_dir

    def get_account_dir(
        self,
        company_id: str,
        platform: Platform,
        identifier: str
    ) -> Path:
        """Get or create account directory within platform."""
        account_dir = self.get_platform_dir(company_id, platform) / identifier
        account_dir.mkdir(parents=True, exist_ok=True)
        return account_dir

    def get_output_path(
        self,
        company_id: str,
        platform: Platform,
        identifier: str,
        data_type: str,
        extension: str = "json",
        timestamp: Optional[datetime] = None
    ) -> Path:
        """Get full output path for a specific data file.

        Args:
            company_id: Company identifier
            platform: Social media platform
            identifier: Account username/ID
            data_type: Type of data (posts, comments, profile)
            extension: File extension (json, csv, xlsx)
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Full path to output file
        """
        if timestamp is None:
            timestamp = datetime.now()

        account_dir = self.get_account_dir(company_id, platform, identifier)
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{data_type}.{extension}"
        return account_dir / filename

    def get_latest_file(
        self,
        company_id: str,
        platform: Platform,
        identifier: str,
        data_type: str
    ) -> Optional[Path]:
        """Get the most recent file of a given type for an account.

        Args:
            company_id: Company identifier
            platform: Social media platform
            identifier: Account username/ID
            data_type: Type of data (posts, comments, profile)

        Returns:
            Path to most recent file, or None if not found
        """
        account_dir = self.get_account_dir(company_id, platform, identifier)
        pattern = f"*_{data_type}.*"
        files = sorted(account_dir.glob(pattern), reverse=True)
        return files[0] if files else None

    def list_company_exports(self, company_id: str) -> dict:
        """List all exports for a company organized by platform/account.

        Returns:
            Dict with structure: {platform: {account: [files]}}
        """
        company_dir = self.get_company_dir(company_id)
        result = {}

        for platform_dir in company_dir.iterdir():
            if platform_dir.is_dir() and platform_dir.name in [p.value for p in Platform]:
                result[platform_dir.name] = {}
                for account_dir in platform_dir.iterdir():
                    if account_dir.is_dir():
                        files = [f.name for f in account_dir.glob("*.*")]
                        result[platform_dir.name][account_dir.name] = sorted(files)

        return result

    def get_combined_output_path(
        self,
        company_id: str,
        data_type: str,
        extension: str = "json",
        timestamp: Optional[datetime] = None
    ) -> Path:
        """Get path for combined company-wide export.

        Args:
            company_id: Company identifier
            data_type: Type of data (all_posts, all_comments, summary)
            extension: File extension
            timestamp: Optional timestamp

        Returns:
            Path to combined output file
        """
        if timestamp is None:
            timestamp = datetime.now()

        company_dir = self.get_company_dir(company_id)
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{data_type}.{extension}"
        return company_dir / filename


# Singleton instance
_output_manager: Optional[CompanyOutputManager] = None


def get_output_manager(base_dir: Optional[Path] = None) -> CompanyOutputManager:
    """Get or create the output manager singleton."""
    global _output_manager
    if _output_manager is None or base_dir is not None:
        _output_manager = CompanyOutputManager(base_dir)
    return _output_manager
