from typing import Any

from app.core.config import Settings


def create_redis_client(settings: Settings) -> Any:
    try:
        from redis import Redis
    except ImportError as exc:
        raise RuntimeError("Install backend requirements to use Redis: pip install -r backend/requirements.txt") from exc

    return Redis.from_url(settings.redis_url, decode_responses=True)
