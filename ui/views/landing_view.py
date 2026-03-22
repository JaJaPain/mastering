import tkinter as tk
from tkinter import ttk
from ui.theme import Colors

class LandingView(ttk.Frame):
    """
    The initial landing page providing the choice between 
    Preset Battle and Hands-on Mastering.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, style="Main.TFrame")
        self.controller = controller
        
        # Center container
        self.container = ttk.Frame(self, style="Panel.TFrame")
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=700, height=450)
        
        # Title & Welcome
        ttk.Label(self.container, text="Welcome to High-Fidelity Mastering", 
                  style="Panel.TLabel", font=("Segoe UI", 20, "bold")).pack(pady=(40, 10))
        
        ttk.Label(self.container, text="Choose your path to sonic excellence:", 
                  style="Panel.TLabel", font=("Segoe UI", 12)).pack(pady=(0, 40))
        
        # Buttons Container
        btn_frame = ttk.Frame(self.container, style="Panel.TFrame")
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=40)
        
        # Option 1: Preset Battle
        battle_card = ttk.Frame(btn_frame, style="Header.TFrame", padding=20)
        battle_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        ttk.Label(battle_card, text="⚔️ Preset Battle", style="Header.TLabel", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        ttk.Label(battle_card, text="Quickly compare multiple\ngenre presets to find the\nbest vibe for your mix.",
                  style="Header.TLabel", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=(0, 20))
        
        self.battle_btn = ttk.Button(battle_card, text="Start Battle", style="ActiveToggle.TButton",
                                     command=self.controller.on_landing_battle)
        self.battle_btn.pack(side=tk.BOTTOM, pady=10)

        # Option 2: Hands-on Approach
        hands_card = ttk.Frame(btn_frame, style="Header.TFrame", padding=20)
        hands_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        ttk.Label(hands_card, text="🛠️ Hands-on", style="Header.TLabel", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        ttk.Label(hands_card, text="Total control over the DSP\nchain. Start with a preset\nand refine every detail.",
                  style="Header.TLabel", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=(0, 20))
        
        self.hands_btn = ttk.Button(hands_card, text="Go Manual", style="ActiveToggle.TButton",
                                    command=self.controller.on_landing_hands_on)
        self.hands_btn.pack(side=tk.BOTTOM, pady=10)
        
        # File Loading Section (NEW)
        load_section = ttk.Frame(self.container, style="Panel.TFrame")
        load_section.pack(pady=(0, 20))
        
        self.load_btn = ttk.Button(load_section, text="📁 Load Audio File", 
                                   command=self.controller.load_audio_file)
        self.load_btn.pack(side=tk.LEFT, padx=10)
        
        self.file_label = ttk.Label(load_section, text="No file loaded", 
                                    style="Panel.TLabel", font=("Segoe UI", 10, "italic"))
        self.file_label.pack(side=tk.LEFT)

        # Bottom Tip
        ttk.Label(self.container, text="Tip: You can always switch modes later from the main console.", 
                  style="Panel.TLabel", font=("Segoe UI", 9, "italic"), foreground=Colors.TEXT_SECONDARY).pack(pady=20)
