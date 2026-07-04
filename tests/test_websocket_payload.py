"""Tests for websocket payload helpers."""

from __future__ import annotations

from custom_components.lhacm.const import ProviderType, RepositoryCategory
from custom_components.lhacm.models import ManagedRepository, RepositoryRef
from custom_components.lhacm.websocket import _repository_info_payload


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
