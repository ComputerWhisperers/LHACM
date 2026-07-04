"""Data models for LHACM."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .const import ProviderType, RepositoryCategory


@dataclass(slots=True)
class ProviderConfig:
    """Configuration needed to connect to a repository provider."""

    provider: ProviderType
    base_url: str
    token: str | None = None
    verify_ssl: bool = True


@dataclass(slots=True)
class RepositoryRef:
    """A repository identifier on a provider."""

    provider: ProviderType
    base_url: str
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        """Return owner/name."""
        return f"{self.owner}/{self.name}"

    @property
    def provider_key(self) -> str:
        """Return a stable repository key."""
        return f"{self.provider}:{self.base_url.rstrip('/')}:{self.full_name}".lower()


@dataclass(slots=True)
class SourceRepository:
    """Repository metadata from a provider."""

    ref: RepositoryRef
    id: str
    default_branch: str
    description: str | None = None
    archived: bool = False
    html_url: str | None = None
    stars: int = 0
    open_issues: int = 0
    topics: list[str] = field(default_factory=list)
    last_updated: str | None = None


@dataclass(slots=True)
class SourceFile:
    """File metadata from a provider repository tree."""

    path: str
    name: str
    is_directory: bool
    download_url: str | None = None


@dataclass(slots=True)
class SourceRelease:
    """Release metadata from a provider."""

    tag: str
    name: str | None = None
    prerelease: bool = False
    draft: bool = False
    assets: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ManagedRepository:
    """Repository stored by LHACM."""

    ref: RepositoryRef
    category: RepositoryCategory
    domain: str | None = None
    installed_version: str | None = None
    installed_commit: str | None = None
    installed: bool = False
    default_branch: str | None = None
    last_version: str | None = None
    manifest_version: str | None = None
    name: str | None = None
    description: str | None = None
    stars: int = 0
    downloads: int = 0
    last_updated: str | None = None
    custom: bool = True
    installed_path: str | None = None
    source_url: str | None = None
    brand_icon_url: str | None = None
    last_checked: str | None = None
    topics: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        """Return the stable key."""
        return self.ref.provider_key

    def to_json(self) -> dict[str, Any]:
        """Serialize the managed repository."""
        data = asdict(self)
        data["ref"]["provider"] = str(self.ref.provider)
        data["category"] = str(self.category)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ManagedRepository:
        """Create a managed repository from storage data."""
        ref_data = data["ref"]
        return cls(
            ref=RepositoryRef(
                provider=ProviderType(ref_data["provider"]),
                base_url=ref_data["base_url"],
                owner=ref_data["owner"],
                name=ref_data["name"],
            ),
            category=RepositoryCategory(data["category"]),
            domain=data.get("domain"),
            installed_version=data.get("installed_version"),
            installed_commit=data.get("installed_commit"),
            installed=bool(data.get("installed", False)),
            default_branch=data.get("default_branch"),
            last_version=data.get("last_version"),
            manifest_version=data.get("manifest_version"),
            name=data.get("name"),
            description=data.get("description"),
            stars=int(data.get("stars") or 0),
            downloads=int(data.get("downloads") or 0),
            last_updated=data.get("last_updated"),
            custom=bool(data.get("custom", True)),
            installed_path=data.get("installed_path"),
            source_url=data.get("source_url"),
            brand_icon_url=data.get("brand_icon_url"),
            last_checked=data.get("last_checked"),
            topics=list(data.get("topics") or []),
        )

    @property
    def display_name(self) -> str:
        """Return a user-facing repository name."""
        return self.name or self.domain or self.ref.name

    @property
    def available_version(self) -> str:
        """Return the version Home Assistant should display."""
        return self.last_version or self.manifest_version or ""

    @property
    def status(self) -> str:
        """Return HACS-like repository status."""
        if self.installed and self.pending_update:
            return "pending-upgrade"
        if self.installed:
            return "installed"
        return "default"

    @property
    def pending_update(self) -> bool:
        """Return whether the repository has a pending update."""
        if not self.installed:
            return False
        if not self.last_version and not self.manifest_version:
            return bool(self.last_updated and self.installed_commit != self.last_updated)
        return bool(self.available_version and self.available_version != self.installed_version)
