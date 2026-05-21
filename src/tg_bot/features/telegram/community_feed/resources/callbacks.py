from aiogram.filters.callback_data import CallbackData

# If this is a PAIRED feature (handling buttons from Redis notifications):
# 1. Import the base callback:
# from features.redis.community_feed.resources.callbacks import CommunityFeedCallback as BaseCallback
# 2. Inherit WITHOUT a new prefix (to catch the same events):
# class CommunityFeedCallback(BaseCallback):
#     pass


# If this is a STANDALONE feature:
class CommunityFeedCallback(CallbackData, prefix="community_feed"):
    """Callback for the CommunityFeed feature."""

    action: str
    id: str | int
