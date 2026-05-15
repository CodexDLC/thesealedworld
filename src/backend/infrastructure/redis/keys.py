from codex_platform.redis_service.keys import BaseRedisKey


class ActorCommitmentKey(BaseRedisKey):
    """Temporary combat actor snapshot assembled before session bootstrap."""

    @property
    def template(self) -> str:
        return "game:combat:snapshot:{actor_id}"


class PlayerCoreKey(BaseRedisKey):
    """Player core state used by game shell and always-visible status panels."""

    @property
    def template(self) -> str:
        return "game:ac:{char_id}"


class WorldLocationKey(BaseRedisKey):
    """Runtime location metadata loaded from persistent world tables."""

    @property
    def template(self) -> str:
        return "game:world:location:{loc_id}"


class WorldLocationPlayersKey(BaseRedisKey):
    """Online character ids currently present in a location."""

    @property
    def template(self) -> str:
        return "game:world:location:{loc_id}:players"


class WorldLocationBattlesKey(BaseRedisKey):
    """Battle summaries currently visible in a location."""

    @property
    def template(self) -> str:
        return "game:world:location:{loc_id}:battles"


class ExpeditionActiveKey(BaseRedisKey):
    """Pointer from character id to the active dirty-gains expedition run."""

    @property
    def template(self) -> str:
        return "game:expedition:active:{char_id}"


class ExpeditionRunKey(BaseRedisKey):
    """Runtime cache for a dirty-gains expedition run."""

    @property
    def template(self) -> str:
        return "game:expedition:{run_id}"
