from __future__ import annotations

from hashlib import blake2b

DEFAULT_WEAPON_ATTACK_FORM = {
    "weapon_attack_button": "Атаковать",
    "weapon_attack_form": "выверенную атаку",
    "weapon_attack_line": "линию атаки",
}

WEAPON_ATTACK_FORMS: dict[str, tuple[dict[str, str], ...]] = {
    "skill_swords": (
        {
            "weapon_attack_button": "Рубануть",
            "weapon_attack_form": "рубящий удар клинком",
            "weapon_attack_line": "линию клинка",
        },
        {
            "weapon_attack_button": "Полоснуть",
            "weapon_attack_form": "режущий проход мечом",
            "weapon_attack_line": "режущую линию",
        },
        {
            "weapon_attack_button": "Ударить клинком",
            "weapon_attack_form": "короткий удар мечом",
            "weapon_attack_line": "линию удара",
        },
    ),
    "skill_fencing": (
        {
            "weapon_attack_button": "Уколоть",
            "weapon_attack_form": "точный колющий выпад",
            "weapon_attack_line": "линию укола",
        },
        {
            "weapon_attack_button": "Сделать выпад",
            "weapon_attack_form": "быстрый выпад клинком",
            "weapon_attack_line": "фехтовальную линию",
        },
        {
            "weapon_attack_button": "Подрезать",
            "weapon_attack_form": "короткий режущий проход",
            "weapon_attack_line": "нижнюю линию",
        },
    ),
    "skill_polearms": (
        {
            "weapon_attack_button": "Ударить древком",
            "weapon_attack_form": "длинный удар древком",
            "weapon_attack_line": "дальнюю линию",
        },
        {
            "weapon_attack_button": "Сделать выпад",
            "weapon_attack_form": "длинный колющий выпад",
            "weapon_attack_line": "линию острия",
        },
        {
            "weapon_attack_button": "Зацепить",
            "weapon_attack_form": "цепляющий удар древком",
            "weapon_attack_line": "линию опоры",
        },
    ),
    "skill_macing": (
        {
            "weapon_attack_button": "Ударить",
            "weapon_attack_form": "тяжелый дробящий удар",
            "weapon_attack_line": "траекторию удара",
        },
        {
            "weapon_attack_button": "Продавить",
            "weapon_attack_form": "давящий удар по защите",
            "weapon_attack_line": "линию блока",
        },
        {
            "weapon_attack_button": "Размахнуться",
            "weapon_attack_form": "широкий силовой замах",
            "weapon_attack_line": "силовую линию",
        },
    ),
    "skill_archery": (
        {
            "weapon_attack_button": "Выстрелить",
            "weapon_attack_form": "выверенный выстрел",
            "weapon_attack_line": "линию выстрела",
        },
        {
            "weapon_attack_button": "Прицелиться",
            "weapon_attack_form": "прицельный выстрел",
            "weapon_attack_line": "линию огня",
        },
        {
            "weapon_attack_button": "Пустить стрелу",
            "weapon_attack_form": "быстрый выстрел",
            "weapon_attack_line": "траекторию стрелы",
        },
    ),
    "skill_unarmed": (
        {
            "weapon_attack_button": "Ударить",
            "weapon_attack_form": "короткий прямой удар",
            "weapon_attack_line": "линию корпуса",
        },
        {
            "weapon_attack_button": "Толкнуть",
            "weapon_attack_form": "давящее движение корпусом",
            "weapon_attack_line": "линию равновесия",
        },
        {
            "weapon_attack_button": "Войти ближе",
            "weapon_attack_form": "ближний удар рукой",
            "weapon_attack_line": "короткую линию",
        },
    ),
}


def resolve_weapon_attack_form(skill_key: str | None, *, seed: str = "") -> dict[str, str]:
    forms = WEAPON_ATTACK_FORMS.get(str(skill_key or ""), ())
    if not forms:
        return dict(DEFAULT_WEAPON_ATTACK_FORM)
    if len(forms) == 1:
        return dict(forms[0])
    digest = blake2b(str(seed or skill_key or "").encode("utf-8"), digest_size=4).digest()
    index = int.from_bytes(digest, "big") % len(forms)
    return dict(forms[index])
