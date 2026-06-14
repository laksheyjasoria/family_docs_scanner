import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
from pathlib import Path
import copy
import os
import darkdetect
import time

from core.scanner import Scanner
from core.image_processor import ImageProcessor
from core.session_manager import SessionManager
from core.exporter import Exporter
from ui.scan_progress import ScanProgressPopup
from ui.confirmation_dialog import ConfirmationDialog
from ui.settings_dialog import SettingsDialog


class MainWindow:
    def __init__(self, root, settings, save_callback):
        self.root = root
        self.settings = settings
        self.save_settings = save_callback
        
        icon_path = Path(__file__).parent.parent / "assets" / "app_icon.ico"

        try:
            self.root.iconbitmap(str(icon_path))
        except Exception as e:
            print("Icon load error:", e)
            
        self.current_theme = settings.get("theme", "Dark")

        if self.current_theme == "Dark":
            ctk.set_default_color_theme("blue")
        else:
            ctk.set_default_color_theme("green")

        # Scanner (initialised in background)
        self.scanner = Scanner(settings)
        self.scanner_initialized = False
        self.scanner_available = False
        self.scanner_init_lock = threading.Lock()

        self.image_processor = ImageProcessor()
        self.session_manager = SessionManager()
        self.exporter = Exporter(settings)

        self.current_page_index = -1
        self.preview_image = None
        self.zoom_factor = 1.0
        self.crop_active = False
        self.crop_rect = None
        self.start_x = self.start_y = 0
        self.pending_crop_rect = None
        self.crop_rect_canvas_id = None
        self.resize_handles = []
        self.drag_mode = None
        self.drag_start = (0, 0)

        # Storage for original image coordinates (unrotated)
        self.page_crop_rects = {}
        self.page_bw_state = {}
        self.page_rotation = {}
        self.original_images = {}
        self.undo_stacks = {}
        self.redo_stacks = {}
        self.hover_mode = None

        self.build_ui()
        self.bind_shortcuts()

        # Start background scanner initialisation
        self.root.after(100, self._init_scanner_background)

    # ------------------------------------------------------------------
    # Background scanner initialisation
    # ------------------------------------------------------------------
    def _init_scanner_background(self):
        def task():
            with self.scanner_init_lock:
                try:
                    self.scanner.refresh_devices()
                    devices = self.scanner.get_devices()

                    if devices:
                        self.scanner.select_device(0)
                        self.scanner_available = True
                        self._ui_set_status("📷 Scanner: Ready ✅")
                    else:
                        self.scanner_available = False
                        self._ui_set_status("📷 Scanner: Not found ❌")

                except Exception:
                    self.scanner_available = False
                    self._ui_set_status("📷 Scanner: Error ❌")

                self.scanner_initialized = True

        threading.Thread(target=task, daemon=True).start()

    # =========================================================
    # UI HELPERS (THREAD SAFE)
    # =========================================================
    def _ui_set_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=text))

    def _ui_set_adf(self, text):
        self.root.after(0, lambda: self.adf_label.configure(text=text))

    # =========================================================
    # SCANNER HEALTH CHECK (IMPORTANT FIX)
    # =========================================================
    def is_scanner_alive(self):
        try:
            self.scanner.refresh_devices()
            return len(self.scanner.get_devices()) > 0
        except:
            return False

    def refresh_scanner_list(self):
        """Manual refresh button"""
        if self.is_scanner_alive():
            self.scanner_available = True
            self._ui_set_status("📷 Scanner: Ready ✅")
            self._ui_set_adf("📄 Feeder: Ready")
        else:
            self._set_scanner_off()

    def _set_scanner_off(self):
        self.scanner_available = False
        self._ui_set_status("📷 Scanner: Not found ❌")
        self._ui_set_adf("📄 Use Import Images")

    # =========================================================
    # WATCHDOG (LIGHTWEIGHT, NOT HEAVY POLLING)
    # =========================================================
    def start_scanner_watchdog(self):
        def loop():
            while True:
                try:
                    alive = self.is_scanner_alive()

                    if alive and not self.scanner_available:
                        self.scanner_available = True
                        self._ui_set_status("📷 Scanner: Ready ✅")

                    if not alive and self.scanner_available:
                        self._set_scanner_off()

                except:
                    pass

                time.sleep(4)  # low CPU usage

        threading.Thread(target=loop, daemon=True).start()

    # ------------------------------------------------------------------
    # Theme colours
    # ------------------------------------------------------------------
    def get_theme_colors(self):
        if self.current_theme == "Dark":
            return {
                "bg": "#1E1E2E", "frame_bg": "#2D2D3D", "frame_bg_light": "#3D3D4D",
                "text": "#FFFFFF", "text_secondary": "#A0A0B0",
                "accent_primary": "#0F8B8D", "accent_blue": "#3B82F6",
                "accent_green": "#10B981", "accent_orange": "#F59E0B",
                "accent_red": "#EF4444", "accent_purple": "#8B5CF6",
                "border": "#4D4D5D", "selected_bg": "#1E3A5F", "selected_border": "#0F8B8D"
            }
        else:
            return {
                "bg": "#F5F5F5", "frame_bg": "#FFFFFF", "frame_bg_light": "#E5E5E5",
                "text": "#1A1A1A", "text_secondary": "#666666",
                "accent_primary": "#0F8B8D", "accent_blue": "#2563EB",
                "accent_green": "#059669", "accent_orange": "#D97706",
                "accent_red": "#DC2626", "accent_purple": "#7C3AED",
                "border": "#D1D5DB", "selected_bg": "#DBEAFE", "selected_border": "#0F8B8D"
            }

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def build_ui(self):
        colors = self.get_theme_colors()
        self.root.configure(fg_color=colors["bg"])
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Top status bar
        status_bar = ctk.CTkFrame(self.main_frame, height=50, corner_radius=12,
                                  fg_color=colors["frame_bg"], border_width=1, border_color=colors["border"])
        status_bar.pack(fill="x", pady=(0,15))
        status_bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(status_bar, text="📷 Scanner: Initializing...",
                                         font=("Segoe UI", 13), text_color=colors["text"])
        self.status_label.pack(side="left", padx=15)
        self.adf_label = ctk.CTkLabel(status_bar, text="📄 Feeder: Unknown",
                                      font=("Segoe UI", 13), text_color=colors["text_secondary"])
        self.adf_label.pack(side="left", padx=20)

        btn_frame = ctk.CTkFrame(status_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="⟳ Refresh", command=self.refresh_scanner_list,
                      width=100, height=35, corner_radius=8,
                      fg_color=colors["frame_bg_light"], text_color=colors["text"],
                      hover_color=colors["border"]).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="⚙️ Settings", command=self.open_settings,
                      width=100, height=35, corner_radius=8,
                      fg_color=colors["frame_bg_light"], text_color=colors["text"],
                      hover_color=colors["border"]).pack(side="left", padx=5)

        # Main content
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Left panel – Thumbnails
        left_panel = ctk.CTkFrame(content, width=320, corner_radius=12,
                                  fg_color=colors["frame_bg"], border_width=1, border_color=colors["border"])
        left_panel.pack(side="left", fill="y", padx=(0,15))
        left_panel.pack_propagate(False)

        thumb_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        thumb_header.pack(fill="x", padx=15, pady=(15,10))
        ctk.CTkLabel(thumb_header, text="📑 Pages", font=("Segoe UI", 16, "bold"), text_color=colors["text"]).pack(side="left")

        # Button row 1
        button_row1 = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_row1.pack(fill="x", padx=15, pady=(0,10))
        ctk.CTkButton(button_row1, text="+ Add", command=self.import_images,
                      width=70, height=32, corner_radius=8,
                      fg_color=colors["accent_blue"], text_color="white").pack(side="left", padx=2)
        ctk.CTkButton(button_row1, text="🗑️ Delete Page", command=self.delete_current_page,
                      width=90, height=32, corner_radius=8,
                      fg_color=colors["accent_red"], text_color="white").pack(side="left", padx=2)
        ctk.CTkButton(button_row1, text="⚠️ Clear All", command=self.clear_session,
                      width=80, height=32, corner_radius=8,
                      fg_color=colors["accent_red"], text_color="white").pack(side="left", padx=2)

        # Button row 2 – Move buttons (equal width)
        button_row2 = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_row2.pack(fill="x", padx=15, pady=(0,10))
        for i in range(4):
            button_row2.grid_columnconfigure(i, weight=1)

        self.move_up_btn = ctk.CTkButton(button_row2, text="⬆", command=self.move_selected_up)
        self.move_up_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.move_down_btn = ctk.CTkButton(button_row2, text="⬇", command=self.move_selected_down)
        self.move_down_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.move_top_btn = ctk.CTkButton(button_row2, text="⏫", command=self.move_selected_to_top)
        self.move_top_btn.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        self.move_bottom_btn = ctk.CTkButton(button_row2, text="⏬", command=self.move_selected_to_bottom)
        self.move_bottom_btn.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        # Thumbnail scrollable frame
        self.thumb_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self.thumb_frame.pack(fill="both", expand=True, padx=15, pady=(0,15))

        # Right panel – preview and tools
        right_panel = ctk.CTkFrame(content, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        canvas_container = ctk.CTkFrame(right_panel, corner_radius=12,
                                        fg_color=colors["frame_bg"], border_width=1, border_color=colors["border"])
        canvas_container.pack(fill="both", expand=True, pady=(0,15))
        self.canvas = ctk.CTkCanvas(canvas_container, bg=colors["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=15, pady=15)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        tools_frame = ctk.CTkFrame(right_panel, corner_radius=12,
                                   fg_color=colors["frame_bg"], border_width=1, border_color=colors["border"])
        tools_frame.pack(fill="x", pady=(0,15))

        edit_row = ctk.CTkFrame(tools_frame, fg_color="transparent")
        edit_row.pack(fill="x", padx=15, pady=(15,10))
        ctk.CTkButton(edit_row, text="✂️ Crop", command=self.activate_crop,
                      width=80, height=35, corner_radius=8,
                      fg_color=colors["accent_blue"], text_color="white").pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="↻ Rotate L", command=lambda: self.rotate_image(-90),
                      width=90, height=35, corner_radius=8,
                      fg_color=colors["frame_bg_light"], text_color=colors["text"]).pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="↺ Rotate R", command=lambda: self.rotate_image(90),
                      width=90, height=35, corner_radius=8,
                      fg_color=colors["frame_bg_light"], text_color=colors["text"]).pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="🃏 Quick Card Crop", command=self.quick_card_crop,
                      width=130, height=35, corner_radius=8,
                      fg_color=colors["accent_orange"], text_color="white").pack(side="left", padx=4)
        self.bw_button = ctk.CTkButton(edit_row, text="⚫ B&W", command=self.toggle_bw,
                                       width=80, height=35, corner_radius=8,
                                       fg_color=colors["frame_bg_light"], text_color=colors["text"])
        self.bw_button.pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="✔ Apply Changes",command=self.apply_changes,
                      width=100, height=35, corner_radius=8,
                      fg_color=colors["accent_green"], text_color="white").pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="⟲ Reset Page", command=self.reset_current_page,
                      width=100, height=35, corner_radius=8,
                      fg_color=colors["accent_red"], text_color="white").pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="↩️ Undo", command=self.undo,
                      width=80, height=35, corner_radius=8,
                      fg_color=colors["accent_purple"], text_color="white").pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="↪️ Redo", command=self.redo,
                      width=80, height=35, corner_radius=8,
                      fg_color=colors["accent_purple"], text_color="white").pack(side="left", padx=4)

        select_row = ctk.CTkFrame(tools_frame, fg_color="transparent")
        select_row.pack(fill="x", padx=15, pady=(0,15))
        ctk.CTkLabel(select_row, text="👨‍👩‍👧 Family:", font=("Segoe UI", 13), text_color=colors["text"]).pack(side="left", padx=5)
        self.family_combo = ctk.CTkComboBox(select_row, values=self.settings["family_members"],
                                            width=160, height=35, corner_radius=8)
        self.family_combo.pack(side="left", padx=5)
        ctk.CTkLabel(select_row, text="📄 Document:", font=("Segoe UI", 13), text_color=colors["text"]).pack(side="left", padx=15)
        self.doc_combo = ctk.CTkComboBox(select_row, values=self.settings["document_types"],
                                         width=160, height=35, corner_radius=8)
        self.doc_combo.pack(side="left", padx=5)

        action_row = ctk.CTkFrame(right_panel, fg_color="transparent")
        action_row.pack(fill="x")
        ctk.CTkButton(action_row, text="📸 Scan", command=self.scan_and_add,
                      height=50, corner_radius=10, font=("Segoe UI", 14, "bold"),
                      fg_color=colors["accent_primary"], text_color="white").pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(action_row, text="📁 Import Images", command=self.import_images,
                      height=50, corner_radius=10, font=("Segoe UI", 14, "bold"),
                      fg_color=colors["accent_blue"], text_color="white").pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(action_row, text="💾 Save All", command=self.save_all,
                      height=50, corner_radius=10, font=("Segoe UI", 14, "bold"),
                      fg_color=colors["accent_green"], text_color="white").pack(side="left", padx=5, expand=True, fill="x")

        self.status_bar = ctk.CTkLabel(self.main_frame, text="✅ Ready", anchor="w",
                                       font=("Segoe UI", 11), fg_color=colors["frame_bg"],
                                       corner_radius=10, height=35, text_color=colors["text_secondary"])
        self.status_bar.pack(fill="x", pady=(15,0))

        self.refresh_thumbnails()

    # ------------------------------------------------------------------
    # Scanner operations
    # ------------------------------------------------------------------
    # def refresh_scanner_list(self):
    #     if not self.scanner_initialized:
    #         self.status_label.configure(text="📷 Scanner: Initializing...")
    #         return
    #     if not self.scanner_available:
    #         self.status_label.configure(text="📷 Scanner: Not available")
    #         self.adf_label.configure(text="📄 Use 'Import Images'")
    #         return
    #     try:
    #         self.scanner.refresh_devices()
    #         devices = self.scanner.get_devices()
    #         if devices:
    #             saved = self.settings.get("scanner_device", "")
    #             if saved and saved in devices:
    #                 self.scanner.select_device_by_name(saved)
    #             else:
    #                 self.scanner.select_device(0)
    #             self.status_label.configure(text="📷 Scanner: Ready ✅")
    #             self.adf_label.configure(text="📄 Feeder: Ready")
    #         else:
    #             self.status_label.configure(text="📷 Scanner: Not found")
    #             self.adf_label.configure(text="📄 Feeder: Unknown")
    #     except Exception as e:
    #         self.status_label.configure(text="📷 Scanner: Error")
    #         print(f"Scanner refresh error: {e}")
        
    def _set_scanner_unavailable(self):
        self.scanner_available = False
        self.status_label.configure(text="📷 Scanner: Not found ❌")
        self.adf_label.configure(text="📄 Use Import Images")

    # def scan_and_add(self):
        
    #     if not self.scanner_initialized:
    #         messagebox.showinfo("Scanner", "Scanner is still starting up. Please wait a few seconds.")
    #         return
    #     if not self.scanner_available:
    #         messagebox.showinfo("Scanner Unavailable", "Scanner not found. Please use 'Import Images'.")
    #         return
    #     if self.scanner.is_scanning:
    #         messagebox.showinfo("Scanner", "Scan already in progress")
    #         return
        
    #     if not self.is_scanner_alive():
    #         self._set_scanner_unavailable()
    #         messagebox.showerror("Scanner", "Scanner not connected")
    #         return

    #     self.scanner_available = True

    #     devices = self.scanner.get_devices()
    #     if devices:
    #         saved = self.settings.get("scanner_device", "")
    #         if saved and saved in devices:
    #             self.scanner.select_device_by_name(saved)
    #         else:
    #             self.scanner.select_device(0)
    #     else:
    #         messagebox.showerror("Scanner Error", "No scanner device found.")
    #         return

    #     popup = ScanProgressPopup(self.root)

    #     def on_cancel():
    #         self.scanner.cancel_scan()
    #         popup._destroy()

    #     popup.set_cancel_callback(on_cancel)

    #     def on_progress(v):
    #         if v >= 0:
    #             self.root.after(0, lambda: popup.set_progress(v))

    #     def on_status(s):
    #         if s.upper() != "INITIALIZING":
    #             self.root.after(0, lambda: popup.set_status(s))

    #     def on_result(img):
    #         def ui():
    #             self.session_manager.add_page(img)
    #             idx = self.session_manager.page_count() - 1
    #             self.original_images[idx] = img.copy()
    #             self.page_rotation[idx] = 0
    #             self.undo_stacks[idx] = []
    #             self.redo_stacks[idx] = []
    #             self.refresh_thumbnails()
    #             self.select_page(idx)
    #             popup._destroy()
    #         self.root.after(0, ui)

    #     def on_error(e):
    #         def ui():
    #             messagebox.showerror("Scan Error", e)
    #             popup._destroy()
    #         self.root.after(0, ui)

    #     self.scanner.scan_async(
    #         progress_callback=on_progress,
    #         result_callback=on_result,
    #         error_callback=on_error,
    #         status_callback=on_status
    #     )
    
    def scan_and_add(self):

        if not self.scanner_initialized:
            messagebox.showinfo("Scanner", "Starting scanner...")
            return

        # 🔴 FORCE REFRESH BEFORE SCAN (IMPORTANT FIX)
        if not self.is_scanner_alive():
            self._set_scanner_off()
            messagebox.showerror("Scanner", "Scanner not connected")
            return

        self.scanner.refresh_devices()
        devices = self.scanner.get_devices()

        if not devices:
            self._set_scanner_off()
            messagebox.showerror("Scanner", "No scanner found")
            return

        self.scanner_available = True

        self.scanner.select_device(0)

        popup = ScanProgressPopup(self.root)

        def on_cancel():
            self.scanner.cancel_scan()
            popup.destroy()

        popup.set_cancel_callback(on_cancel)

        def on_result(img):
            def ui():
                self.session_manager.add_page(img)
                idx = self.session_manager.page_count() - 1
                self.original_images[idx] = img.copy()
                self.refresh_thumbnails()
                self.select_page(idx)
                popup.destroy()
            self.root.after(0, ui)

        def on_error(err):
            self.root.after(0, lambda: messagebox.showerror("Scan Error", str(err)))

        self.scanner.scan_async(
            result_callback=on_result,
            error_callback=on_error
        )

    # ------------------------------------------------------------------
    # Page management (thumbnails, move, delete, clear)
    # ------------------------------------------------------------------
    def refresh_thumbnails(self):
        for widget in self.thumb_frame.winfo_children():
            widget.destroy()

        self.update_move_buttons_state()

        if self.session_manager.page_count() == 0:
            colors = self.get_theme_colors()
            empty_label = ctk.CTkLabel(self.thumb_frame,
                                       text="No pages\nClick Scan or + Add to add images",
                                       font=("Segoe UI", 12), text_color=colors["text_secondary"])
            empty_label.pack(pady=50)
            return

        colors = self.get_theme_colors()

        for idx in range(self.session_manager.page_count()):
            try:
                page = self.session_manager.get_page_edited(idx)
                if page is not None:
                    thumb = page.copy()
                thumb.thumbnail((80, 80), Image.Resampling.LANCZOS)
                img_tk = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=(80, 80))

                is_selected = (idx == self.current_page_index)

                thumb_container = ctk.CTkFrame(self.thumb_frame, fg_color="transparent")
                thumb_container.pack(pady=5, fill="x")

                if is_selected:
                    border_color = colors["selected_border"]
                    border_width = 3
                    bg_color = colors["selected_bg"]
                else:
                    border_color = colors["border"]
                    border_width = 1
                    bg_color = colors["frame_bg_light"]

                thumb_frame = ctk.CTkFrame(thumb_container, width=90, height=120,
                                           corner_radius=8, border_width=border_width,
                                           border_color=border_color, fg_color=bg_color)
                thumb_frame.pack(side="left")
                thumb_frame.pack_propagate(False)

                btn = ctk.CTkButton(thumb_frame, image=img_tk, text="",
                                    command=lambda i=idx: self.select_page(i),
                                    width=80, height=80, corner_radius=6,
                                    fg_color="transparent", hover_color=colors["border"])
                btn.image = img_tk
                btn.pack(pady=(8, 0))

                page_label = ctk.CTkLabel(thumb_frame, text=f"Page {idx+1}",
                                          font=("Segoe UI", 10, "bold" if is_selected else "normal"),
                                          text_color=colors["accent_primary"] if is_selected else colors["text"])
                page_label.pack(pady=4)

            except Exception as e:
                print(f"Thumbnail error for page {idx}: {e}")

    def select_page(self, idx):
        if idx < 0 or idx >= self.session_manager.page_count():
            return

        self.current_page_index = idx

        try:
            original = self.session_manager.get_page_original(idx)
            angle = self.page_rotation.get(idx, 0)
            bw = self.page_bw_state.get(idx, False)

            if original is not None:
                img = original.copy()

            if angle != 0:
                img = img.rotate(angle, expand=True)

            if bw:
                img = img.convert("L").convert("RGB")

            self.preview_image = img
            self.display_image(img)

            stored_rect = self.page_crop_rects.get(idx)

            if stored_rect:
                self.pending_crop_rect = self.transform_rect_to_view(
                    stored_rect,
                    original.size,
                    angle
                )
            else:
                self.pending_crop_rect = None

            self.draw_crop_rect_overlay()

            colors = self.get_theme_colors()

            if bw:
                self.bw_button.configure(
                    fg_color=colors["accent_green"],
                    text="⚫ B&W ✓"
                )
            else:
                self.bw_button.configure(
                    fg_color=colors["frame_bg_light"],
                    text="⚫ B&W"
                )

            self.refresh_thumbnails()
            self.update_move_buttons_state()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load page: {str(e)}")

    def delete_current_page(self):
        if self.current_page_index < 0 or self.current_page_index >= self.session_manager.page_count():
            messagebox.showwarning("No Page", "No page selected")
            return
        if not messagebox.askyesno("Delete Page", f"Delete page {self.current_page_index+1}? This cannot be undone."):
            return
        current_idx = self.current_page_index
        self.session_manager.delete_page(current_idx)

        def shift_dict(d, idx):
            for i in list(d.keys()):
                if i > idx:
                    d[i-1] = d.pop(i)
        shift_dict(self.page_crop_rects, current_idx)
        shift_dict(self.page_bw_state, current_idx)
        shift_dict(self.page_rotation, current_idx)
        shift_dict(self.original_images, current_idx)
        shift_dict(self.undo_stacks, current_idx)
        shift_dict(self.redo_stacks, current_idx)

        self.refresh_thumbnails()
        if self.session_manager.page_count() == 0:
            self.current_page_index = -1
            self.clear_preview()
            self.status_bar.configure(text="No pages left.")
        else:
            new_idx = current_idx if current_idx < self.session_manager.page_count() else self.session_manager.page_count()-1
            self.select_page(new_idx)
            self.status_bar.configure(text=f"Page {current_idx+1} deleted.")

    def clear_session(self):
        if self.session_manager.page_count() > 0 and self.session_manager.has_unsaved_changes():
            if not messagebox.askyesno("Clear All", "All pages will be lost. Continue?"):
                return
        self.session_manager.clear_session()
        self.page_crop_rects.clear()
        self.page_bw_state.clear()
        self.page_rotation.clear()
        self.original_images.clear()
        self.undo_stacks.clear()
        self.redo_stacks.clear()
        self.current_page_index = -1
        self.preview_image = None
        self.pending_crop_rect = None
        self.refresh_thumbnails()
        self.clear_preview()
        self.status_bar.configure(text="All pages cleared.")

    # ------------------------------------------------------------------
    # Move page (reorder)
    # ------------------------------------------------------------------
    def update_move_buttons_state(self):
        count = self.session_manager.page_count()
        has_selection = 0 <= self.current_page_index < count
        if count <= 1 or not has_selection:
            self.move_up_btn.configure(state="disabled")
            self.move_down_btn.configure(state="disabled")
            self.move_top_btn.configure(state="disabled")
            self.move_bottom_btn.configure(state="disabled")
        else:
            self.move_up_btn.configure(state="normal" if self.current_page_index > 0 else "disabled")
            self.move_down_btn.configure(state="normal" if self.current_page_index < count-1 else "disabled")
            self.move_top_btn.configure(state="normal" if self.current_page_index > 0 else "disabled")
            self.move_bottom_btn.configure(state="normal" if self.current_page_index < count-1 else "disabled")

    def move_page_up(self, idx):
        if idx <= 0:
            return
        self.session_manager.move_page(idx, idx-1)
        self.reorder_states(idx, idx-1)
        self.refresh_thumbnails()
        self.select_page(idx-1)
        self.update_move_buttons_state()
        self.status_bar.configure(text=f"Page {idx+1} moved up")

    def move_page_down(self, idx):
        if idx >= self.session_manager.page_count()-1:
            return
        self.session_manager.move_page(idx, idx+1)
        self.reorder_states(idx, idx+1)
        self.refresh_thumbnails()
        self.select_page(idx+1)
        self.update_move_buttons_state()
        self.status_bar.configure(text=f"Page {idx+1} moved down")

    def move_page_to_top(self, idx):
        if idx <= 0:
            return
        self.session_manager.move_page(idx, 0)
        self.reorder_states(idx, 0)
        self.refresh_thumbnails()
        self.select_page(0)
        self.update_move_buttons_state()
        self.status_bar.configure(text=f"Page {idx+1} moved to top")

    def move_page_to_bottom(self, idx):
        if idx >= self.session_manager.page_count()-1:
            return
        last = self.session_manager.page_count()-1
        self.session_manager.move_page(idx, last)
        self.reorder_states(idx, last)
        self.refresh_thumbnails()
        self.select_page(last)
        self.update_move_buttons_state()
        self.status_bar.configure(text=f"Page {idx+1} moved to bottom")

    def reorder_states(self, old_idx, new_idx):
        def move_dict_item(d, old, new):
            if not d:
                return
            items = list(d.items())
            if old < new:
                for i in range(old, new):
                    if i+1 in d:
                        d[i] = d[i+1]
                d[new] = items[old][1]
            elif old > new:
                for i in range(old, new, -1):
                    if i-1 in d:
                        d[i] = d[i-1]
                d[new] = items[old][1]
        move_dict_item(self.page_crop_rects, old_idx, new_idx)
        move_dict_item(self.page_bw_state, old_idx, new_idx)
        move_dict_item(self.page_rotation, old_idx, new_idx)
        move_dict_item(self.original_images, old_idx, new_idx)
        move_dict_item(self.undo_stacks, old_idx, new_idx)
        move_dict_item(self.redo_stacks, old_idx, new_idx)

    # ------------------------------------------------------------------
    # Image editing (crop, rotate, B&W, reset, quick crop)
    # ------------------------------------------------------------------
    def display_image(self, pil_image):
        if pil_image is None:
            self.preview_image = None
            self.canvas.delete("all")
            return
        self.preview_image = pil_image.copy()
        self.zoom_factor = 1.0
        self.update_canvas_image()

    def update_canvas_image(self):
        if self.preview_image is None:
            return
        w, h = self.preview_image.size
        zoom_w = int(w * self.zoom_factor)
        zoom_h = int(h * self.zoom_factor)
        resized = self.preview_image.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.draw_crop_rect_overlay()

    def draw_crop_rect_overlay(self):
        self.canvas.delete("crop_overlay")

        if not self.pending_crop_rect:
            return

        x, y, w, h = self.pending_crop_rect

        x1 = x * self.zoom_factor
        y1 = y * self.zoom_factor

        x2 = (x + w) * self.zoom_factor
        y2 = (y + h) * self.zoom_factor

        self.crop_rect_canvas_id = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#00FF00",
            width=3,
            tags="crop_overlay"
        )

        # Optional guide lines
        self.canvas.create_line(
            (x1 + x2) / 2,
            y1,
            (x1 + x2) / 2,
            y2,
            fill="#00FF00",
            dash=(4, 4),
            tags="crop_overlay"
        )

        self.canvas.create_line(
            x1,
            (y1 + y2) / 2,
            x2,
            (y1 + y2) / 2,
            fill="#00FF00",
            dash=(4, 4),
            tags="crop_overlay"
        )

    def on_mouse_move(self, event):
        if self.pending_crop_rect is None:
            self.canvas.config(cursor="")
            return

        x = self.canvas.canvasx(event.x) / self.zoom_factor
        y = self.canvas.canvasy(event.y) / self.zoom_factor

        rx, ry, rw, rh = self.pending_crop_rect

        x1 = rx
        y1 = ry
        x2 = rx + rw
        y2 = ry + rh

        edge = 15

        mode = None

        # CORNERS
        if abs(x - x1) < edge and abs(y - y1) < edge:
            mode = "nw"
            self.canvas.config(cursor="size_nw_se")

        elif abs(x - x2) < edge and abs(y - y1) < edge:
            mode = "ne"
            self.canvas.config(cursor="size_ne_sw")

        elif abs(x - x1) < edge and abs(y - y2) < edge:
            mode = "sw"
            self.canvas.config(cursor="size_ne_sw")

        elif abs(x - x2) < edge and abs(y - y2) < edge:
            mode = "se"
            self.canvas.config(cursor="size_nw_se")

        # EDGES
        elif abs(x - x1) < edge:
            mode = "w"
            self.canvas.config(cursor="sb_h_double_arrow")

        elif abs(x - x2) < edge:
            mode = "e"
            self.canvas.config(cursor="sb_h_double_arrow")

        elif abs(y - y1) < edge:
            mode = "n"
            self.canvas.config(cursor="sb_v_double_arrow")

        elif abs(y - y2) < edge:
            mode = "s"
            self.canvas.config(cursor="sb_v_double_arrow")

        # MOVE
        elif x1 < x < x2 and y1 < y < y2:
            mode = "move"
            self.canvas.config(cursor="fleur")

        else:
            self.canvas.config(cursor="")

        self.hover_mode = mode

    def on_canvas_click(self, event):
        if self.crop_active:
            return

        if self.pending_crop_rect is None:
            return

        self.drag_mode = getattr(self, "hover_mode", None)

        if self.drag_mode:
            self.drag_start = (
                self.canvas.canvasx(event.x),
                self.canvas.canvasy(event.y)
            )

        def normalize_rect(self, rect):
            x, y, w, h = rect
            if w < 0:
                x += w
                w = abs(w)
            if h < 0:
                y += h
                h = abs(h)
            return (x, y, w, h)

    def transform_rect_to_view(self, rect, original_size, angle):
        x, y, w, h = rect
        ow, oh = original_size
        angle = angle % 360
        if angle == 0:
            return (x, y, w, h)
        elif angle == 90:
            return (y, ow - (x + w), h, w)
        elif angle == 180:
            return (ow - (x + w), oh - (y + h), w, h)
        elif angle == 270:
            return (oh - (y + h), x, h, w)
        return rect

    def transform_rect_to_original(self, rect, original_size, angle):
        x, y, w, h = rect
        ow, oh = original_size
        angle = angle % 360
        if angle == 0:
            return (x, y, w, h)
        elif angle == 90:
            return (ow - (y + h), x, h, w)
        elif angle == 180:
            return (ow - (x + w), oh - (y + h), w, h)
        elif angle == 270:
            return (y, oh - (x + w), h, w)
        return rect

    def on_canvas_drag(self, event):
        if self.drag_mode is None:
            return

        if self.preview_image is None:
            return

        if self.pending_crop_rect is None:
            return

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        dx = (x - self.drag_start[0]) / self.zoom_factor
        dy = (y - self.drag_start[1]) / self.zoom_factor

        rx, ry, rw, rh = self.pending_crop_rect

        x1 = rx
        y1 = ry
        x2 = rx + rw
        y2 = ry + rh

        min_size = 20

        # MOVE
        if self.drag_mode == "move":
            x1 += dx
            x2 += dx
            y1 += dy
            y2 += dy

        # CORNERS
        elif self.drag_mode == "nw":
            x1 += dx
            y1 += dy

        elif self.drag_mode == "ne":
            x2 += dx
            y1 += dy

        elif self.drag_mode == "sw":
            x1 += dx
            y2 += dy

        elif self.drag_mode == "se":
            x2 += dx
            y2 += dy

        # EDGES
        elif self.drag_mode == "n":
            y1 += dy

        elif self.drag_mode == "s":
            y2 += dy

        elif self.drag_mode == "w":
            x1 += dx

        elif self.drag_mode == "e":
            x2 += dx

        # Prevent inversion
        if x2 - x1 < min_size:
            if "w" in self.drag_mode:
                x1 = x2 - min_size
            else:
                x2 = x1 + min_size

        if y2 - y1 < min_size:
            if "n" in self.drag_mode:
                y1 = y2 - min_size
            else:
                y2 = y1 + min_size

        img_w, img_h = self.preview_image.size

        # Clamp to image bounds
        x1 = max(0, min(x1, img_w - min_size))
        y1 = max(0, min(y1, img_h - min_size))

        x2 = max(min_size, min(x2, img_w))
        y2 = max(min_size, min(y2, img_h))

        rw = x2 - x1
        rh = y2 - y1

        self.pending_crop_rect = (x1, y1, rw, rh)

        self.drag_start = (x, y)

        # SAVE BACK TO ORIGINAL COORDINATES
        idx = self.current_page_index
        angle = self.page_rotation.get(idx, 0)

        original_size = self.session_manager.get_page_original(idx).size

        self.page_crop_rects[idx] = self.transform_rect_to_original(
            self.pending_crop_rect,
            original_size,
            angle
        )

        self.draw_crop_rect_overlay()

    def on_canvas_release(self, event):
        self.drag_mode = None

    def activate_crop(self):
        if self.preview_image is None:
            messagebox.showwarning("No Image", "No image to crop")
            return

        self.crop_active = True

        self.status_bar.configure(
            text="Drag mouse to create crop rectangle"
        )

        self.canvas.bind("<ButtonPress-1>", self.on_crop_start)
        self.canvas.bind("<B1-Motion>", self.on_crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_crop_end)

    def on_crop_start(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
        self.crop_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                      outline="red", width=2)

    def on_crop_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.crop_rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_crop_end(self, event):

        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        x1 = min(self.start_x, end_x) / self.zoom_factor
        y1 = min(self.start_y, end_y) / self.zoom_factor

        x2 = max(self.start_x, end_x) / self.zoom_factor
        y2 = max(self.start_y, end_y) / self.zoom_factor

        w = x2 - x1
        h = y2 - y1

        self.crop_active = False

        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
            self.crop_rect = None

        if w < 20 or h < 20:
            return

        self.pending_crop_rect = (x1, y1, w, h)

        idx = self.current_page_index
        angle = self.page_rotation.get(idx, 0)

        original_size = self.session_manager.get_page_original(idx).size

        self.page_crop_rects[idx] = self.transform_rect_to_original(
            self.pending_crop_rect,
            original_size,
            angle
        )

        self.draw_crop_rect_overlay()

        # RESTORE NORMAL EVENTS
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.status_bar.configure(
            text="Crop rectangle ready. Drag edges/corners to resize."
        )

    # def apply_crop(self):
    #     if self.preview_image is None:
    #         return
    #     if self.pending_crop_rect is None:
    #         messagebox.showinfo("Apply Crop", "No crop rectangle defined")
    #         return
    #     self.save_state_for_undo()
    #     idx = self.current_page_index
    #     # Get the rectangle in original coordinates
    #     stored_rect = self.page_crop_rects.get(idx, None)
    #     if stored_rect is None:
    #         messagebox.showinfo("Apply Crop", "No crop rectangle defined")
    #         return
    #     x, y, w, h = stored_rect
    #     original_img = self.session_manager.get_page_original(idx)
    #     # Clamp to image bounds
    #     if x < 0:
    #         x = 0
    #     if y < 0:
    #         y = 0
    #     if x + w > original_img.width:
    #         w = original_img.width - x
    #     if y + h > original_img.height:
    #         h = original_img.height - y
    #     if w <= 5 or h <= 5:
    #         messagebox.showwarning("Crop Error", "Crop area too small")
    #         return
    #     cropped = original_img.crop((x, y, x + w, y + h))
    #     self.session_manager.replace_original(idx, cropped)
    #     # Reset rotation and B&W state
    #     if idx in self.page_rotation:
    #         del self.page_rotation[idx]
    #     if idx in self.page_bw_state:
    #         del self.page_bw_state[idx]
    #     # Clear crop rectangle for this page
    #     if idx in self.page_crop_rects:
    #         del self.page_crop_rects[idx]
    #     self.pending_crop_rect = None
    #     self.preview_image = None
    #     self.select_page(idx)
    #     self.status_bar.configure(text="Crop applied")
    
    def apply_changes(self):

        if self.current_page_index < 0:
            return

        idx = self.current_page_index

        original = self.session_manager.get_page_original(idx)

        if original is None:
            return

        self.save_state_for_undo()

        img = original.copy()

        # ============================================
        # APPLY ROTATION
        # ============================================

        angle = self.page_rotation.get(idx, 0)

        if angle != 0:
            img = img.rotate(angle, expand=True)

        # ============================================
        # APPLY B&W
        # ============================================

        bw = self.page_bw_state.get(idx, False)

        if bw:
            img = img.convert("L").convert("RGB")

        # ============================================
        # APPLY CROP
        # ============================================

        if self.pending_crop_rect:

            x, y, w, h = self.pending_crop_rect

            x = max(0, int(x))
            y = max(0, int(y))

            w = int(w)
            h = int(h)

            if x + w > img.width:
                w = img.width - x

            if y + h > img.height:
                h = img.height - y

            if w > 5 and h > 5:
                img = img.crop((x, y, x + w, y + h))

        # ============================================
        # SAVE FINAL IMAGE
        # ============================================

        self.session_manager.replace_original(idx, img)

        # ============================================
        # RESET TEMP STATES
        # ============================================

        self.page_rotation[idx] = 0
        self.page_bw_state[idx] = False

        if idx in self.page_crop_rects:
            del self.page_crop_rects[idx]

        self.pending_crop_rect = None

        # ============================================
        # REFRESH
        # ============================================

        self.preview_image = None

        self.select_page(idx)

        self.refresh_thumbnails()

        self.status_bar.configure(
            text="Changes applied successfully"
        )

    def rotate_image(self, angle):
        if self.current_page_index < 0:
            return

        self.save_state_for_undo()

        idx = self.current_page_index

        current_angle = self.page_rotation.get(idx, 0)
        new_angle = (current_angle + angle) % 360

        self.page_rotation[idx] = new_angle

        original = self.session_manager.get_page_original(idx)

        stored_rect = self.page_crop_rects.get(idx)

        if stored_rect:
            self.pending_crop_rect = self.transform_rect_to_view(
                stored_rect,
                original.size,
                new_angle
            )

        self.select_page(idx)

        self.status_bar.configure(text=f"Rotated {angle}°")

    def toggle_bw(self):
        if self.preview_image is None:
            return
        self.save_state_for_undo()
        idx = self.current_page_index
        cur = self.page_bw_state.get(idx, False)
        self.page_bw_state[idx] = not cur
        self.select_page(idx)

    def reset_current_page(self):
        if self.current_page_index < 0:
            return
        if not messagebox.askyesno("Reset", "Reset current page to original?"):
            return
        self.save_state_for_undo()
        idx = self.current_page_index
        if idx in self.original_images:
            original_img = self.original_images[idx].copy()
        else:
            original_img = self.session_manager.get_page_original(idx)
        self.session_manager.edit_page(idx, original_img)
        if idx in self.page_crop_rects:
            del self.page_crop_rects[idx]
        if idx in self.page_rotation:
            del self.page_rotation[idx]
        if idx in self.page_bw_state:
            del self.page_bw_state[idx]
        self.pending_crop_rect = None
        self.preview_image = None
        self.select_page(idx)
        self.status_bar.configure(text="Page reset")

    # def quick_card_crop(self):
    #     if self.preview_image is None:
    #         messagebox.showwarning("No Image", "No image to crop")
    #         return

    #     self.save_state_for_undo()

    #     img_w, img_h = self.preview_image.size

    #     target_ratio = 1.586

    #     if img_w > img_h:
    #         card_w = int(img_w * 0.6)
    #         card_h = int(card_w / target_ratio)
    #     else:
    #         card_h = int(img_h * 0.45)
    #         card_w = int(card_h * target_ratio)

    #     x = (img_w - card_w) // 2
    #     y = (img_h - card_h) // 2

    #     self.pending_crop_rect = (x, y, card_w, card_h)

    #     idx = self.current_page_index
    #     angle = self.page_rotation.get(idx, 0)

    #     original_size = self.session_manager.get_page_original(idx).size

    #     self.page_crop_rects[idx] = self.transform_rect_to_original(
    #         self.pending_crop_rect,
    #         original_size,
    #         angle
    #     )

    #     self.draw_crop_rect_overlay()

    #     self.status_bar.configure(
    #         text="Quick card crop applied. Adjust rectangle then click Apply Crop"
    #     )
    
    def quick_card_crop(self):
        if self.preview_image is None:
            messagebox.showwarning("No Image", "No image to crop")
            return

        self.save_state_for_undo()

        img_w, img_h = self.preview_image.size

        # Standard card ratio (ID-1 / CR80 card)
        target_ratio = 1.586  # width / height

        # ---- FIXED MARGIN FACTOR (key improvement) ----
        # This ensures crop is not too tight and always adjustable
        margin_factor = 0.75  # 75% of available space

        # Decide max usable area with margin
        usable_w = int(img_w * margin_factor)
        usable_h = int(img_h * margin_factor)

        # Fit card inside usable area while maintaining aspect ratio
        if usable_w / usable_h > target_ratio:
            # height is limiting factor
            card_h = usable_h
            card_w = int(card_h * target_ratio)
        else:
            # width is limiting factor
            card_w = usable_w
            card_h = int(card_w / target_ratio)

        # Center crop
        x = (img_w - card_w) // 2
        y = (img_h - card_h) // 2

        self.pending_crop_rect = (x, y, card_w, card_h)

        idx = self.current_page_index
        angle = self.page_rotation.get(idx, 0)

        original_size = self.session_manager.get_page_original(idx).size

        # Map to original image space (rotation-safe)
        self.page_crop_rects[idx] = self.transform_rect_to_original(
            self.pending_crop_rect,
            original_size,
            angle
        )

        self.draw_crop_rect_overlay()

        self.status_bar.configure(
            text="Standard card crop applied (adjustable with margin)"
        )

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def save_state_for_undo(self):
        idx = self.current_page_index
        if idx < 0 or idx >= self.session_manager.page_count():
            return
        state = {
            'crop_rect': self.page_crop_rects.get(idx, None),
            'rotation': self.page_rotation.get(idx, 0),
            'bw': self.page_bw_state.get(idx, False)
        }
        if idx not in self.undo_stacks:
            self.undo_stacks[idx] = []
        if idx not in self.redo_stacks:
            self.redo_stacks[idx] = []
        self.undo_stacks[idx].append(copy.deepcopy(state))
        if len(self.undo_stacks[idx]) > 50:
            self.undo_stacks[idx].pop(0)
        self.redo_stacks[idx].clear()

    def undo(self):
        idx = self.current_page_index
        if idx < 0 or idx >= self.session_manager.page_count():
            messagebox.showinfo("Undo", "No page selected")
            return
        if idx not in self.undo_stacks or not self.undo_stacks[idx]:
            messagebox.showinfo("Undo", "Nothing to undo")
            return
        current = {
            'crop_rect': self.page_crop_rects.get(idx, None),
            'rotation': self.page_rotation.get(idx, 0),
            'bw': self.page_bw_state.get(idx, False)
        }
        self.redo_stacks[idx].append(copy.deepcopy(current))
        prev = self.undo_stacks[idx].pop()
        if prev['crop_rect'] is not None:
            self.page_crop_rects[idx] = prev['crop_rect']
        elif idx in self.page_crop_rects:
            del self.page_crop_rects[idx]
        self.page_rotation[idx] = prev['rotation']
        self.page_bw_state[idx] = prev['bw']
        self.select_page(idx)
        self.status_bar.configure(text="Undo")

    def redo(self):
        idx = self.current_page_index
        if idx < 0 or idx >= self.session_manager.page_count():
            messagebox.showinfo("Redo", "No page selected")
            return
        if idx not in self.redo_stacks or not self.redo_stacks[idx]:
            messagebox.showinfo("Redo", "Nothing to redo")
            return
        current = {
            'crop_rect': self.page_crop_rects.get(idx, None),
            'rotation': self.page_rotation.get(idx, 0),
            'bw': self.page_bw_state.get(idx, False)
        }
        self.undo_stacks[idx].append(copy.deepcopy(current))
        nxt = self.redo_stacks[idx].pop()
        if nxt['crop_rect'] is not None:
            self.page_crop_rects[idx] = nxt['crop_rect']
        elif idx in self.page_crop_rects:
            del self.page_crop_rects[idx]
        self.page_rotation[idx] = nxt['rotation']
        self.page_bw_state[idx] = nxt['bw']
        self.select_page(idx)
        self.status_bar.configure(text="Redo")

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------
    def import_images(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if not files:
            return
        for f in files:
            try:
                img = Image.open(f).convert("RGB")
                self.session_manager.add_page(img)
                idx = self.session_manager.page_count() - 1
                self.original_images[idx] = img.copy()
                self.page_rotation[idx] = 0
                self.undo_stacks[idx] = []
                self.redo_stacks[idx] = []
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to load {os.path.basename(f)}: {str(e)}")
        self.refresh_thumbnails()
        if self.session_manager.page_count() > 0:
            self.select_page(0)

    def save_all(self):
        if self.session_manager.page_count() == 0:
            messagebox.showwarning("No data", "Nothing to save")
            return
        # Apply any pending crop rectangles (convert to permanent crop)
        for idx, rect in self.page_crop_rects.items():
            if idx < self.session_manager.page_count():
                original_img = self.session_manager.get_page_original(idx)
                x, y, w, h = rect
                if w > 0 and h > 0:
                    if x + w > original_img.width:
                        w = original_img.width - x
                    if y + h > original_img.height:
                        h = original_img.height - y
                    if w > 0 and h > 0:
                        cropped = original_img.crop((x, y, x + w, y + h))
                        self.session_manager.replace_original(idx, cropped)
        self.page_crop_rects.clear()
        self.pending_crop_rect = None
        family = self.family_combo.get()
        doc_type = self.doc_combo.get()
        try:
            out = self.exporter.export_session(self.session_manager, family, doc_type)
            messagebox.showinfo("Success", f"Saved to:\n{out}")
            self.session_manager.mark_saved()
            self.status_bar.configure(text=f"Exported to {out}")
            self.refresh_thumbnails()
            if self.current_page_index >= 0:
                self.select_page(self.current_page_index)
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ------------------------------------------------------------------
    # Zoom & mouse
    # ------------------------------------------------------------------
    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.update_canvas_image()

    def zoom_out(self):
        self.zoom_factor /= 1.2
        self.update_canvas_image()

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def clear_preview(self):
        self.preview_image = None
        self.canvas.delete("all")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def bind_shortcuts(self):
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-s>", lambda e: self.save_all())
        self.root.bind("<Control-r>", lambda e: self.reset_current_page())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())

    def update_theme(self, new_theme):
        self.current_theme = new_theme
        if new_theme == "Dark":
            ctk.set_default_color_theme("blue")
        else:
            ctk.set_default_color_theme("green")
        colors = self.get_theme_colors()
        self.root.configure(fg_color=colors["bg"])
        for w in self.main_frame.winfo_children():
            w.destroy()
        self.build_ui()
        self.refresh_scanner_list()
        if self.current_page_index >= 0:
            self.select_page(self.current_page_index)

    def open_settings(self):
        SettingsDialog(self.root, self, self.settings, self.save_settings, None, self.current_theme)

    # ------------------------------------------------------------------
    # Convenience methods for move buttons
    # ------------------------------------------------------------------
    def move_selected_up(self):
        if self.current_page_index > 0:
            self.move_page_up(self.current_page_index)

    def move_selected_down(self):
        if self.current_page_index < self.session_manager.page_count() - 1:
            self.move_page_down(self.current_page_index)

    def move_selected_to_top(self):
        if self.current_page_index > 0:
            self.move_page_to_top(self.current_page_index)

    def move_selected_to_bottom(self):
        if self.current_page_index < self.session_manager.page_count() - 1:
            self.move_page_to_bottom(self.current_page_index)
            
        def on_scanner_changed(self):
            def task():
                alive = self.is_scanner_alive()

                if alive:
                    self.scanner_available = True
                    self._ui_set_status("📷 Scanner: Ready ✅")
                else:
                    self._set_scanner_off()

            threading.Thread(target=task, daemon=True).start()
    
    def start_scanner_health_check(self):
        def loop():
            def check():
                try:
                    alive = self.is_scanner_alive()

                    if not alive and self.scanner_available:
                        self.scanner_available = False
                        self._set_scanner_off()
                except:
                    pass

                self.root.after(4000, check)  # runs every 4 sec safely

            self.root.after(4000, check)

        import threading
        threading.Thread(target=loop, daemon=True).start()