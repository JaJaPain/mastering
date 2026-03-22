import pygame
import pyaudio
import numpy as np
import math
import time
import sys

# --- Configuration ---
WIDTH = 1024
HEIGHT = 768
FPS = 60
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Frequencies for bands (in Hz)
BASS_RANGE = (20, 250)
MID_RANGE = (250, 4000)
TREBLE_RANGE = (4000, 20000)

class AudioProcessor:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.audio_callback
        )
        self.bass = 0.0
        self.mids = 0.0
        self.treble = 0.0
        
        # Smoothing factors limit jarring frame-to-frame jumps
        self.smoothing_up = 0.8
        self.smoothing_down = 0.2
        
        self.running = True

    def audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback used by PyAudio to process audio chunks in a separate thread.
        This prevents blocking the Pygame render loop.
        """
        if not self.running:
            return (None, pyaudio.paComplete)
            
        try:
            # Convert byte data to 16-bit integers
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Apply hanning window for a smoother FFT
            windowed_data = audio_data * np.hanning(len(audio_data))
            
            # Perform Fast Fourier Transform
            fft_data = np.abs(np.fft.rfft(windowed_data))
            fft_freqs = np.fft.rfftfreq(len(windowed_data), 1.0/RATE)
            
            # Helper to calculate mean energy within a specific frequency band
            def get_energy(freq_range):
                mask = (fft_freqs >= freq_range[0]) & (fft_freqs <= freq_range[1])
                return np.mean(fft_data[mask]) if np.any(mask) else 0.0

            # Raw energy values
            raw_bass = get_energy(BASS_RANGE)
            raw_mids = get_energy(MID_RANGE)
            raw_treble = get_energy(TREBLE_RANGE)
            
            # Normalize and scale (Adjust denominators to calibrate mic sensitivity)
            raw_bass = min(1.0, raw_bass / 50000.0)
            raw_mids = min(1.0, raw_mids / 30000.0)
            raw_treble = min(1.0, raw_treble / 15000.0)

            # Apply smoothing (faster attack, slower decay)
            self.bass = self.smooth(self.bass, raw_bass)
            self.mids = self.smooth(self.mids, raw_mids)
            self.treble = self.smooth(self.treble, raw_treble)
            
        except Exception:
            pass

        return (in_data, pyaudio.paContinue)

    def smooth(self, current, target):
        if target > current:
            return current + (target - current) * self.smoothing_up
        else:
            return current + (target - current) * self.smoothing_down

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


def draw_branch(surface, x, y, angle, length, depth, max_depth, audio_data):
    """
    Recursively draw a branch of the fractal tree.
    """
    if depth == 0 or length < 2:
        return

    # 1. Trigonometry for End Point Calculation
    # Using simple SOH CAH TOA to find the opposite (y) and adjacent (x) sides.
    # Note: math.sin/cos use radians. Negative on y since Pygame Y-axis moves downward.
    end_x = x + length * math.cos(angle)
    end_y = y - length * math.sin(angle)

    # Thicker branches closer to the trunk
    thickness = max(1, int(length / 8))
    
    # --- Audio Reactivity Mappings ---
    
    # MIDS: Alter split angle, simulating "breathing" expanding/contracting
    base_split = math.pi / 7 # ~25.7 degrees
    split_angle = base_split + (audio_data['mids'] * 0.4)
    
    # TREBLE: Enhance "leaves" at maximum depth
    color = (80, 70, 60) # Default trunk/lower branch color (brownish)
    
    if depth <= 2: 
        # Base leaf color
        base_r, base_g, base_b = 30, 150, 40
        # Add pulsing treble intensity
        treble_intensity = int(audio_data['treble'] * 255)
        
        color = (
            min(255, base_r + treble_intensity // 2), 
            min(255, base_g + treble_intensity), 
            min(255, base_b + treble_intensity // 2)
        )
        # Pulse leaves thickness slightly
        thickness = max(1, thickness + int(audio_data['treble'] * 6))
    elif depth > max_depth - 2:
        # Gradually shift early trunk to slightly brighter brownish based on bass
        trunk_pulse = int(audio_data['bass'] * 50)
        color = (min(255, 80 + trunk_pulse), min(255, 70 + trunk_pulse), min(255, 60 + trunk_pulse))

    # Draw this segment
    pygame.draw.line(surface, color, (x, y), (end_x, end_y), thickness)

    # Next branches are scaled down
    new_length = length * 0.72 
    
    # Recursively branch left and right
    draw_branch(surface, end_x, end_y, angle - split_angle, new_length, depth - 1, max_depth, audio_data)
    draw_branch(surface, end_x, end_y, angle + split_angle, new_length, depth - 1, max_depth, audio_data)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sensory Fractal Tree: Plantz")
    clock = pygame.time.Clock()

    # Initialize and kickstart Audio listening in its PyAudio thread
    audio_proc = AudioProcessor()
    audio_proc.stream.start_stream()

    start_time = time.time()
    growth_duration = 18.0 # Growth completes after 18 seconds

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # --- Growth Mechanic ---
        elapsed = time.time() - start_time
        # clamp growth_factor tightly from [0.0 to 1.0]
        growth_factor = min(1.0, elapsed / growth_duration)
        
        # Max recursion depth caps at 11 based on growth. Starts at depth 1 (a sprout)
        current_max_depth = max(1, int(growth_factor * 11))
        # Trunk length scales up as it grows
        base_length = max(10, growth_factor * 200) 

        # Snapshot smoothed audio thread data to guarantee sync for this drawing frame
        current_audio = {
            'bass': audio_proc.bass,
            'mids': audio_proc.mids,
            'treble': audio_proc.treble
        }

        # Clear screen every frame (Deep void background)
        screen.fill((12, 10, 18))

        # BASS: Affects the root angle. PI/2 points straight up.
        # It creates a steady swaying back and forth driven by low-end rumble.
        sway_offset = (current_audio['bass'] * 0.6) - 0.3
        root_angle = (math.pi / 2) + sway_offset

        # Start from the bottom center of the screen
        start_x = WIDTH // 2
        start_y = HEIGHT

        # Fire recursive fractal!
        draw_branch(
            surface=screen,
            x=start_x,
            y=start_y,
            angle=root_angle,
            length=base_length,
            depth=current_max_depth,
            max_depth=current_max_depth,
            audio_data=current_audio
        )

        pygame.display.flip()
        # Ensure smooth 60 FPS update
        clock.tick(FPS)

    # Graceful shutdown
    audio_proc.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
