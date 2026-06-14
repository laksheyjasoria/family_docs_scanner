# Usage

Main concepts
- The app works in sessions: add pages (scan or import), edit pages, then Save/Export.

Primary controls (Main window)
- `📸 Scan` — start a scan from the selected scanner device (Windows only).
- `📁 Import Images` — open image files (png/jpg/tiff) and add as pages.
- `💾 Save All` — export the current session for the selected family member and document type.

Page editing
- `✂️ Crop` — click and drag on the preview to select crop area, then `Apply Changes`.
- `↻ Rotate L` / `↺ Rotate R` — rotate the current page.
- `⚫ B&W` — toggle black & white preview.
- `🃏 Quick Card Crop` — quick crop preset for cards/IDs.
- `↩️ Undo` / `↪️ Redo` — undo/redo per-page edits.

Managing pages
- Left panel shows page thumbnails.
- Use `+ Add` to import, `🗑️ Delete Page` to remove a page, and `⚠️ Clear All` to reset the session.
- Move pages with the arrow buttons (up/down/top/bottom).

Exporting
- Select the family member and document type using the combo boxes, then press `💾 Save All`.
- Export location defaults to `settings.json` -> `export_folder`.

Troubleshooting
- If the scanner status shows `Not found`, ensure drivers are installed and powered on.
- Use `Import Images` when scanning hardware is unavailable.
