# Runtime

## Лиги

Шесть лиг по рейтингу. По умолчанию `DEFAULT_RATING = 1000` → Rookie.

| Tier | Code | Name | Рейтинг |
|------|------|------|---------|
| 1 | rookie | Rookie | 0 – 1199 |
| 2 | fighter | Fighter | 1200 – 1399 |
| 3 | challenger | Challenger | 1400 – 1599 |
| 4 | veteran | Veteran | 1600 – 1799 |
| 5 | elite | Elite | 1800 – 2099 |
| 6 | legend | Legend | 2100+ |

`LeagueResolver.resolve(rating)` — возвращает `LeagueRule` для заданного рейтинга.
`LeagueResolver.floor_for_tier(tier)` — минимальный рейтинг для tier (используется при деградации).

## ELO

Параметры расчёта:

| Константа | Значение | Назначение |
|-----------|---------|-----------|
| `K_BASE` | 32 | Базовый K-фактор |
| `K_PLACEMENT` | 48 | K-фактор на placement матчах |
| `DEFAULT_RATING` | 1000 | Начальный рейтинг |
| `GS_MOD_MAX` | 0.20 | Максимальная модификация за разницу gear score |
| `GS_DELTA_NORM` | 200 | Нормировочный делитель для GS-разницы |
| `DRAW_SCORE` | 0.5 | Счёт ничьей |

::: backend.features.arena.runtime.league_resolver.LeagueResolver
    options:
      show_source: false
      show_root_heading: false
