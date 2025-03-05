import redis
import json
import os


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379
REDIS_TTL = 300

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def cache_set_networth_for_user_in_currency(user_name: str, currency: str, value: dict):
    cache_key = f"networth:{user_name}:{currency}"
    redis_client.setex(cache_key, REDIS_TTL, json.dumps(value))


def cache_get_networth_for_user_in_currency(user_name: str, currency: str):
    cache_key = f"networth:{user_name}:{currency}"
    data = redis_client.get(cache_key)
    return json.loads(data) if data else None


def cache_clear_user_networth(user_name: str):
    pattern = f"networth:{user_name}:*"
    keys = list(redis_client.scan_iter(pattern))

    if keys:
        return redis_client.delete(*keys)
    return 0


def is_symbol_in_cache(symbol: str) -> bool:
    key = f"symbol:{symbol}"
    return redis_client.exists(key) > 0


def update_symbol_in_cache(symbol: str):
    key = f"symbol:{symbol}"
    return redis_client.setex(key, REDIS_TTL, "1")
