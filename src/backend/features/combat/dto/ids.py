type ActorId = str
type ActorIdLike = int | str


def normalize_actor_id(value: ActorIdLike) -> ActorId:
    return str(value)


def normalize_actor_ids(values: list[ActorIdLike]) -> list[ActorId]:
    return [normalize_actor_id(value) for value in values]
