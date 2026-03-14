import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import numpy as np
from ui.theme import Colors
from ui.components.detailed_waveform import DetailedWaveform
from ui.components.range_slider import RangeSlider

class PresetBattleDialog(tk.Toplevel):
    """Dialog to select up to 4 presets for comparison."""
    def __init__(self, parent, preset_names, on_start_callback):
        super().__init__(parent)
        self.title("Preset Battle - Select Challengers")
        self.geometry("400x500")
        self.preset_names = preset_names
        self.on_start_callback = on_start_callback
        self.selected_presets = []
        
        self.configure(bg=Colors.BG_MAIN)
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self, text="Select up to 4 presets to compare:", font=("Segoe UI", 12, "bold")).pack(pady=20)
        
        # Scrollable list of presets
        list_frame = ttk.Frame(self, style="Panel.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        self.vars = {}
        for name in self.preset_names:
            var = tk.BooleanVar()
            self.vars[name] = var
            chk = ttk.Checkbutton(list_frame, text=name, variable=var, command=self.check_limit)
            chk.pack(anchor="w", pady=2)

        btn_frame = ttk.Frame(self, style="Panel.TFrame")
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Spatial Enhancement Toggle
        self.spatial_var = tk.BooleanVar(value=True)
        self.spatial_chk = ttk.Checkbutton(btn_frame, text="Apply Pro Spatial Enhancements (Stereo Width + Mono Bass)", 
                                           variable=self.spatial_var)
        self.spatial_chk.pack(pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Battle!", state="disabled", command=self.on_start)
        self.start_btn.pack()

    def check_limit(self):
        selected = [name for name, var in self.vars.items() if var.get()]
        if len(selected) > 4:
            # Uncheck the last one
            messagebox.showwarning("Limit Reached", "You can only compare up to 4 presets at once.")
            return
        
        self.selected_presets = selected
        if len(selected) > 0:
            self.start_btn.config(state="normal")
        else:
            self.start_btn.config(state="disabled")

    def on_start(self):
        output_dir = filedialog.askdirectory(title="Choose Output Folder for Masters")
        if output_dir:
            self.on_start_callback(self.selected_presets, output_dir, self.spatial_var.get())
            self.destroy()

class BatchProgressWindow(tk.Toplevel):
    """Mini window showing progress during mastering."""
    def __init__(self, parent, on_cancel):
        super().__init__(parent)
        self.title("Mastering in Progress...")
        self.geometry("350x150")
        self.on_cancel = on_cancel
        self.configure(bg=Colors.BG_PANEL)
        
        self.transient(parent)
        self.grab_set()
        
        self.label = ttk.Label(self, text="Initializing...")
        self.label.pack(pady=10)
        
        self.progress = ttk.Progressbar(self, length=250, mode='determinate')
        self.progress.pack(pady=10)
        
        ttk.Button(self, text="Cancel", command=self.cancel).pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def update_progress(self, text, value):
        self.label.config(text=text)
        self.progress['value'] = value
        self.update()

    def cancel(self):
        if messagebox.askyesno("Cancel?", "Are you sure you want to stop the batch process?"):
            self.on_cancel()
            self.destroy()

class ComparisonConsole(tk.Toplevel):
    """Full screen window to compare multiple mastered versions synced."""
    def __init__(self, parent, audio_data_dict, sample_rate, controller):
        """
        audio_data_dict: { 'Original': data, 'PresetName': data, ... }
        """
        super().__init__(parent)
        self.title("Comparison Console - Sync Playback")
        self.geometry("1100x800")
        self.audio_dict = audio_data_dict
        self.sample_rate = sample_rate
        self.controller = controller
        
        self.active_version = "Original"
        self.is_playing = False
        self.current_frame = 0 # Sync point
        
        self.configure(bg=Colors.BG_MAIN)
        
        # Initial Loading State
        self.loading_frame = tk.Frame(self, bg=Colors.BG_MAIN)
        self.loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(self.loading_frame, text="Analyzing Audio & Building Waveforms...", 
                 fg="#FFFFFF", bg=Colors.BG_MAIN, font=("Segoe UI", 14, "italic")).pack(expand=True)
        
        # Setup UI layout (will be hidden by loading_frame initially)
        self.setup_ui()
        
        # Load audio data asynchronously to show the loading marker
        self.after(100, self.async_load_waveforms)

    def setup_ui(self):
        # Header
        ttk.Label(self, text="SYNCED MASTER COMPARISON", font=("Segoe UI", 16, "bold")).pack(pady=20)
        
        main_scroll_canvas = tk.Canvas(self, bg=Colors.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_scroll_canvas.yview)
        scroll_frame = ttk.Frame(main_scroll_canvas, style="Main.TFrame")
        
        scroll_frame.bind("<Configure>", lambda e: main_scroll_canvas.configure(scrollregion=main_scroll_canvas.bbox("all")))
        main_scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=1050)
        main_scroll_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_scroll_canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")

        # --- Loop Marker Section (At the top of the comparison) ---
        loop_frame = ttk.Frame(scroll_frame, style="Panel.TFrame")
        loop_frame.pack(fill=tk.X, padx=10, pady=(10, 20))
        ttk.Label(loop_frame, text="Battle Loop Region:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.loop_slider = RangeSlider(loop_frame, height=25)
        self.loop_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.loop_slider.on_change_callback = self.on_loop_change

        self.waveforms = {}
        self.solo_btns = {}
        
        # Row for each audio file (Placeholders first)
        for name in self.audio_dict.keys():
            row = ttk.Frame(scroll_frame, style="Panel.TFrame")
            row.pack(fill=tk.X, pady=10)
            
            info_frame = ttk.Frame(row, width=150)
            info_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
            info_frame.pack_propagate(False)
            
            ttk.Label(info_frame, text=name, font=("Segoe UI", 10, "bold")).pack(pady=5)
            
            btn = ttk.Button(info_frame, text="SOLO", command=lambda n=name: self.solo(n))
            btn.pack(pady=5)
            self.solo_btns[name] = btn
            
            if name == "Original":
                btn.config(style="ActiveToggle.TButton")
            
            wave = DetailedWaveform(row, height=120, color="#FF8C00" if name=="Original" else "#00D2FF")
            wave.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            # Make it clickable to seek
            wave.bind("<Button-1>", self.on_seek) 
            self.waveforms[name] = wave

        # Footer controls
        footer = ttk.Frame(self, style="Header.TFrame", height=80)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.play_btn = ttk.Button(footer, text="▶ PLAY ALL (SYNCED)", command=self.toggle_play)
        self.play_btn.pack(pady=20)

    def solo(self, name):
        self.active_version = name
        # Update UI
        for k, b in self.solo_btns.items():
            b.config(style="ActiveToggle.TButton" if k == name else "TButton")
        
        # Swapping buffer in player without resetting current_frame
        buffer = self.audio_dict[name]
        # We use a hacky direct access to the player in controller or a dedicated secondary player
        # Let's say we use a dedicated player for this window since main window might be open
        from engine.io.playback import AudioPlayer
        if not hasattr(self, 'player'):
            self.player = AudioPlayer()
        
        self.player.set_buffer(buffer, self.sample_rate)
        self.player.current_frame = self.current_frame

    def toggle_play(self):
        if not hasattr(self, 'player'):
            self.player = AudioPlayer()
            self.solo(self.active_version) # Init buffer
            
        if self.player.is_playing:
            self.player.stop()
            self.play_btn.config(text="▶ PLAY ALL (SYNCED)")
        else:
            self.player.play()
            self.play_btn.config(text="⏹ STOP")

    def on_seek(self, event):
        w = event.widget.winfo_width()
        progress = event.x / w
        
        total_frames = len(self.audio_dict["Original"])
        self.current_frame = int(progress * total_frames)
        
        if hasattr(self, 'player'):
            self.player.current_frame = self.current_frame
        
        self.update_waveforms()

    def update_waveforms(self):
        total_frames = len(self.audio_dict["Original"])
        progress = self.current_frame / total_frames if total_frames > 0 else 0
        for w in self.waveforms.values():
            w.set_progress(progress)

    def async_load_waveforms(self):
        """Processes waveforms and removes loading screen."""
        for i, (name, data) in enumerate(self.audio_dict.items()):
            self.waveforms[name].update_data(data)
            self.update() # Keep UI alive
            
        # Remove loading screen
        if hasattr(self, 'loading_frame'):
            self.loading_frame.destroy()
            
        # Start the sync loop
        self.update_loop()

    def on_loop_change(self, start, end):
        if not hasattr(self, 'player'):
            from engine.io.playback import AudioPlayer
            self.player = AudioPlayer()
            self.solo(self.active_version) # Init buffer
            
        total_frames = len(self.audio_dict["Original"])
        self.player.loop_start = int(start * total_frames)
        self.player.loop_end = int(end * total_frames)

    def update_loop(self):
        if hasattr(self, 'player') and self.player.is_playing:
            self.current_frame = self.player.current_frame
            self.update_waveforms()
            
        self.after(30, self.update_loop)
