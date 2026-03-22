import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import numpy as np
from ui.theme import Colors
from ui.components.detailed_waveform import DetailedWaveform
from ui.components.range_slider import RangeSlider
from ui.components.meter import LevelMeter, LufsMeter, DbScale
from engine.io import preset_manager
import json

class CustomCompareDialog(tk.Toplevel):
    def __init__(self, parent, start_callback):
        super().__init__(parent)
        self.parent = parent
        self.title("Custom Track Match")
        self.geometry("600x400")
        self.configure(bg=Colors.BG_MAIN)
        self.grab_set()
        
        self.start_callback = start_callback
        self.file_vars = [tk.StringVar() for _ in range(4)]
        
        container = tk.Frame(self, bg=Colors.BG_MAIN)
        container.pack(expand=True, fill=tk.BOTH, padx=30, pady=30)
        
        ttk.Label(container, text="Select Up to 4 Files to Compare", font=("Segoe UI", 16, "bold"), background=Colors.BG_MAIN, foreground="#FFF").pack(pady=(0, 20))
        
        for i in range(4):
            row = tk.Frame(container, bg=Colors.BG_MAIN)
            row.pack(fill=tk.X, pady=10)
            
            lbl = ttk.Label(row, text=f"Track {i+1}:", font=("Segoe UI", 10, "bold"), background=Colors.BG_MAIN, foreground="#FFF", width=10)
            lbl.pack(side=tk.LEFT)
            
            entry = ttk.Entry(row, textvariable=self.file_vars[i], state="readonly")
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            btn = ttk.Button(row, text="Browse", command=lambda idx=i: self.browse_file(idx))
            btn.pack(side=tk.RIGHT)
            
        btn_frame = tk.Frame(container, bg=Colors.BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=30)
        
        self.go_btn = ttk.Button(btn_frame, text="Start Match", style="ActiveToggle.TButton", state="disabled", command=self.on_go)
        self.go_btn.pack(side=tk.RIGHT)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=10)
        
    def on_cancel(self):
        self.parent.deiconify()
        self.destroy()
        
    def browse_file(self, idx):
        path = filedialog.askopenfilename(title=f"Select Track {idx+1}", filetypes=[("Audio Files", "*.wav *.flac *.mp3 *.ogg")])
        if path:
            self.file_vars[idx].set(path)
            self.check_files()
            
    def check_files(self):
        count = sum(1 for v in self.file_vars if v.get())
        if count >= 2:
            self.go_btn.config(state="normal")
        else:
            self.go_btn.config(state="disabled")
            
    def on_go(self):
        paths = [v.get() for v in self.file_vars if v.get()]
        self.destroy()
        self.start_callback(paths)

class PresetBattleDialog(tk.Toplevel):
    """Dialog to select up to 4 presets for comparison."""
    def __init__(self, parent, preset_names, on_start_callback):
        super().__init__(parent)
        self.title("Preset Battle - Select Challengers")
        self.preset_names = preset_names
        self.on_start_callback = on_start_callback
        self.selected_presets = []
        self.presets_data = preset_manager.load_presets().get("presets", {})
        
        self.configure(bg=Colors.BG_MAIN)
        self.grab_set()

        # --- Smart Sizing ---
        # Calculate height based on rows needed (2 presets per row)
        HEADER_H = 80   # title
        FOOTER_H = 130  # spatial check + button + padding
        ROW_H    = 42   # height of each preset row (with padding)
        n_rows   = (len(preset_names) + 1) // 2
        ideal_h  = HEADER_H + (n_rows * ROW_H) + FOOTER_H

        # Cap at 90% of screen height 
        screen_h = self.winfo_screenheight()
        max_h    = int(screen_h * 0.90)
        win_h    = min(ideal_h, max_h)
        
        self.needs_scroll = ideal_h > max_h  # Only scroll if content overflows
        
        self.geometry(f"660x{win_h}")
        self.resizable(False, True)
        
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self, text="Select up to 4 presets to compare:", font=("Segoe UI", 12, "bold")).pack(pady=20)
        
        # Bottom controls packed FIRST to anchor them at the bottom
        btm_frame = ttk.Frame(self, style="Panel.TFrame")
        btm_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=20)
        
        # Spatial Enhancement Toggle
        self.spatial_var = tk.BooleanVar(value=True)
        spatial_chk = ttk.Checkbutton(btm_frame, text="Apply Pro Spatial Enhancements (Stereo Width + Mono Bass)", 
                                           variable=self.spatial_var)
        spatial_chk.pack(pady=5)
        
        # Center the start button
        self.start_btn = ttk.Button(btm_frame, text="Start Battle!", state="disabled", command=self.on_start)
        self.start_btn.pack(pady=10)

        # Main content area uses remaining space
        content_frame = tk.Frame(self, bg=Colors.BG_MAIN)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Scrollable area for many presets
        canvas = tk.Canvas(content_frame, bg=Colors.BG_MAIN, highlightthickness=0)
        scroll_frame = ttk.Frame(canvas, style="Panel.TFrame")
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        if self.needs_scroll:
            scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas_w = 580  # slightly narrower to leave room for scrollbar
            
            # Mousewheel only active when scroll is needed
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            canvas_w = 620  # full width, no scrollbar
        
        canvas.create_window((0,0), window=scroll_frame, anchor="nw", width=canvas_w)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Grid frame for presets inside scroll_frame
        list_grid = ttk.Frame(scroll_frame, style="Panel.TFrame")
        list_grid.pack(fill=tk.BOTH, expand=True)
        
        list_grid.columnconfigure(0, weight=1)
        list_grid.columnconfigure(1, weight=1)
        
        from ui.components.tooltip import ToolTip
        
        self.vars = {}
        for i, name in enumerate(self.preset_names):
            data = self.presets_data.get(name, {})
            is_custom = data.get("is_custom", False)
            
            # Container for each preset line to allow delete button
            item_frame = tk.Frame(list_grid, bg=Colors.BG_PANEL)
            row = i // 2
            col = i % 2
            item_frame.grid(row=row, column=col, sticky="nsew", pady=5, padx=10)
            
            var = tk.BooleanVar()
            self.vars[name] = var
            
            # Use different color for custom presets
            text_color = "#00D2FF" if is_custom else Colors.TEXT_PRIMARY
            
            chk = tk.Checkbutton(item_frame, text=name, variable=var, 
                                 bg=Colors.BG_PANEL, fg=text_color, 
                                 selectcolor=Colors.BG_HEADER,
                                 activebackground=Colors.BG_PANEL,
                                 activeforeground=text_color,
                                 font=("Segoe UI", 10),
                                 command=lambda n=name: self.check_limit(n))
            chk.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            if is_custom:
                # Add small delete button only for custom presets
                del_btn = tk.Button(item_frame, text="✕", font=("Segoe UI", 7, "bold"),
                                   bg="#444444", fg="#FF4444", borderwidth=0,
                                   command=lambda n=name: self.delete_preset_ui(n))
                del_btn.pack(side=tk.RIGHT, padx=5)
                ToolTip(del_btn, f"Delete custom preset: {name}")

    def delete_preset_ui(self, name):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the '{name}' preset?"):
            if preset_manager.delete_preset(name):
                # Refresh UI
                self.preset_names.remove(name)
                # Cleanup and rebuild - simplest way to refresh a complex scrollable grid
                for widget in self.winfo_children():
                    widget.destroy()
                self.selected_presets = []
                self.vars = {}
                self.presets_data = preset_manager.load_presets().get("presets", {})
                self.setup_ui()

    def check_limit(self, changed_name):
        selected = [name for name, var in self.vars.items() if var.get()]
        if len(selected) > 4:
            # Uncheck the one that just tipped us over
            messagebox.showwarning("Limit Reached", "You can only compare up to 4 presets at once.")
            self.vars[changed_name].set(False)
            selected.remove(changed_name)
            
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
        self.geometry("350x180")
        self.on_cancel = on_cancel
        self.configure(bg=Colors.BG_PANEL)
        self.grab_set()
        
        self.label = ttk.Label(self, text="Initializing...")
        self.label.pack(pady=10)
        
        self.progress = ttk.Progressbar(self, length=250, mode='determinate')
        self.progress.pack(pady=5)
        
        ttk.Button(self, text="Cancel", command=self.cancel).pack(pady=5)
        
        self.cheeky_var = tk.StringVar()
        self.cheeky_label = ttk.Label(self, textvariable=self.cheeky_var, font=("Segoe UI", 9, "italic"), foreground=Colors.TEXT_SECONDARY)
        self.cheeky_label.pack(pady=(5, 10))
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        import json
        import os
        msg_file = os.path.join(os.path.dirname(__file__), '..', '..', 'loading_messages.json')
        try:
            with open(msg_file, 'r') as f:
                self.cheeky_messages = json.load(f)
        except Exception:
            self.cheeky_messages = ["Mastering in progress..."]
            
        self.update_cheeky()
        
    def update_cheeky(self):
        import random
        if self.winfo_exists():
            self.cheeky_var.set(random.choice(self.cheeky_messages))
            self.after(5000, self.update_cheeky)

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
    def __init__(self, parent, audio_data_dict, sample_rate, controller, output_dir=""):
        """
        audio_data_dict: { 'Original': data, 'PresetName': data, ... }
        """
        super().__init__(parent)
        self.output_dir = output_dir
        self.title("Comparison Console - Sync Playback")
        # Widen to 1400px and center on screen
        width, height = 1400, 850
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.audio_dict = audio_data_dict
        self.sample_rate = sample_rate
        self.controller = controller
        
        self.active_version = "Original"
        self.is_playing = False
        self.current_frame = 0 # Sync point
        
        self.metering_dict = {} # Low-res buffers for CPU-friendly metering
        self.meter_sample_rate = 4000 # 4kHz is plenty for a visual meter
        
        self.win_btns = {}
        
        self.configure(bg=Colors.BG_MAIN)
        
        # Stop playback on red X exit
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Setup UI layout directly
        self.setup_ui()
        # Load audio data asynchronously
        self.after(100, self.async_load_waveforms)

    def on_close(self):
        if hasattr(self, 'player') and self.player.is_playing:
            self.player.stop()
        self.destroy()
        self.controller.view.deiconify()

    def declare_winner(self, winner_name):
        """Called when a user picks a winner. Gives options to keep or delete losing masters."""
        
        # Stop playback aggressively so it isn't playing while looking at the popups
        if hasattr(self, 'player') and self.player.is_playing:
            self.player.stop()
            if self.winfo_exists():
                self.play_btn.config(text="▶ PLAY ALL")
                
        # If output_dir is empty, this is a custom comparison mode, no file operations needed.
        if not self.output_dir:
            messagebox.showinfo("Winner Selected!", f"You selected '{winner_name}' as the winner!", parent=self)
            self.on_close()
            return
            
        msg = f"You chose '{winner_name}' as the winner!\n\nDo you want to keep all the newly generated masters, or permanently delete the losing masters?\n\n(The Original track is completely safe regardless)"
        
        from tkinter.messagebox import askyesnocancel
        # Yes = Keep All, No = Delete Losers, Cancel = Back
        answer = askyesnocancel("Select Battle Winner", msg + "\n\nYES = Keep All & Rename Winner\nNO = Delete Losers & Rename Winner\nCANCEL = Back to Comparison", parent=self)
        
        if answer is None:
            return
            
        keep_all = answer
        
        if hasattr(self, 'player') and self.player.is_playing:
            self.player.stop()
            
        try:
            for name in self.audio_dict.keys():
                if name == "Original":
                    continue
                    
                safe_name = "".join([c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name])
                filename = f"Master_{safe_name.replace(' ', '_')}.wav"
                file_path = os.path.join(self.output_dir, filename)
                
                if name == winner_name:
                    # Rename winner clearly
                    winner_filename = f"WINNER_{filename}"
                    winner_path = os.path.join(self.output_dir, winner_filename)
                    if os.path.exists(file_path):
                        os.rename(file_path, winner_path)
                else:
                    if not keep_all:
                        # User wants to trace out losers
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            
            messagebox.showinfo("Battle Concluded!", f"Winner successfully designated!\nFiles managed at:\n{self.output_dir}", parent=self)
            
            # Open the folder where the winners are saved
            import platform, subprocess
            if platform.system() == "Windows":
                os.startfile(self.output_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", self.output_dir])
            else:
                subprocess.Popen(["xdg-open", self.output_dir])
                
            self.destroy()
            self.controller.view.deiconify() # Restore the app instead of closing it
        except Exception as e:
            messagebox.showerror("Error Saving Master Files", f"Could not cleanly finish file management:\n{e}", parent=self)

    def setup_ui(self):
        # Header
        ttk.Label(self, text="SYNCED MASTER COMPARISON", font=("Segoe UI", 16, "bold")).pack(pady=20)
        
        # --- Initialize Scrollable Area ---
        main_scroll_canvas = tk.Canvas(self, bg=Colors.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_scroll_canvas.yview)
        scroll_frame = ttk.Frame(main_scroll_canvas, style="Main.TFrame")
        
        # Make the scroll frame expand to the full width of the canvas dynamically
        def _on_canvas_configure(e):
            main_scroll_canvas.itemconfig(frame_id, width=e.width)
        
        frame_id = main_scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        main_scroll_canvas.bind("<Configure>", _on_canvas_configure)
        
        scroll_frame.bind("<Configure>", lambda e: main_scroll_canvas.configure(scrollregion=main_scroll_canvas.bbox("all")))
        main_scroll_canvas.configure(yscrollcommand=scrollbar.set)
        
        # --- Right Panel: Meter Bridge (Static) ---
        # Pack Meter Bridge FIRST on the right to anchor it
        meter_bridge = ttk.Frame(self, style="Panel.TFrame", width=220)
        meter_bridge.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 20), pady=10)
        meter_bridge.pack_propagate(False)
        
        ttk.Label(meter_bridge, text="READY LEVELS", font=("Segoe UI", 10, "bold")).pack(pady=10)
        
        meters_inner = ttk.Frame(meter_bridge, style="Panel.TFrame")
        meters_inner.pack(fill=tk.BOTH, expand=True)
        
        # L Meter
        l_frame = ttk.Frame(meters_inner, style="Panel.TFrame")
        l_frame.pack(side=tk.LEFT, expand=True)
        self.meter_l = LevelMeter(l_frame, height=250, width=20)
        self.meter_l.pack()
        ttk.Label(l_frame, text="L", font=("Segoe UI", 8, "bold")).pack()
        
        # Scale
        s_frame = ttk.Frame(meters_inner, style="Panel.TFrame")
        s_frame.pack(side=tk.LEFT, pady=(0, 20))
        self.scale = DbScale(s_frame, height=250, width=30)
        self.scale.pack()
        
        # LUFS Meter
        self.meter_lufs = LufsMeter(meters_inner, label="INTEGRATED")
        self.meter_lufs.pack(side=tk.LEFT, expand=True, padx=2)
        self.meter_lufs.meter.config(height=250, width=35)
        
        # R Meter
        r_frame = ttk.Frame(meters_inner, style="Panel.TFrame")
        r_frame.pack(side=tk.LEFT, expand=True)
        self.meter_r = LevelMeter(r_frame, height=250, width=20)
        self.meter_r.pack()
        ttk.Label(r_frame, text="R", font=("Segoe UI", 8, "bold")).pack()

        # Play/Stop Button - Integrated into the Level Panel
        ctrl_frame = ttk.Frame(meter_bridge, style="Panel.TFrame")
        ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        
        style = ttk.Style()
        if "FlashRed.TButton" not in style.theme_names():
            style.configure("FlashRed.TButton", background="#FF3333", foreground="white", font=("Segoe UI", 10, "bold"))
            
        self.play_btn = ttk.Button(ctrl_frame, text="▶ PLAY ALL", command=self.toggle_play, state="disabled")
        self.play_btn.pack(expand=True, padx=20, ipady=5)
        self.flash_state = False
        self.flash_loop_id = None
        
        # When user clicks the X button to close Comparison Console
        self.protocol("WM_DELETE_WINDOW", self.on_close_console)



        # Pack Scrollbar next to the meters
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Finally pack the canvas to fill all REMAINING space (Eliminates the gap)
        main_scroll_canvas.pack(side=tk.LEFT, fill="both", expand=True, padx=(20, 0), pady=(10, 0))


        # --- Loop Marker Section (At the top of the comparison) ---
        loop_row = ttk.Frame(scroll_frame, style="Panel.TFrame")
        loop_row.pack(fill=tk.X, pady=(10, 20))
        
        # Spacer to match the info_frame width (170px for buttons + padding)
        loop_info_spacer = ttk.Frame(loop_row, width=170, height=40) 
        loop_info_spacer.pack(side=tk.LEFT)
        loop_info_spacer.pack_propagate(False)
        
        ttk.Label(loop_info_spacer, text="Loop Range", font=("Segoe UI", 9, "bold")).pack(expand=True)
        
        self.loop_slider = RangeSlider(loop_row, height=30)
        self.loop_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5) # Match waveform padx
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
            
            btn = ttk.Button(info_frame, text="SOLO", command=lambda n=name: self.solo(n), state="disabled")
            btn.pack(pady=5)
            self.solo_btns[name] = btn
            
            if name == "Original":
                btn.config(style="ActiveToggle.TButton")
                win_frame = ttk.Frame(row, width=120)
                win_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 10))
                win_frame.pack_propagate(False)
                
                win_btn = ttk.Button(win_frame, text="Original", state="disabled")
                win_btn.pack(expand=True, fill=tk.BOTH, pady=10)
            else:
                win_frame = ttk.Frame(row, width=120)
                win_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 10))
                win_frame.pack_propagate(False)
                
                win_btn = ttk.Button(win_frame, text="🏆 WINNER", command=lambda n=name: self.declare_winner(n), state="disabled")
                win_btn.pack(expand=True, fill=tk.BOTH, pady=10)
                self.win_btns[name] = win_btn
            
            wave = DetailedWaveform(row, height=120, color="#FF8C00" if name=="Original" else "#00D2FF")
            wave.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            # Make it clickable to seek
            wave.bind("<Button-1>", self.on_seek) 
            self.waveforms[name] = wave

    def on_close_console(self):
        if hasattr(self, 'player') and self.player.is_playing:
            self.player.stop()
        self.destroy()
        self.controller.view.deiconify() # Restore the main view

    def solo(self, name):
        self.active_version = name
        # Update UI
        for k, b in self.solo_btns.items():
            b.config(style="ActiveToggle.TButton" if k == name else "TButton")
        
        # Buffer is already pre-cached as float32 in async_load_waveforms
        buffer = self.audio_dict[name]
        
        if not hasattr(self, 'player'):
            from engine.io.playback import AudioPlayer
            self.player = AudioPlayer()
        
        self.player.set_buffer(buffer, self.sample_rate)
        self.player.current_frame = self.current_frame

    def toggle_play(self):
        if not hasattr(self, 'player'):
            from engine.io.playback import AudioPlayer
            self.player = AudioPlayer()
            self.solo(self.active_version) # Init buffer
            
        if self.player.is_playing:
            self.player.stop()
            self.play_btn.config(text="▶ PLAY ALL")
        else:
            self.player.play()
            self.play_btn.config(text="⏹ STOP")

    def on_seek(self, event):
        w = event.widget.winfo_width()
        progress = event.x / w
        
        first_key = list(self.audio_dict.keys())[0]
        total_frames = len(self.audio_dict[first_key])
        self.current_frame = int(progress * total_frames)
        
        if hasattr(self, 'player'):
            self.player.current_frame = self.current_frame
        
        self.update_waveforms()

    def update_waveforms(self):
        first_key = list(self.audio_dict.keys())[0]
        total_frames = len(self.audio_dict[first_key])
        progress = self.current_frame / total_frames if total_frames > 0 else 0
        for w in self.waveforms.values():
            w.set_progress(progress)

    def async_load_waveforms(self):
        """Processes waveforms and removes loading screen."""
        for i, (name, data) in enumerate(self.audio_dict.items()):
            # HEAVY WORK: Pre-convert to contiguous float32 to avoid hiccups during solo switches
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            f_data = np.ascontiguousarray(data, dtype=np.float32)
            self.audio_dict[name] = f_data
            
            # --- CREATE LOW-RES METERING BUFFER ---
            # Downsample to 4kHz to save CPU during real-time metering
            ds_factor = self.sample_rate // self.meter_sample_rate
            if ds_factor > 1:
                self.metering_dict[name] = f_data[::ds_factor]
            else:
                self.metering_dict[name] = f_data
            
            self.waveforms[name].update_data(f_data)
            self.update() # Keep UI alive
            
        # Pre-initialize player and prime first available buffer
        from engine.io.playback import AudioPlayer
        self.player = AudioPlayer()
        first_key = list(self.audio_dict.keys())[0]
        self.solo(first_key)
        
        # Initial draw of loop highlights (Default 0-1)
        self.on_loop_change(0.0, 1.0)
            
        # Enable Controls
        self.play_btn.config(state="normal")
        for btn in self.solo_btns.values():
            btn.config(state="normal")
        if hasattr(self, 'win_btns'):
            for btn in self.win_btns.values():
                btn.config(state="normal")
            
        # Start the sync and flash loops
        self.update_loop()
        self.flash_play_button_loop()
        
    def flash_play_button_loop(self):
        if not self.winfo_exists():
            return
            
        is_playing = hasattr(self, 'player') and self.player.is_playing
        
        if is_playing or str(self.play_btn['state']) == 'disabled':
            # Do not flash
            self.play_btn.config(style="TButton")
            self.flash_state = False
        else:
            # Flash!
            self.flash_state = not self.flash_state
            if self.flash_state:
                self.play_btn.config(style="FlashRed.TButton")
            else:
                self.play_btn.config(style="TButton")
                
        self.flash_loop_id = self.after(500, self.flash_play_button_loop)
            
    def update_loading_heartbeat(self):
        """Rotates the icon and changes cheeky text every 5 seconds to prove we aren't hung."""
        if not hasattr(self, 'loading_frame') or not self.loading_frame.winfo_exists():
            return
            
        import random
        # Switch text
        self.cheeky_status_var.set(random.choice(self.cheeky_messages))
        
        # Toggle hourglass state
        icons = ["⌛", "⏳"] 
        self.hour_glass_var.set(icons[self.hour_glass_angle % 2])
        self.hour_glass_angle += 1
        
        # Check every 5 seconds (User asked for 30, but 5 proves 'not hung' much better visually)
        self.after(5000, self.update_loading_heartbeat)
            

    def on_loop_change(self, start, end):
        if not hasattr(self, 'player'):
            from engine.io.playback import AudioPlayer
            self.player = AudioPlayer()
            self.solo(self.active_version) # Init buffer
            
        first_key = list(self.audio_dict.keys())[0]
        total_frames = len(self.audio_dict[first_key])
        self.player.loop_start = int(start * total_frames)
        self.player.loop_end = int(end * total_frames)
        
        # Update waveform highlighting to match the loop region
        for w in self.waveforms.values():
            w.set_highlight_range(start, end)

    def update_loop(self):
        if hasattr(self, 'player') and self.player.is_playing:
            self.current_frame = self.player.current_frame
            self.update_waveforms()
            self.calculate_realtime_meters()
            
        self.after(30, self.update_loop)

    def calculate_realtime_meters(self):
        """Calculates RMS and Peak using the low-res metering buffers (High Efficiency)."""
        buffer = self.metering_dict.get(self.active_version)
        if buffer is None: return
        
        # Map current frame to the downsampled buffer position
        ratio = self.sample_rate / self.meter_sample_rate
        meter_frame = int(self.current_frame / ratio)
        
        # Window size for metering (approx 50ms)
        window_size = int(self.meter_sample_rate * 0.05)
        start = max(0, meter_frame - window_size)
        end = min(len(buffer), meter_frame)
        
        if end <= start: return
        
        chunk = buffer[start:end]
        
        # Peak/RMS calculation (Now running on 10x less data!)
        if chunk.ndim > 1:
            l_data = chunk[:, 0]
            r_data = chunk[:, 1]
        else:
            l_data = r_data = chunk
            
        def get_metrics(data):
            if len(data) == 0: return -100, -100
            # np.mean(data**2) is very fast on small arrays
            rms = 20 * np.log10(np.sqrt(np.mean(data**2)) + 1e-10)
            peak = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
            return rms, peak
            
        rms_l, peak_l = get_metrics(l_data)
        rms_r, peak_r = get_metrics(r_data)
        
        self.meter_l.set_level(rms_l, peak_l)
        self.meter_r.set_level(rms_r, peak_r)
        self.meter_lufs.update_lufs((rms_l + rms_r) / 2 - 1.0)
