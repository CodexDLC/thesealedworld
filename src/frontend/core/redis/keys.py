from codex_platform.redis_service.keys import BaseRedisKey


class SitePageCacheKey(BaseRedisKey):
    """Optional rendered site page cache namespace."""

    @property
    def template(self) -> str:
        return "site:page:{page_key}"
