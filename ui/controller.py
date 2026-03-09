import threading
import os
import queue
import numpy as np
from tkinter import filedialog, messagebox
from ui.views.main_view import MainView
from engine.dsp.processor import AudioProcessor
from engine.io.audio_io import read_audio, write_audio
from engine.io.playback import AudioPlayer
from engine.io import preset_manager

class UIController:
    def __init__(self):
        self.view = MainView(self)
        self.processor = AudioProcessor()
        self.player = AudioPlayer()
        
        self.dry_audio = None
        self.wet_audio = None
        self.sample_rate = 44100
        self.loaded_file_path = ""
        self.listen_mode = "A" # "A" = Dry, "B" = Wet
        self.render_timer = None
        self.is_rendering = False
        
        self.visuals_enabled = True
        self.vis_timer_id = None
        self.lufs_history = [] 
        self.fft_history = None # For smoothing the spectrogram
        
        self.view.export_btn.config(command=self.export_master)
        self.view.load_btn.config(command=self.load_audio_file)
        self.view.toggle_vis_btn.config(command=self.toggle_visuals)
        self.view.vis_btn.config(command=self.toggle_visual_mode)
        
        # Playback events
        self.view.play_btn.config(command=self.play_audio)
        self.view.stop_btn.config(command=self.stop_audio)
        self.view.btn_a.config(command=lambda: self.set_listen_mode("A"))
        self.view.btn_b.config(command=lambda: self.set_listen_mode("B"))
        
        # Sliders: Trigger debounced render
        self.view.gain_slider.config(command=self.on_slider_change)
        self.view.air_slider.config(command=self.on_slider_change)
        self.view.drive_low_slider.config(command=self.on_slider_change)
        self.view.drive_mid_slider.config(command=self.on_slider_change)
        self.view.drive_high_slider.config(command=self.on_slider_change)
        self.view.lufs_slider.config(command=self.on_slider_change)
        self.view.exciter_bypass_chk.config(command=self.on_slider_change)
        self.view.mono_freq_slider.config(command=self.on_slider_change)
        self.view.mono_bypass_chk.config(command=self.on_slider_change)
        
        # Presets Bindings
        self.refresh_presets()
        self.view.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)
        self.view.save_preset_btn.config(command=self.on_save_preset)
        self.view.match_btn.config(command=self.auto_match_loudness)
        
    def refresh_presets(self):
        names = preset_manager.get_preset_names()
        self.view.preset_combo['values'] = names
        
    def on_preset_selected(self, event):
        selected = self.view.preset_combo.get()
        preset_data = preset_manager.get_preset(selected)
        if preset_data:
            # Update sliders without triggering a storm of render events
            self.view.gain_slider.set(preset_data.get("input_gain", preset_data.get("Input Gain (dB)", 0.0)))
            self.view.air_slider.set(preset_data.get("air_gain", preset_data.get("Air Shelf (dB)", 2.0)))
            
            # Support both old single drive presets and new multiband ones
            if "drive_mid" in preset_data or "Clipper Drive (dB)" in preset_data:
                self.view.drive_low_slider.set(preset_data.get("drive_low", 0.0))
                self.view.drive_mid_slider.set(preset_data.get("drive_mid", preset_data.get("Clipper Drive (dB)", 0.0)))
                self.view.drive_high_slider.set(preset_data.get("drive_high", 0.0))
            else:
                # Default for legacy presets
                legacy_drive = preset_data.get("drive", 0.0)
                self.view.drive_low_slider.set(legacy_drive * 0.2)
                self.view.drive_mid_slider.set(legacy_drive)
                self.view.drive_high_slider.set(legacy_drive * 0.5)

            self.view.exciter_bypass_var.set(preset_data.get("exciter_bypass", False))
            self.view.mono_freq_slider.set(preset_data.get("mono_freq", 150.0))
            self.view.mono_freq_val.config(text=f"{int(float(self.view.mono_freq_slider.get()))} Hz")
            self.view.mono_bypass_var.set(preset_data.get("mono_bypass", False))
            self.view.lufs_slider.set(preset_data.get("target_lufs", preset_data.get("Target LUFS", -14.0)))
            self.trigger_render()
            
    def on_save_preset(self):
        # Extremely simple inline prompt using pure tkinter
        import tkinter.simpledialog as sd
        name = sd.askstring("Save Preset", "Enter a name for your preset:")
        if name:
            data = {
                "target_lufs": float(self.view.lufs_slider.get()),
                "air_gain": float(self.view.air_slider.get()),
                "drive_low": float(self.view.drive_low_slider.get()),
                "drive_mid": float(self.view.drive_mid_slider.get()),
                "drive_high": float(self.view.drive_high_slider.get()),
                "exciter_bypass": self.view.exciter_bypass_var.get(),
                "mono_freq": float(self.view.mono_freq_slider.get()),
                "mono_bypass": self.view.mono_bypass_var.get(),
                "input_gain": float(self.view.gain_slider.get()),
                "description": "User Custom Preset"
            }
            if preset_manager.save_custom_preset(name, data):
                self.refresh_presets()
                self.view.preset_combo.set(name)
                messagebox.showinfo("Success", f"Preset '{name}' saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save preset.")
                
    def load_audio_file(self):
        file_path = filedialog.askopenfilename(
            title="Select WAV File",
            filetypes=(("WAV Files", "*.wav"), ("All Files", "*.*"))
        )
        if file_path:
            try:
                self.sample_rate, data = read_audio(file_path)
                # Soundfile always_2d ensures (samples, channels)
                self.dry_audio = data
                self.processor.sample_rate = self.sample_rate
                self.loaded_file_path = file_path
                self.view.file_label.config(text=os.path.basename(file_path))
                
                self.stop_audio()
                self.set_listen_mode("A")
                self.trigger_render() # Pre-render wet signal
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def play_audio(self):
        if self.dry_audio is None:
            return
        buffer = self.dry_audio if self.listen_mode == "A" else (self.wet_audio if self.wet_audio is not None else self.dry_audio)
        self.player.set_buffer(buffer, self.sample_rate)
        if not self.player.is_playing:
            self.player.play()
            
    def stop_audio(self):
        self.player.stop()

    def set_listen_mode(self, mode):
        self.listen_mode = mode
        if mode == "A":
            self.view.btn_a.config(style="ActiveToggle.TButton")
            self.view.btn_b.config(style="TButton")
            if self.dry_audio is not None:
                self.player.set_buffer(self.dry_audio, self.sample_rate)
        else:
            self.view.btn_a.config(style="TButton")
            self.view.btn_b.config(style="ActiveToggle.TButton")
            if self.wet_audio is not None:
                self.player.set_buffer(self.wet_audio, self.sample_rate)

    def toggle_visual_mode(self):
        if self.view.visual_mode == "FFT":
            self.view.visual_mode = "WAVE"
        else:
            self.view.visual_mode = "FFT"
        self.view.vis_btn.config(text=f"View: {self.view.visual_mode}")
        self.view.vis_panel.delete("fft", "wave")

    def toggle_visuals(self):
        self.visuals_enabled = not self.visuals_enabled
        state_text = "ON" if self.visuals_enabled else "OFF"
        self.view.toggle_vis_btn.config(text=f"Vis: {state_text}")
        
        if self.visuals_enabled:
            self._sample_wave_loop()
        else:
            if self.vis_timer_id is not None:
                self.view.after_cancel(self.vis_timer_id)
                self.vis_timer_id = None
                
    def _sample_wave_loop(self):
        if not self.visuals_enabled:
            return
            
        try:
            if self.player.is_playing and self.dry_audio is not None:
                chunk_size = 2048
                frame = self.player.current_frame
                
                # Fetch Audio
                dry_slice = self.dry_audio[frame:frame+chunk_size]
                dry_mono = np.mean(dry_slice, axis=1) if dry_slice.shape[1] > 1 else dry_slice[:, 0]
                dry_mono = np.nan_to_num(dry_mono, nan=0.0, posinf=0.0, neginf=0.0)
                
                wet_slice = None
                wet_mono = None
                if self.wet_audio is not None and len(self.wet_audio) > frame:
                    wet_slice = self.wet_audio[frame:frame+chunk_size]
                    wet_mono = np.mean(wet_slice, axis=1) if wet_slice.shape[1] > 1 else wet_slice[:, 0]
                    wet_mono = np.nan_to_num(wet_mono, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Pipe cleanly padded array into thread queue
                self.view.vis_queue.put({'type': 'wave', 'data': (dry_mono, wet_mono, self.listen_mode)})

                # --- LIVE PEAK METERS ---
                # This makes the L/R meters dance while the music plays!
                active_slice = wet_slice if (self.listen_mode == "B" and wet_slice is not None) else dry_slice
                if active_slice is not None and len(active_slice) > 0:
                    def get_metrics(chn):
                        data = active_slice[:, chn] if active_slice.shape[1] > chn else active_slice
                        rms = 20 * np.log10(np.sqrt(np.mean(np.square(data))) + 1e-10)
                        peak = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
                        return rms, peak
                    
                    rlk, plk = get_metrics(0)
                    rrk, prk = get_metrics(1 if active_slice.shape[1] > 1 else 0)
                    self.view.vis_queue.put({'type': 'meters', 'data': (rlk, plk, rrk, prk)})

                # --- LUFS Real-Time Calculation ---
                # We analyze the currently playing signal (A or B)
                active_buffer = self.dry_audio if self.listen_mode == "A" else self.wet_audio
                
                window_size = int(self.sample_rate * 0.4) # 400ms momentary window
                start_frame = max(0, frame - window_size)
                
                if active_buffer is not None:
                    # We need at least some data to analyze
                    end_idx = min(len(active_buffer), frame)
                    start_idx = max(0, end_idx - window_size)
                    
                    if end_idx > start_idx:
                        analysis_chunk = active_buffer[start_idx:end_idx]
                        try:
                            # 400ms Energy Integration
                            energy = np.sqrt(np.mean(np.square(analysis_chunk)))
                            # Convert to dBFS (LUFS approximation)
                            lufs = 20 * np.log10(energy + 1e-10)
                            self.view.vis_queue.put({'type': 'lufs', 'data': lufs})
                        except:
                            pass
                
                # --- LIVE SPECTROGRAM (FFT) ---
                # We calculate the frequency spectrum of the currently audible signal
                active_mono = wet_mono if (self.listen_mode == "B" and wet_mono is not None) else dry_mono
                
                if active_mono is not None and len(active_mono) > 512:
                    try:
                        # Use a Hanning window to prevent spectral leakage
                        window = np.hanning(len(active_mono))
                        windowed_audio = active_mono * window
                        
                        # Compute real-FFT and NORMALIZE by window length to avoid maxing out
                        fft_vals = np.abs(np.fft.rfft(windowed_audio)) / (len(windowed_audio) / 2)
                        
                        # Downsample/Group bins into a logarithmic scale (Human hearing)
                        num_ui_bars = 64
                        log_bins = np.logspace(0, np.log10(len(fft_vals)-1), num_ui_bars + 1).astype(int)
                        
                        buckets = []
                        for i in range(num_ui_bars):
                            start, end = log_bins[i], log_bins[i+1]
                            if end <= start: end = start + 1
                            val = np.mean(fft_vals[start:end])
                            buckets.append(val)
                        
                        buckets = np.array(buckets)
                        
                        # Professional Logarithmic amplitude scaling (-80dB floor)
                        # This avoids the "Ceiling hitting" effect
                        buckets = 20 * np.log10(buckets + 1e-10)
                        buckets = (buckets + 80) / 80.0 # Map -80...0 to 0...1
                        buckets = np.clip(buckets, 0.0, 1.0)
                        
                        # Smoothing (Exponential moving average)
                        if self.fft_history is None or len(self.fft_history) != len(buckets):
                            self.fft_history = buckets
                        else:
                            self.fft_history = 0.6 * self.fft_history + 0.4 * buckets
                        
                        self.view.vis_queue.put({'type': 'fft', 'data': (self.fft_history.tolist(), self.listen_mode)})
                    except:
                        pass
        except Exception as e:
            pass
            
        # Target ~30ms map update
        self.vis_timer_id = self.view.after(30, self._sample_wave_loop)

    def on_slider_change(self, value=None):
        if self.dry_audio is None:
            return
            
        # Quality of Life UX: Automatically switch to the Processed 'B' channel 
        # so the user can immediately hear the effect of the slider they just moved!
        if self.listen_mode == "A":
            self.set_listen_mode("B")
            
        if self.render_timer is not None:
            self.view.after_cancel(self.render_timer)
        self.render_timer = self.view.after(300, self.trigger_render)
        
        # Update Real-Time Readouts
        m_freq = int(float(self.view.mono_freq_slider.get()))
        self.view.mono_freq_val.config(text=f"{m_freq} Hz")
        
        # Update LUFS Target Line on UI immediately
        self.view.meter_lufs.meter.set_target(float(self.view.lufs_slider.get()))
        
    def trigger_render(self):
        if self.is_rendering or self.dry_audio is None:
            # Check again later if we are currently mid-render
            if self.is_rendering:
                self.render_timer = self.view.after(200, self.trigger_render)
            return

        self.is_rendering = True
        self.view.status_label.config(text="Rendering Preview...")
        
        params = {
            'input_gain_db': float(self.view.gain_slider.get()),
            'air_gain_db': float(self.view.air_slider.get()),
            'drive_low_db': float(self.view.drive_low_slider.get()),
            'drive_mid_db': float(self.view.drive_mid_slider.get()),
            'drive_high_db': float(self.view.drive_high_slider.get()),
            'exciter_bypass': self.view.exciter_bypass_var.get(),
            'mono_freq': float(self.view.mono_freq_slider.get()),
            'mono_bypass': self.view.mono_bypass_var.get()
        }
        
        threading.Thread(target=self._render_task, args=(params,), daemon=True).start()
        
    def _render_task(self, params):
        try:
            # Processor now handles mono/stereo internally
            processed_audio = self.processor.process(self.dry_audio, **params)
            
            # Extract metrics for meters from the processed buffer
            # Handles (samples, channels)
            if processed_audio.ndim > 1 and processed_audio.shape[1] > 1:
                proc_l = processed_audio[:, 0]
                proc_r = processed_audio[:, 1]
            else:
                proc_l = processed_audio.flatten()
                proc_r = proc_l

            rms_l = self.processor.calculate_rms(proc_l)
            rms_r = self.processor.calculate_rms(proc_r)
            peak_l = 20 * np.log10(max(np.max(np.abs(np.nan_to_num(proc_l))), 1e-10))
            peak_r = 20 * np.log10(max(np.max(np.abs(np.nan_to_num(proc_r))), 1e-10))
            self.view.vis_queue.put({'type': 'meters', 'data': (rms_l, peak_l, rms_r, peak_r)})
                
            self.view.vis_queue.put({'type': 'render_complete', 'data': processed_audio})
        except Exception as e:
            self.view.vis_queue.put({'type': 'render_error', 'data': str(e)})
            
    def _update_meters(self, rms_l, peak_l, rms_r, peak_r):
        self.view.meter_l.set_level(rms_l, peak_l)
        self.view.meter_r.set_level(rms_r, peak_r)
        
    def _on_render_complete(self, processed_audio):
        self.wet_audio = processed_audio
        self.is_rendering = False
        self.view.status_label.config(text="Preview Ready")
        
        # If currently listening to B (Wet), hotly update the player buffer
        if self.listen_mode == "B":
            self.player.set_buffer(self.wet_audio, self.sample_rate)

    def _on_render_error(self, err_msg):
        self.is_rendering = False
        self.view.status_label.config(text=f"Render Error: {err_msg}")

    def export_master(self):
        if self.wet_audio is None:
            messagebox.showwarning("Warning", "No rendered audio to export.")
            return

        # Need the final render with the Heavy Target LUFS calculation applied!
        self.view.status_label.config(text="Applying Target LUFS formatting...")
        
        # --- Pick save path with extension based on format ---
        fmt = self.view.format_combo.get().lower()
        orig_name = os.path.basename(self.loaded_file_path)
        # Strip old extension
        name_no_ext = os.path.splitext(orig_name)[0]
        default_save = f"Mastered_{name_no_ext}.{fmt}"
        
        save_path = filedialog.asksaveasfilename(
            title="Export Mastered File",
            initialfile=default_save,
            defaultextension=f".{fmt}",
            filetypes=((f"{fmt.upper()} Files", f"*.{fmt}"), ("All Files", "*.*"))
        )
        
        if save_path:
            try:
                # --- Define Export Characteristics ---
                export_fmt = self.view.format_combo.get().upper()
                depth_str = self.view.bit_depth_combo.get()
                
                # Mapping of bitdepth to soundfile subtypes
                subtype_map = {
                    "16-bit": "PCM_16",
                    "24-bit": "PCM_24",
                    "32-bit float": "FLOAT"
                }
                subtype = subtype_map.get(depth_str, "PCM_24")

                # Run full render path with target lufs enabled 
                params = {
                    'input_gain_db': float(self.view.gain_slider.get()),
                    'air_gain_db': float(self.view.air_slider.get()),
                    'drive_low_db': float(self.view.drive_low_slider.get()),
                    'drive_mid_db': float(self.view.drive_mid_slider.get()),
                    'drive_high_db': float(self.view.drive_high_slider.get()),
                    'exciter_bypass': self.view.exciter_bypass_var.get(),
                    'mono_freq': float(self.view.mono_freq_slider.get()),
                    'mono_bypass': self.view.mono_bypass_var.get(),
                    'target_lufs': float(self.view.lufs_slider.get())
                }
                
                # Double-check render (some apps like soundfile don't like 32-bit for MP3)
                if export_fmt == 'MP3':
                    subtype = None # soundfile will handle it or fail gracefully

                def export_task():
                    try:
                        audio = self.dry_audio
                        # Processor handles mono vs stereo correctly inside
                        final_audio = self.processor.process(audio, **params)
                            
                        write_audio(save_path, self.sample_rate, final_audio, format=export_fmt, subtype=subtype)
                        self.view.after(0, lambda: self.view.status_label.config(text=f"Exported to {os.path.basename(save_path)}"))
                        self.view.after(0, lambda: messagebox.showinfo("Success", "Mastering Export Complete!"))
                    except Exception as err:
                        self.view.after(0, lambda e=err: messagebox.showerror("Export Error", f"Failed to save:\n{e}"))
                        
                threading.Thread(target=export_task, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to start export:\n{e}")
                self.view.status_label.config(text="Export failed.")

    def auto_match_loudness(self):
        """
        Background task to analyze the full song and adjust gain to hit target LUFS.
        """
        if self.dry_audio is None:
            messagebox.showwarning("Warning", "Load an audio file first!")
            return

        target = float(self.view.lufs_slider.get())
        self.view.status_label.config(text=f"Analyzing for {target} LUFS...")
        self.view.match_btn.config(state="disabled")

        def analysis_thread():
            try:
                # 1. Take current settings (Air, Drive)
                params = {
                    'air_gain_db': float(self.view.air_slider.get()),
                    'drive_low_db': float(self.view.drive_low_slider.get()),
                    'drive_mid_db': float(self.view.drive_mid_slider.get()),
                    'drive_high_db': float(self.view.drive_high_slider.get()),
                    'exciter_bypass': self.view.exciter_bypass_var.get(),
                }
                
                # 2. Start from current gain
                current_gain = float(self.view.gain_slider.get())
                
                # Simple iterative approach (max 3 passes for efficiency)
                for i in range(3):
                    params['input_gain_db'] = current_gain
                    
                    # Process directly (handles mono/stereo)
                    test_output = self.processor.process(self.dry_audio, **params)
                    
                    # Analyze LUFS
                    actual_lufs = self.processor.loudness_analyzer.analyze(test_output, self.sample_rate)
                    diff = target - actual_lufs
                    
                    # If within 0.2dB, we're good
                    if abs(diff) < 0.2:
                        break
                        
                    # Adjust gain for next pass
                    current_gain += diff
                    # Clamp to slider limits
                    current_gain = max(-24.0, min(12.0, current_gain))

                # Update UI on main thread
                def update_ui():
                    self.view.gain_slider.set(current_gain)
                    self.view.status_label.config(text=f"Matched to {actual_lufs:.1f} LUFS")
                    self.view.match_btn.config(state="normal")
                    self.trigger_render()
                    messagebox.showinfo("Loudness Match", f"Gain adjusted to {current_gain:.1f} dB\nto hit {actual_lufs:.1f} LUFS.")

                self.view.after(0, update_ui)

            except Exception as e:
                self.view.after(0, lambda: self.view.status_label.config(text="Match Error"))
                self.view.after(0, lambda: self.view.match_btn.config(state="normal"))
                self.view.after(0, lambda msg=str(e): messagebox.showerror("Error", f"Matching failed:\n{msg}"))

        threading.Thread(target=analysis_thread, daemon=True).start()

    def run(self):
        self._sample_wave_loop() # Kick off visual loop safely
        self.view.mainloop()
