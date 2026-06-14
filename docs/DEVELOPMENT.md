# Development

Project structure
- `app.py` — entrypoint and settings loader
- `core/` — business logic (scanner, image processing, session manager, exporter)
- `ui/` — CustomTkinter UI

Running during development

```powershell
python app.py
```

Useful notes
- `settings.json` contains default settings (family members, document types, export folder).
- Temporary images and session data are managed in memory; look at `core/session_manager.py` for persistence behaviour.

Adding dependencies

```powershell
pip install <package>
pip freeze > requirements.txt
```
