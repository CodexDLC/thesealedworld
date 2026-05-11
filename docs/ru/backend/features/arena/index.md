# Arena

`src/backend/features/arena/` — матчмейкинг, рейтинговые бои и тренировки.

## Типы боёв

| Тип | Описание |
|-----|---------|
| `pvp` | Два реальных игрока найденных через очередь |
| `shadow` | Игрок против копии своего персонажа |

## Экраны (ArenaScreenEnum)

```mermaid
stateDiagram-v2
    [*] --> MAIN_MENU: enter_arena
    MAIN_MENU --> MODE_MENU: выбор режима
    MODE_MENU --> SEARCHING: join_queue (pvp)
    MODE_MENU --> COMBAT_PENDING: start_shadow
    SEARCHING --> COMBAT_PENDING: opponent found
    SEARCHING --> SHADOW_OFFER: таймаут → предложить shadow
    SHADOW_OFFER --> COMBAT_PENDING: accept_shadow
    SHADOW_OFFER --> SEARCHING: continue_search
    COMBAT_PENDING --> [*]: enter_combat → Combat
    COMBAT_PENDING --> COMBAT_FAILED: таймаут / ошибка
    COMBAT_FAILED --> MAIN_MENU
```

## Флоу матчмейкинга (pvp)

```mermaid
sequenceDiagram
    participant P as Player
    participant AS as ArenaService
    participant SI as SessionIntegration
    participant IN as ArenaSystemIntegrator

    P->>AS: join_queue(char_id, mode)
    AS->>IN: create_combat_commitment(request_id, char_id)
    Note over IN: Redis-резервация боевого слота
    AS->>SI: join_queue(char_id, gs, wait_limit_sec)
    AS-->>P: SEARCHING screen

    loop poll check_match
        P->>AS: check_match(char_id, mode)
        AS->>SI: acquire_match_lock(char_id)
        AS->>SI: find_opponent(char_id, mode)
        alt opponent found
            AS->>SI: create_match → request_combat_session
            AS-->>P: COMBAT_PENDING screen
        else wait_limit exceeded
            AS->>SI: leave_queue
            AS-->>P: MODE_MENU (timeout)
        end
    end

    P->>AS: check_combat_ready(char_id, confirm=True)
    AS->>IN: enter_combat(char_id, combat_id)
    AS-->>P: → Combat domain
```

## Структура модуля

| Слой | Назначение |
|------|-----------|
| `services/` | Бизнес-логика: матчмейкинг, рейтинг, сезоны, дуэли |
| `integrations/` | Связь с character, combat, stream |
| `runtime/` | ELO-калькулятор, лиги |
| `repositories/` | Redis-хранилище сессий очереди и матчей |
| `gateway/` | WebSocket gateway |
| `dto/` | Внутренние DTO (сессии, матчи, очередь) |
