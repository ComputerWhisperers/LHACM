"""Parse custom repository URLs for LHACM."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from .const import ProviderType
from .exceptions import RepositoryValidationError
from .models import ProviderConfig, RepositoryRef

SSH_RE = re.compile(r"^(?:git@)?(?P<host>[^:]+):(?P<path>.+?)(?:\.git)?$")


def parse_repository_url(repository: str) -> RepositoryRef:
    """Parse a GitLab or Gitea repository URL.

    This intentionally mirrors the HACS custom repository model: the repository
    location is supplied when adding a custom repository, not during integration setup.
    """
    repository = repository.strip()
    if not repository:
        raise RepositoryValidationError("Repository URL is required")

    parsed = urlparse(repository)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        host = parsed.netloc
        path = parsed.path.strip("/")
        base_url = f"{parsed.scheme}://{host}"
    elif match := SSH_RE.match(repository):
        host = match.group("host")
        path = match.group("path").strip("/")
        base_url = f"https://{host}"
    else:
        raise RepositoryValidationError("Expected a GitLab or Gitea repository URL")

    path = path.removesuffix(".git")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise RepositoryValidationError("Repository URL must include owner and repository")

    owner = "/".join(parts[:-1])
    name = parts[-1]
    provider = infer_provider(host)
    return RepositoryRef(provider=provider, base_url=base_url, owner=owner, name=name)


def provider_config_for_repository(ref: RepositoryRef) -> ProviderConfig:
    """Build provider configuration from a parsed repository reference."""
    return ProviderConfig(
        provider=ref.provider,
        base_url=ref.base_url,
        token=_token_for_host(ref.base_url),
    )


def infer_provider(host: str) -> ProviderType:
    """Infer provider type from a repository host."""
    host_lower = host.lower()
    if "gitlab" in host_lower:
        return ProviderType.GITLAB
    if "gitea" in host_lower:
        return ProviderType.GITEA
    return ProviderType.UNKNOWN


def _token_for_host(base_url: str) -> str | None:
    """Return an optional token for a repository host.

    Tokens are deliberately not collected in the integration config. For private
    repositories, operators can set LHACM_TOKEN_<HOST>, with non-alphanumeric
    characters converted to underscores.
    """
    host = urlparse(base_url).netloc.upper()
    key = "LHACM_TOKEN_" + re.sub(r"[^A-Z0-9]", "_", host)
    return os.getenv(key)
