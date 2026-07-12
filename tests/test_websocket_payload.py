"""Tests for websocket payload helpers."""

from __future__ import annotations

from custom_components.lhacm.const import ProviderType, RepositoryCategory
from custom_components.lhacm.models import ManagedRepository, RepositoryRef
from custom_components.lhacm.websocket import (
    _repository_info_payload,
    _repository_payload,
    _repository_version_options,
)


def test_repository_info_payload_contains_readme() -> None:
    """Repository details include markdown content for the detail view."""
    repository = ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner="lab",
            name="demo",
        ),
        category=RepositoryCategory.INTEGRATION,
        name="Demo",
        description="Demo integration",
        last_version="v1.0.0",
    )

    payload = _repository_info_payload(repository)

    assert payload["name"] == "Demo"
    assert "# Demo" in payload["readme"]
    assert "Demo integration" in payload["readme"]


def test_repository_version_options_include_manifest_version() -> None:
    """Version options include manifest versions used by branch-backed repositories."""
    repository = ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner="lab",
            name="demo",
        ),
        category=RepositoryCategory.INTEGRATION,
        default_branch="main",
        manifest_version="1.2.3",
        installed_version="1.2.2",
    )

    assert _repository_version_options(repository) == [
        {"value": "1.2.3", "label": "1.2.3"},
        {"value": "1.2.2", "label": "1.2.2 (installed)"},
    ]


def test_repository_payload_marks_manifest_update_pending() -> None:
    """Frontend payloads expose pending update rows when versions differ."""
    repository = ManagedRepository(
        ref=RepositoryRef(
            provider=ProviderType.GITLAB,
            base_url="https://gitlab.example.test",
            owner="lab",
            name="autemower-plus",
        ),
        category=RepositoryCategory.INTEGRATION,
        name="Autemower Plus",
        installed=True,
        installed_version="1.0.0",
        manifest_version="1.0.1",
    )

    payload = _repository_payload(repository)

    assert payload["installed_version"] == "1.0.0"
    assert payload["available_version"] == "1.0.1"
    assert payload["pending_upgrade"] is True
    assert payload["status"] == "pending-upgrade"
