import tkinter as tk
import numpy as np
from ui.theme import Colors

class DetailedWaveform(tk.Canvas):
    """
    A high-resolution waveform display for static comparisons.
    Supports silhouette rendering and themed gradients.
    """
    def __init__(self, parent, height=120, color="#00D2FF"):
        super().__init__(parent, bg=Colors.BG_PANEL, height=height, highlightthickness=0)
        self.height = height
        self.base_color = color
        self.waveform_data = None
        self.progress = 0.0
        self.highlight_start = 0.0 # Range start
        self.highlight_end = 1.0   # Range end
        
        self.bind("<Configure>", lambda e: self.draw())

    def update_data(self, audio_array):
        """Generates 800 detailed points using high-speed vectorization."""
        if audio_array is None: return
        
        # Mix to mono efficiently
        if audio_array.ndim > 1:
            data = np.mean(audio_array, axis=1)
        else:
            data = audio_array.flatten()
            
        n_points = 800
        total_samples = len(data)
        chunk_size = total_samples // n_points
        
        if chunk_size < 1:
            self.waveform_data = [0.0] * n_points
            self.draw()
            return

        # Vectorized peak detection: MUCH faster than a Python for-loop
        # Trim data to fit exactly into chunks for reshaping
        trimmed_data = np.abs(data[:n_points * chunk_size])
        reshaped_data = trimmed_data.reshape(n_points, chunk_size)
        waveform = np.max(reshaped_data, axis=1)
                
        # Scale 0-1
        max_val = np.max(waveform) if len(waveform) > 0 else 1.0
        if max_val > 0:
            self.waveform_data = (waveform / max_val).tolist()
        else:
            self.waveform_data = [0.0] * n_points
            
        self.draw()

    def set_progress(self, progress):
        self.progress = progress
        self.draw()

    def set_highlight_range(self, start, end):
        self.highlight_start = start
        self.highlight_end = end
        self.draw()

    def draw(self):
        self.delete("all")
        if self.waveform_data is None: return
        
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 40: return
        
        # Match RangeSlider's internal margins so visuals align vertically
        margin = 20
        track_w = w - 2 * margin
        
        n_points = len(self.waveform_data)
        bar_width = track_w / n_points
        
        # Draw silhouette
        for i, val in enumerate(self.waveform_data):
            x = margin + (i * bar_width)
            bar_h = max(2, val * h * 0.8)
            y1 = (h - bar_h) / 2
            y2 = (h + bar_h) / 2
            
            # Determine color based on highlight range
            current_pos = i / n_points
            if self.highlight_start <= current_pos <= self.highlight_end:
                color = self.base_color
            else:
                color = "#333333" # Dimmed outside loop
                
            # Draw as lines for a smoother 'vector' look
            self.create_line(x, y1, x, y2, fill=color, width=1)

        # Draw a clear progress line (Playhead) aligned with the track
        px = margin + (self.progress * track_w)
        self.create_line(px, 0, px, h, fill="#FFFFFF", width=1.5, tags="playhead")
