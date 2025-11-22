"""Company registry for managing multi-company extraction targets."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .models import Platform


class CompanyAccount(BaseModel):
    """Social media account for a company."""
    platform: Platform
    identifier: str
    url: Optional[str] = None
    display_name: Optional[str] = None
    enabled: bool = True


class Company(BaseModel):
    """Company with social media accounts across platforms."""
    id: str
    name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    accounts: List[CompanyAccount] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_accounts_by_platform(self, platform: Platform) -> List[CompanyAccount]:
        """Get all enabled accounts for a specific platform."""
        return [
            acc for acc in self.accounts
            if acc.platform == platform and acc.enabled
        ]

    def get_enabled_accounts(self) -> List[CompanyAccount]:
        """Get all enabled accounts."""
        return [acc for acc in self.accounts if acc.enabled]

    def get_platforms(self) -> List[Platform]:
        """Get list of platforms this company has accounts on."""
        return list(set(acc.platform for acc in self.accounts if acc.enabled))


class CompanyRegistry:
    """Registry for managing company configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize registry from config file.

        Args:
            config_path: Path to companies.json. Defaults to config/companies.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "companies.json"

        self.config_path = Path(config_path)
        self._companies: Dict[str, Company] = {}
        self._extraction_defaults: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load companies from JSON configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Companies config not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._extraction_defaults = data.get('extraction_defaults', {})

        for company_data in data.get('companies', []):
            # Convert platform strings to enum
            accounts = []
            for acc_data in company_data.get('accounts', []):
                acc_data['platform'] = Platform(acc_data['platform'])
                accounts.append(CompanyAccount(**acc_data))

            company = Company(
                id=company_data['id'],
                name=company_data['name'],
                industry=company_data.get('industry'),
                country=company_data.get('country'),
                accounts=accounts,
                metadata=company_data.get('metadata', {})
            )
            self._companies[company.id] = company

    def get_company(self, company_id: str) -> Optional[Company]:
        """Get company by ID."""
        return self._companies.get(company_id)

    def get_all_companies(self) -> List[Company]:
        """Get all registered companies."""
        return list(self._companies.values())

    def get_company_ids(self) -> List[str]:
        """Get list of all company IDs."""
        return list(self._companies.keys())

    def get_companies_by_industry(self, industry: str) -> List[Company]:
        """Get all companies in a specific industry."""
        return [
            c for c in self._companies.values()
            if c.industry and c.industry.lower() == industry.lower()
        ]

    def get_companies_by_country(self, country: str) -> List[Company]:
        """Get all companies in a specific country."""
        return [
            c for c in self._companies.values()
            if c.country and c.country.lower() == country.lower()
        ]

    def get_extraction_defaults(self) -> Dict[str, Any]:
        """Get default extraction parameters."""
        return self._extraction_defaults.copy()

    def list_all_accounts(self) -> List[Dict[str, Any]]:
        """List all accounts across all companies for overview."""
        accounts = []
        for company in self._companies.values():
            for acc in company.get_enabled_accounts():
                accounts.append({
                    'company_id': company.id,
                    'company_name': company.name,
                    'platform': acc.platform.value,
                    'identifier': acc.identifier,
                    'url': acc.url
                })
        return accounts

    def get_extraction_targets(
        self,
        company_ids: Optional[List[str]] = None,
        platforms: Optional[List[Platform]] = None
    ) -> List[Dict[str, Any]]:
        """Get extraction targets filtered by company and platform.

        Args:
            company_ids: List of company IDs to include (None = all)
            platforms: List of platforms to include (None = all)

        Returns:
            List of extraction target dicts with company and account info
        """
        targets = []

        companies = self._companies.values()
        if company_ids:
            companies = [c for c in companies if c.id in company_ids]

        for company in companies:
            for account in company.get_enabled_accounts():
                if platforms and account.platform not in platforms:
                    continue

                targets.append({
                    'company_id': company.id,
                    'company_name': company.name,
                    'platform': account.platform,
                    'identifier': account.identifier,
                    'url': account.url,
                    'display_name': account.display_name
                })

        return targets

    def __len__(self) -> int:
        return len(self._companies)

    def __contains__(self, company_id: str) -> bool:
        return company_id in self._companies


# Singleton instance for easy access
_registry_instance: Optional[CompanyRegistry] = None


def get_registry(config_path: Optional[Path] = None) -> CompanyRegistry:
    """Get or create the company registry singleton.

    Args:
        config_path: Optional path to companies.json

    Returns:
        CompanyRegistry instance
    """
    global _registry_instance
    if _registry_instance is None or config_path is not None:
        _registry_instance = CompanyRegistry(config_path)
    return _registry_instance
