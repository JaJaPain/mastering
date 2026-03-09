import tkinter as tk
from tkinter import ttk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from ui.theme import Colors

class VisualizerDashboard(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, style="Panel.TFrame", *args, **kwargs)
        
        self.fig, (self.ax_wave, self.ax_fft) = plt.subplots(1, 2, figsize=(10, 2.5), facecolor=Colors.BG_PANEL)
        self.fig.tight_layout(pad=2.0)
        
        # UI Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Audio Buffer state
        self.chunk_size = 2048
        
        # Waveform Setup
        self.x_wave = np.arange(self.chunk_size)
        self.line_wave_dry, = self.ax_wave.plot(self.x_wave, np.zeros(self.chunk_size), color="#666666", lw=1, alpha=0.5, label="Dry")
        self.line_wave_wet, = self.ax_wave.plot(self.x_wave, np.zeros(self.chunk_size), color=Colors.ACCENT_PRIMARY, lw=1.5, label="Wet")
        self.ax_wave.set_ylim(-1.1, 1.1)
        self.ax_wave.set_xlim(0, self.chunk_size)
        self.ax_wave.set_axis_off()
        self.ax_wave.set_title("Live Waveform", color=Colors.TEXT_SECONDARY, fontsize=9)
        
        # FFT Setup
        self.x_fft = np.fft.rfftfreq(self.chunk_size, 1/44100) # Assuming 44.1k for UI visual freq mapping
        self.line_fft_dry, = self.ax_fft.semilogx(self.x_fft, np.zeros(len(self.x_fft)), color="#666666", lw=1, alpha=0.5)
        self.line_fft_wet, = self.ax_fft.semilogx(self.x_fft, np.zeros(len(self.x_fft)), color=Colors.ACCENT_PRIMARY, lw=1.5)
        self.ax_fft.set_ylim(-100, 10) # dBFS
        self.ax_fft.set_xlim(20, 20000)
        self.ax_fft.set_axis_off()
        self.ax_fft.set_title("Frequency Spectrum", color=Colors.TEXT_SECONDARY, fontsize=9)
        
        # Start fresh
        self.canvas.draw()
        
    def _compute_fft_db(self, audio_chunk):
        """Helper to get smoothed FFT in dB"""
        window = np.hanning(len(audio_chunk))
        spectrum = np.abs(np.fft.rfft(audio_chunk * window))
        # Prevent log(0)
        spectrum = np.maximum(spectrum, 1e-10)
        # Convert to dB, scaled roughly for visualization mapping overlay
        db = 20 * np.log10(spectrum) - 40 
        return db

    def draw_waveform(self, dry_chunk, wet_chunk, active_mode="A"):
        """
        Clears the canvas and redraws the normalized waveform and spectrum. 
        """
        # Clear plots to avoid solid blocks of color
        self.ax_wave.clear()
        self.ax_fft.clear()
        
        # Restore basic plot properties
        self.ax_wave.set_ylim(-1.1, 1.1)
        self.ax_wave.set_xlim(0, self.chunk_size)
        self.ax_wave.set_axis_off()
        self.ax_wave.set_title("Live Waveform", color=Colors.TEXT_SECONDARY, fontsize=9)
        
        self.ax_fft.set_ylim(-100, 10) # dBFS
        self.ax_fft.set_xlim(20, 20000)
        self.ax_fft.set_axis_off()
        self.ax_fft.set_title("Frequency Spectrum", color=Colors.TEXT_SECONDARY, fontsize=9)
        
        # --- Waveform Data ---
        if dry_chunk is not None and len(dry_chunk) > 0:
            if len(dry_chunk) < self.chunk_size:
                dry_chunk = np.pad(dry_chunk, (0, self.chunk_size - len(dry_chunk)))
                
            # Normalize 64-bit chunk between -1 and 1
            max_dry = np.max(np.abs(dry_chunk))
            if max_dry > 0:
                dry_chunk = dry_chunk / max_dry
                
            dry_fft = self._compute_fft_db(dry_chunk)
            
            # Draw Dry
            alpha_val = 1.0 if active_mode == "A" else 0.3
            z_val = 10 if active_mode == "A" else 5
            self.ax_wave.plot(self.x_wave, dry_chunk, color="#666666", lw=1, alpha=alpha_val, label="Dry", zorder=z_val)
            self.ax_fft.semilogx(self.x_fft, dry_fft, color="#666666", lw=1, alpha=alpha_val, zorder=z_val)

        if wet_chunk is not None and len(wet_chunk) > 0:
            if len(wet_chunk) < self.chunk_size:
                wet_chunk = np.pad(wet_chunk, (0, self.chunk_size - len(wet_chunk)))
                
            # Normalize 64-bit chunk between -1 and 1
            max_wet = np.max(np.abs(wet_chunk))
            if max_wet > 0:
                wet_chunk = wet_chunk / max_wet
                
            wet_fft = self._compute_fft_db(wet_chunk)
            
            # Draw Wet
            alpha_val = 1.0 if active_mode == "B" else 0.3
            z_val = 10 if active_mode == "B" else 5
            self.ax_wave.plot(self.x_wave, wet_chunk, color=Colors.ACCENT_PRIMARY, lw=1.5, label="Wet", zorder=z_val)
            self.ax_fft.semilogx(self.x_fft, wet_fft, color=Colors.ACCENT_PRIMARY, lw=1.5, alpha=alpha_val, zorder=z_val)
            
        self.canvas.draw_idle()
