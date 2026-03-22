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
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=850, height=450)
        
        # Title & Welcome
        ttk.Label(self.container, text="Welcome to High-Fidelity Mastering", 
                  style="Panel.TLabel", font=("Segoe UI", 20, "bold")).pack(pady=(40, 10))
        
        # Main Content Layout
        main_content = ttk.Frame(self.container, style="Panel.TFrame")
        main_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 5))
        
        # --- LEFT GROUP (Boxed) ---
        # Using a raw tk.Frame to get highlightthickness for the physical box border
        left_box = tk.Frame(main_content, bg=Colors.BG_PANEL, highlightbackground="#555", highlightcolor="#555", highlightthickness=1)
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        left_inner = ttk.Frame(left_box, style="Panel.TFrame")
        left_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        left_cards = ttk.Frame(left_inner, style="Panel.TFrame")
        left_cards.pack(fill=tk.BOTH, expand=True)
        
        # Option 1: Preset Battle
        battle_card = ttk.Frame(left_cards, style="Header.TFrame", padding=20)
        battle_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        ttk.Label(battle_card, text="⚔️ Preset Battle", style="Header.TLabel", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        ttk.Label(battle_card, text="Quickly compare multiple\ngenre presets to find the\nbest vibe for your mix.",
                  style="Header.TLabel", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=(0, 20))
        
        self.battle_btn = ttk.Button(battle_card, text="Start Battle", style="ActiveToggle.TButton",
                                     command=self.controller.on_landing_battle)
        self.battle_btn.pack(side=tk.BOTTOM, pady=10)

        # Option 2: Hands-on Approach
        hands_card = ttk.Frame(left_cards, style="Header.TFrame", padding=20)
        hands_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        ttk.Label(hands_card, text="🛠️ Hands-on", style="Header.TLabel", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        ttk.Label(hands_card, text="Total control over the DSP\nchain. Start with a preset\nand refine every detail.",
                  style="Header.TLabel", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=(0, 20))
        
        self.hands_btn = ttk.Button(hands_card, text="Go Manual", style="ActiveToggle.TButton",
                                    command=self.controller.on_landing_hands_on)
        self.hands_btn.pack(side=tk.BOTTOM, pady=10)
        
        # File Loading Section (Inside the box)
        load_section = ttk.Frame(left_inner, style="Panel.TFrame")
        load_section.pack(pady=(20, 0))
        
        self.load_btn = ttk.Button(load_section, text="📁 Load Audio File", 
                                   command=self.controller.load_audio_file)
        self.load_btn.pack(side=tk.LEFT, padx=10)
        
        self.file_label = ttk.Label(load_section, text="No file loaded", 
                                    style="Panel.TLabel", font=("Segoe UI", 10, "italic"))
        self.file_label.pack(side=tk.LEFT)
        
        # --- RIGHT GROUP (Isolated) ---
        right_box = ttk.Frame(main_content, style="Panel.TFrame")
        right_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(10, 0))
        
        right_inner = ttk.Frame(right_box, style="Panel.TFrame")
        right_inner.pack(fill=tk.BOTH, expand=True, padx=0, pady=15)
        
        # Option 3: Compare Custom Files
        custom_card = ttk.Frame(right_inner, style="Header.TFrame", padding=20)
        custom_card.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(custom_card, text="🎧 Track Match", style="Header.TLabel", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 15))
        
        ttk.Label(custom_card, text="Load up to 4 exact\nlength audio files to\ncompare mixes side-by-side.",
                  style="Header.TLabel", font=("Segoe UI", 10), justify=tk.CENTER).pack(pady=(0, 20))
        
        self.custom_btn = ttk.Button(custom_card, text="Compare Files", style="ActiveToggle.TButton",
                                     command=self.controller.compare_custom_files)
        self.custom_btn.pack(side=tk.BOTTOM, pady=10)
        
        # Bottom Tip
        ttk.Label(self.container, text="Tip: You can always switch modes later from the main console.", 
                  style="Panel.TLabel", font=("Segoe UI", 9, "italic"), foreground=Colors.TEXT_SECONDARY).pack(pady=(5, 10))
