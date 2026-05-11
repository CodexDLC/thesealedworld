# DTO

Внутренние DTO арены. Публичный контракт фронтенда (`ArenaUIPayloadDTO`, `ArenaScreenEnum`) живёт в `src/shared/schemas/arena.py`.

## ArenaRuntimeSessionDTO

Redis-сессия игрока внутри арены. Хранит текущий экран, режим, ссылки на активный матч и combat_id.

```
arena:runtime:{uuid}  →  ArenaRuntimeSessionDTO
```

::: backend.features.arena.dto.session.ArenaRuntimeSessionDTO
    options:
      show_source: false
      show_root_heading: false

## ArenaQueueRequestDTO

Заявка игрока в очередь матчмейкинга. Содержит gear score (`gs`) для балансировки, лимит ожидания и ссылку на commitment.

::: backend.features.arena.dto.session.ArenaQueueRequestDTO
    options:
      show_source: false
      show_root_heading: false

## ArenaCombatRequestDTO

Созданный матч. Живёт в Redis пока combat не стартовал. Статусы: `pending → ready → failed`.

`commitments` — словарь `{char_id: commitment_id}` для всех участников матча.
`participants` — команды: `{"team_1": [char_id], "team_2": [opponent_id]}`. Для shadow `team_2=[]`.

::: backend.features.arena.dto.session.ArenaCombatRequestDTO
    options:
      show_source: false
      show_root_heading: false
