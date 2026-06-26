"""Exceptions for LHACM."""

from __future__ import annotations


class LHACMError(Exception):
    """Base LHACM error."""


class ProviderAuthenticationError(LHACMError):
    """Raised when provider authentication fails."""


class ProviderNotFoundError(LHACMError):
    """Raised when a provider resource cannot be found."""


class RepositoryValidationError(LHACMError):
    """Raised when a repository cannot be installed safely."""

