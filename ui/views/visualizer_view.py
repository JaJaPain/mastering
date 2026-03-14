import tkinter as tk
from tkinter import ttk, filedialog
from ui.theme import Colors
from ui.components.tooltip import ToolTip

class VisualizerView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="Main.TFrame")
        self.controller = controller

        # --- Top Section: Status & Preview ---
        self.create_preview_section()

        # --- Bottom Section: Controls ---
        self.create_controls_section()

    def create_preview_section(self):
        status_frame = ttk.Frame(self, style="Main.TFrame")
        status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(10, 5))

        self.status_label = ttk.Label(status_frame, text="NEBULA ENGINE STANDBY", 
                                      style="Header.TLabel", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)

        # Main Visualization Toggle (Template Switcher)
        template_frame = ttk.Frame(status_frame, style="Main.TFrame")
        template_frame.pack(side=tk.RIGHT)

        ttk.Button(template_frame, text="<", width=3).pack(side=tk.LEFT)
        ttk.Label(template_frame, text="Template: NEBULA V1", style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        ttk.Button(template_frame, text=">", width=3).pack(side=tk.LEFT)

        # Canvas for Preview
        self.canvas = tk.Canvas(self, bg="black", height=280, highlightthickness=1, highlightbackground="#333333")
        self.canvas.pack(fill=tk.X, padx=20, pady=5)
        self.canvas.create_text(450, 140, text="VISUALIZER PREVIEW AREA", fill="#444444", font=("Segoe UI", 20, "bold"))

    def create_controls_section(self):
        container = ttk.Frame(self, style="Panel.TFrame")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 20))

        # --- Row 1: Asset Selection ---
        asset_frame = ttk.Frame(container, style="Panel.TFrame")
        asset_frame.pack(fill=tk.X, padx=15, pady=10)

        # Logo Upload
        logo_f = ttk.Frame(asset_frame, style="Panel.TFrame")
        logo_f.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(logo_f, text="CENTRAL LOGO", style="Panel.TLabel", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        self.logo_btn = ttk.Button(logo_f, text="Choose Image")
        self.logo_btn.pack(side=tk.LEFT, pady=5)
        self.logo_path_label = ttk.Label(logo_f, text="None", style="Panel.TLabel", font=("Segoe UI", 8))
        self.logo_path_label.pack(side=tk.LEFT, padx=10)

        # Audio Upload (or use mastered)
        audio_f = ttk.Frame(asset_frame, style="Panel.TFrame")
        audio_f.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(audio_f, text="AUDIO SOURCE", style="Panel.TLabel", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        self.audio_btn = ttk.Button(audio_f, text="Use Mastered")
        self.audio_btn.pack(side=tk.LEFT, pady=5)
        self.audio_path_label = ttk.Label(audio_f, text="Current Session", style="Panel.TLabel", font=("Segoe UI", 8))
        self.audio_path_label.pack(side=tk.LEFT, padx=10)

        # Watermark Upload
        mark_f = ttk.Frame(asset_frame, style="Panel.TFrame")
        mark_f.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(mark_f, text="BRAND WATERMARK", style="Panel.TLabel", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        self.mark_btn = ttk.Button(mark_f, text="Choose PNG")
        self.mark_btn.pack(side=tk.LEFT, pady=5)

        # --- Row 2: Parameters ---
        param_frame = ttk.Frame(container, style="Panel.TFrame")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=15)

        # Three Columns of Sliders (Match the HTML layout)
        col1 = ttk.Frame(param_frame, style="Panel.TFrame")
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.color_a_btn = tk.Button(col1, text="COLOR A", bg="#00f2ff", fg="black", 
                                     font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2")
        self.color_a_btn.pack(fill=tk.X, pady=5)
        
        self.color_b_btn = tk.Button(col1, text="COLOR B", bg="#7000ff", fg="white", 
                                     font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2")
        self.color_b_btn.pack(fill=tk.X, pady=5)

        self.cycle_slider = self.create_slider(col1, "Cycle Speed", 0.0, 10.0, 2.0)

        col2 = ttk.Frame(param_frame, style="Panel.TFrame")
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.travel_slider = self.create_slider(col2, "Travel Speed", 1.0, 40.0, 15.0)
        self.rotate_slider = self.create_slider(col2, "Rotation Force", 0.0, 5.0, 1.2)

        col3 = ttk.Frame(param_frame, style="Panel.TFrame")
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.shake_slider = self.create_slider(col3, "Shake Force", 0.0, 100.0, 40.0)
        self.star_slider = self.create_slider(col3, "Star Size", 1.0, 30.0, 10.0)

        # --- Row 3: Buttons ---
        btn_frame = ttk.Frame(container, style="Panel.TFrame")
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        self.start_btn = ttk.Button(btn_frame, text="START RENDER (AUTO-STOP)", style="ActiveToggle.TButton")
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.reset_btn = ttk.Button(btn_frame, text="EMERGENCY RESET")
        self.reset_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

    def create_slider(self, parent, label, from_, to_, initial):
        f = ttk.Frame(parent, style="Panel.TFrame")
        f.pack(fill=tk.X, pady=5)
        
        lbl_f = ttk.Frame(f, style="Panel.TFrame")
        lbl_f.pack(fill=tk.X)
        ttk.Label(lbl_f, text=label, style="Panel.TLabel", font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)
        val_lbl = ttk.Label(lbl_f, text=str(initial), style="Panel.TLabel", font=("Segoe UI", 7), foreground="#2ecc71")
        val_lbl.pack(side=tk.RIGHT)

        def _on_move(v):
            val_lbl.config(text=f"{float(v):.1f}")
            if hasattr(s, 'external_cmd'):
                s.external_cmd(v)

        s = ttk.Scale(f, from_=from_, to=to_, orient=tk.HORIZONTAL, style="Horizontal.TScale",
                      command=_on_move)
        s.set(initial)
        s.pack(fill=tk.X, pady=(2, 0))
        return s
