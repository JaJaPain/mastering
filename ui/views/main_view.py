import tkinter as tk
from tkinter import ttk
import queue
import numpy as np
from ui.theme import apply_dark_theme, Colors
from ui.components.meter import LevelMeter, LufsMeter, DbScale
from ui.components.tooltip import ToolTip
from ui.views.visualizer_view import VisualizerView

class MainView(tk.Tk):
    """
    Main application view containing the layout scaffolding.
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("High-Fidelity Mastering Program")
        self.geometry("900x600")
        
        # Apply dark theme
        apply_dark_theme(self)
        
        self.vis_queue = queue.Queue()
        self.visual_mode = "FFT" # "WAVE" or "FFT"
        
        # Layout Frames
        self.create_header()
        self.create_tab_navbar()
        self.create_main_content()
        self.create_footer()
        
        # Start UI queue polling
        self.update_visualizer()
        
    def create_tab_navbar(self):
        nav_frame = ttk.Frame(self, style="Header.TFrame", height=40)
        nav_frame.pack(side=tk.TOP, fill=tk.X)
        nav_frame.pack_propagate(False)

        self.tab_master_btn = ttk.Button(nav_frame, text="🎚 MASTERING", width=15)
        self.tab_master_btn.pack(side=tk.LEFT, padx=(20, 5), pady=5)

        self.tab_viz_btn = ttk.Button(nav_frame, text="🌌 VISUALIZER", width=15)
        self.tab_viz_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Tab Switching Logic (implemented via local hide/show)
        self.tab_master_btn.config(command=lambda: self.switch_tab("master"))
        self.tab_viz_btn.config(command=lambda: self.switch_tab("visualizer"))
        
    def create_header(self):
        header_frame = ttk.Frame(self, style="Header.TFrame", height=60)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False) # Prevent shrinking
        
        # Load File Section
        load_btn_frame = ttk.Frame(header_frame, style="Header.TFrame")
        load_btn_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.load_btn = ttk.Button(load_btn_frame, text="Load WAV")
        self.load_btn.pack(side=tk.LEFT)
        
        self.file_label = ttk.Label(load_btn_frame, text="No file loaded", style="Header.TLabel", font=("Segoe UI", 10))
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        self.title_label = ttk.Label(header_frame, text="Mastering Console v1", style="Header.TLabel", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Visualizer Controls
        header_right = ttk.Frame(header_frame, style="Header.TFrame")
        header_right.pack(side=tk.RIGHT, padx=10, pady=15)

        self.vis_btn = ttk.Button(header_right, text="View: FFT", width=10)
        self.vis_btn.pack(side=tk.LEFT, padx=5)
        
        self.toggle_vis_btn = ttk.Button(header_right, text="Vis: ON", width=8)
        self.toggle_vis_btn.pack(side=tk.LEFT, padx=5)
        
    def create_main_content(self):
        # Container for the tabs
        self.tab_container = ttk.Frame(self, style="Main.TFrame")
        self.tab_container.pack(fill=tk.BOTH, expand=True)

        # --- TAB: Mastering ---
        self.mastering_frame = ttk.Frame(self.tab_container, style="Main.TFrame")
        self.mastering_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        outer_frame = self.mastering_frame

        # --- Top Panel: Visualizer ---
        self.vis_panel = tk.Canvas(outer_frame, height=180, bg=Colors.BG_PANEL, highlightthickness=0)
        self.vis_panel.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(15, 5))
        
        # Draw Background Grid & dB Scale
        # 0dB (Top), -20dB, -40dB, -60dB, -80dB (Bottom)
        db_markings = [0, -20, -40, -60, -80]
        for db in db_markings:
            # Scale -80...0 to 0...180 (canvas height)
            ratio = (db + 80) / 80.0
            y = 180 - (ratio * 180)
            
            # Subtle grid line
            color = "#333333" if db != 0 else "#444444"
            self.vis_panel.create_line(0, y, 900, y, fill=color, tags="grid")
            
            # dB Text
            self.vis_panel.create_text(8, y + 8, text=f"{db}dB", fill="#666666", font=("Segoe UI", 7), anchor=tk.W, tags="grid")
            
        # Overlay mode labels
        self.vis_panel.create_text(30, 15, text="FFT", fill=Colors.ACCENT_LIGHT, font=("Segoe UI", 8, "bold"), tags="mode_indicator")
        
        content_frame = ttk.Frame(outer_frame, style="Main.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # --- Left Panel: Processing Controls ---
        control_panel = ttk.Frame(content_frame, style="Panel.TFrame", width=600)
        control_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        control_panel.pack_propagate(False)
        
        # Presets Section
        preset_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        preset_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(preset_frame, text="Genre Preset:", style="Panel.TLabel", width=15, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(preset_frame, state="readonly", font=("Segoe UI", 10))
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        self.save_preset_btn = ttk.Button(preset_frame, text="Save Current")
        self.save_preset_btn.pack(side=tk.RIGHT)
        
        ttk.Label(control_panel, text="DSP Chain Parameters", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        # Input Gain Slider
        gain_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        gain_frame.pack(fill=tk.X, padx=20, pady=10)
        
        lbl_gain = ttk.Label(gain_frame, text="Input Gain (dB)", style="Panel.TLabel", width=15)
        lbl_gain.pack(side=tk.LEFT)
        ToolTip(lbl_gain, "Controls the pre-processing volume level.\nUse this to balance quiet mixes before they hit the DSP chain.")
        
        self.gain_slider = ttk.Scale(gain_frame, from_=-24.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.gain_slider.set(0.0)
        self.gain_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Air Shelf Gain Slider
        air_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        air_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.air_slider = ttk.Scale(air_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.air_slider.set(2.0)
        self.air_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Stereo Width Slider
        width_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        width_frame.pack(fill=tk.X, padx=20, pady=10)
        
        lbl_width = ttk.Label(width_frame, text="Stereo Width (dB)", style="Panel.TLabel", width=15)
        lbl_width.pack(side=tk.LEFT)
        ToolTip(lbl_width, "Enhances the stereo image by boosting side-channel energy.\nAdds dimension and 'bigness' to the master.")
        
        self.width_slider = ttk.Scale(width_frame, from_=-6.0, to=6.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.width_slider.set(0.0)
        self.width_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Multi-Band Exciter Section
        exciter_header = ttk.Frame(control_panel, style="Panel.TFrame")
        exciter_header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        ttk.Label(exciter_header, text="Multi-Band Harmonic Exciter", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        self.exciter_bypass_var = tk.BooleanVar(value=False)
        self.exciter_bypass_chk = ttk.Checkbutton(exciter_header, text="Bypass", variable=self.exciter_bypass_var)
        self.exciter_bypass_chk.pack(side=tk.RIGHT)
        
        self.sat_mode_combo = ttk.Combobox(exciter_header, values=["Soft Clip", "Tape"], state="readonly", width=10, font=("Segoe UI", 9))
        self.sat_mode_combo.set("Soft Clip")
        self.sat_mode_combo.pack(side=tk.RIGHT, padx=10)
        ttk.Label(exciter_header, text="Mode:", style="Panel.TLabel").pack(side=tk.RIGHT)
        
        # Low Drive
        low_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        low_frame.pack(fill=tk.X, padx=20, pady=5)
        lbl_low = ttk.Label(low_frame, text="Low Drive (dB)", style="Panel.TLabel", width=15)
        lbl_low.pack(side=tk.LEFT)
        ToolTip(lbl_low, "Saturation for frequencies below 250Hz.\nAdds weight and 'growl' to the bass and kick.")
        self.drive_low_slider = ttk.Scale(low_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.drive_low_slider.set(0.0)
        self.drive_low_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        # Mid Drive
        mid_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        mid_frame.pack(fill=tk.X, padx=20, pady=5)
        lbl_mid = ttk.Label(mid_frame, text="Mid Drive (dB)", style="Panel.TLabel", width=15)
        lbl_mid.pack(side=tk.LEFT)
        ToolTip(lbl_mid, "Saturation for 250Hz - 3kHz.\nAdds presence to vocals, guitars, and snare punch.")
        self.drive_mid_slider = ttk.Scale(mid_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.drive_mid_slider.set(0.0)
        self.drive_mid_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        # High Drive
        high_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        high_frame.pack(fill=tk.X, padx=20, pady=5)
        lbl_high = ttk.Label(high_frame, text="High Drive (dB)", style="Panel.TLabel", width=15)
        lbl_high.pack(side=tk.LEFT)
        ToolTip(lbl_high, "Saturation for frequencies above 3kHz.\nAdds 'crunch' and high-end detail to hats and textures.")
        self.drive_high_slider = ttk.Scale(high_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.drive_high_slider.set(0.0)
        self.drive_high_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Mono Maker Section
        mono_header = ttk.Frame(control_panel, style="Panel.TFrame")
        mono_header.pack(fill=tk.X, padx=20, pady=(15, 5))
        
        ttk.Label(mono_header, text="Mono Maker (Tightens Bass)", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        self.mono_bypass_var = tk.BooleanVar(value=False)
        self.mono_bypass_chk = ttk.Checkbutton(mono_header, text="Bypass", variable=self.mono_bypass_var)
        self.mono_bypass_chk.pack(side=tk.RIGHT)

        mono_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        mono_frame.pack(fill=tk.X, padx=20, pady=5)
        
        lbl_mono = ttk.Label(mono_frame, text="Mono Crossover (Hz)", style="Panel.TLabel", width=17)
        lbl_mono.pack(side=tk.LEFT)
        ToolTip(lbl_mono, "Frequencies below this point will be forced to Mono.\nUsually 120Hz-180Hz is best for a tight sound.")
        
        self.mono_freq_slider = ttk.Scale(mono_frame, from_=20.0, to=500.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.mono_freq_slider.set(150.0)
        self.mono_freq_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))

        self.mono_freq_val = ttk.Label(mono_frame, text="150 Hz", style="Panel.TLabel", width=8)
        self.mono_freq_val.pack(side=tk.RIGHT)

        # Target LUFS Slider
        lufs_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        lufs_frame.pack(fill=tk.X, padx=20, pady=10)
        
        lbl_lufs = ttk.Label(lufs_frame, text="Target LUFS", style="Panel.TLabel", width=15)
        lbl_lufs.pack(side=tk.LEFT)
        ToolTip(lbl_lufs, "The final total loudness target for the exported master.\n-14 LUFS is the industry standard for Spotify/YouTube streaming.")
        self.lufs_slider = ttk.Scale(lufs_frame, from_=-24.0, to=-5.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.lufs_slider.set(-14.0)
        self.lufs_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))

        self.match_btn = ttk.Button(lufs_frame, text="Auto-Match", width=12)
        self.match_btn.pack(side=tk.RIGHT)
        ToolTip(self.match_btn, "Analyzes the whole song and automatically adjusts\nGain to hit your target LUFS exactly.")
        
        
        # --- Right Panel: Metering ---
        meter_panel = ttk.Frame(content_frame, style="Panel.TFrame", width=280)
        meter_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        meter_panel.pack_propagate(False)
        
        ttk.Label(meter_panel, text="Output Levels", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        meters_frame = ttk.Frame(meter_panel, style="Panel.TFrame")
        meters_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Channel Meter
        left_meter_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        left_meter_frame.pack(side=tk.LEFT, expand=True)
        self.meter_l = LevelMeter(left_meter_frame, height=180)
        self.meter_l.pack()
        ttk.Label(left_meter_frame, text="L", style="Panel.TLabel").pack(pady=5)
        
        # dB Reference Scale (Static)
        db_scale_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        db_scale_frame.pack(side=tk.LEFT, pady=(0, 25)) # Align with meter height
        self.db_scale = DbScale(db_scale_frame, height=180, width=35)
        self.db_scale.pack()

        # LUFS Meter (Center)
        self.meter_lufs = LufsMeter(meters_frame, label="LOUDNESS")
        self.meter_lufs.pack(side=tk.LEFT, expand=True, padx=10)

        # dB Reference Scale Right (Static)
        db_scale_right_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        db_scale_right_frame.pack(side=tk.LEFT, pady=(0, 25))
        self.db_scale_r = DbScale(db_scale_right_frame, height=180, width=35)
        self.db_scale_r.pack()

        # Right Channel Meter
        right_meter_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        right_meter_frame.pack(side=tk.LEFT, expand=True)
        self.meter_r = LevelMeter(right_meter_frame, height=180)
        self.meter_r.pack()
        ttk.Label(right_meter_frame, text="R", style="Panel.TLabel").pack(pady=5)

        # --- TAB: Visualizer ---
        self.visualizer_frame = VisualizerView(self.tab_container, self.controller)
        self.visualizer_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Show Mastering by default
        self.switch_tab("master")

    def switch_tab(self, tab_name):
        if tab_name == "master":
            self.mastering_frame.tkraise()
            self.tab_master_btn.config(style="ActiveToggle.TButton")
            self.tab_viz_btn.config(style="TButton")
        else:
            self.visualizer_frame.tkraise()
            self.tab_master_btn.config(style="TButton")
            self.tab_viz_btn.config(style="ActiveToggle.TButton")

    def create_footer(self):
        footer_frame = ttk.Frame(self, style="Header.TFrame", height=60)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)
        
        # Left Side: Status
        status_frame = ttk.Frame(footer_frame, style="Header.TFrame")
        status_frame.pack(side=tk.LEFT, padx=20, pady=10)
        self.status_label = ttk.Label(status_frame, text="Ready", style="Header.TLabel", font=("Segoe UI", 9))
        self.status_label.pack(side=tk.LEFT)
        
        # Center: Playback & A/B Toggle
        playback_frame = ttk.Frame(footer_frame, style="Header.TFrame")
        playback_frame.pack(side=tk.LEFT, expand=True, fill=tk.Y, pady=10)
        
        self.play_btn = ttk.Button(playback_frame, text="▶ Play")
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(playback_frame, text="⏹ Stop")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # A/B Toggles
        self.btn_a = ttk.Button(playback_frame, text="A (Dry)", style="ActiveToggle.TButton")
        self.btn_a.pack(side=tk.LEFT, padx=(20, 0))
        
        self.btn_b = ttk.Button(playback_frame, text="B (Wet)", style="TButton")
        self.btn_b.pack(side=tk.LEFT, padx=(0, 20))
        
        # Right Side: Export Master
        export_frame = ttk.Frame(footer_frame, style="Header.TFrame")
        export_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # Quality dropdown
        ttk.Label(export_frame, text="Bit-Depth:", style="Header.TLabel", font=("Segoe UI", 8)).pack(side=tk.TOP, pady=(0, 2))
        self.bit_depth_combo = ttk.Combobox(export_frame, values=["16-bit", "24-bit", "32-bit float"], state="readonly", width=12, font=("Segoe UI", 8))
        self.bit_depth_combo.set("24-bit")
        self.bit_depth_combo.pack(side=tk.TOP)
        ToolTip(self.bit_depth_combo, "Final audio resolution. \n24-bit is professional standard.\n32-bit float is lossless for further processing.")

        export_right = ttk.Frame(footer_frame, style="Header.TFrame")
        export_right.pack(side=tk.RIGHT, padx=(0, 20), pady=15)

        self.format_combo = ttk.Combobox(export_right, values=["WAV", "FLAC", "MP3"], state="readonly", width=6, font=("Segoe UI", 10, "bold"))
        self.format_combo.set("WAV")
        self.format_combo.pack(side=tk.LEFT, padx=5)
        ToolTip(self.format_combo, "Output Format:\nWAV: Lossless, uncompressed.\nFLAC: Lossless, compressed.\nMP3: Lossy, for sharing.")

        self.export_btn = ttk.Button(export_right, text="Export Master", width=15)
        self.export_btn.pack(side=tk.LEFT)

        # New: Visualizer Export Section
        viz_frame = ttk.Frame(footer_frame, style="Header.TFrame")
        viz_frame.pack(side=tk.RIGHT, padx=(20, 0), pady=15)

        self.viz_render_btn = ttk.Button(viz_frame, text="🎥 Visualizer", width=15)
        self.viz_render_btn.pack(side=tk.LEFT)
        ToolTip(self.viz_render_btn, "Generate a 1080p MP4 visualizer \nfor YouTube using the mastered audio.")

    def update_visualizer(self):
        try:
            while not self.vis_queue.empty():
                msg = self.vis_queue.get_nowait()
                if msg['type'] == 'wave':
                    if self.visual_mode == "WAVE":
                        self.vis_panel.delete("fft") # Clear FFT if switching to wave
                        self.draw_waveform(*msg['data'])
                elif msg['type'] == 'meters':
                    rms_l, peak_l, rms_r, peak_r = msg['data']
                    self.meter_l.set_level(rms_l, peak_l)
                    self.meter_r.set_level(rms_r, peak_r)
                elif msg['type'] == 'lufs':
                    self.meter_lufs.update_lufs(msg['data'])
                elif msg['type'] == 'fft':
                    if self.visual_mode == "FFT":
                        self.vis_panel.delete("wave") # Clear wave if switching to FFT
                        self.draw_fft(msg['data'])
                elif msg['type'] == 'render_complete':
                    self.controller._on_render_complete(msg['data'])
                elif msg['type'] == 'render_error':
                    self.controller._on_render_error(msg['data'])
            
            # Keep labels and grid in front of the visual data
            self.vis_panel.tag_raise("grid")
            self.vis_panel.tag_raise("mode_indicator")
        except Exception as e:
            pass
            
        self.after(30, self.update_visualizer)
        
    def draw_waveform(self, dry_chunk, wet_chunk, listen_mode):
        if not hasattr(self, 'vis_panel') or not self.vis_panel.winfo_exists():
            return
            
        w = self.vis_panel.winfo_width()
        h = self.vis_panel.winfo_height()
        
        if w < 10 or h < 10:
            return
            
        self.vis_panel.delete("wave")
        mid_y = h / 2
        
        if dry_chunk is not None and len(dry_chunk) > 0:
            step = max(1, len(dry_chunk) // w)
            plot_chunk_dry = dry_chunk[::step]
            
            coords_dry = []
            for i, val in enumerate(plot_chunk_dry):
                x = (i / len(plot_chunk_dry)) * w
                y = mid_y - (val * mid_y * 0.9)
                coords_dry.extend([x, y])
            
            if len(coords_dry) > 4:
                alpha_col = "#666666" if listen_mode == "A" else "#444444"
                self.vis_panel.create_line(coords_dry, fill=alpha_col, width=1, tags="wave")

        if wet_chunk is not None and len(wet_chunk) > 0:
            step = max(1, len(wet_chunk) // w)
            plot_chunk_wet = wet_chunk[::step]
            
            coords_wet = []
            for i, val in enumerate(plot_chunk_wet):
                x = (i / len(plot_chunk_wet)) * w
                y = mid_y - (val * mid_y * 0.9)
                coords_wet.extend([x, y])
                
            if len(coords_wet) > 4:
                alpha_col = "#FFB300" if listen_mode == "B" else "#886600"
                self.vis_panel.create_line(coords_wet, fill=alpha_col, width=2, tags="wave")

    def draw_fft(self, fft_data):
        if not hasattr(self, 'vis_panel') or not self.vis_panel.winfo_exists():
            return
            
        w = self.vis_panel.winfo_width()
        h = self.vis_panel.winfo_height()
        if w < 10 or h < 10: return

        self.vis_panel.delete("fft")
        
        # fft_data is a tuple of (freq_mags, listen_mode)
        mags, mode = fft_data
        if len(mags) == 0: return

        # Draw a beautiful gradient spectrum
        num_bars = len(mags)
        bar_w = w / num_bars
        
        color = "#00D2FF" if mode == "B" else "#555555"
        
        points = [0, h]
        for i, mag in enumerate(mags):
            x = i * bar_w
            # Magnitude is already somewhat normalized, but let's scale for UI
            y = h - (mag * h * 0.85)
            points.extend([x, y])
        points.extend([w, h])

        if len(points) > 4:
            # We use multiple polygons with different outlines/fills for a "Glow" effect
            self.vis_panel.create_polygon(points, fill="#003344", outline="", tags="fft")
            # The top line is the bright part
            self.vis_panel.create_line(points[2:-2], fill=color, width=2, tags="fft")
