import tkinter as tk
from tkinter import ttk, messagebox
import threading
from ui.theme import Colors

class HandsOnSetupDialog(tk.Toplevel):
    """
    Initial configuration dialog for the Hands-on approach.
    Explains the process and runs initial automatch.
    """
    def __init__(self, parent, controller, preset_names, on_complete_callback):
        super().__init__(parent)
        self.title("Hands-on Mastering Setup")
        self.geometry("500x400")
        self.configure(bg=Colors.BG_PANEL)
        self.resizable(False, False)
        
        self.controller = controller
        self.preset_names = preset_names
        self.on_complete_callback = on_complete_callback
        
        # Initialize UI attributes for static analysis
        self.preset_combo = None
        self.prog_frame = None
        self.prog_label = None
        self.progress = None
        self.start_btn = None
        
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header Message
        ttk.Label(self, text="Setting Your Starting Point", 
                  style="Panel.TLabel", font=("Segoe UI", 14, "bold")).pack(pady=(30, 10))
        
        msg = ("This setup will analyze your track and apply an initial\n"
               "genre-based preset with automatic loudness matching.\n\n"
               "Think of this as a professional starting point—you can\n"
               "adjust every single parameter once we're done.")
        
        ttk.Label(self, text=msg, style="Panel.TLabel", justify=tk.CENTER).pack(pady=10)
        
        # Preset Selection
        selection_frame = ttk.Frame(self, style="Panel.TFrame")
        selection_frame.pack(pady=20)
        
        ttk.Label(selection_frame, text="Select Starter Preset:", style="Panel.TLabel").pack(side=tk.LEFT, padx=10)
        self.preset_combo = ttk.Combobox(selection_frame, values=self.preset_names, state="readonly", width=25)
        if self.preset_names:
            self.preset_combo.set(self.preset_names[0])
        self.preset_combo.pack(side=tk.LEFT)
        
        # Progress Section (Hidden initially)
        self.prog_frame = ttk.Frame(self, style="Panel.TFrame")
        self.prog_label = ttk.Label(self.prog_frame, text="Analyzing track dynamics...", style="Panel.TLabel")
        self.prog_label.pack(pady=(0, 5))
        self.progress = ttk.Progressbar(self.prog_frame, length=300, mode='determinate')
        self.progress.pack()
        
        # Action Button
        self.start_btn = ttk.Button(self, text="Initialize Mastering Engine", 
                                    style="ActiveToggle.TButton", command=self.run_setup)
        self.start_btn.pack(side=tk.BOTTOM, pady=40)

    def run_setup(self):
        selected_preset = self.preset_combo.get()
        if not selected_preset:
            messagebox.showwarning("Selection Required", "Please select a starter preset.")
            return
            
        self.start_btn.config(state="disabled")
        self.preset_combo.config(state="disabled")
        self.prog_frame.pack(pady=10)
        
        # Run the setup task in a background thread
        threading.Thread(target=self._setup_task, args=(selected_preset,), daemon=True).start()
        
    def _setup_task(self, preset_name):
        try:
            # Step 1: Initialize the preset params
            self.after(0, lambda: self._update_progress(10, f"Loading {preset_name} preset..."))
            import time
            time.sleep(0.3)
            
            # Step 2: Trigger the actual loudness matching with a progress callback
            def on_match_progress(percent, text):
                self.after(0, lambda p=percent, t=text: self._update_progress(10 + p * 0.8, t))

            # Apply the preset first so loudness matching has the correct context (Air, Drive, etc.)
            # We call this on the UI thread to update the sliders safely
            self.after(0, lambda: self.controller.apply_preset_by_name(preset_name))
            time.sleep(0.2) # Small gap for UI update
            
            # Trigger the loudness analysis (must run in this thread or another non-main thread)
            # We use a blocking version for simplicity inside this thread
            final_gain, final_lufs = self.controller.perform_auto_match_sync(progress_callback=on_match_progress)
            
            # Step 3: Finalizing and showing the required pop-up BEFORE closing
            self.after(0, lambda: self._update_progress(100, "Optimization Complete!"))
            
            # We show the message box while still on the 'Setting your starting point' screen.
            # This is the 'hold' the user requested.
            msg = f"Gain adjusted to {final_gain:.1f} dB\nto hit {final_lufs:.1f} LUFS."
            messagebox.showinfo("Loudness Match", msg, parent=self)
            
            # Finalize transition only AFTER the user clicks OK on the pop-up
            self.after(0, lambda: self.on_complete_callback(preset_name))
            self.after(100, self.destroy)
            
        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror("Setup Error", f"Failed to initialize:\n{msg}"))
            if self.start_btn:
                self.after(0, lambda: self.start_btn.config(state="normal"))
            if self.preset_combo:
                self.after(0, lambda: self.preset_combo.config(state="normal"))

    def _update_progress(self, value, text):
        self.progress['value'] = value
        self.prog_label.config(text=text)
        self.update_idletasks()
