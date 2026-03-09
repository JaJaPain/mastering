import tkinter as tk
from tkinter import ttk
from ui.theme import Colors

class LevelMeter(tk.Canvas):
    """
    A simple vertical level meter using Tkinter Canvas.
    Displays appropriate colors for safe (-inf to -6dB), warning (-6dB to -1dB), and clip (> -1dB).
    """
    def __init__(self, parent, min_db=-60.0, max_db=0.0, width=20, height=200):
        super().__init__(parent, width=width, height=height, bg=Colors.BG_HEADER, highlightthickness=0)
        self.min_db = min_db
        self.max_db = max_db
        self.meter_width = width
        self.meter_height = height
        
        # Draw background trough
        self.create_rectangle(0, 0, width, height, fill=Colors.BG_HEADER, outline=Colors.BG_MAIN)
        
        # The physical meter bar (starts fully empty / min_db)
        self.bar = self.create_rectangle(0, height, width, height, fill=Colors.METER_SAFE, outline="")
        
        # Peak hold indicator
        self.peak_line = self.create_line(0, height, width, height, fill=Colors.TEXT_PRIMARY, width=2)

        # Target Marker (Optional)
        self.target_db = None
        self.target_line = None
        self.target_text_id = None # Store the ID specifically 
        
    def set_level(self, current_db: float, peak_db: float = None):
        """
        Updates the meter display.
        current_db: Current RMS or immediate peak level.
        peak_db: Slower decaying peak hold level.
        """
        if current_db < self.min_db:
            current_db = self.min_db
            
        # Linear interpolation for meter height
        db_range = self.max_db - self.min_db
        level_ratio = (current_db - self.min_db) / db_range
        
        # Clamp ratio
        level_ratio = max(0.0, min(1.0, level_ratio))
        
        y_pos = self.meter_height - (level_ratio * self.meter_height)
        
        # Determine color based on level
        if current_db > -1.0:
            fill_color = Colors.METER_CLIP
        elif current_db > -6.0:
            fill_color = Colors.METER_WARN
        else:
            fill_color = Colors.METER_SAFE
            
        # Update main bar
        self.coords(self.bar, 0, y_pos, self.meter_width, self.meter_height)
        self.itemconfig(self.bar, fill=fill_color)
        
        # Update peak line if provided
        if peak_db is not None:
            if peak_db < self.min_db:
                peak_db = self.min_db
            peak_ratio = (peak_db - self.min_db) / db_range
            peak_ratio = max(0.0, min(1.0, peak_ratio))
            peak_y_pos = self.meter_height - (peak_ratio * self.meter_height)
            self.coords(self.peak_line, 0, peak_y_pos, self.meter_width, peak_y_pos)

    def set_target(self, target_db: float):
        """Draws a static target line on the meter (e.g. -14 LUFS)."""
        self.target_db = target_db
        db_range = self.max_db - self.min_db
        ratio = (target_db - self.min_db) / db_range
        ratio = max(0.0, min(1.0, ratio))
        y_pos = self.meter_height - (ratio * self.meter_height)
        
        if self.target_line:
            self.delete(self.target_line)
        if self.target_text_id:
            self.delete(self.target_text_id)
        
        self.target_line = self.create_line(0, y_pos, self.meter_width, y_pos, fill="#FF00FF", width=2, dash=(4, 2))
        self.target_text_id = self.create_text(self.meter_width/2, y_pos - 8, text="Spotify", fill="#FF00FF", font=("Segoe UI", 7, "bold"))

class LufsMeter(tk.Frame):
    """
    Dedicated LUFS meter with a text readout and a bar.
    """
    def __init__(self, parent, label="LUFS"):
        super().__init__(parent, bg=Colors.BG_PANEL)
        
        ttk.Label(self, text=label, style="Panel.TLabel", font=("Segoe UI", 9, "bold")).pack()
        
        self.meter = LevelMeter(self, min_db=-60.0, max_db=0.0, width=30, height=180)
        self.meter.pack(pady=5)
        self.meter.set_target(-14.0) # Default Spotify target
        
        self.readout = ttk.Label(self, text="-60.0", style="Panel.TLabel", font=("Consolas", 11, "bold"))
        self.readout.pack()

    def update_lufs(self, val: float):
        # Enforce meter range for color logic
        display_val = max(-60.0, val)
        if display_val <= -60.0:
            txt = "-inf"
        else:
            txt = f"{val:.1f}"
        
        self.readout.config(text=txt, foreground="#00D2FF")
        self.meter.set_level(display_val)
        # Force the bar to be Cyan
        self.meter.itemconfig(self.meter.bar, fill="#00D2FF")
