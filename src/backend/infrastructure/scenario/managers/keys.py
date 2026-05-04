from codex_platform.redis_service.keys import BaseRedisKey


class ScenarioSessionKey(BaseRedisKey):
    @property
    def template(self) -> str:
        return "game:scen:session:{char_id}"


class ScenarioStaticKey(BaseRedisKey):
    @property
    def template(self) -> str:
        return "game:scen:static:{quest_key}"
