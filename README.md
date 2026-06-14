# Family Docs Scanner

Lightweight desktop app to scan, edit and export family documents.

Features
- Scan from TWAIN/WIA scanners (Windows), or import images
- Simple crop/rotate/black-&-white edits, undo/redo
- Session-based workflow and export per family member/document type

Quick start
1. Create and activate a virtual environment (Windows):

```powershell
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python app.py
```

Packaging
- A packaged exe can be built with the included `build_exe.bat` or using the provided `.spec` files.

Docs
- Installation: docs/INSTALL.md
- Usage: docs/USAGE.md
- Development: docs/DEVELOPMENT.md
- Contributing: docs/CONTRIBUTING.md
- Architecture: docs/ARCHITECTURE.md

Repository layout (important files)
- `app.py` — application entrypoint
- `requirements.txt` — Python dependencies
- `core/` — scanner, image processing, session management, exporter
- `ui/` — GUI windows and dialogs

License
- No license file included. Add a `LICENSE` if you wish to publish this repository.
