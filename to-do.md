# To-Do List: FastAPI Refactoring

This to-do list tracks the progress of refactoring the OpenRouter proxy to a Vertical Slice Architecture. Follow the phases in order. Only proceed to the next phase when the current one is complete and verified.

## Phase 0: Project Setup and Foundation

- [x] Create the base directory structure: `src/`, `src/features/`, `src/shared/`, `src/services/`.
- [x] Move existing files (`config.py`, `constants.py`, `utils.py`, `metrics.py`) into the `src/shared/` directory.
- [x] Update all imports in the moved files to be relative to the `src` root (e.g., `from .constants import ...`).
- [x] Create an empty `__init__.py` in `src/`, `src/features/`, `src/shared/`, and `src/services/`.

## Phase 1: Refactor Key Management Service

- [x] Extract the `KeyManager` class from `key_management_service.py` into a new file: `src/services/key_manager.py`.
- [x] Create the **"Get Next Key" Query Feature**:
  - [x] `src/features/get_next_key/query.py`
  - [x] `src/features/get_next_key/handler.py`
  - [x] `src/features/get_next_key/endpoints.py`
- [x] Create the **"Disable Key" Command Feature**:
  - [x] `src/features/disable_key/command.py`
  - [x] `src/features/disable_key/handler.py`
  - [x] `src/features/disable_key/endpoints.py`
- [x] Create the **"Update KMS Metrics" Command Feature**:
  - [x] `src/features/update_kms_metrics/command.py`
  - [x] `src/features/update_kms_metrics/handler.py`
  - [x] `src/features/update_kms_metrics/endpoints.py`

## Phase 2: Refactor Core Proxy Logic

- [x] Create the **"List Models" Query Feature**:
  - [x] `src/features/list_models/query.py`
  - [x] `src/features/list_models/handler.py`
  - [x] `src/features/list_models/endpoints.py`
- [x] Create the **"Proxy Chat Request" Command Feature**:
  - [x] `src/features/proxy_chat/command.py`
  - [x] `src/features/proxy_chat/handler.py`
  - [x] `src/features/proxy_chat/endpoints.py`

## Phase 3: Final Assembly and Cleanup

- [x] Refactor `main.py` to be a lean application loader. It should only initialize FastAPI and include the routers from all features in `src/features/`.
- [x] Delete the old, now empty, files: `routes.py` and `key_management_service.py`.
- [x] Review and update `test.py` to work with the new feature-based endpoints.
