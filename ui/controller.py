import threading
import os
import queue
import random
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from ui.views.main_view import MainView
from engine.dsp.processor import AudioProcessor
from engine.io.audio_io import read_audio, write_audio
from engine.io.playback import AudioPlayer
from engine.io import preset_manager
from ui.dialogs.preset_battle import PresetBattleDialog, BatchProgressWindow, ComparisonConsole
from ui.dialogs.hands_on_setup import HandsOnSetupDialog
from ui.components.tooltip import ToolTip

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
        self.match_fir_coeff = None
        
        # Player-ready caches (float32, contiguous) for zero-latency A/B switching
        self.player_ready_dry = None
        self.player_ready_wet = None
        
        self.visuals_enabled = True
        self.lufs_history = [] 
        self.fft_history = None # For smoothing the spectrogram
        
        self.view.export_btn.config(command=self.export_master)
        self.view.load_btn.config(command=self.load_audio_file)
        self.view.compare_btn.config(command=self.start_preset_battle)
        
        # Playback events
        self.view.play_btn.config(command=self.play_audio)
        self.view.stop_btn.config(command=self.stop_audio)
        self.view.btn_a.config(command=lambda: self.set_listen_mode("A"))
        self.view.btn_b.config(command=lambda: self.set_listen_mode("B"))
        
        # Sliders: Trigger debounced render
        self.view.gain_slider.config(command=self.on_slider_change)
        self.view.air_slider.config(command=self.on_slider_change)
        self.view.width_slider.config(command=self.on_slider_change)
        self.view.glue_slider.config(command=self.on_slider_change)
        self.view.match_amount_slider.config(command=self.on_slider_change)
        self.view.drive_low_slider.config(command=self.on_slider_change)
        self.view.drive_mid_slider.config(command=self.on_slider_change)
        self.view.drive_high_slider.config(command=self.on_slider_change)
        self.view.lufs_slider.config(command=self.on_slider_change)
        self.view.exciter_bypass_chk.config(command=self.on_slider_change)
        self.view.sat_mode_combo.bind("<<ComboboxSelected>>", self.on_slider_change)
        self.view.mono_freq_slider.config(command=self.on_slider_change)
        self.view.mono_bypass_chk.config(command=self.on_slider_change)
        
        # Presets Bindings
        self.refresh_presets()
        self.view.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)
        self.view.save_preset_btn.config(command=self.on_save_preset)
        self.view.match_btn.config(command=self.auto_match_loudness, state="disabled")
        ToolTip(self.view.match_btn, "Please select a Genre Preset first\nto unlock Loudness Matching.")
        
        self.view.load_ref_btn.config(command=self.load_reference_track)
        self.view.clear_ref_btn.config(command=self.clear_reference_track)
        self.view.waveform_seeker.on_seek_callback = self.seek_audio
        
        
    def refresh_presets(self):
        names = preset_manager.get_preset_names()
        self.view.preset_combo['values'] = names
        
    def on_preset_selected(self, event):
        # Pause if currently playing to prevent glitches during multi-parameter updates
        was_playing = self.player.is_playing
        if was_playing:
            self.stop_audio()

        selected = self.view.preset_combo.get()
        preset_data = preset_manager.get_preset(selected)
        if preset_data:
            # Update sliders without triggering a storm of render events
            self.view.gain_slider.set(preset_data.get("input_gain", preset_data.get("Input Gain (dB)", 0.0)))
            self.view.air_slider.set(preset_data.get("air_gain", preset_data.get("Air Shelf (dB)", 2.0)))
            self.view.width_slider.set(preset_data.get("stereo_width", 0.0))
            self.view.sat_mode_combo.set(preset_data.get("saturation_mode", "Soft Clip"))
            
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
            
            # Unlock Auto-Match once a preset (vibe) is chosen
            self.view.match_btn.config(state="normal")
            from ui.components.tooltip import ToolTip
            ToolTip(self.view.match_btn, "Analyzes the whole song and automatically adjusts\nGain to hit your target LUFS exactly.")
            
            self.trigger_render()

            if was_playing:
                # Give the app a 1-second window to render before resuming playback
                self.view.after(1000, self.play_audio)
            
    def apply_preset_by_name(self, name):
        """Used by external dialogs to apply a preset to the UI."""
        self.view.preset_combo.set(name)
        self.on_preset_selected(None)
            
    def on_save_preset(self):
        # Extremely simple inline prompt using pure tkinter
        import tkinter.simpledialog as sd
        name = sd.askstring("Save Preset", "Enter a name for your preset:")
        if name:
            data = {
                "target_lufs": float(self.view.lufs_slider.get()),
                "air_gain": float(self.view.air_slider.get()),
                "stereo_width": float(self.view.width_slider.get()),
                "saturation_mode": self.view.sat_mode_combo.get(),
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
                
    def load_reference_track(self):
        if self.dry_audio is None:
            messagebox.showwarning("Warning", "Please load your song first so we have something to match!")
            return
            
        file_path = filedialog.askopenfilename(
            title="Select Reference WAV File",
            filetypes=(("WAV Files", "*.wav"), ("All Files", "*.*"))
        )
        if file_path:
            self.view.status_label.config(text="Analyzing Reference Spectrum...")
            self.view.load_ref_btn.config(state="disabled")
            
            def analyze_task():
                try:
                    sr, ref_data = read_audio(file_path)
                    # Resample if needed would be complex, assume 44.1 for now or handle in processor
                    # Processor handles basic spectral matching
                    fir = self.processor.calculate_matching_fir(ref_data, self.dry_audio)
                    
                    def update_ui():
                        self.match_fir_coeff = fir
                        self.view.match_status_label.config(text=os.path.basename(file_path), foreground="#00D2FF")
                        self.view.match_amount_slider.state(['!disabled'])
                        if self.view.match_amount_slider.get() == 0:
                            self.view.match_amount_slider.set(50.0) # Start with 50% match
                        self.view.load_ref_btn.config(state="normal")
                        self.view.status_label.config(text="Match Balanced")
                        self.trigger_render()
                        
                    self.view.after(0, update_ui)
                except Exception as e:
                    self.view.after(0, lambda: messagebox.showerror("Analysis Error", f"Failed to analyze reference:\n{e}"))
                    self.view.after(0, lambda: self.view.load_ref_btn.config(state="normal"))

            threading.Thread(target=analyze_task, daemon=True).start()

    def clear_reference_track(self):
        self.match_fir_coeff = None
        self.view.match_status_label.config(text="None Loaded", foreground="#CCCCCC")
        self.view.match_amount_slider.set(0.0)
        self.view.match_amount_slider.state(['disabled'])
        self.trigger_render()


    def seek_audio(self, progress):
        if self.dry_audio is None:
            return
        total_frames = len(self.dry_audio)
        target_frame = int(progress * total_frames)
        self.player.current_frame = target_frame
        self.view.waveform_seeker.set_progress(progress)

    def _generate_waveform(self, audio_data):
        # Downsample to ~200 points for the visualizer
        n_points = 200
        # If stereo, mix to mono first for speed
        if audio_data.ndim > 1:
            mono = np.mean(audio_data, axis=1)
        else:
            mono = audio_data.flatten()
            
        # Take max values in chunks
        chunk_size = len(mono) // n_points
        waveform = []
        for i in range(n_points):
            chunk = np.abs(mono[i*chunk_size : (i+1)*chunk_size])
            if len(chunk) > 0:
                waveform.append(float(np.max(chunk)))
            else:
                waveform.append(0.0)
        
        # Scale to 0.0 - 1.0 (with headroom)
        max_val = np.max(waveform) if len(waveform) > 0 else 1.0
        if max_val > 0.0:
            waveform = [float(v / max_val) for v in waveform]
            
        self.view.waveform_seeker.set_waveform(waveform)

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
                
                # Also update landing page label if it exists
                if hasattr(self.view, 'landing_frame') and hasattr(self.view.landing_frame, 'file_label'):
                    self.view.landing_frame.file_label.config(text=os.path.basename(file_path))
                
                # Generate visual waveform
                self._generate_waveform(data)
                
                # Reset loop markers in player
                self.player.loop_start = 0
                self.player.loop_end = len(data)
                
                # Pre-cache player-ready buffer
                self.player_ready_dry = np.ascontiguousarray(data, dtype=np.float32)
                
                self.stop_audio()
                self.set_listen_mode("A")
                self.trigger_render() # Pre-render wet signal
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def play_audio(self):
        if self.dry_audio is None:
            return
            
        ready_buffer = self.player_ready_dry if self.listen_mode == "A" else self.player_ready_wet
        
        # Fallback if wet isn't ready yet but user wants to hear 'something'
        if ready_buffer is None:
            ready_buffer = self.player_ready_dry
            
        self.player.set_buffer(ready_buffer, self.sample_rate)
        if not self.player.is_playing:
            self.player.play()
            
    def stop_audio(self):
        self.player.stop()

    def set_listen_mode(self, mode):
        self.listen_mode = mode
        if mode == "A":
            self.view.btn_a.config(style="ActiveToggle.TButton")
            self.view.btn_b.config(style="TButton")
            if self.player_ready_dry is not None:
                self.player.set_buffer(self.player_ready_dry, self.sample_rate)
        else:
            self.view.btn_a.config(style="TButton")
            self.view.btn_b.config(style="ActiveToggle.TButton")
            if self.player_ready_wet is not None:
                self.player.set_buffer(self.player_ready_wet, self.sample_rate)
            elif self.player_ready_dry is not None:
                self.player.set_buffer(self.player_ready_dry, self.sample_rate)

                
    def _sample_wave_loop(self):
        if not self.visuals_enabled:
            return
            
        try:
            if self.player.is_playing and self.dry_audio is not None:
                chunk_size = 2048
                frame = self.player.current_frame
                
                # Pipe cleanly padded array into thread queue
                progress = frame / len(self.dry_audio)
                self.view.vis_queue.put({'type': 'progress', 'data': progress})

                # --- LIVE PEAK METERS ---
                # This makes the L/R meters dance while the music plays!
                # We need to re-fetch slices because I commented out the previous ones for clarity
                dry_slice = self.dry_audio[frame:frame+chunk_size]
                wet_slice = self.wet_audio[frame:frame+chunk_size] if (self.wet_audio is not None and len(self.wet_audio) > frame+chunk_size) else None
                
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
            'stereo_width_db': float(self.view.width_slider.get()),
            'drive_low_db': float(self.view.drive_low_slider.get()),
            'drive_mid_db': float(self.view.drive_mid_slider.get()),
            'drive_high_db': float(self.view.drive_high_slider.get()),
            'exciter_bypass': self.view.exciter_bypass_var.get(),
            'saturation_mode': self.view.sat_mode_combo.get(),
            'mono_freq': float(self.view.mono_freq_slider.get()),
            'mono_bypass': self.view.mono_bypass_var.get(),
            'match_eq_fir': self.match_fir_coeff,
            'match_amount': float(self.view.match_amount_slider.get()) / 100.0,
            'target_lufs': float(self.view.lufs_slider.get()),
            'glue_db': float(self.view.glue_slider.get())
        }
        
        threading.Thread(target=self._render_task, args=(params,), daemon=True).start()
        
    EXPORT_SUCCESS_MESSAGES = [
        "Masterpiece delivered. Go grab a coffee!",
        "The listeners aren't ready for how good this sounds.",
        "Export successful. This one’s a banger!",
        "Sonic gold safely tucked into your folder.",
        "Mastering complete. Your fans are going to love this.",
        "Polished, loud, and ready for the airwaves!",
        "Transients preserved. Bass tightened. Let's go!",
        "Mission accomplished. That mix is officially glued.",
        "Another hit in the books. Great work!",
        "Exported and ready to dominate the charts.",
        "The sonic sculpture is complete. It looks... err, sounds beautiful.",
        "Spotify isn't ready for this level of fire.",
        "Smooth as butter and twice as loud.",
        "Final master rendered. Go turn it up!",
        "Your ears deserve a vacation after this one.",
        "Mastering magic applied. It’s a wrap!",
        "The low end is now legal in all 50 states.",
        "Export finished. Time to upload and celebrate.",
        "That's a wrap! The sonics are sublime.",
        "Crystal clear and competitively loud. Perfect.",
        "Mastered to perfection. Don't forget us when you're famous.",
        "The ghosts in the machine approve of this master.",
        "Rendering complete. Sonic excellence achieved.",
        "Your track just graduated from the Mastering Academy.",
        "Wrapped up and ready to rumble.",
        "Loud, proud, and safely exported.",
        "The transients called—they wanted to say thanks.",
        "Bit-perfect and ready for the world.",
        "Mastering complete. Status: Legendary.",
        "Another sonic victory. Well played!",
        "Exported! Now go listen in your car for the final test.",
        "Mastering finished. Go treat your ears to something nice.",
        "That's some high-fidelity heat right there. Done!"
    ]

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
        self.player_ready_wet = np.ascontiguousarray(processed_audio, dtype=np.float32)
        
        self.is_rendering = False
        self.view.status_label.config(text="Preview Ready")
        
        # If currently listening to B (Wet), hotly update the player buffer
        if self.listen_mode == "B":
            self.player.set_buffer(self.player_ready_wet, self.sample_rate)

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
                    'stereo_width_db': float(self.view.width_slider.get()),
                    'drive_low_db': float(self.view.drive_low_slider.get()),
                    'drive_mid_db': float(self.view.drive_mid_slider.get()),
                    'drive_high_db': float(self.view.drive_high_slider.get()),
                    'exciter_bypass': self.view.exciter_bypass_var.get(),
                    'saturation_mode': self.view.sat_mode_combo.get(),
                    'mono_freq': float(self.view.mono_freq_slider.get()),
                    'mono_bypass': self.view.mono_bypass_var.get(),
                    'target_lufs': float(self.view.lufs_slider.get()),
                    'match_eq_fir': self.match_fir_coeff,
                    'match_amount': float(self.view.match_amount_slider.get()) / 100.0
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
                        msg = random.choice(self.EXPORT_SUCCESS_MESSAGES)
                        self.view.after(0, lambda m=msg: messagebox.showinfo("Success", m))
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
                    'stereo_width_db': float(self.view.width_slider.get()),
                    'drive_low_db': float(self.view.drive_low_slider.get()),
                    'drive_mid_db': float(self.view.drive_mid_slider.get()),
                    'drive_high_db': float(self.view.drive_high_slider.get()),
                    'exciter_bypass': self.view.exciter_bypass_var.get(),
                    'saturation_mode': self.view.sat_mode_combo.get(),
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

    def perform_auto_match_sync(self, progress_callback=None):
        """
        Synchronous version of auto-match for use inside a worker thread.
        returns final_gain
        """
        target = float(self.view.lufs_slider.get())
        
        # 1. Take current settings
        params = {
            'air_gain_db': float(self.view.air_slider.get()),
            'stereo_width_db': float(self.view.width_slider.get()),
            'drive_low_db': float(self.view.drive_low_slider.get()),
            'drive_mid_db': float(self.view.drive_mid_slider.get()),
            'drive_high_db': float(self.view.drive_high_slider.get()),
            'exciter_bypass': self.view.exciter_bypass_var.get(),
            'saturation_mode': self.view.sat_mode_combo.get(),
            'mono_freq': float(self.view.mono_freq_slider.get()),
            'mono_bypass': self.view.mono_bypass_var.get(),
            'match_eq_fir': self.match_fir_coeff,
            'match_amount': float(self.view.match_amount_slider.get()) / 100.0,
            'glue_db': float(self.view.glue_slider.get())
        }
        
        current_gain = float(self.view.gain_slider.get())
        actual_lufs = -60.0 # fallback
        
        for i in range(3):
            if progress_callback:
                progress_callback(i * 30, f"Analyzing Pass {i+1}/3...")
                
            params['input_gain_db'] = current_gain
            test_output = self.processor.process(self.dry_audio, **params)
            actual_lufs = self.processor.loudness_analyzer.analyze(test_output, self.sample_rate)
            
            diff = target - actual_lufs
            if abs(diff) < 0.2:
                break
                
            current_gain += diff
            current_gain = max(-24.0, min(12.0, current_gain))

        if progress_callback:
            progress_callback(100, f"Matched to {actual_lufs:.1f} LUFS")
            
        def update_ui():
            self.view.gain_slider.set(current_gain)
            self.view.status_label.config(text=f"Matched to {actual_lufs:.1f} LUFS")
            self.trigger_render()
            
        self.view.after(0, update_ui)
        return current_gain, actual_lufs

    def on_landing_battle(self):
        """Action for the 'Preset Battle' button on the landing page."""
        if self.dry_audio is None:
            messagebox.showwarning("Warning", "Please load an audio file first!")
            return
            
        self.start_preset_battle() # Pop up the battle dialog

    def on_landing_hands_on(self):
        """Action for the 'Hands-on' button on the landing page."""
        if self.dry_audio is None:
            messagebox.showwarning("Warning", "Please load an audio file first!")
            return
            
        names = preset_manager.get_preset_names()
        HandsOnSetupDialog(self.view, self, names, self._on_setup_finished)

    def _on_setup_finished(self, preset_name):
        """Callback from Hands-on Setup dialog."""
        # The HandsOnSetupDialog already applied the preset and synchronously 
        # auto-matched the gain. We just need to hide the landing and reveal the console.
        
        # Hide landing
        self.view.show_hands_on()

    def start_preset_battle(self):
        if self.dry_audio is None:
            messagebox.showwarning("Warning", "Please load an audio file first!")
            return
            
        names = preset_manager.get_preset_names()
        PresetBattleDialog(self.view, names, self.on_battle_start)

    def on_battle_start(self, selected_presets, output_dir, use_spatial):
        msg = f"This will master your track using {len(selected_presets)} different presets.\n\n"
        msg += "It may take several minutes depending on your CPU.\n"
        msg += "Do you want to proceed?"
        if not messagebox.askyesno("Confirm Batch", msg):
            return
            
        self.batch_win = BatchProgressWindow(self.view, self.cancel_batch)
        self.batch_running = True
        
        threading.Thread(target=self._run_batch_mastering, args=(selected_presets, output_dir, use_spatial), daemon=True).start()

    def cancel_batch(self):
        self.batch_running = False

    def _run_batch_mastering(self, presets, output_dir, use_spatial):
        results = {"Original": self.dry_audio}
        target_lufs = float(self.view.lufs_slider.get())
        
        total_steps = len(presets)
        
        try:
            for i, name in enumerate(presets):
                if not self.batch_running: break
                
                self.view.after(0, lambda: self.batch_win.update_progress(f"Processing: {name}...", (i / total_steps) * 100))
                
                # Load preset data
                p_data = preset_manager.get_preset(name)
                
                # Map JSON keys to processor arguments (handling both long and short names)
                params = {
                    'input_gain_db': float(p_data.get('input_gain', 0.0)),
                    'air_gain_db': float(p_data.get('air_gain', p_data.get('air_gain_db', p_data.get('air', 2.0)))),
                    'stereo_width_db': float(p_data.get('stereo_width', p_data.get('stereo_width_db', p_data.get('width', 1.5 if use_spatial else 0.0)))),
                    'drive_low_db': float(p_data.get('drive', p_data.get('drive_low_db', p_data.get('drive_low', 0.0)))),
                    'drive_mid_db': float(p_data.get('drive', p_data.get('drive_mid_db', p_data.get('drive_mid', 0.0)))),
                    'drive_high_db': float(p_data.get('drive', p_data.get('drive_high_db', p_data.get('drive_high', 0.0)))),
                    'exciter_bypass': bool(p_data.get('exciter_bypass', False)),
                    'saturation_mode': str(p_data.get('saturation_mode', 'Soft Clip')),
                    'mono_freq': float(p_data.get('mono_freq', 150.0 if use_spatial else 20.0)),
                    'mono_bypass': bool(p_data.get('mono_bypass', False)) if not use_spatial else False,
                    'match_eq_fir': self.match_fir_coeff,
                    'match_amount': float(p_data.get('match_amount', float(self.view.match_amount_slider.get()))) / 100.0,
                    'target_lufs': float(p_data.get('target_lufs', target_lufs)),
                    'glue_db': float(p_data.get('glue', p_data.get('glue_db', float(self.view.glue_slider.get()))))
                }
                
                # Perform the master
                mastered = self.processor.process(self.dry_audio, **params)
                results[name] = mastered
                
                # Save to disk
                # Sanitize name for illegal characters in filename (Windows)
                safe_name = "".join([c if c.isalnum() or c in (' ', '_', '-') else '_' for c in name])
                filename = f"Master_{safe_name.replace(' ', '_')}.wav"
                save_path = os.path.join(output_dir, filename)
                write_audio(save_path, self.sample_rate, mastered, format='WAV', subtype='PCM_24')
                
            if self.batch_running:
                self.view.after(0, lambda: self.batch_win.destroy())
                self.view.after(0, lambda: ComparisonConsole(self.view, results, self.sample_rate, self))
                
        except Exception as e:
            self.view.after(0, lambda: messagebox.showerror("Batch Error", f"Process failed:\n{e}"))
            if hasattr(self, 'batch_win'):
                self.view.after(0, lambda: self.batch_win.destroy())

    def run(self):
        self._sample_wave_loop() # Kick off visual loop safely
        self.view.mainloop()
