# AI

Боевой ИИ монстров. Runtime-инференс читает обученную политику и выдаёт
payload-ы намерений через обычный путь `CombatTurnManager`. Обучение —
**только оффлайн**, отдельным скриптом, на синтетических сценариях.

> Дизайнерский контекст и тактические оси: см.
> [`docs/game-design/designer/combat/07_ai_brain.md`](../../../../game-design/designer/combat/07_ai_brain.md).

## Где код

```
src/backend/features/combat/runtime/ai/
├── __init__.py
├── observation.py       # фичи из ActorSnapshot + BattleContext
├── action_space.py      # перечисление легальных действий per target
├── policy.py            # Pydantic-модель Policy
├── scorer.py            # детерминированная функция скоринга
├── brain.py             # MonsterCombatBrain.decide_turn
├── policy_store.py      # загрузка политики с fallback
├── policies/
│   └── default_policy.json  # встроенный baseline
└── training/
    ├── scenarios.py     # синтетические тренировочные сценарии
    ├── environment.py   # ScoringEnvironment (reward функция)
    ├── evolution.py     # эволюционный поиск весов
    └── train_policy.py  # CLI + функция train(args)
```

Интеграция:

- [`src/backend/features/combat/runtime/processors/ai_processor.py`](../../../../../../src/backend/features/combat/runtime/processors/ai_processor.py)
  — `decide_turn` + `decide_exchange` (обёртка).
- [`src/backend/features/combat/workers/tasks/ai_turn_task.py`](../../../../../../src/backend/features/combat/workers/tasks/ai_turn_task.py)
  — вызывает `decide_turn` один раз со всем `BattleContext`.

## Runtime-инференс

### Точка входа

```python
class MonsterCombatBrain:
    def decide_turn(
        bot: ActorSnapshot,
        battle: BattleContext | None,
        candidate_targets: list[ActorSnapshot],
    ) -> list[dict[str, Any]]: ...
```

Возвращает по одному payload на цель в форме, которую принимает
`CombatTurnManager.register_moves_batch`:

```python
{"action": "attack", "target_id": <ActorId>, "feint_id": <str | absent>}
```

### Поток

1. **`StatsEngine.ensure_stats`** для бота и всех целей — тот же контракт,
   что у резолвера. Это единственный side-effect: материализуется
   `actor.stats.mods`. Никакие токены/стамина/hand не меняются.
2. **`extract_self(bot, alive_enemy_count)`** → `SelfObservation`.
3. **`extract_target(target)`** → `TargetObservation` для каждой цели.
4. **`build_legal_actions_for_target(bot, target)`** — для каждой цели:
   - всегда: базовая атака,
   - для каждого финта в `bot.meta.feints.hand`, чья стамина-стоимость
     (`FeintService.activation_stamina_cost`) укладывается в текущую
     стамину — `attack + feint`.
5. **`PolicyScorer.score`** — детерминированная линейная комбинация
   фич × весов политики с опциональным seeded шумом.
6. **Жадная аллокация** — финт идёт на цель с максимальным
   `delta = score(best_feint) - score(basic_attack)` при условии:
   стамины хватает на этот и предыдущие финты, и сам финт ещё не
   использован против другой цели в этом ходе.
7. На выходе — `list[payload]` ровно длины `len(candidate_targets)`.

### Observation: какие фичи берутся

**`SelfObservation`** ([observation.py](../../../../../../src/backend/features/combat/runtime/ai/observation.py)):

| Поле | Источник |
|---|---|
| `hp_pct` | `meta.hp / meta.max_hp` |
| `stamina_pct` | `meta.stamina / meta.max_stamina` |
| `en_pct` | `meta.en / meta.max_en` |
| `tokens` | `meta.tokens` копия |
| `alive_enemy_count` | `battle.get_enemies(bot.id)` или фоллбек |
| `low_hp` | `hp_pct <= 0.30` |
| `low_stamina` | `stamina_pct <= 0.30` |

**`TargetObservation`**:

| Поле | Источник |
|---|---|
| `hp_pct` | `meta.hp / meta.max_hp` |
| `armor` | `stats.mods.armor` |
| `physical_resistance` | `stats.mods.physical_resistance` |
| `evasion` | `stats.mods.evasion` |
| `parry` | `stats.mods.parry` |
| `block` | `stats.mods.block` |
| `counter_attack_chance` | `stats.mods.counter_attack_chance` |
| `has_bleed` | в `statuses.effects` найдено `"bleed"` |
| `has_control` | `effect.control` не None или ключевое слово в `effect_id` |
| `finishable` | `hp_pct <= 0.25` |

Резолверная математика не дублируется. Если нужен новый сигнал — добавить
поле, читать `actor.stats.mods.<key>`, и НИЧЕГО не считать в observation.

### Action space: какие теги собираются

После переделки каталога (`feat: overhaul combat catalog and stat assembly`)
дизайнеры стали проставлять `applicability_tags` на каждом финте явно —
это первичный источник тегов для AI. Substring-маппинг по
modifier/pipeline/effect id-шникам остался как fallback для записей без
явных тегов.

| Источник | Маппинг | Тег |
|---|---|---|
| `cost.tactics["hit"\|"crit"]` | token → тег | `damage_tag` |
| `cost.tactics["tempo"]` | token → тег | `preparation` |
| `cost.tactics["block"]` | token → тег | `anti_block` |
| `cost.tactics["parry"]` | token → тег | `anti_parry` |
| `cost.tactics["dodge"]` | token → тег | `anti_evasion` |
| `cost.tactics["counter"]` | token → тег | `counter_resource` |
| `cost.tactics["blood"]` | token → тег | `blood_resource` |
| `cost.tactics["gift"]` | token → тег | `gift_resource` |
| `applicability_tags` | как есть | произвольные (например `anti_parry`, `heal`, `preparation`, `counter`, `debuff`, `defense`, `bleed`, `control`, `shield_bash`, `concussion`, ...) |
| `purchase_group` | flat-tag | `group_basic` / `group_tactical` / `group_weapon` |
| `target_count > 1` | флаг | `multi_target` |
| `preparation_effects[*]` с `target_actor=source` | флаг | `self_buff` |
| `preparation_effects[*].params` содержит `heal_*` | флаг | `heal` |
| `effects[*]` с `target_actor=target` | флаг | `debuff` |
| `shield_guard_damage_ratio > 0` | флаг | `shield_damage`, `damage_tag` |
| `modifier_applications[*].modifier_id` | substring match (`block_mult` → `anti_block`, `parry_mult` → `anti_parry`, и т. д.) | fallback |
| `pipeline_mutations[*].mutation_id` | то же substring match | fallback |
| `effects[*].id` | substring match (`stun`/`control`/`root`/`blind`/`concussion` → `control`, `bleed`/`dot_bleed` → `bleed`, `heal` → `heal`) | fallback |
| `triggers[*]` | substring match | fallback |

Полная таблица substring → тег — в
[`action_space.py:_ID_KEYWORD_TAGS`](../../../../../../src/backend/features/combat/runtime/ai/action_space.py).

Все 9 токенов из
[`game_catalog/combat/resources/tokens.py`](../../../../../../src/backend/features/game_catalog/combat/resources/tokens.py)
покрыты: `tempo`, `hit`, `crit`, `dodge`, `parry`, `block`, `counter`,
`blood`, `gift`.

### Scorer: формула

```python
score = Σ weight[feature] × feature_value
```

Основные пары `feature × weight` (полный список —
[`scorer.py`](../../../../../../src/backend/features/combat/runtime/ai/scorer.py)):

| Условие/тег действия | Вес × множитель |
|---|---|
| цель — всегда | `target_low_hp × (1 - hp_pct)` + `target_high_hp × hp_pct` |
| `target.finishable` | `+ finishable` (константа) |
| `target.has_control` | `+ control × 0.4` |
| `target.has_bleed` | `+ bleed × 0.4` |
| любое атакующее действие | `+ expected_damage × hp_pct × (1 - phys_resist)` |
| тег `anti_block` | `+ anti_block × target.block` |
| тег `anti_parry` | `+ anti_parry × target.parry` |
| тег `anti_evasion` | `+ anti_evasion × target.evasion` |
| тег `armor_bypass` | `+ armor_bypass × min(1, armor/50)` |
| тег `control` | `+ control` |
| тег `bleed` | `+ bleed` |
| тег `debuff` | `+ debuff` |
| тег `multi_target` | `+ multi_target × max(0, enemies − 1)` |
| тег `preparation` | `+ preparation` |
| тег `counter` | `+ counter × (0.5 + target.counter_attack_chance)` |
| тег `damage_tag` | `+ damage_tag` |
| тег `heal` | `+ heal × max(0, 0.7 − self.hp_pct)` |
| тег `self_buff` | `+ self_buff` |
| тег `defense` | `+ defense × (1 − self.hp_pct)` |
| тег `group_basic` / `group_tactical` / `group_weapon` | `+ group_*` (выбор cost-vs-school) |
| бот имеет `blood` токены | `+ blood_resource × min(3, blood)` |
| бот имеет `counter` токены и в action есть тег `counter` | `+ counter_resource` |
| бот имеет `gift` токены | `+ gift_resource` |
| токены | `+ token_cost × Σ cost.values()` |
| стамина | `+ stamina_cost × action.stamina_cost` |
| `low_hp` бот + финт | `+ self_low_hp_resource_save` (обычно отрицательный) |
| `low_stamina` бот + финт | `+ self_low_stamina_save` |
| опциональный шум | `+ N(0, randomness)` зажат на ±3σ |

Веса — все в `policy.weights`. Отсутствующий ключ — нулевой вес.

### Жадная аллокация ресурсов

Финт в руке можно использовать **один раз за ход**. Стамина делится между
всеми intent-ами одного бота. Токены **уже заморожены** при `refill_hand`
(после `consume_feint` идёт `refund_cost`).

Алгоритм ([`brain.MonsterCombatBrain._greedy_allocate`](../../../../../../src/backend/features/combat/runtime/ai/brain.py)):

1. Для каждой цели взять лучшую базовую атаку и все её feint-кандидаты.
2. Для каждого feint-кандидата вычислить `delta = score(feint) - score(basic)`.
3. Отсортировать кортежи `(target_idx, action, score, delta)` по `delta DESC`,
   `score DESC` (детерминированно).
4. Идти по списку: если цель ещё не получила финт, финт не использован
   против другой цели, стамины хватает — назначить. Иначе пропустить.
5. Незаполненным целям отдать `basic_attack`.

Тонкая совместная оптимизация (полный комбинаторный поиск) — deferred.

## Хранение и загрузка политики

`PolicyStore.load(path=None) -> Policy` резолвит источник в порядке:

1. Аргумент `path` (если передан явно).
2. ENV `COMBAT_AI_POLICY_PATH`.
3. Встроенный
   [`src/backend/features/combat/runtime/ai/policies/default_policy.json`](../../../../../../src/backend/features/combat/runtime/ai/policies/default_policy.json).

При битом внешнем артефакте — лог `CombatAiPolicyLoadFailed` и fallback
на встроенный default. LRU-кэш по `(absolute_path, mtime_ns)` — JSON
парсится один раз за процесс воркера.

### Формат

```json
{
  "policy_id": "default_v1",
  "version": 2,
  "weights": {
    "finishable": 3.0,
    "anti_block": 2.4,
    "anti_parry": 2.2,
    "anti_evasion": 2.0,
    "heal": 3.5,
    "defense": 1.5,
    "token_cost": -0.12,
    "stamina_cost": -0.015,
    "...": "..."
  },
  "metadata": {
    "algorithm": "manual_seed",
    "created_by": "combat-ai-mvp"
  }
}
```

Полный список ключей — в
[`policy.DEFAULT_WEIGHT_KEYS`](../../../../../../src/backend/features/combat/runtime/ai/policy.py).

Контракт — [`Policy`](../../../../../../src/backend/features/combat/runtime/ai/policy.py).
Ключи весов — открытая мапа: добавление нового тега в action space →
добавление веса в `default_policy.json` → переобучение, без правок API.

## Offline-обучение

### CLI

```powershell
.\.venv\Scripts\python.exe -m src.backend.features.combat.runtime.ai.training.train_policy `
    --generations 50 --population 30 --seed 1 `
    --output-dir C:\tmp\combat-ai-runs\v2 `
    [--start-from C:\tmp\combat-ai-runs\v1\best_policy.json] `
    [--duration-seconds 60] `
    [--sigma 0.25]
```

Без `--output-dir` пишется в `C:\tmp\combat-ai-runs\<timestamp>\`. В
`src/` тренер не пишет ничего — только встроенный `default_policy.json`
лежит под source control.

### Что внутри

| Шаг | Где |
|---|---|
| Набор сценариев `(bot, targets, expected_tags)` | [`scenarios.default_scenario_set`](../../../../../../src/backend/features/combat/runtime/ai/training/scenarios.py) |
| Reward-функция | [`environment.ScoringEnvironment.evaluate`](../../../../../../src/backend/features/combat/runtime/ai/training/environment.py) |
| Эволюционный цикл (gaussian mutation + турнирная селекция + elitism + sigma decay) | [`evolution.evolve`](../../../../../../src/backend/features/combat/runtime/ai/training/evolution.py) |

Reward (детерминированный):

- `+1.0` за совпадение тегов выбранного действия с ожидаемыми.
- `−0.4` за выбор финта против цели, у которой ожидался `frozenset()`.
- `−0.3` за финт там, где ожидалась чистая атака; `+0.6` за чистую атаку там же.
- `−0.1 × cost_tokens` за необоснованную трату токенов.
- `+0.1` за полноту плана (есть payload на каждую цель).

### Артефакты

| Файл | Содержание |
|---|---|
| `best_policy.json` | Лучшая политика прогона. Готова к деплою. |
| `leaderboard.json` | Все политики последнего поколения с их reward и весами. |
| `metrics.jsonl` | По строке на поколение: `{generation, best_reward, mean_reward, elapsed_seconds}`. |

### Программный API

Тренер импортируем как функция — используется и в smoke-тесте, и
в потенциальных pipeline-обёртках:

```python
from src.backend.features.combat.runtime.ai.training import TrainArgs, train

run = train(TrainArgs(generations=20, population=30, seed=42, output_dir=Path("...")))
print(run.best_policy.metadata.get("final_reward"))
```

### MVP scope: чего ЭТОТ тренер не делает

- **Не запускает `CombatPipeline`.** Reward — tag-match по ручным сценариям,
  не «выиграл/проиграл бой». Следующая итерация — заменить
  `ScoringEnvironment` на headless-прогон двух policy-команд.
- **Не учится в реальном бою.** Combat-runtime read-only по отношению
  к весам политики. Online-learning **не входит** в архитектуру MVP.

### Baseline: какие numbers нужно ожидать

На текущем наборе из 6 сценариев reward-потолок ≈ 6.4.

| Политика | Total reward | Поведение |
|---|---|---|
| `zero` (все веса 0) | 0.8 | Только базовая атака — теряет три anti-X сценария и heal-сценарий |
| `default_v2` (встроенный) | 6.4 | Выигрывает все 6 сценариев |
| `trained` (50–80 поколений, pop 30–40) | 6.4 на training reward; ~5.0–6.4 на eval | Сходится к политике того же качества, что и default_v2; разброс — артефакт `randomness` шума при разных RNG seed |

Это значит: **встроенный baseline уже близок к локальному оптимуму** на
этом узком наборе сценариев. Главный потолок улучшения — не алгоритм
поиска, а сам набор сценариев. Чтобы получить выше — нужен реальный
`CombatPipeline` self-play.

## Деплой политики

```powershell
# 1. Обучить
.\.venv\Scripts\python.exe -m src.backend.features.combat.runtime.ai.training.train_policy `
    --generations 50 --population 30 --seed 1 --output-dir C:\tmp\combat-ai-runs\v2

# 2. Подложить как override (per-worker-process env)
$env:COMBAT_AI_POLICY_PATH = "C:\tmp\combat-ai-runs\v2\best_policy.json"
# перезапустить ARQ-воркер

# 3. Откат — снять env-переменную и перезапустить.
# Встроенный default_policy.json продолжит работать.
```

Если внешний JSON битый/отсутствует — runtime автоматически падает на
default, бой не ломается.

## Расширения (точки швов)

| Цель | Куда править | Что НЕ трогать |
|---|---|---|
| Действия `instant` / abilities / heals | `action_space.build_legal_actions_for_target` (ветка по `bot.loadout.known_abilities`); теги в `_ID_KEYWORD_TAGS`; веса в `default_policy.json` | `MonsterCombatBrain`, `PolicyScorer` |
| Per-archetype политики | `PolicyStore.load_for(profile: MonsterAIProfileDTO)` с маршрутизацией | API `decide_turn` |
| БД-хранилище | Подкласс `PolicyStore` | Brain |
| Реальный self-play | Заменить `ScoringEnvironment.evaluate` на headless `CombatPipeline` | `scorer.py`, `brain.py` |
| Player telemetry → сценарии | `training/scenarios.py` | Runtime |
| Intelligence tier / noise | Опц. аргументы в `observation.extract_self/target` | Контракты DTO |

## Верификация

```powershell
# Точечно по AI-модулю
.\.venv\Scripts\python.exe -m pytest `
    tests\backend\features\combat\test_ai_runtime.py `
    tests\backend\features\combat\test_ai_training.py --no-cov -v

# Регрессия комбата + монстров
.\.venv\Scripts\python.exe -m pytest tests\backend\features\combat tests\backend\features\monsters\runtime --no-cov

# End-to-end smoke тренировки
.\.venv\Scripts\python.exe -m src.backend.features.combat.runtime.ai.training.train_policy `
    --generations 2 --population 4 --seed 0 --output-dir C:\tmp\combat-ai-runs\smoke

# Полный quality gate
uv run python tools/dev/check.py
```
