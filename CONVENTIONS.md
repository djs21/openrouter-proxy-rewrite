# CONVENTIONS.md

This document outlines the strict conventions to be followed by the AI pair programmer for the FastAPI Vertical Slice refactoring project. Adherence to these rules is mandatory.

## General Principles

1.  **Follow the Plan**: Only perform the tasks specified in the current phase of `to-do.md`. Do not work ahead.
2.  **Idempotent Operations**: All file creation and modification instructions should be idempotent. Assume the script might be run multiple times.
3.  **Acknowledge and Confirm**: Start every response by acknowledging the task and confirming what you will do.

## File and Directory Structure

1.  **Vertical Slices**: All business features MUST be implemented as vertical slices inside the `src/features/` directory.
2.  **Feature Directory**: Each feature slice MUST have its own directory, named after the feature in `snake_case` (e.g., `proxy_request`).
3.  **CQRS File Naming**:
    * **Endpoints**: All FastAPI routers MUST be in an `endpoints.py` file.
    * **Commands**: Operations that modify state.
        * Request/Response models MUST be in a `command.py` file.
        * Business logic MUST be in a `handler.py` file.
    * **Queries**: Operations that read state.
        * Request/Response models MUST be in a `query.py` file.
        * Business logic MUST be in a `handler.py` file.
4.  **Shared Code**: Truly generic, cross-cutting concerns (config, constants, base utilities, metrics) belong in `src/shared/`.
5.  **Services**: Stateful, domain-specific logic (like `KeyManager`) belongs in `src/services/`.

## Code Conventions

1.  **Line of Code (LOC) Limit**: **No file shall exceed 150 lines of code.** This is a hard limit. If a file is growing too large, break its logic into smaller, focused functions or classes, potentially in new helper files within the same feature directory.
2.  **Type Hinting**: All function signatures and variable declarations MUST include type hints (`str`, `int`, `Callable`, `Dict`, etc.). Use the `typing` module extensively.
3.  **Strictly No Business Logic in Endpoints**: The `endpoints.py` file is for routing and dependency injection ONLY. It defines the path, response model, and dependencies. The actual work MUST be delegated to a handler.
4.  **Dependency Injection is Mandatory**:
    * Never instantiate services (e.g., `KeyManager()`) or clients (e.g., `httpx.AsyncClient()`) directly in a handler or endpoint.
    * They MUST be provided via FastAPI's `Depends`. Define dependencies as separate functions if they have their own setup logic.
5.  **Models**: Use Pydantic's `BaseModel` for all data transfer objects (DTOs) in `command.py` and `query.py`.
6.  **Logging**: Import the `logger` instance from `src.shared.config` for all logging. Do not create new loggers.
7.  **Configuration**: Import the `config` object from `src.shared.config`. Do not load configuration manually in features.


