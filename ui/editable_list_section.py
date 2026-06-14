import customtkinter as ctk

class EditableListSection(ctk.CTkFrame):
    def __init__(self, parent, title, get_items,
                 on_add, on_remove, on_update):
        super().__init__(parent, fg_color="transparent")
        self.get_items = get_items
        self.on_add = on_add
        self.on_remove = on_remove
        self.on_update = on_update
        self._build_ui(title)

    def _build_ui(self, title):
        ctk.CTkLabel(self, text=title, font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))

        # Add row
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        self.entry = ctk.CTkEntry(row)
        self.entry.grid(row=0, column=0, sticky="ew", padx=5)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(row, text="➕", width=40, fg_color="#2E7D32", hover_color="#1B5E20",
                      command=self.add_item).grid(row=0, column=1)

        # List container
        self.list_frame = ctk.CTkScrollableFrame(self, height=150)
        self.list_frame.pack(fill="x", pady=5)
        self.refresh()

    def _normalize(self, text):
        return text.strip().title()

    def _exists(self, value):
        return any(v.lower() == value.lower() for v in self.get_items())

    def add_item(self):
        value = self._normalize(self.entry.get())
        if not value or self._exists(value):
            return
        self.on_add(value)
        self.entry.delete(0, "end")
        self.refresh()

    def remove_item(self, value):
        self.on_remove(value)
        self.refresh()

    def update_item(self, old, new):
        new = self._normalize(new)
        if not new or new.lower() == old.lower() or self._exists(new):
            self.refresh()
            return
        self.on_update(old, new)
        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        for item in self.get_items():
            row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)

            label = ctk.CTkLabel(row, text=item, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=5)

            entry = ctk.CTkEntry(row)
            entry.insert(0, item)

            def start_edit(e, old=item):
                label.grid_forget()
                entry.grid(row=0, column=0, sticky="ew", padx=5)
                entry.focus_set()

            def save_edit(e=None, old=item):
                new_val = entry.get()
                self.update_item(old, new_val)

            label.bind("<Double-Button-1>", start_edit)
            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)

            # Delete button
            ctk.CTkButton(row, text="🗑", width=35, fg_color="#D32F2F", hover_color="#B71C1C",
                          command=lambda x=item: self.remove_item(x)).grid(row=0, column=1, padx=5)

            # Hover effect
            def on_enter(e, r=row):
                r.configure(fg_color="#2A2A3A")
            def on_leave(e, r=row):
                r.configure(fg_color="transparent")
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)