import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import numpy as np
from ui.theme import Colors
from ui.components.detailed_waveform import DetailedWaveform
from ui.components.range_slider import RangeSlider
from ui.components.meter import LevelMeter, LufsMeter, DbScale

class PresetBattleDialog(tk.Toplevel):
    """Dialog to select up to 4 presets for comparison."""
    def __init__(self, parent, preset_names, on_start_callback):
        super().__init__(parent)
        self.title("Preset Battle - Select Challengers")
        self.geometry("600x600")
        self.preset_names = preset_names
        self.on_start_callback = on_start_callback
        self.selected_presets = []
        
        self.configure(bg=Colors.BG_MAIN)
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self, text="Select up to 4 presets to compare:", font=("Segoe UI", 12, "bold")).pack(pady=20)
        
        # Grid frame for presets
        list_frame = ttk.Frame(self, style="Panel.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Configure columns to be equal width
        list_frame.columnconfigure(0, weight=1)
        list_frame.columnconfigure(1, weight=1)
        
        self.vars = {}
        for i, name in enumerate(self.preset_names):
            var = tk.BooleanVar()
            self.vars[name] = var
            chk = ttk.Checkbutton(list_frame, text=name, variable=var, command=self.check_limit)
            row = i // 2
            col = i % 2
            chk.grid(row=row, column=col, sticky="w", pady=2, padx=10)

        btn_frame = ttk.Frame(self, style="Panel.TFrame")
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Spatial Enhancement Toggle
        self.spatial_var = tk.BooleanVar(value=True)
        self.spatial_chk = ttk.Checkbutton(btn_frame, text="Apply Pro Spatial Enhancements (Stereo Width + Mono Bass)", 
                                           variable=self.spatial_var)
        self.spatial_chk.pack(pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Battle!", state="disabled", command=self.on_start)
        self.start_btn.pack(pady=(0, 20))

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
        
        self.configure(bg=Colors.BG_MAIN)
        
        # Initial Loading State
        self.loading_frame = tk.Frame(self, bg=Colors.BG_MAIN)
        self.loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Center container for loading elements
        load_center = tk.Frame(self.loading_frame, bg=Colors.BG_MAIN)
        load_center.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(load_center, text="Analyzing Audio & Building Waveforms...", 
                 fg="#FFFFFF", bg=Colors.BG_MAIN, font=("Segoe UI", 16, "italic")).pack(pady=10)
        
        # The Hourglass & Cheeky Status
        self.hour_glass_var = tk.StringVar(value="⏳")
        self.hour_glass_label = tk.Label(load_center, textvariable=self.hour_glass_var, 
                                         fg="#FFD700", bg=Colors.BG_MAIN, font=("Segoe UI", 30))
        self.hour_glass_label.pack()
        self.hour_glass_angle = 0
        
        self.cheeky_status_var = tk.StringVar(value="Waking up the transistors...")
        self.cheeky_label = tk.Label(load_center, textvariable=self.cheeky_status_var, 
                                     fg="#888888", bg=Colors.BG_MAIN, font=("Segoe UI", 10, "italic"))
        self.cheeky_label.pack(pady=10)
        
        self.cheeky_messages = [
            "Polishing the transients...", "De-essing the ghosts in the machine...", "Adding exactly 3 grams of 'Soul'...",
            "Teaching the limiter some manners...", "Removing the sound of silence...", "Converting math into magic...",
            "Tuning the ozone layers...", "Organizing the bits and bobs...", "Convincing the bass to stay in mono...",
            "Buffers are buffering their best...", "Ironing out the audio wrinkles...", "Sprinkling some analog dust...",
            "Making it loud, but like, professionally loud...", "Hunting for stray harmonics...", "Calculating the 3rd dimension...",
            "Aligning the stars and the waveforms...", "Feeding the algorithm some coffee...", "Mastering the art of waiting...",
            "Re-ordering the chaos...", "Polishing the air frequencies...", "Ensuring the kick punch is non-lethal...",
            "Sweeping the digital floor...", "Warming up the virtual tubes...", "Calibrating the vibe-o-meter...",
            "Distilling the essence of the mix...", "Removing accidental sneeze from track 4...", "Glueing things with digital honey...",
            "Stretching the stereo field...", "Sharpening the snares...", "Finalizing the sonic sculpture...",
            "Checking if you are still awake...", "Optimizing the 'shimmer' index...", "Negotiating with the drum peaks..."
        ]
        
        # Start Heartbeat
        self.update_loading_heartbeat()
        
        # Setup UI layout (will be hidden by loading_frame initially)
        self.setup_ui()
        
        # Load audio data asynchronously to show the loading marker
        self.after(100, self.async_load_waveforms)

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
        
        self.play_btn = ttk.Button(ctrl_frame, text="▶ PLAY ALL", command=self.toggle_play, state="disabled")
        self.play_btn.pack(expand=True, padx=20, ipady=5)

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
            
            wave = DetailedWaveform(row, height=120, color="#FF8C00" if name=="Original" else "#00D2FF")
            wave.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            # Make it clickable to seek
            wave.bind("<Button-1>", self.on_seek) 
            self.waveforms[name] = wave

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
            
        # --- LOADING COMPLETE ---
        # Remove loading screen
        if hasattr(self, 'loading_frame'):
            self.loading_frame.destroy()
            
        # Pre-initialize player and prime 'Original' buffer
        from engine.io.playback import AudioPlayer
        self.player = AudioPlayer()
        self.solo("Original")
        
        # Initial draw of loop highlights (Default 0-1)
        self.on_loop_change(0.0, 1.0)
            
        # Enable Controls
        self.play_btn.config(state="normal")
        for btn in self.solo_btns.values():
            btn.config(state="normal")
            
        # Start the sync loop
        self.update_loop()
            
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
            
        total_frames = len(self.audio_dict["Original"])
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
