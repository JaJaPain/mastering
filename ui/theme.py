import tkinter as tk
from tkinter import ttk

class Colors:
    """Color palette for the Mastering Program dark theme."""
    BG_MAIN = "#1E1E1E"
    BG_PANEL = "#252526"
    BG_HEADER = "#333333"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#CCCCCC"
    ACCENT_LIGHT = "#007ACC"
    ACCENT_DARK = "#005C99"
    METER_SAFE = "#4CAF50"
    METER_WARN = "#FFC107"
    METER_CLIP = "#F44336"

def apply_dark_theme(root: tk.Tk):
    """
    Applies the custom dark theme to the tkinter root window and ttk styles.
    """
    root.configure(bg=Colors.BG_MAIN)
    
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure common ttk widgets
    style.configure("TFrame", background=Colors.BG_MAIN)
    style.configure("Panel.TFrame", background=Colors.BG_PANEL)
    style.configure("Header.TFrame", background=Colors.BG_HEADER)
    
    style.configure("TLabel", 
                    background=Colors.BG_MAIN, 
                    foreground=Colors.TEXT_PRIMARY,
                    font=("Segoe UI", 10))
    style.configure("Header.TLabel", 
                    background=Colors.BG_HEADER, 
                    foreground=Colors.TEXT_PRIMARY,
                    font=("Segoe UI", 12, "bold"))
    style.configure("Panel.TLabel", 
                    background=Colors.BG_PANEL, 
                    foreground=Colors.TEXT_SECONDARY,
                    font=("Segoe UI", 10))
                    
    style.configure("TButton", 
                    background=Colors.BG_HEADER, 
                    foreground=Colors.TEXT_PRIMARY,
                    font=("Segoe UI", 10),
                    borderwidth=1,
                    focusthickness=3,
                    focuscolor='none')
    style.map("TButton",
              background=[("active", Colors.ACCENT_DARK), ("pressed", Colors.ACCENT_LIGHT)])
              
    style.configure("ActiveToggle.TButton", 
                    background=Colors.ACCENT_LIGHT, 
                    foreground=Colors.TEXT_PRIMARY,
                    font=("Segoe UI", 10, "bold"),
                    borderwidth=2)
    style.map("ActiveToggle.TButton",
              background=[("active", Colors.ACCENT_LIGHT), ("pressed", Colors.ACCENT_DARK)])

    style.configure("Horizontal.TScale",
                    background=Colors.BG_PANEL,
                    troughcolor=Colors.BG_HEADER)
    
    return style
