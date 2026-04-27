from typing import Any

from loguru import logger
from simpleeval import simple_eval

from src.backend.services.calculators.data.stats_formulas import MODIFIER_RULES


class StatsWaterfallCalculator:
    """
    Универсальный калькулятор характеристик (Waterfall Calculation).

    Логика расчета:
    1. Атрибуты (Stats): Складываются все источники (Base + Source + Temp).
    2. База Модификаторов (Base Modifiers):
       - Конвертация Атрибутов (Bridge) -> дает Flat (+).
    3. Финальные Модификаторы:
       - База (Derived) + Source (Items) + Temp (Buffs).
       - Формула: (Sum(Flats)) * Product(Multipliers).
    """

    # Кеш для трансформированных правил (Source -> [Target, Factor])
    _SOURCE_TO_TARGET_RULES: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def _get_rules(cls) -> dict[str, list[dict[str, Any]]]:
        """
        Ленивая инициализация и трансформация правил из MODIFIER_RULES.
        """
        if not cls._SOURCE_TO_TARGET_RULES:
            transformed: dict[str, list[dict[str, Any]]] = {}
            for target_mod, sources in MODIFIER_RULES.items():
                for source_attr, factor in sources.items():
                    if source_attr not in transformed:
                        transformed[source_attr] = []
                    transformed[source_attr].append({"target": target_mod, "factor": factor})
            cls._SOURCE_TO_TARGET_RULES = transformed
        return cls._SOURCE_TO_TARGET_RULES

    @staticmethod
    def calculate_waterfall(raw_data: dict[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
        """
        Полный цикл расчета характеристик.

        Args:
            raw_data: Структура v:raw (attributes, modifiers).
                      Каждый стат имеет структуру: {"base": X, "source": {...}, "temp": {...}}

        Returns:
            Tuple: (v:cache (values), v:explanation (formulas))
        """
        # 1. Расчет Атрибутов (Primary Stats)
        raw_attributes = raw_data.get("attributes", {})
        final_attributes, attr_explanations = StatsWaterfallCalculator._calculate_attributes(raw_attributes)

        # 2. Конвертация (Derivation Bridge)
        derived_bonuses = StatsWaterfallCalculator._derive_bonuses(final_attributes)

        # 3. Расчет Модификаторов (Secondary Stats)
        raw_modifiers = raw_data.get("modifiers", {})
        final_modifiers, mod_explanations = StatsWaterfallCalculator._calculate_modifiers(
            raw_modifiers, derived_bonuses
        )

        # Объединяем все в плоские словари
        cache_result = {**final_attributes, **final_modifiers}
        explanation_result = {**attr_explanations, **mod_explanations}

        return cache_result, explanation_result

    @staticmethod
    def evaluate_sources(sources: dict[str, Any] | list[str] | None, base_value: float = 0.0) -> tuple[float, str]:
        """
        Публичный метод для расчета значения из набора источников.
        Может использоваться для HP, Energy, XP и любых других ресурсов.

        Args:
            sources: Словарь {source_id: value_str} или список строк ["+10", "*1.1"].
            base_value: Базовое значение (если есть).

        Returns:
            (final_value, formula_string)
        """
        if not sources:
            return base_value, str(base_value)

        # Нормализация входных данных в список строк
        commands = []
        if isinstance(sources, dict):
            commands = [str(v) for v in sources.values()]
        elif isinstance(sources, list):
            commands = [str(v) for v in sources]

        return StatsWaterfallCalculator._evaluate_pipeline(commands, base_value)

    @staticmethod
    def _calculate_attributes(raw_attributes: dict[str, Any]) -> tuple[dict[str, float], dict[str, str]]:
        """
        Фаза 1: Расчет атрибутов.
        """
        results = {}
        explanations = {}

        for attr_name, data in raw_attributes.items():
            # Base
            base_raw = data.get("base", 0.0)
            base = float(base_raw) if base_raw else 0.0

            # Собираем все источники (Source + Temp)
            sources_list = []

            # Source (Items, Skills)
            src_dict = data.get("source", {})
            if src_dict:
                sources_list.extend(src_dict.values())

            # Temp (Buffs)
            temp_dict = data.get("temp", {})
            if temp_dict:
                sources_list.extend(temp_dict.values())

            # Расчет
            val, expr = StatsWaterfallCalculator.evaluate_sources(sources_list, base)

            results[attr_name] = val
            explanations[attr_name] = expr

        return results, explanations

    @staticmethod
    def _derive_bonuses(attributes: dict[str, float]) -> dict[str, list[str]]:
        """
        Фаза 2: Генерация бонусов от атрибутов (Bridge).
        """
        derived: dict[str, list[str]] = {}
        rules_map = StatsWaterfallCalculator._get_rules()

        for attr_name, attr_value in attributes.items():
            rules = rules_map.get(attr_name, [])
            for rule in rules:
                target = rule["target"]
                factor = rule["factor"]

                bonus_val = attr_value * factor

                if bonus_val != 0:
                    if target not in derived:
                        derived[target] = []
                    # Записываем как Flat Add
                    derived[target].append(f"+{bonus_val}")

        return derived

    @staticmethod
    def _calculate_modifiers(
        raw_modifiers: dict[str, Any], derived_bonuses: dict[str, list[str]]
    ) -> tuple[dict[str, float], dict[str, str]]:
        """
        Фаза 3: Расчет модификаторов.
        """
        results_values = {}
        results_explanations = {}

        # Собираем все ключи
        all_keys = set(raw_modifiers.keys()) | set(derived_bonuses.keys())

        for mod_name in all_keys:
            sources_list = []

            # 1. Derived (База от статов)
            if mod_name in derived_bonuses:
                sources_list.extend(derived_bonuses[mod_name])

            # 2. Raw Data (Source + Temp)
            if mod_name in raw_modifiers:
                data = raw_modifiers[mod_name]

                # Base (обычно 0, но может быть)
                base_raw = data.get("base", 0.0)
                # Если база есть в raw, добавляем её как +X (или используем как base_value в evaluate)
                # Но так как у нас уже есть Derived, лучше все считать как список команд.
                if base_raw:
                    sources_list.append(f"+{base_raw}")

                # Source
                src_dict = data.get("source", {})
                if src_dict:
                    sources_list.extend(src_dict.values())

                # Temp
                temp_dict = data.get("temp", {})
                if temp_dict:
                    sources_list.extend(temp_dict.values())

            # 3. Расчет
            # base_value=0.0, так как база уже внутри sources_list (Derived или Base из raw)
            val, expr = StatsWaterfallCalculator.evaluate_sources(sources_list, 0.0)

            results_values[mod_name] = val
            results_explanations[mod_name] = expr

        return results_values, results_explanations

    @staticmethod
    def _evaluate_pipeline(commands: list[str], base_value: float = 0.0) -> tuple[float, str]:
        """
        Вычисляет значение, собирая строковую формулу и выполняя её через simpleeval.
        """
        flats = [str(base_value)] if base_value != 0 else []
        mults: list[str] = []

        for cmd in commands:
            if not cmd:
                continue

            # Очистка от пробелов
            cmd = str(cmd).strip()
            if not cmd:
                continue

            operator = cmd[0]
            val_str = cmd[1:]

            if operator == "=":
                # Override полностью сбрасывает строку базы
                flats = [val_str]
                mults = []  # И сбрасывает мультипликаторы (обычно override это финал)
            elif operator == "+":
                flats.append(val_str)
            elif operator == "-":
                flats.append(f"-{val_str}")
            elif operator == "*":
                mults.append(val_str)
            # Fallback для чисел без оператора (считаем как +)
            elif cmd.replace(".", "", 1).isdigit() or (cmd.startswith("-") and cmd[1:].replace(".", "", 1).isdigit()):
                # Если число отрицательное без оператора (напр "-0.1"), считаем как flat
                flats.append(cmd)
            else:
                # Если просто число "10" -> "+10"
                flats.append(cmd)

        # 1. Сборка СТРОКИ (Explanation)
        # Собираем базу в скобки и умножаем на всё остальное
        if not flats:
            base_expr = "0"
        elif len(flats) == 1:
            base_expr = flats[0]
        else:
            base_expr = f"({' + '.join(flats)})"

        mult_expr = f" * {' * '.join(mults)}" if mults else ""
        full_expression = f"{base_expr}{mult_expr}"

        # 2. Вычисление ЧИСЛА (Cache) через SimpleEval
        try:
            raw_result = simple_eval(full_expression)
            final_value = round(float(raw_result), 4)
        except Exception as e:  # noqa: BLE001
            logger.error(f"StatsWaterfallCalculator | Eval error: {e} expr='{full_expression}'")
            final_value = 0.0

        return final_value, full_expression
