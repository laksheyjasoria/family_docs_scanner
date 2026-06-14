import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess
import sys
import os
import threading
import tempfile

from core.scanner import Scanner
from ui.editable_list_section import EditableListSection


class SettingsDialog(ctk.CTkToplevel):

    def __init__(
        self,
        parent,
        main_window,
        settings,
        save_callback,
        refresh_ui_callback,
        current_theme
    ):
        super().__init__(parent)

        self.main_window = main_window
        self.settings = settings.copy()
        self.save_callback = save_callback
        self.refresh_ui_callback = refresh_ui_callback
        self.current_theme = current_theme

        self.scanner = Scanner(self.settings)

        self.set_theme()

        self.title("Settings")
        self.geometry("950x750")

        # IMPORTANT
        self.transient(parent)
        self.focus_force()

        self.build_ui()
        self.load_settings()

        # Delay scanner refresh slightly
        self.after(500, self.refresh_devices)

        # Enable modal AFTER UI loads
        self.after(200, self.enable_modal)

    def enable_modal(self):
        try:
            self.grab_set()
        except:
            pass

    # =========================================================
    # THEME
    # =========================================================

    def set_theme(self):

        if self.current_theme == "Dark":
            self.bg = "#1E1E2E"
            self.card = "#2B2B3A"
            self.text = "#FFFFFF"
            self.sub = "#A0A0B0"
            self.hover = "#3A3A4A"
            self.accent = "#0F8B8D"

        else:
            self.bg = "#F5F5F5"
            self.card = "#FFFFFF"
            self.text = "#1A1A1A"
            self.sub = "#666666"
            self.hover = "#EAEAEA"
            self.accent = "#0F8B8D"

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        self.configure(fg_color=self.bg)

        self.canvas = ctk.CTkScrollableFrame(
            self,
            fg_color=self.bg
        )
        self.canvas.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        # =====================================================
        # Scanner Section
        # =====================================================

        self._section_title("📠 Scanner Settings")

        self.device_combo = self._row_dropdown(
            "Scanner Device",
            []
        )

        self.device_status = ctk.CTkLabel(
            self.canvas,
            text="",
            text_color=self.sub
        )
        self.device_status.pack(
            anchor="w",
            padx=20,
            pady=(0, 10)
        )

        self.refresh_btn = ctk.CTkButton(
            self.canvas,
            text="⟳ Refresh Devices",
            command=self.refresh_devices
        )
        self.refresh_btn.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        self.resolution_entry = self._row_entry(
            "Resolution (DPI)",
            "300"
        )

        self.colour_combo = self._row_dropdown(
            "Color Mode",
            ["Color", "Grayscale", "Black/White"]
        )

        self.paper_combo = self._row_dropdown(
            "Paper Size",
            ["A4", "Letter", "Legal"]
        )

        self.adf_var = ctk.BooleanVar()

        ctk.CTkCheckBox(
            self.canvas,
            text="Use Automatic Document Feeder (ADF)",
            variable=self.adf_var
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        # =====================================================
        # Output
        # =====================================================

        self._section_title("💾 Output Settings")

        self.export_entry = self._row_folder(
            "Export Folder"
        )

        self.pdf_var = ctk.BooleanVar()

        ctk.CTkCheckBox(
            self.canvas,
            text="Create combined PDF",
            variable=self.pdf_var
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        self.keep_original_var = ctk.BooleanVar()

        ctk.CTkCheckBox(
            self.canvas,
            text="Keep Original Files",
            variable=self.keep_original_var
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        # =====================================================
        # Organization
        # =====================================================

        self._section_title("📂 Organization")

        org_container = ctk.CTkFrame(
            self.canvas,
            fg_color="transparent"
        )
        org_container.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # Family
        family_frame = ctk.CTkFrame(
            org_container,
            fg_color=self.card,
            corner_radius=8
        )
        family_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        self.family_list = EditableListSection(
            family_frame,
            "Family Members",
            get_items=lambda: self.settings["family_members"],
            on_add=lambda v: self.settings["family_members"].append(v),
            on_remove=lambda v: self.settings["family_members"].remove(v),
            on_update=lambda old, new:
                self.settings["family_members"].remove(old)
                or self.settings["family_members"].append(new)
        )

        self.family_list.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # Document Types
        doc_frame = ctk.CTkFrame(
            org_container,
            fg_color=self.card,
            corner_radius=8
        )
        doc_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        self.doc_list = EditableListSection(
            doc_frame,
            "Document Types",
            get_items=lambda: self.settings["document_types"],
            on_add=lambda v: self.settings["document_types"].append(v),
            on_remove=lambda v: self.settings["document_types"].remove(v),
            on_update=lambda old, new:
                self.settings["document_types"].remove(old)
                or self.settings["document_types"].append(new)
        )

        self.doc_list.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # =====================================================
        # Advanced
        # =====================================================

        self._section_title("⚙️ Advanced")

        self.theme_combo = self._row_dropdown(
            "Theme",
            ["Dark", "Light", "System"]
        )

        self.log_combo = self._row_dropdown(
            "Log Level",
            ["DEBUG", "INFO", "WARNING", "ERROR"]
        )

        self.keep_temp_var = ctk.BooleanVar()

        ctk.CTkCheckBox(
            self.canvas,
            text="Keep Temporary Files",
            variable=self.keep_temp_var
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        # =====================================================
        # Buttons
        # =====================================================

        btn_frame = ctk.CTkFrame(
            self.canvas,
            fg_color="transparent"
        )

        btn_frame.pack(
            fill="x",
            pady=30
        )

        ctk.CTkButton(
            btn_frame,
            text="Reset Defaults",
            fg_color="orange",
            command=self.reset_defaults
        ).pack(
            side="left",
            padx=5
        )

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self.destroy
        ).pack(
            side="right",
            padx=5
        )

        ctk.CTkButton(
            btn_frame,
            text="💾 Save Settings",
            fg_color="green",
            command=self.save
        ).pack(
            side="right",
            padx=5
        )

    # =========================================================
    # UI HELPERS
    # =========================================================

    def _section_title(self, text):

        ctk.CTkLabel(
            self.canvas,
            text=text,
            font=("Arial", 16, "bold"),
            text_color=self.text
        ).pack(
            anchor="w",
            padx=10,
            pady=(20, 10)
        )

    def _row_dropdown(self, label, values):

        frame = ctk.CTkFrame(
            self.canvas,
            fg_color=self.card
        )

        frame.pack(
            fill="x",
            padx=15,
            pady=5
        )

        ctk.CTkLabel(
            frame,
            text=label,
            width=180,
            anchor="w",
            text_color=self.text
        ).pack(
            side="left",
            padx=10
        )

        combo = ctk.CTkComboBox(
            frame,
            values=values,
            width=250
        )

        combo.pack(
            side="left",
            padx=10,
            pady=10
        )

        return combo

    def _row_entry(self, label, default=""):

        frame = ctk.CTkFrame(
            self.canvas,
            fg_color=self.card
        )

        frame.pack(
            fill="x",
            padx=15,
            pady=5
        )

        ctk.CTkLabel(
            frame,
            text=label,
            width=180,
            anchor="w",
            text_color=self.text
        ).pack(
            side="left",
            padx=10
        )

        entry = ctk.CTkEntry(
            frame,
            width=250
        )

        entry.pack(
            side="left",
            padx=10,
            pady=10
        )

        entry.insert(0, default)

        return entry

    def _row_folder(self, label):

        frame = ctk.CTkFrame(
            self.canvas,
            fg_color=self.card
        )

        frame.pack(
            fill="x",
            padx=15,
            pady=5
        )

        ctk.CTkLabel(
            frame,
            text=label,
            width=180,
            anchor="w",
            text_color=self.text
        ).pack(
            side="left",
            padx=10
        )

        entry = ctk.CTkEntry(
            frame,
            width=400
        )

        entry.pack(
            side="left",
            padx=10,
            pady=10
        )

        browse_btn = ctk.CTkButton(
            frame,
            text="📁 Browse",
            command=self._browse_folder
        )

        browse_btn.pack(
            side="left",
            padx=5
        )

        return entry

    # =========================================================
    # FIXED FOLDER BROWSER
    # =========================================================

    def _browse_folder(self):

        try:
            # Disable dialog while opening
            self.attributes("-disabled", True)

            # Release modal grab
            try:
                self.grab_release()
            except:
                pass

            self.update()
            self.lift()

            folder = filedialog.askdirectory(
                title="Select Export Folder",
                mustexist=False
            )

            if folder:
                self.export_entry.delete(0, "end")
                self.export_entry.insert(0, folder)

        except Exception as e:

            messagebox.showerror(
                "Folder Selection Error",
                str(e)
            )

        finally:

            try:
                self.attributes("-disabled", False)
            except:
                pass

            try:
                self.grab_set()
                self.focus_force()
            except:
                pass

    # =========================================================
    # SCANNER
    # =========================================================

    def refresh_devices(self):

        self.refresh_btn.configure(state="disabled")

        def task():

            try:

                self.scanner.refresh_devices()

                devices = self.scanner.get_devices()

                self.after(
                    0,
                    lambda: self._update_device_combo(devices)
                )

            except Exception:

                self.after(
                    0,
                    lambda: self._update_device_combo([])
                )

            finally:

                self.after(
                    0,
                    lambda: self.refresh_btn.configure(state="normal")
                )

        threading.Thread(
            target=task,
            daemon=True
        ).start()

    def _update_device_combo(self, devices):

        if not self.winfo_exists():
            return

        if not devices:

            devices = ["No Scanner Found"]

            self.device_status.configure(
                text="0 scanners detected – check connection"
            )

        else:

            self.device_status.configure(
                text=f"{len(devices)} scanner(s) detected"
            )

        current = self.settings.get(
            "scanner_device",
            ""
        )

        self.device_combo.configure(
            values=devices
        )

        if current in devices:
            self.device_combo.set(current)
        else:
            self.device_combo.set(devices[0])

    # =========================================================
    # LOAD SETTINGS
    # =========================================================

    def load_settings(self):

        self.resolution_entry.delete(0, "end")

        self.resolution_entry.insert(
            0,
            str(
                self.settings.get(
                    "scanner_resolution_dpi",
                    300
                )
            )
        )

        export_folder = self.settings.get(
            "export_folder",
            ""
        )

        if not export_folder:
            export_folder = str(
                Path.home() / "Documents/FamilyDocs"
            )

        self.export_entry.delete(0, "end")

        self.export_entry.insert(
            0,
            export_folder
        )

        self.colour_combo.set(
            self.settings.get(
                "scanner_colour_mode",
                "Color"
            )
        )

        self.paper_combo.set(
            self.settings.get(
                "scanner_paper_size",
                "A4"
            )
        )

        self.adf_var.set(
            self.settings.get(
                "use_adf",
                False
            )
        )

        self.pdf_var.set(
            self.settings.get(
                "create_pdf",
                True
            )
        )

        self.keep_original_var.set(
            self.settings.get(
                "keep_original",
                True
            )
        )

        self.theme_combo.set(
            self.settings.get(
                "theme",
                "Dark"
            )
        )

        self.log_combo.set(
            self.settings.get(
                "log_level",
                "INFO"
            )
        )

        self.keep_temp_var.set(
            self.settings.get(
                "keep_temp_files",
                False
            )
        )

        self.family_list.refresh()
        self.doc_list.refresh()

    # =========================================================
    # SAVE
    # =========================================================

    def save(self):

        self.settings["scanner_device"] = self.device_combo.get()

        try:
            self.settings["scanner_resolution_dpi"] = int(
                self.resolution_entry.get()
            )
        except:
            pass

        self.settings["scanner_colour_mode"] = self.colour_combo.get()
        self.settings["scanner_paper_size"] = self.paper_combo.get()
        self.settings["use_adf"] = self.adf_var.get()
        self.settings["export_folder"] = self.export_entry.get()
        self.settings["create_pdf"] = self.pdf_var.get()
        self.settings["keep_original"] = self.keep_original_var.get()
        self.settings["theme"] = self.theme_combo.get()
        self.settings["log_level"] = self.log_combo.get()
        self.settings["keep_temp_files"] = self.keep_temp_var.get()

        self.save_callback(self.settings)

        self.main_window.settings.update(self.settings)

        self.destroy()

        answer = messagebox.askyesno(
            "Restart Required",
            "Settings saved.\n\n"
            "Some changes require restart.\n\n"
            "Restart application now?"
        )

        if answer:
            self._restart_application()

    # =========================================================
    # RESTART
    # =========================================================

    def _restart_application(self):

        try:

            if getattr(sys, 'frozen', False):

                app_path = os.path.abspath(sys.executable)

                cmd_line = f'"{app_path}"'

            else:

                python_exe = sys.executable

                script_path = os.path.abspath(sys.argv[0])

                cmd_line = f'"{python_exe}" "{script_path}"'

            batch_path = os.path.join(
                tempfile.gettempdir(),
                "restart_family_scanner.bat"
            )

            with open(batch_path, 'w') as f:

                f.write('@echo off\n')
                f.write('timeout /t 1 /nobreak > nul\n')
                f.write(f'start "" {cmd_line}\n')
                f.write('del "%~f0"\n')

            subprocess.Popen(
                [batch_path],
                shell=True
            )

            self.main_window.root.quit()

            sys.exit(0)

        except Exception as e:

            messagebox.showerror(
                "Restart Error",
                f"Could not restart automatically.\n\n{e}"
            )

    # =========================================================
    # RESET
    # =========================================================

    def reset_defaults(self):

        if not messagebox.askyesno(
            "Reset",
            "Reset all settings to defaults?"
        ):
            return

        self.settings.update({

            "scanner_device": "",

            "scanner_resolution_dpi": 300,

            "scanner_colour_mode": "Color",

            "scanner_paper_size": "A4",

            "use_adf": False,

            "export_folder":
                str(Path.home() / "Documents/FamilyDocs"),

            "create_pdf": True,

            "keep_original": True,

            "theme": "Dark",

            "log_level": "INFO",

            "keep_temp_files": False,

            "family_members": [
                "Father",
                "Mother",
                "Brother",
                "Sister"
            ],

            "document_types": [
                "Aadhaar",
                "PAN",
                "Voter ID",
                "Driving License",
                "Vehicle RC",
                "10th Marksheet",
                "12th Marksheet",
                "Passport",
                "Medical",
                "Insurance",
                "Certificate"
            ]
        })

        self.load_settings()