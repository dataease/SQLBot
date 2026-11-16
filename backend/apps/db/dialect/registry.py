"""Registry of dialect policies keyed by datasource type."""

import threading

from apps.db.dialect.base import DialectPolicy


class UnsupportedDialectError(ValueError):
    """Raised when no policy is registered for a datasource type."""


class DialectRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, DialectPolicy] = {}
        self._lock = threading.Lock()

    def register(self, policy: DialectPolicy, *, replace: bool = False) -> DialectPolicy:
        key = policy.key()
        with self._lock:
            if key in self._policies and not replace:
                raise ValueError(f"Dialect policy already registered: {policy.ds_type}")
            self._policies[key] = policy
        return policy

    def find(self, ds_type: str | None) -> DialectPolicy | None:
        if not ds_type:
            return None
        return self._policies.get(ds_type.lower())

    def get(self, ds_type: str | None) -> DialectPolicy:
        """Return the policy or fail closed when the type is unknown."""
        policy = self.find(ds_type)
        if policy is None:
            raise UnsupportedDialectError(f"Unsupported datasource type: {ds_type}")
        return policy

    def types(self) -> set[str]:
        return set(self._policies)


dialect_registry = DialectRegistry()
