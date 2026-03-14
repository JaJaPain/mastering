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
        
        self.bind("<Configure>", lambda e: self.draw())

    def update_data(self, audio_array):
        """Generates 1000 detailed points from audio data."""
        if audio_array is None: return
        
        # Mix to mono
        if audio_array.ndim > 1:
            data = np.mean(audio_array, axis=1)
        else:
            data = audio_array.flatten()
            
        n_points = 800 # Higher resolution for comparison console
        chunk_size = len(data) // n_points
        
        waveform = []
        for i in range(n_points):
            chunk = np.abs(data[i*chunk_size : (i+1)*chunk_size])
            if len(chunk) > 0:
                waveform.append(float(np.max(chunk)))
            else:
                waveform.append(0.0)
                
        # Scale 0-1
        max_val = np.max(waveform) if len(waveform) > 0 else 1.0
        if max_val > 0:
            self.waveform_data = [v / max_val for v in waveform]
        else:
            self.waveform_data = [0.0] * n_points
            
        self.draw()

    def set_progress(self, progress):
        self.progress = progress
        self.draw()

    def draw(self):
        self.delete("all")
        if self.waveform_data is None: return
        
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: return
        
        n_points = len(self.waveform_data)
        bar_width = w / n_points
        
        # Draw silhouette
        for i, val in enumerate(self.waveform_data):
            x = i * bar_width
            bar_h = max(2, val * h * 0.8)
            y1 = (h - bar_h) / 2
            y2 = (h + bar_h) / 2
            
            # Determine color based on progress
            # If past progress, use a dimmed version or gray
            current_pos = i / n_points
            if current_pos <= self.progress:
                color = self.base_color
            else:
                color = "#444444" # Unplayed gray
                
            # Draw as lines for a smoother 'vector' look
            self.create_line(x, y1, x, y2, fill=color, width=1)

        # Highlight Playhead
        px = self.progress * w
        self.create_line(px, 0, px, h, fill="#FFFFFF", width=1)
