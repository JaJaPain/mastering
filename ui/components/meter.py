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
        
        # Brick Wall LED (Small box at the top)
        self.clip_led_height = 10
        self.clip_led = self.create_rectangle(0, 0, width, self.clip_led_height, fill="#330000", outline=Colors.BG_MAIN)
        self.clip_timer = None
        
        # The physical meter bar (starts fully empty / min_db)
        # We start the bar below the LED
        self.bar_top_limit = self.clip_led_height + 2
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
            
        # Linear interpolation for meter height (excluding the LED area)
        usable_height = self.meter_height - self.bar_top_limit
        db_range = self.max_db - self.min_db
        level_ratio = (current_db - self.min_db) / db_range
        
        # Clamp ratio
        level_ratio = max(0.0, min(1.0, level_ratio))
        
        y_pos = self.meter_height - (level_ratio * usable_height)
        
        # Determine color based on level
        if current_db >= -0.1: # Brick wall hit
            fill_color = Colors.METER_CLIP
            self.trigger_clip_led()
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
            peak_y_pos = self.meter_height - (peak_ratio * usable_height)
            self.coords(self.peak_line, 0, peak_y_pos, self.meter_width, peak_y_pos)

    def trigger_clip_led(self):
        """Turns the LED bright red and sets a timer to turn it off."""
        self.itemconfig(self.clip_led, fill="#FF0000")
        if self.clip_timer:
            self.after_cancel(self.clip_timer)
        self.clip_timer = self.after(1500, self.reset_clip_led)

    def reset_clip_led(self):
        self.itemconfig(self.clip_led, fill="#330000")
        self.clip_timer = None

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

class DbScale(tk.Canvas):
    """
    A static dB scale to provide reference markings next to the meters.
    """
    def __init__(self, parent, min_db=-60.0, max_db=0.0, height=180, width=30):
        super().__init__(parent, width=width, height=height, bg=Colors.BG_PANEL, highlightthickness=0)
        self.min_db = min_db
        self.max_db = max_db
        self.h = height
        self.w = width
        
        self.draw_scale()
        
    def draw_scale(self):
        # Professional dB markings
        ticks = [0, -3, -6, -10, -14, -20, -30, -45, -60]
        db_range = self.max_db - self.min_db
        
        for db in ticks:
            if db < self.min_db: continue
            
            # Calculate Y position
            ratio = (db - self.min_db) / db_range
            y = self.h - (ratio * self.h)
            
            # Draw tick line
            color = "#888888" if db < -1 else "#FF4444"
            self.create_line(self.w - 10, y, self.w, y, fill=color)
            
            # Draw text
            self.create_text(self.w - 15, y, text=str(db), fill=color, font=("Segoe UI", 8), anchor=tk.E)
