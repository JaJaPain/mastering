import tkinter as tk
from tkinter import ttk
import queue
import numpy as np
from ui.theme import apply_dark_theme, Colors
from ui.components.meter import LevelMeter, LufsMeter
from ui.components.tooltip import ToolTip

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
        
        # Layout Frames
        self.create_header()
        self.create_main_content()
        self.create_footer()
        
        # Start UI queue polling
        self.update_visualizer()
        
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
        
        # Toggle Visuals Button
        self.toggle_vis_btn = ttk.Button(header_frame, text="Vis: ON", style="TButton")
        self.toggle_vis_btn.pack(side=tk.RIGHT, padx=10, pady=15)
        
    def create_main_content(self):
        # Frame holding everything below header
        outer_frame = ttk.Frame(self, style="Main.TFrame")
        outer_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Panel: Visualizer ---
        # Explicit pure-tk Canvas for native rendering
        # 900 width roughly, 150 height.
        self.vis_panel = tk.Canvas(outer_frame, height=150, bg=Colors.BG_PANEL, highlightthickness=0)
        self.vis_panel.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(20, 10))
        
        # Draw center line
        self.vis_panel.create_line(0, 75, 900, 75, fill="#444444", tags="grid")
        
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
        
        lbl_air = ttk.Label(air_frame, text="Air Shelf (dB)", style="Panel.TLabel", width=15)
        lbl_air.pack(side=tk.LEFT)
        ToolTip(lbl_air, "A zero-phase 12kHz shelf EQ filter.\nAdds 'shimmer' and top-end clarity to dull mixes without phasing.")
        
        self.air_slider = ttk.Scale(air_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.air_slider.set(2.0)
        self.air_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Multi-Band Exciter Section
        exciter_header = ttk.Frame(control_panel, style="Panel.TFrame")
        exciter_header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        ttk.Label(exciter_header, text="Multi-Band Harmonic Exciter", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        self.exciter_bypass_var = tk.BooleanVar(value=False)
        self.exciter_bypass_chk = ttk.Checkbutton(exciter_header, text="Bypass", variable=self.exciter_bypass_var)
        self.exciter_bypass_chk.pack(side=tk.RIGHT)
        
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
        meter_panel = ttk.Frame(content_frame, style="Panel.TFrame", width=200)
        meter_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        meter_panel.pack_propagate(False)
        
        ttk.Label(meter_panel, text="Output Levels", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        meters_frame = ttk.Frame(meter_panel, style="Panel.TFrame")
        meters_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Channel Meter
        left_meter_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        left_meter_frame.pack(side=tk.LEFT, expand=True)
        self.meter_l = LevelMeter(left_meter_frame)
        self.meter_l.pack()
        ttk.Label(left_meter_frame, text="L", style="Panel.TLabel").pack(pady=5)
        
        # LUFS Meter (Center)
        self.meter_lufs = LufsMeter(meters_frame, label="LOUDNESS")
        self.meter_lufs.pack(side=tk.LEFT, expand=True, padx=10)

        # Right Channel Meter
        right_meter_frame = ttk.Frame(meters_frame, style="Panel.TFrame")
        right_meter_frame.pack(side=tk.LEFT, expand=True)
        self.meter_r = LevelMeter(right_meter_frame)
        self.meter_r.pack()
        ttk.Label(right_meter_frame, text="R", style="Panel.TLabel").pack(pady=5)

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
        self.export_btn = ttk.Button(footer_frame, text="Export Master")
        self.export_btn.pack(side=tk.RIGHT, padx=20, pady=15)

    def update_visualizer(self):
        try:
            while not self.vis_queue.empty():
                msg = self.vis_queue.get_nowait()
                if msg['type'] == 'wave':
                    self.draw_waveform(*msg['data'])
                elif msg['type'] == 'meters':
                    rms_l, peak_l, rms_r, peak_r = msg['data']
                    self.meter_l.set_level(rms_l, peak_l)
                    self.meter_r.set_level(rms_r, peak_r)
                elif msg['type'] == 'lufs':
                    self.meter_lufs.update_lufs(msg['data'])
                elif msg['type'] == 'render_complete':
                    self.controller._on_render_complete(msg['data'])
                elif msg['type'] == 'render_error':
                    self.controller._on_render_error(msg['data'])
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
