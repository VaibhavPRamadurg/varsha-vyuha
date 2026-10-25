"""Deployment-safe runtime settings for the FastAPI service."""

from __future__ import annotations

import os
from urllib.parse import urlparse


LOCAL_FRONTEND_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


def allowed_frontend_origins(value: str | None = None) -> list[str]:
    """Return local origins plus comma-separated deployment origins from the environment.

    ``ALLOWED_FRONTEND_ORIGINS`` accepts complete origins only, for example
    ``https://varshavyuha.vercel.app``. Rejecting paths and wildcards makes a
    deployment misconfiguration explicit instead of silently widening CORS.
    """

    configured = os.getenv("ALLOWED_FRONTEND_ORIGINS", "") if value is None else value
    origins = list(LOCAL_FRONTEND_ORIGINS)
    for candidate in configured.split(","):
        origin = candidate.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.params or parsed.query or parsed.fragment:
            raise ValueError(
                "ALLOWED_FRONTEND_ORIGINS must contain comma-separated full origins, "
                "for example https://varshavyuha.vercel.app"
            )
        origins.append(origin)
    return list(dict.fromkeys(origins))
