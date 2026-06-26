"""Repository provider clients for LHACM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any
from urllib.parse import quote, urljoin

from aiohttp import ClientResponse, ClientSession

from .const import ProviderType
from .exceptions import ProviderAuthenticationError, ProviderNotFoundError, LHACMError
from .models import ProviderConfig, RepositoryRef, SourceFile, SourceRelease, SourceRepository


class RepositoryProvider(ABC):
    """Common interface for repository providers."""

    provider_type: ProviderType

    def __init__(self, config: ProviderConfig, session: ClientSession) -> None:
        """Initialize the provider."""
        self.config = config
        self.session = session
        self.base_url = config.base_url.rstrip("/")

    @abstractmethod
    async def validate_auth(self) -> None:
        """Validate authentication."""

    @abstractmethod
    async def get_repository(self, ref: RepositoryRef) -> SourceRepository:
        """Get repository metadata."""

    @abstractmethod
    async def get_tree(self, ref: RepositoryRef, branch: str) -> list[SourceFile]:
        """Get a recursive repository tree."""

    @abstractmethod
    async def get_releases(self, ref: RepositoryRef) -> list[SourceRelease]:
        """Get repository releases."""

    @abstractmethod
    def archive_url(self, ref: RepositoryRef, revision: str) -> str:
        """Return a URL that downloads a repository archive."""

    @abstractmethod
    def raw_url(self, ref: RepositoryRef, revision: str, path: str) -> str:
        """Return a URL for raw repository file content."""

    @abstractmethod
    def archive_headers(self) -> dict[str, str]:
        """Return headers for archive downloads."""

    def _api_url(self, path: str) -> str:
        """Build a provider API URL."""
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> Any:
        """Send an API request and return JSON."""
        response = await self.session.request(
            method,
            url,
            headers=self._headers(),
            ssl=self.config.verify_ssl,
            **kwargs,
        )
        await self._raise_for_status(response)
        if response.status == 204:
            return None
        return await response.json()

    async def _raise_for_status(self, response: ClientResponse) -> None:
        """Convert provider HTTP status codes to LHACM errors."""
        if response.status in (401, 403):
            raise ProviderAuthenticationError("Provider authentication failed")
        if response.status == 404:
            raise ProviderNotFoundError("Provider resource was not found")
        if response.status >= 400:
            text = await response.text()
            raise LHACMError(f"Provider returned HTTP {response.status}: {text[:250]}")

    @abstractmethod
    def _headers(self) -> dict[str, str]:
        """Return authentication headers."""


class GitLabProvider(RepositoryProvider):
    """GitLab provider client."""

    provider_type = ProviderType.GITLAB

    async def validate_auth(self) -> None:
        """Validate GitLab authentication."""
        await self._request_json("GET", self._api_url("/api/v4/user"))

    async def get_repository(self, ref: RepositoryRef) -> SourceRepository:
        """Get GitLab project metadata."""
        project = await self._request_json("GET", self._project_url(ref))
        return SourceRepository(
            ref=ref,
            id=str(project["id"]),
            default_branch=project.get("default_branch") or "main",
            description=project.get("description"),
            archived=bool(project.get("archived", False)),
            html_url=project.get("web_url"),
            stars=int(project.get("star_count") or 0),
            open_issues=int(project.get("open_issues_count") or 0),
            topics=list(project.get("topics") or project.get("tag_list") or []),
        )

    async def get_tree(self, ref: RepositoryRef, branch: str) -> list[SourceFile]:
        """Get a recursive GitLab repository tree."""
        project_url = self._project_url(ref)
        items: list[SourceFile] = []
        page = 1
        while True:
            batch = await self._request_json(
                "GET",
                f"{project_url}/repository/tree",
                params={"recursive": "true", "ref": branch, "per_page": 100, "page": page},
            )
            if not batch:
                break
            items.extend(self._gitlab_tree_items(ref, branch, batch))
            if len(batch) < 100:
                break
            page += 1
        return items

    async def get_releases(self, ref: RepositoryRef) -> list[SourceRelease]:
        """Get GitLab releases."""
        releases = await self._request_json("GET", f"{self._project_url(ref)}/releases")
        return [
            SourceRelease(
                tag=release["tag_name"],
                name=release.get("name"),
                prerelease=bool(release.get("upcoming_release", False)),
                assets=list((release.get("assets") or {}).get("links") or []),
            )
            for release in releases
        ]

    def archive_url(self, ref: RepositoryRef, revision: str) -> str:
        """Return GitLab archive URL."""
        return f"{self._project_url(ref)}/repository/archive.zip?sha={quote(revision, safe='')}"

    def raw_url(self, ref: RepositoryRef, revision: str, path: str) -> str:
        """Return GitLab raw file URL."""
        encoded_path = quote(path, safe="")
        encoded_revision = quote(revision, safe="")
        return f"{self._project_url(ref)}/repository/files/{encoded_path}/raw?ref={encoded_revision}"

    def archive_headers(self) -> dict[str, str]:
        """Return GitLab archive headers."""
        return self._headers()

    def _headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": self.config.token} if self.config.token else {}

    def _project_url(self, ref: RepositoryRef) -> str:
        encoded = quote(ref.full_name, safe="")
        return self._api_url(f"/api/v4/projects/{encoded}")

    def _gitlab_tree_items(
        self,
        ref: RepositoryRef,
        branch: str,
        batch: Iterable[dict[str, Any]],
    ) -> list[SourceFile]:
        return [
            SourceFile(
                path=item["path"],
                name=item["name"],
                is_directory=item["type"] == "tree",
                download_url=None
                if item["type"] == "tree"
                else self.raw_url(ref, branch, item["path"]),
            )
            for item in batch
        ]


class GiteaProvider(RepositoryProvider):
    """Gitea provider client."""

    provider_type = ProviderType.GITEA

    async def validate_auth(self) -> None:
        """Validate Gitea authentication."""
        await self._request_json("GET", self._api_url("/api/v1/user"))

    async def get_repository(self, ref: RepositoryRef) -> SourceRepository:
        """Get Gitea repository metadata."""
        repo = await self._request_json("GET", self._repo_url(ref))
        return SourceRepository(
            ref=ref,
            id=str(repo["id"]),
            default_branch=repo.get("default_branch") or "main",
            description=repo.get("description"),
            archived=bool(repo.get("archived", False)),
            html_url=repo.get("html_url"),
            stars=int(repo.get("stars_count") or 0),
            open_issues=int(repo.get("open_issues_count") or 0),
            topics=list(repo.get("topics") or []),
        )

    async def get_tree(self, ref: RepositoryRef, branch: str) -> list[SourceFile]:
        """Get a recursive Gitea repository tree."""
        tree = await self._request_json(
            "GET",
            f"{self._repo_url(ref)}/git/trees/{quote(branch, safe='')}",
            params={"recursive": "1"},
        )
        return [
            SourceFile(
                path=item["path"],
                name=item["path"].split("/")[-1],
                is_directory=item.get("type") == "tree",
                download_url=None
                if item.get("type") == "tree"
                else self.raw_url(ref, branch, item["path"]),
            )
            for item in tree.get("tree", [])
        ]

    async def get_releases(self, ref: RepositoryRef) -> list[SourceRelease]:
        """Get Gitea releases."""
        releases = await self._request_json("GET", f"{self._repo_url(ref)}/releases")
        return [
            SourceRelease(
                tag=release["tag_name"],
                name=release.get("name"),
                prerelease=bool(release.get("prerelease", False)),
                draft=bool(release.get("draft", False)),
                assets=list(release.get("assets") or []),
            )
            for release in releases
        ]

    def archive_url(self, ref: RepositoryRef, revision: str) -> str:
        """Return Gitea archive URL."""
        encoded_revision = quote(revision, safe="")
        return self._api_url(f"/api/v1/repos/{ref.owner}/{ref.name}/archive/{encoded_revision}.zip")

    def raw_url(self, ref: RepositoryRef, revision: str, path: str) -> str:
        """Return Gitea raw file URL."""
        encoded_path = quote(path)
        encoded_revision = quote(revision, safe="")
        return self._api_url(
            f"/api/v1/repos/{ref.owner}/{ref.name}/raw/{encoded_path}?ref={encoded_revision}"
        )

    def archive_headers(self) -> dict[str, str]:
        """Return Gitea archive headers."""
        return self._headers()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"token {self.config.token}"} if self.config.token else {}

    def _repo_url(self, ref: RepositoryRef) -> str:
        return self._api_url(f"/api/v1/repos/{ref.owner}/{ref.name}")


def create_provider(config: ProviderConfig, session: ClientSession) -> RepositoryProvider:
    """Create a provider from configuration."""
    if config.provider == ProviderType.GITLAB:
        return GitLabProvider(config, session)
    if config.provider == ProviderType.GITEA:
        return GiteaProvider(config, session)
    raise LHACMError(f"Unsupported provider: {config.provider}")
