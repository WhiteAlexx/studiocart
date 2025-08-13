from typing import Any, Awaitable, Callable

import redis

from config import config


redis_client = redis.Redis.from_url(config.REDIS_URL)


async def banner_cache(cache_key: str, func: Callable[[], Awaitable[Any]], ttl: int):

    if cached_data := redis_client.hgetall(cache_key):
        image_id = cached_data[b'image_id'].decode()
        description = cached_data[b'description'].decode()

    else:
        banner = await func()

        try:
            image_id = banner.image
        except AttributeError:
            image_id = banner.banner

        try:
            description = banner.description
        except AttributeError:
            description = banner.name


        redis_client.hset(cache_key, mapping={
            "image_id": image_id,
            "description": description
        })
        redis_client.expire(cache_key, ttl)

    return image_id, description
