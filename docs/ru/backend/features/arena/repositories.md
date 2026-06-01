# Repositories

## SQL repositories

Arena persistence находится в инфраструктурном слое `backend.infrastructure.arena.repositories`.
Feature-слой arena получает эти репозитории через dependencies и передает их в сервисы рейтинга и сезонов.

::: backend.infrastructure.arena.repositories.league_repository.ArenaLeagueRepository
    options:
      show_source: false
      show_root_heading: false

::: backend.infrastructure.arena.repositories.match_repository.ArenaMatchRepository
    options:
      show_source: false
      show_root_heading: false

::: backend.infrastructure.arena.repositories.rating_repository.ArenaRatingRepository
    options:
      show_source: false
      show_root_heading: false

::: backend.infrastructure.arena.repositories.season_repository.ArenaSeasonRepository
    options:
      show_source: false
      show_root_heading: false
