"""Tests for provider URL helpers."""

from __future__ import annotations

from custom_components.lhacm.const import ProviderType
from custom_components.lhacm.models import ProviderConfig, RepositoryRef
from custom_components.lhacm.provider import GiteaProvider, GitLabProvider


class DummySession:
    """Placeholder session for URL-only tests."""


def test_gitlab_archive_and_raw_urls() -> None:
    """GitLab URLs use encoded project and file paths."""
    provider = GitLabProvider(
        ProviderConfig(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            token="token",
        ),
        DummySession(),
    )
    ref = RepositoryRef(
        provider=ProviderType.GITLAB,
        base_url="https://gitlab.example.test",
        owner="home/lab",
        name="weather-card",
    )

    assert (
        provider.archive_url(ref, "v1.0.0")
        == "https://gitlab.example.test/api/v4/projects/home%2Flab%2Fweather-card/repository/archive.zip?sha=v1.0.0"
    )
    assert (
        provider.raw_url(ref, "main", "custom_components/weather/manifest.json")
        == "https://gitlab.example.test/api/v4/projects/home%2Flab%2Fweather-card/repository/files/custom_components%2Fweather%2Fmanifest.json/raw?ref=main"
    )


def test_gitea_archive_and_raw_urls() -> None:
    """Gitea URLs target the repository API."""
    provider = GiteaProvider(
        ProviderConfig(
            provider=ProviderType.GITEA,
            base_url="https://gitea.example.test/",
            token="token",
        ),
        DummySession(),
    )
    ref = RepositoryRef(
        provider=ProviderType.GITEA,
        base_url="https://gitea.example.test",
        owner="lab",
        name="weather-card",
    )

    assert (
        provider.archive_url(ref, "v1.0.0")
        == "https://gitea.example.test/api/v1/repos/lab/weather-card/archive/v1.0.0.zip"
    )
    assert (
        provider.raw_url(ref, "main", "custom_components/weather/manifest.json")
        == "https://gitea.example.test/api/v1/repos/lab/weather-card/raw/custom_components/weather/manifest.json?ref=main"
    )
