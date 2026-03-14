import tkinter as tk
from ui.theme import Colors

class WaveformSeeker(tk.Canvas):
    """
    A full-song waveform display that allows clicking to seek.
    Orange bars represent played audio, gray bars represent remaining.
    """
    def __init__(self, parent, height=80):
        # We use BG_PANEL to match the surrounding area
        super().__init__(parent, bg=Colors.BG_PANEL, height=height, highlightthickness=0)
        self.height = height
        self.waveform_data = None # Downsampled array of max values
        self.current_progress = 0.0 # 0.0 to 1.0
        self.on_seek_callback = None
        
        self.bind("<Button-1>", self.handle_click)
        self.bind("<B1-Motion>", self.handle_click)
        self.bind("<Configure>", self.on_resize)

    def set_waveform(self, data):
        """Expects a numpy array or list of values ranging from 0.0 to 1.0."""
        self.waveform_data = data
        self.draw_waveform()

    def set_progress(self, progress):
        """Updates the visual playback head position."""
        self.current_progress = progress
        self.draw_waveform()

    def handle_click(self, event):
        if self.waveform_data is None:
            return
        w = self.winfo_width()
        if w == 0: return
        progress = event.x / w
        progress = max(0.0, min(1.0, progress))
        if self.on_seek_callback:
            self.on_seek_callback(progress)

    def on_resize(self, event):
        self.draw_waveform()

    def draw_waveform(self):
        self.delete("all")
        if self.waveform_data is None:
            # Draw a placeholder line
            w = self.winfo_width()
            h = self.winfo_height()
            self.create_line(0, h/2, w, h/2, fill="#333333", width=2)
            return
            
        w = self.winfo_width()
        h = self.winfo_height()
        
        if w < 10: return
        
        n_bars = len(self.waveform_data)
        # We want small gaps between bars for that 'pro' look
        bar_spacing = 1
        bar_width = max(1, (w / n_bars) - bar_spacing)
        
        for i, val in enumerate(self.waveform_data):
            x = i * (bar_width + bar_spacing)
            # Clip if bar is too many for pixel width
            if x > w: break
            
            # Normalize height (0.0 to 1.0)
            # We add a floor so silent parts still show a tiny tick
            display_val = max(0.05, val)
            bar_h = display_val * h * 0.9
            
            y1 = (h - bar_h) / 2
            y2 = (h + bar_h) / 2
            
            # Use the orange color from the user's reference image for played portion
            # Gray for unplayed
            color = "#FF8C00" if (i / n_bars) <= self.current_progress else "#666666"
            
            self.create_rectangle(x, y1, x + bar_width, y2, fill=color, outline="")
        
        # Draw a subtle playback head line
        head_x = self.current_progress * w
        self.create_line(head_x, 0, head_x, h, fill="#FFFFFF", width=1)
