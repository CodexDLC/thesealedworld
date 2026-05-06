"""Auth feature integration adapters."""

from src.backend.features_site.auth.integrations.auth_persistence import AuthPersistence, DuplicateEmailError

__all__ = ["AuthPersistence", "DuplicateEmailError"]
