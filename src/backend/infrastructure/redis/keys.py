from codex_platform.redis_service.keys import BaseRedisKey


class ActorCommitmentKey(BaseRedisKey):
    """Temporary combat actor snapshot assembled before session bootstrap."""

    @property
    def template(self) -> str:
        return "combat:snapshot:{actor_id}"


class PlayerCoreKey(BaseRedisKey):
    """Player core state used by game shell and always-visible status panels."""

    @property
    def template(self) -> str:
        return "game:ac:{char_id}"


class SitePageCacheKey(BaseRedisKey):
    """Optional rendered site page cache namespace."""

    @property
    def template(self) -> str:
        return "site:page:{page_key}"


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
