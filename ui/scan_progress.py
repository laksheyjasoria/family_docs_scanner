import customtkinter as ctk

class ScanProgressPopup(ctk.CTkToplevel):
    def __init__(self, parent, title="Scanning..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x170")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.label = ctk.CTkLabel(self, text="Initializing...", font=("Segoe UI", 14))
        self.label.pack(pady=(20, 10))

        self.progress = ctk.CTkProgressBar(self, width=280, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start()

        self.cancel_btn = ctk.CTkButton(self, text="Cancel", fg_color="red", command=self._cancel)
        self.cancel_btn.pack(pady=15)

        self._cancel_callback = None
        self._destroyed = False

    def set_cancel_callback(self, callback):
        self._cancel_callback = callback

    def set_status(self, text):
        if not self._destroyed:
            try:
                self.label.configure(text=text)
            except:
                pass

    def set_progress(self, value):
        """value: 0-100 integer or float"""
        if not self._destroyed:
            try:
                if self.progress.cget("mode") == "indeterminate":
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                self.progress.set(value / 100.0)
            except:
                pass

    def _cancel(self):
        if self._cancel_callback:
            self._cancel_callback()
        self._destroy()

    def _on_close(self):
        # User clicked the X – treat as cancel
        if self._cancel_callback:
            self._cancel_callback()
        self._destroy()

    def _destroy(self):
        if not self._destroyed:
            self._destroyed = True
            try:
                self.grab_release()
                self.destroy()
            except:
                pass