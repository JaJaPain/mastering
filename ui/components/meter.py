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
