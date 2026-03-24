import tkinter as tk
from tkinter import ttk
import queue
import numpy as np
from ui.theme import apply_dark_theme, Colors
from ui.components.meter import LevelMeter, LufsMeter, DbScale
from ui.components.tooltip import ToolTip
from ui.components.waveform import WaveformSeeker
from ui.components.range_slider import RangeSlider
from ui.views.landing_view import LandingView

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
        self.create_main_content()
        self.create_footer()
        
        # Overlay Landing Page
        self.landing_frame = LandingView(self, self.controller)
        self.landing_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # === SPACEBAR PLAY/STOP SYSTEM ===
        # Override the default TButton class binding that invokes buttons on <space>.
        # In a DAW-style app, spacebar should ALWAYS control playback, never click buttons.
        self.bind_class('TButton', '<KeyPress-space>', lambda e: None)
        self.bind_class('TButton', '<KeyRelease-space>', lambda e: None)
        
        # Single global handler — routes to whichever window has focus
        self.bind_all('<KeyPress-space>', self._on_spacebar)
        
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
        
        self.compare_btn = ttk.Button(load_btn_frame, text="Preset Battle ⚔️")
        self.compare_btn.pack(side=tk.LEFT, padx=(10, 0))
        ToolTip(self.compare_btn, "Compare up to 4 different mastering presets side-by-side\nwith synced solo-playback.")

        self.file_label = ttk.Label(load_btn_frame, text="No file loaded", style="Header.TLabel", font=("Segoe UI", 10))
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        self.title_label = ttk.Label(header_frame, text="Mastering Console v1", style="Header.TLabel", font=("Segoe UI", 16, "bold"))
        self.title_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
        # Status Label in header instead of viz controls
        self.status_header_label = ttk.Label(header_frame, text="Ready", style="Header.TLabel", font=("Segoe UI", 10))
        self.status_header_label.pack(side=tk.RIGHT, padx=20, pady=15)
        
    def create_main_content(self):
        # Container for the tabs
        self.tab_container = ttk.Frame(self, style="Main.TFrame")
        self.tab_container.pack(fill=tk.BOTH, expand=True)

        # --- TAB: Mastering ---
        self.mastering_frame = ttk.Frame(self.tab_container, style="Main.TFrame")
        self.mastering_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        outer_frame = self.mastering_frame
        
        content_frame = ttk.Frame(outer_frame, style="Main.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # --- Left Panel: Processing Controls with Scrollbar ---
        control_panel_container = ttk.Frame(content_frame, style="Panel.TFrame")
        control_panel_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.canvas_scroll = tk.Canvas(control_panel_container, bg=Colors.BG_PANEL, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(control_panel_container, orient="vertical", command=self.canvas_scroll.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas_scroll, style="Panel.TFrame")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))
        )
        
        self.canvas_scroll.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=580)
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas_scroll.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        control_panel = self.scrollable_frame
        
        # Presets Section
        preset_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        preset_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(preset_frame, text="Genre Preset:", style="Panel.TLabel", width=15, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(preset_frame, state="readonly", font=("Segoe UI", 10))
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        self.save_preset_btn = ttk.Button(preset_frame, text="Save Current")
        self.save_preset_btn.pack(side=tk.RIGHT)
        
        ttk.Label(control_panel, text="Reference Matching", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))
        
        match_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        match_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.load_ref_btn = ttk.Button(match_frame, text="Select Reference Track...")
        self.load_ref_btn.pack(side=tk.LEFT)
        ToolTip(self.load_ref_btn, "Choose a professional song (WAV) to match your tonal balance to.")
        
        self.match_status_label = ttk.Label(match_frame, text="None Loaded", foreground=Colors.TEXT_SECONDARY, font=("Segoe UI", 8))
        self.match_status_label.pack(side=tk.LEFT, padx=10)
        
        self.clear_ref_btn = ttk.Button(match_frame, text="Clear", width=8)
        self.clear_ref_btn.pack(side=tk.RIGHT)
        
        match_amount_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        match_amount_frame.pack(fill=tk.X, padx=20, pady=5)
        
        lbl_match = ttk.Label(match_amount_frame, text="Apply Match (%)", style="Panel.TLabel", width=15)
        lbl_match.pack(side=tk.LEFT)
        ToolTip(lbl_match, "Blends the reference EQ curve into your track.\n0% = Original Tone | 100% = Full Match.")
        
        self.match_amount_slider = ttk.Scale(match_amount_frame, from_=0.0, to=100.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.match_amount_slider.set(0.0)
        self.match_amount_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        self.match_amount_slider.state(['disabled'])

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
        
        # Master Glue Slider (3D Depth)
        glue_frame = ttk.Frame(control_panel, style="Panel.TFrame")
        glue_frame.pack(fill=tk.X, padx=20, pady=10)
        
        lbl_glue = ttk.Label(glue_frame, text="Master Glue (dB)", style="Panel.TLabel", width=15)
        lbl_glue.pack(side=tk.LEFT)
        ToolTip(lbl_glue, "Applies Asymmetric M/S Compression.\nGlues the center (Mid) while letting the outer edges (Side) breathe.")
        
        self.glue_slider = ttk.Scale(glue_frame, from_=0.0, to=12.0, orient=tk.HORIZONTAL, style="Horizontal.TScale")
        self.glue_slider.set(0.0)
        self.glue_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Multi-Band Exciter Section
        exciter_header = ttk.Frame(control_panel, style="Panel.TFrame")
        exciter_header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        ttk.Label(exciter_header, text="Multi-Band Harmonic Exciter", style="Panel.TLabel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        self.exciter_bypass_var = tk.BooleanVar(value=False)
        self.exciter_bypass_chk = ttk.Checkbutton(exciter_header, text="Bypass", variable=self.exciter_bypass_var)
        self.exciter_bypass_chk.pack(side=tk.RIGHT)
        
        self.sat_mode_combo = ttk.Combobox(exciter_header, values=["Soft Clip", "Tape", "Intelligent"], state="readonly", width=10, font=("Segoe UI", 9))
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
        
        # --- Bottom: Waveform Seeker (Full Width) ---
        waveform_container = ttk.Frame(outer_frame, style="Panel.TFrame", height=100)
        waveform_container.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 10))
        
        self.waveform_seeker = WaveformSeeker(waveform_container, height=80)
        self.waveform_seeker.pack(fill=tk.BOTH, expand=True)



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


    def update_visualizer(self):
        try:
            while not self.vis_queue.empty():
                msg = self.vis_queue.get_nowait()
                if msg['type'] == 'meters':
                    rms_l, peak_l, rms_r, peak_r = msg['data']
                    self.meter_l.set_level(rms_l, peak_l)
                    self.meter_r.set_level(rms_r, peak_r)
                elif msg['type'] == 'lufs':
                    self.meter_lufs.update_lufs(msg['data'])
                elif msg['type'] == 'progress':
                    self.waveform_seeker.set_progress(msg['data'])
                elif msg['type'] == 'render_complete':
                    self.controller._on_render_complete(msg['data'])
                elif msg['type'] == 'render_error':
                    self.controller._on_render_error(msg['data'])
        except Exception as e:
            pass
            
        self.after(30, self.update_visualizer)
        
    def _on_spacebar(self, event):
        """Global spacebar handler — routes to whichever window has focus."""
        # Only block for real text-entry widgets (not readonly comboboxes)
        focused = self.focus_get()
        if focused and isinstance(focused, (tk.Entry, ttk.Entry)) and not isinstance(focused, ttk.Combobox):
            return  # Let the space character be typed normally
        
        # Don't toggle if the landing page is still visible
        if hasattr(self, 'landing_frame') and self.landing_frame.winfo_ismapped():
            return "break"
        
        # Route to the correct window's player
        toplevel = event.widget.winfo_toplevel()
        if toplevel == self:
            # Main mastering console
            self.controller.toggle_play()
        elif hasattr(toplevel, 'toggle_play'):
            # ComparisonConsole (Preset Battle or Custom Track Match)
            toplevel.toggle_play()
        
        return "break"

    def show_hands_on(self):
        """Hides the landing frame to reveal the mastering console."""
        if hasattr(self, 'landing_frame'):
            self.landing_frame.place_forget()
            
    def show_landing_page(self):
        """Re-displays the landing frame."""
        if hasattr(self, 'landing_frame'):
            self.landing_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.landing_frame.lift()
