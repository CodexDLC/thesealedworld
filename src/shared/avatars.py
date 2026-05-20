AVATAR_CATALOG: dict[str, list[str]] = {
    "feminine": [f"/static/images/avatars/feminine/avatar_f_{i:02d}.png" for i in range(1, 7)],
    "masculine": [f"/static/images/avatars/masculine/avatar_m_{i:02d}.png" for i in range(1, 7)],
}

ALL_VALID_AVATAR_URLS: set[str] = {url for urls in AVATAR_CATALOG.values() for url in urls} | {
    "/static/images/avatars/silhouette_f.png",
    "/static/images/avatars/silhouette_m.png",
}

_GENDER_TAB_MAP: dict[str, str] = {
    "female": "feminine",
    "male": "masculine",
    "other": "feminine",
}


def get_default_tab(gender: str) -> str:
    return _GENDER_TAB_MAP.get(gender, "masculine")
