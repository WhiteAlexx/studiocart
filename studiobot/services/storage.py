import json
import redis

from config import config


redis_client = redis.Redis.from_url(config.REDIS_URL)

class Storage:

    @staticmethod
    def save_verification(verification_id: str, data: dict):
        '''Сохраняет данные верификации'''

        redis_client.hset(
            f"verification:{verification_id}",
            mapping={key: str(value) for key, value in data.items()}
        )
        redis_client.expire(f"verification:{verification_id}", 86400)  # 24 часа


    @staticmethod
    def get_verification(verification_id: str):
        '''Получает данные верификации'''

        data = redis_client.hgetall(f"verification:{verification_id}")
        if not data:
            return {}
        return {key.decode(): value.decode() for key, value in data.items()}


    @staticmethod
    def delete_verification(verification_id: str):
        '''Удаляет данные верификации'''

        redis_client.delete(f"verification:{verification_id}")


    @staticmethod
    def save_state(user_id: int, state: dict):
        '''Сохраняет состояние пользователя'''

        redis_client.set(f"state:{user_id}", json.dumps(state), ex=3600)


    @staticmethod
    def get_state(user_id: int):
        '''Получает состояние пользователя'''

        state = redis_client.get(f"state:{user_id}")
        return json.loads(state) if state else {}


    @staticmethod
    def delete_state(user_id: int):
        '''Удаляет состояние пользователя'''

        redis_client.delete(f"state:{user_id}")
