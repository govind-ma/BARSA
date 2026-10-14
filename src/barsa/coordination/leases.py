"""Lease management, fencing tokens, and heartbeat tracking for task coordination."""

import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

logger = logging.getLogger("barsa.coordination.leases")

_LEASE_COUNTER = 0


def generate_fencing_token(prefix: str = "lease") -> str:
    """Generate a monotonically unique fencing token to prevent stale worker writes."""
    global _LEASE_COUNTER
    _LEASE_COUNTER += 1
    timestamp_ms = int(time.time() * 1000)
    rand_part = uuid4().hex[:6]
    return f"{prefix}-{timestamp_ms}-{_LEASE_COUNTER}-{rand_part}"


def compute_lease_expiration(duration_seconds: int, from_time: datetime | None = None) -> datetime:
    """Compute expiration timestamp from a duration in seconds."""
    base = from_time or datetime.now(UTC)
    return base + timedelta(seconds=duration_seconds)


def is_lease_expired(expires_at: datetime | None, current_time: datetime | None = None) -> bool:
    """Check whether a lease has expired."""
    if expires_at is None:
        return False
    now = current_time or datetime.now(UTC)
    return now > expires_at
