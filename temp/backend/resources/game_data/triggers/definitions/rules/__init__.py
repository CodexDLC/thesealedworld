from .on_accuracy import ON_ACCURACY_RULES
from .on_block import ON_BLOCK_RULES
from .on_control import ON_CONTROL_RULES
from .on_crit import ON_CRIT_RULES
from .on_damage import ON_DAMAGE_RULES
from .on_dodge import ON_DODGE_RULES
from .on_parry import ON_PARRY_RULES
from .styles import STYLE_RULES

# Собираем все списки в один
ALL_RULES_LIST = (
    ON_ACCURACY_RULES
    + ON_CRIT_RULES
    + ON_DODGE_RULES
    + ON_PARRY_RULES
    + ON_BLOCK_RULES
    + ON_CONTROL_RULES
    + ON_DAMAGE_RULES
    + STYLE_RULES
)

# Превращаем в ПЛОСКИЙ словарь {ID: RULE}
TRIGGER_RULES_DICT = {}

for rule in ALL_RULES_LIST:
    TRIGGER_RULES_DICT[rule.id] = rule.model_dump()
