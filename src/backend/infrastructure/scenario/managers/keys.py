from codex_platform.redis_service.keys import BaseRedisKey


class ScenarioSessionKey(BaseRedisKey):
    @property
    def template(self) -> str:
        return "game:ac:{char_id}:scenario"


class ScenarioStaticKey(BaseRedisKey):
    @property
    def template(self) -> str:
        return "game:scenario:content:{quest_key}"
