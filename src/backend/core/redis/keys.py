from codex_platform.redis_service.keys import BaseRedisKey


class ActorSnapshotKey(BaseRedisKey):
    """Temporary actor snapshot assembled for feature session bootstrap."""

    @property
    def template(self) -> str:
        return "game:actor:snapshot:{snapshot_id}"


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
