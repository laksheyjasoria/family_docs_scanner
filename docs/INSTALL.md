# Installation

Requirements
- Windows 10/11 (scanning via WIA/TWAIN supported)
- Python 3.11+ (project was built/tested with Python 3.12)
- Recommended: virtual environment

Steps
1. Clone the repo.
2. Create and activate a virtual environment:

```powershell
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
```

3. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

4. Run the application:

```powershell
python app.py
```

Optional: build an executable
- Use `build_exe.bat` or the included PyInstaller spec files (`app.spec`, `FamilyDocsScanner.spec`).

Notes
- If Python cannot find scanner drivers, use `Import Images` in the UI to add image files.
