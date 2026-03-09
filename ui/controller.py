import threading
import os
import queue
import numpy as np
from tkinter import filedialog, messagebox
from ui.views.main_view import MainView
from engine.dsp.processor import AudioProcessor
from engine.io.wav_io import read_wav, write_wav
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
        
        self.view.export_btn.config(command=self.export_master)
        self.view.load_btn.config(command=self.load_audio_file)
        self.view.toggle_vis_btn.config(command=self.toggle_visuals)
        
        # Playback events
        self.view.play_btn.config(command=self.play_audio)
        self.view.stop_btn.config(command=self.stop_audio)
        self.view.btn_a.config(command=lambda: self.set_listen_mode("A"))
        self.view.btn_b.config(command=lambda: self.set_listen_mode("B"))
        
        # Sliders: Trigger debounced render
        self.view.gain_slider.config(command=self.on_slider_change)
        self.view.air_slider.config(command=self.on_slider_change)
        self.view.drive_slider.config(command=self.on_slider_change)
        self.view.lufs_slider.config(command=self.on_slider_change)
        
        # Presets Bindings
        self.refresh_presets()
        self.view.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)
        self.view.save_preset_btn.config(command=self.on_save_preset)
        
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
            self.view.drive_slider.set(preset_data.get("drive", preset_data.get("Clipper Drive (dB)", 0.0)))
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
                "drive": float(self.view.drive_slider.get()),
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
                self.sample_rate, data = read_wav(file_path)
                # Ensure audio is 2D for easier management
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                    
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
                
                wet_mono = None
                if self.wet_audio is not None and len(self.wet_audio) > frame:
                    wet_slice = self.wet_audio[frame:frame+chunk_size]
                    wet_mono = np.mean(wet_slice, axis=1) if wet_slice.shape[1] > 1 else wet_slice[:, 0]
                    wet_mono = np.nan_to_num(wet_mono, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Pipe cleanly padded array into thread queue
                self.view.vis_queue.put({'type': 'wave', 'data': (dry_mono, wet_mono, self.listen_mode)})
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
            'drive_db': float(self.view.drive_slider.get())
        }
        
        threading.Thread(target=self._render_task, args=(params,), daemon=True).start()
        
    def _render_task(self, params):
        try:
            audio = self.dry_audio
            if audio.shape[1] == 1:
                # Mono
                processed = self.processor.process(audio[:, 0], **params)
                processed_audio = processed.reshape(-1, 1)
                
                rms = self.processor.calculate_rms(processed)
                peak = 20 * np.log10(max(np.max(np.abs(np.nan_to_num(processed))), 1e-10))
                self.view.vis_queue.put({'type': 'meters', 'data': (rms, peak, rms, peak)})
            else:
                # Stereo
                proc_l = self.processor.process(audio[:, 0], **params)
                proc_r = self.processor.process(audio[:, 1], **params)
                processed_audio = np.vstack((proc_l, proc_r)).T
                
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
        
        orig_name = os.path.basename(self.loaded_file_path)
        default_save = f"Mastered_{orig_name}"
        
        save_path = filedialog.asksaveasfilename(
            title="Export Mastered File",
            initialfile=default_save,
            defaultextension=".wav",
            filetypes=(("WAV Files", "*.wav"), ("All Files", "*.*"))
        )
        
        if save_path:
            try:
                # Apply Final target LUFS on export only (heavy CPU)
                target_lufs = float(self.view.lufs_slider.get())
                
                # We need to run full render path with target lufs enabled so clipping happens cleanly after LUFS
                # It's better to process the whole audio data to get precise file LUFS than frame by frame.
                params = {
                    'input_gain_db': float(self.view.gain_slider.get()),
                    'air_gain_db': float(self.view.air_slider.get()),
                    'drive_db': float(self.view.drive_slider.get()),
                    'target_lufs': target_lufs
                }
                
                # Single background task for heavy export
                def export_task():
                    try:
                        audio = self.dry_audio
                        if audio.shape[1] == 1:
                            final_audio = self.processor.process(audio[:, 0], **params).reshape(-1, 1)
                        else:
                            proc_l = self.processor.process(audio[:, 0], **params)
                            proc_r = self.processor.process(audio[:, 1], **params)
                            final_audio = np.vstack((proc_l, proc_r)).T
                            
                        write_wav(save_path, self.sample_rate, final_audio)
                        self.view.after(0, lambda: self.view.status_label.config(text=f"Exported to {save_path}"))
                        self.view.after(0, lambda: messagebox.showinfo("Success", "Mastering Export Complete!"))
                    except Exception as err:
                        self.view.after(0, lambda e=err: messagebox.showerror("Export Error", f"Failed to save:\n{e}"))
                        
                threading.Thread(target=export_task, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to start export:\n{e}")
                self.view.status_label.config(text="Export failed.")

    def run(self):
        self._sample_wave_loop() # Kick off visual loop safely
        self.view.mainloop()
