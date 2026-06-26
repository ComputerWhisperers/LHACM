"""Tests for custom repository URL parsing."""

from __future__ import annotations

from custom_components.lhacm.const import ProviderType
from custom_components.lhacm.repository_url import parse_repository_url


def test_parse_gitlab_url() -> None:
    """GitLab URLs are parsed into provider, host, owner, and repo."""
    ref = parse_repository_url("https://gitlab.example.test/home/lab/weather-card.git")

    assert ref.provider == ProviderType.GITLAB
    assert ref.base_url == "https://gitlab.example.test"
    assert ref.owner == "home/lab"
    assert ref.name == "weather-card"


def test_parse_gitea_ssh_url() -> None:
    """Gitea SSH URLs are accepted for HACS-style custom repository entry."""
    ref = parse_repository_url("git@gitea.example.test:lab/weather-card.git")

    assert ref.provider == ProviderType.GITEA
    assert ref.base_url == "https://gitea.example.test"
    assert ref.owner == "lab"
    assert ref.name == "weather-card"


def test_unknown_host_is_allowed_for_probe_detection() -> None:
    """Private local hosts can be probed as GitLab then Gitea later."""
    ref = parse_repository_url("https://source.local/home/lab/weather-card")

    assert ref.provider == ProviderType.UNKNOWN
    assert ref.base_url == "https://source.local"
    assert ref.owner == "home/lab"
    assert ref.name == "weather-card"
