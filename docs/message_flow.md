# 🔄 Request Lifecycle

Understanding how a message travels from the user to the rendered interface.

## 1. Middleware Layer (`codex-bot` Library)
1. **UserValidation** — Extracts the user and checks their status (Admin/Owner).
2. **Throttling** — Controls request frequency (Flood protection).
3. **DirectorMiddleware** — Automatically instantiates a `Director` for the current event.
4. **ContainerMiddleware** — Injects the DI Container with all available services.

## 2. Handlers Layer (Your Project)
The handler catches the command or button click. Its only job is to delegate the task to the Director:
```python
await director.set_scene("feature_name", payload=data)
```

## 3. Orchestrator Layer (Your Project)
1. **Routing**: `Director` finds the requested orchestrator in the container.
2. **State**: The FSM state is automatically updated (if specified in the Orchestrator).
3. **Entry**: The `handle_entry()` or `render()` method is called.
4. **Logic**: The Orchestrator requests data from `infrastructure/` (DB or API).
5. **UI**: Data is passed to the feature's UI layer, which returns text blocks and keyboards.

## 4. ViewSender Layer (`codex-bot` Library)
1. The Orchestrator returns a `UnifiedViewDTO`.
2. The Handler passes this DTO to `container.view_sender.send()`.
3. `ViewSender` checks the user's message history in Redis.
4. **Edit**: If messages already exist — it edits them (SPA effect).
5. **Send**: If it's a new interaction — it sends new messages and saves their IDs in Redis.
