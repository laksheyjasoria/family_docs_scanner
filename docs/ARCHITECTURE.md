# Architecture

High level
- `ui` — GUI layer. `MainWindow` constructs the UI and connects user actions to `core`.
- `core` — application logic:
  - `scanner.py` — hardware interaction and async scan flow
  - `image_processor.py` — image transforms, crop/rotate/BW
  - `session_manager.py` — session pages, undo/redo, persistence
  - `exporter.py` — writes session to disk (per family/doc type)

Flow
1. User triggers `Scan` or `Import Images` in `MainWindow`.
2. Images are added to `SessionManager` and can be edited via `ImageProcessor` helpers.
3. `Exporter` serializes and saves the session when `Save All` is invoked.
