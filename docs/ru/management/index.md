# Management

Раздел описывает эксплуатационный слой проекта: деплой, CI/CD, образы, ручные gates, rollback и границы перезапуска сервисов.

Management layer не является runtime-модулем и не должен протекать в gameplay code. Runtime-код живет в `src/`, а operational wiring живет в `deploy/`, GitHub Actions и runbook-документации.

## Документы

- [Деплой](deployment.md) — текущая схема CI/CD, production compose files и выпуск образов.
- [Контракт деплоя](deployment-contract.md) — ownership matrix, границы перезапуска, rollback и правила взаимодействия слоев.
