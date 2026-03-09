import sounddevice as sd
import numpy as np

class AudioPlayer:
    """
    Handles real-time audio playback using sounddevice.
    Supports seamless hot-swapping of the audio buffer for A/B testing.
    """
    def __init__(self):
        self.stream = None
        self.buffer = None
        self.sample_rate = 44100
        self.current_frame = 0
        self.is_playing = False
        
    def set_buffer(self, buffer: np.ndarray, sample_rate: int):
        """
        Updates the playback buffer. 
        If currently playing, the audio stream seamlessly reads from the new buffer.
        """
        # Ensure the buffer is 2D for sounddevice (samples, channels)
        if buffer.ndim == 1:
            buffer = buffer.reshape(-1, 1)
            
        # Crucial for stable sounddevice output: lock it into 32-bit float C-contiguous structure
        self.buffer = np.ascontiguousarray(buffer, dtype=np.float32)
        self.sample_rate = sample_rate
        
        if self.buffer is not None and self.current_frame >= len(self.buffer):
            self.current_frame = 0

    def play(self):
        if self.buffer is None or self.is_playing:
            return
            
        def callback(outdata, frames, time, status):
            if status:
                pass # Ignore underflows in simple playback
            
            chunksize = min(len(self.buffer) - self.current_frame, frames)
            if chunksize <= 0:
                outdata.fill(0)
                raise sd.CallbackStop()
                
            outdata[:chunksize] = self.buffer[self.current_frame:self.current_frame + chunksize]
            if chunksize < frames:
                outdata[chunksize:] = 0
                raise sd.CallbackStop()
                
            self.current_frame += chunksize

        channels = self.buffer.shape[1]
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=channels,
            callback=callback,
            finished_callback=self._on_finished
        )
        self.stream.start()
        self.is_playing = True
        
    def _on_finished(self):
        self.is_playing = False
        self.current_frame = 0
        
    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_playing = False
        self.current_frame = 0
