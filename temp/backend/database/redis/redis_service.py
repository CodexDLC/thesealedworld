import json
from collections.abc import Callable
from typing import Any

from loguru import logger as log
from redis.asyncio import Redis
from redis.asyncio.client import Pipeline  # Нужно для аннотации типов
from redis.exceptions import RedisError


class RedisService:
    """
    Сервис для взаимодействия с Redis, предоставляющий асинхронные методы
    для работы с различными структурами данных Redis (хеши, множества, списки, ZSET, строки).

    Инкапсулирует логику обработки ошибок Redis и сериализации/десериализации JSON.
    """

    def __init__(self, client: Redis):
        """
        Инициализирует RedisService с заданным асинхронным клиентом Redis.

        Args:
            client: Экземпляр асинхронного клиента Redis.
        """
        self.redis_client = client
        log.debug(f"RedisService | status=initialized client={client}")

    async def execute_pipeline(self, builder_func: Callable[[Pipeline], None]) -> list[Any]:
        """
        Выполняет последовательность команд в пайплайне Redis.

        Args:
            builder_func: Функция, принимающая объект Pipeline и наполняющая его командами.
                          Важно: команды внутри builder_func не должны использовать await,
                          так как методы pipeline в redis-py возвращают сам pipeline.

        Returns:
            Список результатов выполнения команд. Возвращает пустой список в случае ошибки.
        """
        try:
            async with self.redis_client.pipeline() as pipe:
                # Менеджер наполняет пайплайн
                builder_func(pipe)
                # Сервис выполняет пайплайн
                results = await pipe.execute()

            log.debug(f"RedisPipeline | action=execute status=success commands_count={len(results)}")
            return results

        except RedisError:
            log.exception("RedisPipeline | action=execute status=failed reason='Redis error'")
            return []
        except Exception as e:  # noqa: BLE001
            # Ловим ошибки, которые могли возникнуть внутри builder_func (например, сериализация)
            log.exception(f"RedisPipeline | action=execute status=failed reason='Builder error' error='{e}'")
            return []

    # --- RedisJSON Methods ---

    async def json_set(self, key: str, path: str, obj: Any, nx: bool = False, xx: bool = False) -> bool:
        """
        Устанавливает значение JSON по указанному пути.

        Args:
            key: Ключ Redis.
            path: Путь JSON (например, "$").
            obj: Объект для сохранения.
            nx: Set if Not Exists.
            xx: Set if Exists.

        Returns:
            bool: Успех операции.
        """
        try:
            # redis-py stubs issue with async json
            result = await self.redis_client.json().set(key, path, obj, nx=nx, xx=xx)  # type: ignore
            log.debug(f"RedisJSON | action=set status=success key='{key}' path='{path}'")
            return bool(result)
        except RedisError:
            log.exception(f"RedisJSON | action=set status=failed reason='Redis error' key='{key}'")
            return False

    async def json_get(self, key: str, path: str = "$") -> Any:
        """
        Получает значение JSON по указанному пути.

        Args:
            key: Ключ Redis.
            path: Путь JSON.

        Returns:
            Any: Значение или None.
        """
        try:
            # redis-py stubs issue with async json
            result = await self.redis_client.json().get(key, path)  # type: ignore
            log.debug(f"RedisJSON | action=get status=found key='{key}' path='{path}'")
            return result
        except RedisError:
            log.exception(f"RedisJSON | action=get status=failed reason='Redis error' key='{key}'")
            return None

    async def json_arrappend(self, key: str, path: str, *args: Any) -> int:
        """
        Добавляет элементы в массив JSON.

        Args:
            key: Ключ Redis.
            path: Путь к массиву.
            *args: Элементы для добавления.

        Returns:
            int: Новая длина массива.
        """
        try:
            # redis-py stubs issue with async json
            count = await self.redis_client.json().arrappend(key, path, *args)  # type: ignore
            log.debug(f"RedisJSON | action=arrappend status=success key='{key}' count={count}")
            return int(count) if count else 0
        except RedisError:
            log.exception(f"RedisJSON | action=arrappend status=failed reason='Redis error' key='{key}'")
            return 0

    async def json_del(self, key: str, path: str = "$") -> int:
        """
        Удаляет значение JSON по указанному пути.

        Args:
            key: Ключ Redis.
            path: Путь для удаления.

        Returns:
            int: Количество удаленных элементов.
        """
        try:
            # redis-py stubs issue with async json
            result = await self.redis_client.json().delete(key, path)  # type: ignore
            log.debug(f"RedisJSON | action=del status=success key='{key}' path='{path}' count={result}")
            return int(result)
        except RedisError:
            log.exception(f"RedisJSON | action=del status=failed reason='Redis error' key='{key}'")
            return 0

    # --- Standard Methods ---

    async def eval_script(self, script: str, keys: list[str], args: list[Any]) -> Any:
        """
        Выполняет Lua-скрипт.

        Args:
            script: Текст скрипта.
            keys: Список ключей.
            args: Список аргументов.

        Returns:
            Any: Результат выполнения скрипта.
        """
        try:
            result = await self.redis_client.eval(script, len(keys), *keys, *args)  # type: ignore
            return result
        except RedisError:
            log.exception("RedisService | action=eval status=failed reason='Redis error'")
            return None

    async def expire(self, key: str, time: int) -> bool:
        """
        Устанавливает время жизни (TTL) для ключа.

        Args:
            key: Ключ Redis.
            time: Время жизни в секундах.

        Returns:
            True, если тайм-аут был установлен, иначе False.
        """
        try:
            result = await self.redis_client.expire(key, time)  # type: ignore
            log.debug(f"RedisKey | action=expire status=success key='{key}' ttl={time}")
            return bool(result)
        except RedisError:
            log.exception(f"RedisKey | action=expire status=failed reason='Redis error' key='{key}'")
            return False

    async def set_hash_json(self, key: str, field: str, data: dict[str, Any]) -> None:
        """
        Сериализует словарь в JSON-строку и сохраняет её в указанное поле хеша Redis.

        Args:
            key: Ключ хеша Redis.
            field: Поле внутри хеша.
            data: Словарь для сериализации и сохранения.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
            TypeError: Если `data` не может быть сериализован в JSON.
        """
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(key, field, data_json)  # type: ignore
            log.debug(f"RedisHash | action=set_json status=success key='{key}' field='{field}'")
        except TypeError:
            log.error(
                f"RedisHash | action=set_json status=failed reason='JSON serialization error' key='{key}' field='{field}'",
                exc_info=True,
            )
        except RedisError:
            log.exception(f"RedisHash | action=set_json status=failed reason='Redis error' key='{key}' field='{field}'")

    async def set_hash_fields(self, key: str, data: dict[str, Any]) -> None:
        """
        Устанавливает несколько полей и их значений в хеше Redis за один вызов.

        Args:
            key: Ключ хеша Redis.
            data: Словарь, где ключи — это поля, а значения — значения полей.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.hset(key, mapping=data)  # type: ignore
            log.debug(f"RedisHash | action=set_fields status=success key='{key}' fields={list(data.keys())}")
        except RedisError:
            log.exception(f"RedisHash | action=set_fields status=failed reason='Redis error' key='{key}'")

    async def set_hash_field(self, key: str, field: str, value: str) -> None:
        """
        Устанавливает значение одного поля в хеше Redis.

        Args:
            key: Ключ хеша Redis.
            field: Поле внутри хеша.
            value: Значение поля.
        """
        try:
            await self.redis_client.hset(key, field, value)  # type: ignore
            log.debug(f"RedisHash | action=set_field status=success key='{key}' field='{field}'")
        except RedisError:
            log.exception(
                f"RedisHash | action=set_field status=failed reason='Redis error' key='{key}' field='{field}'"
            )

    async def get_hash_json(self, key: str, field: str) -> dict[str, Any] | None:
        """
        Получает JSON-строку из поля хеша Redis и десериализует её в словарь.

        Args:
            key: Ключ хеша Redis.
            field: Поле внутри хеша.

        Returns:
            Десериализованный словарь, если найден и успешно десериализован, иначе None.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
            json.JSONDecodeError: Если содержимое поля не является валидным JSON.
        """
        try:
            data_json = await self.redis_client.hget(key, field)  # type: ignore
            if data_json:
                log.debug(f"RedisHash | action=get_json status=found key='{key}' field='{field}'")
                return json.loads(data_json)
            log.debug(f"RedisHash | action=get_json status=not_found key='{key}' field='{field}'")
            return None
        except json.JSONDecodeError:
            log.error(
                f"RedisHash | action=get_json status=failed reason='JSON deserialization error' key='{key}' field='{field}'",
                exc_info=True,
            )
            return None
        except RedisError:
            log.exception(f"RedisHash | action=get_json status=failed reason='Redis error' key='{key}' field='{field}'")
            return None

    async def get_hash_field(self, key: str, field: str) -> str | None:
        """
        Получает строковое значение одного поля из хеша Redis.

        Args:
            key: Ключ хеша Redis.
            field: Поле внутри хеша.

        Returns:
            Строковое значение поля, если найдено, иначе None.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            value = await self.redis_client.hget(key, field)  # type: ignore
            if value:
                log.debug(f"RedisHash | action=get_field status=found key='{key}' field='{field}'")
                return value
            log.debug(f"RedisHash | action=get_field status=not_found key='{key}' field='{field}'")
            return None
        except RedisError:
            log.exception(
                f"RedisHash | action=get_field status=failed reason='Redis error' key='{key}' field='{field}'"
            )
            return None

    async def get_all_hash(self, key: str) -> dict[str, str] | None:
        """
        Получает все поля и их строковые значения из хеша Redis.

        Args:
            key: Ключ хеша Redis.

        Returns:
            Словарь со всеми полями и значениями хеша, если хеш существует и не пуст, иначе None.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            data_dict = await self.redis_client.hgetall(key)  # type: ignore
            if data_dict:
                log.debug(f"RedisHash | action=get_all status=found key='{key}' fields_count={len(data_dict)}")
                return data_dict
            log.debug(f"RedisHash | action=get_all status=not_found key='{key}'")
            return None
        except RedisError:
            log.exception(f"RedisHash | action=get_all status=failed reason='Redis error' key='{key}'")
            return None

    async def delete_hash_key(self, key: str) -> None:
        """
        Удаляет весь хеш по указанному ключу Redis.

        Args:
            key: Ключ хеша Redis для удаления.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.delete(key)  # type: ignore
            log.debug(f"RedisHash | action=delete_key status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisHash | action=delete_key status=failed reason='Redis error' key='{key}'")

    async def delete_hash_field(self, key: str, field: str) -> None:
        """
        Удаляет одно поле из хеша Redis.

        Args:
            key: Ключ хеша Redis.
            field: Поле для удаления из хеша.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.hdel(key, field)  # type: ignore
            log.debug(f"RedisHash | action=delete_field status=success key='{key}' field='{field}'")
        except RedisError:
            log.exception(
                f"RedisHash | action=delete_field status=failed reason='Redis error' key='{key}' field='{field}'"
            )

    async def add_to_set(self, key: str, value: str | int) -> None:
        """
        Добавляет строковое или целочисленное значение в множество Redis.

        Args:
            key: Ключ множества Redis.
            value: Значение для добавления.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.sadd(key, str(value))  # type: ignore
            log.debug(f"RedisSet | action=add status=success key='{key}' value='{value}'")
        except RedisError:
            log.exception(f"RedisSet | action=add status=failed reason='Redis error' key='{key}' value='{value}'")

    async def get_set_members(self, key: str) -> set[str]:
        """
        Возвращает все элементы множества Redis.

        Args:
            key: Ключ множества Redis.

        Returns:
            Множество строковых элементов. Возвращает пустое множество в случае ошибки.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            members = await self.redis_client.smembers(key)  # type: ignore
            log.debug(f"RedisSet | action=get_all status=success key='{key}' members_count={len(members)}")
            return members
        except RedisError:
            log.exception(f"RedisSet | action=get_all status=failed reason='Redis error' key='{key}'")
            return set()

    async def is_set_member(self, key: str, value: str | int) -> bool:
        """
        Проверяет, является ли указанное значение элементом множества Redis.

        Args:
            key: Ключ множества Redis.
            value: Значение для проверки.

        Returns:
            True, если значение является элементом множества, иначе False.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            is_member = await self.redis_client.sismember(key, str(value))  # type: ignore
            log.debug(
                f"RedisSet | action=is_member status=checked key='{key}' value='{value}' result={bool(is_member)}"
            )
            return bool(is_member)
        except RedisError:
            log.exception(f"RedisSet | action=is_member status=failed reason='Redis error' key='{key}' value='{value}'")
            return False

    async def remove_from_set(self, key: str, value: str | int) -> None:
        """
        Удаляет указанное значение из множества Redis.

        Args:
            key: Ключ множества Redis.
            value: Значение для удаления.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.srem(key, str(value))  # type: ignore
            log.debug(f"RedisSet | action=remove status=success key='{key}' value='{value}'")
        except RedisError:
            log.exception(f"RedisSet | action=remove status=failed reason='Redis error' key='{key}' value='{value}'")

    async def key_exists(self, key: str) -> bool:
        """
        Проверяет существование ключа в Redis.

        Args:
            key: Ключ для проверки.

        Returns:
            True, если ключ существует, иначе False.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            exists = await self.redis_client.exists(key)  # type: ignore
            log.debug(f"RedisKey | action=exists status=checked key='{key}' result={bool(exists)}")
            return bool(exists)
        except RedisError:
            log.exception(f"RedisKey | action=exists status=failed reason='Redis error' key='{key}'")
            return False

    async def add_to_zset(self, key: str, mapping: dict[str, float]) -> int:
        """
        Добавляет или обновляет элементы в отсортированном множестве (ZSET) Redis.

        Args:
            key: Ключ ZSET Redis.
            mapping: Словарь, где ключи — это члены ZSET, а значения — их очки (scores).

        Returns:
            Количество добавленных или обновленных элементов. Возвращает 0 в случае ошибки.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            count = await self.redis_client.zadd(key, mapping)  # type: ignore
            log.debug(f"RedisZSet | action=add status=success key='{key}' count={count}")
            return int(count)
        except RedisError:
            log.exception(f"RedisZSet | action=add status=failed reason='Redis error' key='{key}'")
            return 0

    async def get_zset_score(self, key: str, member: str) -> float | None:
        """
        Возвращает очки (score) указанного члена отсортированного множества Redis.

        Args:
            key: Ключ ZSET Redis.
            member: Член ZSET, очки которого нужно получить.

        Returns:
            Очки члена в виде float, если член существует, иначе None.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            score = await self.redis_client.zscore(key, member)  # type: ignore
            log.debug(f"RedisZSet | action=get_score status=success key='{key}' member='{member}' score={score}")
            return float(score) if score is not None else None
        except RedisError:
            log.exception(
                f"RedisZSet | action=get_score status=failed reason='Redis error' key='{key}' member='{member}'"
            )
            return None

    async def get_zset_range_by_score(self, key: str, min_score: float, max_score: float) -> list[str]:
        """
        Возвращает список членов отсортированного множества Redis, чьи очки находятся в заданном диапазоне.

        Args:
            key: Ключ ZSET Redis.
            min_score: Минимальное значение очков (включительно).
            max_score: Максимальное значение очков (включительно).

        Returns:
            Список строковых членов ZSET. Возвращает пустой список в случае ошибки.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            res = await self.redis_client.zrangebyscore(key, min_score, max_score)  # type: ignore
            log.debug(
                f"RedisZSet | action=get_range_by_score status=success key='{key}' min={min_score} max={max_score} count={len(res)}"
            )
            return res
        except RedisError:
            log.exception(f"RedisZSet | action=get_range_by_score status=failed reason='Redis error' key='{key}'")
            return []

    async def remove_from_zset(self, key: str, member: str) -> bool:
        """
        Удаляет указанный член из отсортированного множества Redis.

        Args:
            key: Ключ ZSET Redis.
            member: Член для удаления.

        Returns:
            True, если член был удален, иначе False.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            count = await self.redis_client.zrem(key, member)  # type: ignore
            if count > 0:
                log.debug(f"RedisZSet | action=remove status=success key='{key}' member='{member}'")
                return True
            log.debug(f"RedisZSet | action=remove status=not_found key='{key}' member='{member}'")
            return False
        except RedisError:
            log.exception(f"RedisZSet | action=remove status=failed reason='Redis error' key='{key}' member='{member}'")
            return False

    async def set_value(self, key: str, value: str, ttl: int | None = None) -> None:
        """
        Устанавливает строковое значение для ключа Redis с опциональным временем жизни (TTL).

        Args:
            key: Ключ Redis.
            value: Строковое значение.
            ttl: Время жизни ключа в секундах. Если None, ключ не имеет TTL.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.set(key, value, ex=ttl)  # type: ignore
            log.debug(f"RedisString | action=set status=success key='{key}' ttl={ttl}")
        except RedisError:
            log.exception(f"RedisString | action=set status=failed reason='Redis error' key='{key}'")

    async def get_value(self, key: str) -> str | None:
        """
        Получает строковое значение по ключу Redis.

        Args:
            key: Ключ Redis.

        Returns:
            Строковое значение, если ключ существует, иначе None.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            val = await self.redis_client.get(key)  # type: ignore
            if val is not None:
                log.debug(f"RedisString | action=get status=found key='{key}'")
                return str(val)
            log.debug(f"RedisString | action=get status=not_found key='{key}'")
            return None
        except RedisError:
            log.exception(f"RedisString | action=get status=failed reason='Redis error' key='{key}'")
            return None

    async def delete_key(self, key: str) -> None:
        """
        Удаляет ключ любого типа из Redis.

        Args:
            key: Ключ Redis для удаления.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.delete(key)  # type: ignore
            log.debug(f"RedisKey | action=delete status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisKey | action=delete status=failed reason='Redis error' key='{key}'")

    async def push_to_list(self, key: str, value: str) -> None:
        """
        Добавляет элемент в конец списка Redis (RPUSH).

        Args:
            key: Ключ списка Redis.
            value: Строковое значение для добавления.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            await self.redis_client.rpush(key, value)  # type: ignore
            log.debug(f"RedisList | action=push status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisList | action=push status=failed reason='Redis error' key='{key}'")

    async def pop_from_list_left(self, key: str) -> str | None:
        """
        Удаляет и возвращает первый элемент списка Redis (LPOP).

        Args:
            key: Ключ списка Redis.

        Returns:
            Строковое значение элемента или None, если список пуст.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            value = await self.redis_client.lpop(key)  # type: ignore
            if value:
                log.debug(f"RedisList | action=lpop status=success key='{key}'")
                return str(value)
            return None
        except RedisError:
            log.exception(f"RedisList | action=lpop status=failed reason='Redis error' key='{key}'")
            return None

    async def get_list_range(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """
        Возвращает диапазон элементов из списка Redis.

        Args:
            key: Ключ списка Redis.
            start: Начальный индекс диапазона (включительно).
            end: Конечный индекс диапазона (включительно, -1 для последнего элемента).

        Returns:
            Список строковых элементов. Возвращает пустой список в случае ошибки.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        try:
            result = await self.redis_client.lrange(key, start, end)  # type: ignore
            log.debug(
                f"RedisList | action=get_range status=success key='{key}' start={start} end={end} count={len(result)}"
            )
            return result
        except RedisError:
            log.exception(f"RedisList | action=get_range status=failed reason='Redis error' key='{key}'")
            return []

    async def get_list_length(self, key: str) -> int:
        """
        Возвращает длину списка Redis.

        Args:
            key: Ключ списка Redis.

        Returns:
            Длина списка. Возвращает 0 в случае ошибки или если ключ не существует.
        """
        try:
            count = await self.redis_client.llen(key)  # type: ignore
            log.debug(f"RedisList | action=len status=success key='{key}' count={count}")
            return int(count)
        except RedisError:
            log.exception(f"RedisList | action=len status=failed reason='Redis error' key='{key}'")
            return 0

    async def delete_by_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи из Redis, соответствующие заданному паттерну.
        Использует `SCAN` для безопасного удаления большого количества ключей.

        Args:
            pattern: Паттерн для поиска ключей (например, "prefix:*").

        Returns:
            Количество удаленных ключей. Возвращает 0 в случае ошибки.

        Raises:
            RedisError: Если произошла ошибка при взаимодействии с Redis.
        """
        deleted_count = 0
        try:
            keys_to_delete = [k async for k in self.redis_client.scan_iter(match=pattern)]
            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)  # type: ignore
            log.debug(
                f"RedisKey | action=delete_by_pattern status=success pattern='{pattern}' deleted_count={deleted_count}"
            )
            return int(deleted_count)
        except RedisError:
            log.exception(f"RedisKey | action=delete_by_pattern status=failed reason='Redis error' pattern='{pattern}'")
            return 0
