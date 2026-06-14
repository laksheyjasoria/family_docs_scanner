# app.py

import sys
import os
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from ui.main_window import MainWindow


class FamilyDocsApp:

    def __init__(self):

        self.root = ctk.CTk()

        self.root.title("Family Docs Scanner")

        self.settings_file = Path("settings.json")

        self.settings = self.load_settings()

        theme = self.settings.get(
            "theme",
            "Dark"
        )

        ctk.set_appearance_mode(theme)

        ctk.set_default_color_theme("blue")

        self.main_window = MainWindow(
            self.root,
            self.settings,
            self.save_settings
        )

        self.root.after(
            100,
            lambda: self.root.state("zoomed")
        )

    # =====================================================
    # LOAD SETTINGS
    # =====================================================

    def load_settings(self):

        default_settings = {

            "scanner_device": "",

            "scanner_resolution_dpi": 300,

            "scanner_colour_mode": "Color",

            "scanner_paper_size": "A4",

            "use_adf": False,

            "export_folder": str(
                Path.home() / "Documents/FamilyDocs"
            ),

            "dpi_versions": [150, 300],

            "keep_original": True,

            "create_pdf": True,

            "pdf_compression": "Medium",

            "auto_deskew": True,

            "auto_crop_enabled": True,

            "auto_crop_margin": 10,

            "theme": "Dark",

            "family_members": [
                "Father",
                "Mother",
                "Brother",
                "Sister"
            ],

            "document_types": [
                "Aadhaar",
                "PAN",
                "Passport",
                "Medical",
                "Insurance",
                "Certificate"
            ],

            "log_level": "INFO",

            "keep_temp_files": False
        }

        if self.settings_file.exists():

            with open(
                    self.settings_file,
                    "r"
            ) as f:

                loaded = json.load(f)

                default_settings.update(loaded)

        else:

            self.save_settings(default_settings)

        return default_settings

    # =====================================================
    # SAVE SETTINGS
    # =====================================================

    def save_settings(self, settings=None):

        if settings is None:
            settings = self.settings

        with open(
                self.settings_file,
                "w"
        ) as f:

            json.dump(
                settings,
                f,
                indent=4
            )

    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":

    app = FamilyDocsApp()

    app.run()