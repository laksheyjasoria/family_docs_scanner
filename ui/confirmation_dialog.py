import customtkinter as ctk

class ConfirmationDialog:
    @staticmethod
    def ask_save_discard_cancel(parent, message):
        dialog = ctk.CTkToplevel(parent)
        dialog.title("Unsaved Changes")
        dialog.geometry("400x150")
        dialog.grab_set()
        
        label = ctk.CTkLabel(dialog, text=message, wraplength=350)
        label.pack(pady=20)
        
        result = [None]
        
        def on_save():
            result[0] = "save"
            dialog.destroy()
        
        def on_discard():
            result[0] = "discard"
            dialog.destroy()
        
        def on_cancel():
            result[0] = "cancel"
            dialog.destroy()
        
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Save & Continue", command=on_save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Discard & Continue", command=on_discard).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)
        
        parent.wait_window(dialog)
        return result[0]
