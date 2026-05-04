# backend/domains/user_features/scenario/engine/evaluator.py
import random
import re
import time
from typing import Any

from loguru import logger as log
from simpleeval import SimpleEval


class ScenarioEvaluator:
    """
    Математический движок.
    Вычисляет условия и применяет изменения к контексту.
    Поддерживает арифметику, кубики (1d6) и операции со списками (push/pop).
    """

    def __init__(self, seed: int | float | str | None = None):
        self._rng = random.Random(seed)
        self.s_eval = SimpleEval()

        # Регистрация безопасных функций для использования в формулах
        self.s_eval.functions = {
            "rand": self._rng.randint,
            "min": min,
            "max": max,
            "abs": abs,
            "len": len,
            "has_item": self._has_item_func,
            "has_skill": self._has_skill_func,
        }

        # Регулярное выражение для поиска кубиков (напр., 1d6, 2d10)
        self.dice_pattern = re.compile(r"(\d+)d(\d+)")

    def set_seed(self, seed: int | float | str | None) -> None:
        """Устанавливает зерно для генератора случайных чисел."""
        if seed is None:
            seed = time.time_ns()
        self._rng.seed(seed)

    def _has_item_func(self, item_id: str) -> bool:
        """Проверка наличия предмета в loot_queue."""
        loot = self.s_eval.names.get("loot_queue", [])
        return item_id in loot

    def _has_skill_func(self, skill_id: str) -> bool:
        """Проверка наличия навыка в skills_queue."""
        skills = self.s_eval.names.get("skills_queue", [])
        return skill_id in skills

    def check_condition(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Проверяет логическое условие (напр., для Smart Selection).
        Пример выражения: "(w_strength + w_agility) > 20 and has_item('key')"
        """
        if not expression or not isinstance(expression, str) or expression.strip() == "":
            return True

        # Подставляем переменные из контекста сессии
        self.s_eval.names = context
        try:
            # Вычисляем логическое значение
            result = self.s_eval.eval(expression)
            return bool(result)
        except Exception as e:  # noqa: BLE001
            log.error(f"Evaluator | condition_error expr='{expression}' err='{e}'")
            return False

    def apply_math(self, math_instructions: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Применяет изменения к переменным.
        Обрабатывает как числа, так и спец-команды для списков (push/pop).
        """
        new_context = context.copy()
        # Синхронизируем имена для функций типа has_item, чтобы они видели изменения в реальном времени
        self.s_eval.names = new_context

        for var_name, instruction in math_instructions.items():
            # 1. Работа со списками (loot_queue, skills_queue)
            # Проверяем, является ли инструкция списком команд или строкой с префиксом push/pop
            if isinstance(instruction, (list, str)):
                # Превращаем одиночную строку в список для унификации
                instr_list = instruction if isinstance(instruction, list) else [instruction]

                # Если хотя бы одна команда начинается с push/pop, обрабатываем как список
                if any(str(instr).startswith(("push:", "pop:")) for instr in instr_list if isinstance(instr, str)):
                    new_context[var_name] = self._handle_list_ops(new_context.get(var_name, []), instr_list)
                    # Обновляем контекст для следующих вычислений
                    self.s_eval.names = new_context
                    continue

            # 2. Прямое присвоение не-строк (числа, булевы, словари без спец-команд)
            if not isinstance(instruction, str):
                new_context[var_name] = instruction
                self.s_eval.names = new_context
                continue

            # 3. Арифметика и формулы (только для строк)
            # Сначала обрабатываем кубики
            processed_instr = self._process_dice(instruction)

            # Получаем текущее значение
            current_val = new_context.get(var_name, 0)

            # Вычисляем новое значение
            new_context[var_name] = self._calculate_step(current_val, processed_instr, new_context)

            # Обновляем рабочие имена для следующей итерации цикла
            self.s_eval.names = new_context

        return new_context

    def _handle_list_ops(self, current_data: Any, instruction: Any) -> list:
        """Исполняет push:item или pop:item."""
        # Гарантируем, что работаем со списком
        target_list = list(current_data) if isinstance(current_data, list) else []

        ops = instruction if isinstance(instruction, list) else [instruction]

        for op in ops:
            if not isinstance(op, str):
                continue

            if op.startswith("push:"):
                val = op.split(":", 1)[1]
                target_list.append(val)
            elif op.startswith("pop:"):
                val = op.split(":", 1)[1]
                if val in target_list:
                    target_list.remove(val)

        return target_list

    def _calculate_step(self, current_val: Any, instr: str, context: dict[str, Any]) -> Any:
        """
        Разбирает арифметические префиксы (+, -, =) или выполняет сложную формулу.
        """
        instr = instr.strip()

        try:
            # Арифметический префикс: Инкремент
            if instr.startswith("+"):
                delta = self._evaluate_fragment(instr[1:], context)
                return current_val + delta

            # Арифметический префикс: Декремент
            elif instr.startswith("-"):
                delta = self._evaluate_fragment(instr[1:], context)
                return current_val - delta

            # Арифметический префикс: Прямое присваивание
            elif instr.startswith("="):
                return self._evaluate_fragment(instr[1:], context)

            # Если префиксов нет, вычисляем как полноценную формулу
            return self._evaluate_fragment(instr, context)

        except Exception as e:  # noqa: BLE001
            log.warning(f"Evaluator | math_fallback instr='{instr}' err='{e}'")
            return self._to_numeric(instr)

    def _evaluate_fragment(self, fragment: str, context: dict[str, Any]) -> Any:
        """Вычисляет фрагмент строки через SimpleEval."""
        self.s_eval.names = context
        return self.s_eval.eval(fragment)

    def _process_dice(self, text: str) -> str:
        """
        Находит все вхождения типа '1d6' и заменяет их на результат броска.
        """

        def roll_replacer(match):
            count = int(match.group(1))
            sides = int(match.group(2))
            # Защита от безумных значений
            count = min(count, 100)
            sides = min(sides, 1000)
            return str(sum(self._rng.randint(1, sides) for _ in range(count)))

        return self.dice_pattern.sub(roll_replacer, text)

    def _to_numeric(self, val: str) -> int | float | str:
        """Приводит строку к числу, если это возможно."""
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val
