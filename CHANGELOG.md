# Changelog

All notable changes to this project will be documented in this file. This project is currently in the **Legacy Code Migration** phase, transitioning to a new platform.

## [In Progress] - Legacy Migration & Modernization

### Backend

- **Event Bus Architecture**: Integrated `codex-platform` streams with `StreamProducer`, `StreamConsumer`, and `StreamProcessor`.
- **Game Streams**: Implemented `GameStreamRouter` for decoupled event handling across features (combat, inventory, actor_state).
- **Core Features**: Ported Arena, Combat, Chat, and Exploration modules to the new backend.
- **Bio-Fantasy Content**: Integrated Gemini API for dynamic generation of narrative elements.

### Frontend

- **User Management**: Implementation of registration and authentication flows via `FrontendAuthService`.
- **Gateway Architecture**: New gateway designed for horizontal scalability and stateless operation.
- **Bio-Fantasy UI/UX**: Transitioned theme to Dark Fantasy Post-Apocalyptic with "symbiote" narrative elements.
- **Real-time Updates**: Implemented World Data Stream visualization in game scene templates.

---

## 2026-04-29
### Added [2026-04-29]

- **Game Stream Router**: Implemented `GameStreamRouter` in the backend core to handle events across all modules.
- **Event Bus Integration**: Fully integrated `StreamProcessor` for real-time event distribution.
- **Architecture Scalability**: Optimized frontend gateway to be stateless, enabling multi-instance deployment.
- **Frontend Core**: Refined `src/frontend/app.py` for improved performance.

---

## 2026-04-28
### Added [2026-04-28]

- **User Registration**: Implemented full user creation flow, including `register` service and themed forms.
- **Bio-Fantasy Theme**: Applied a new visual style across the site, replacing the previous cyberpunk aesthetic.
- **Symbiote Elements**: Integrated narrative-driven UI components for authentication.
- **Health Checks**: Added `/health` endpoint to frontend for service monitoring.
- **Site Structure**: Implemented global `base_site.html` template and shared CSS components (header, footer).
- **Authentication Pages**: Built new Login and Registration pages with themed styling.

---

## 2026-04-27
### Added [2026-04-27]

- **Project Initialization**: Setup core directory structure and dependency management via `uv`.
- **Legacy Reference**: Imported legacy source code to `temp/` for migration reference.
- **Configuration**: Basic `.gitignore`, `.env`, and pre-commit hooks.
