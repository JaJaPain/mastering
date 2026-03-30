"""
youtube_ref.py
--------------
Downloads audio from a YouTube URL using yt-dlp and converts it to a
temporary WAV file suitable for spectral analysis.

Quality note:
    YouTube streams at 128-256 kbps. For reference EQ matching this is
    perfectly adequate — we are analysing broad tonal curves (bass / mid /
    air balance), not microscopic details. The approach is identical to how
    professionals pull reference tracks from streaming services.
"""

import os
import re
import tempfile
import threading
from pathlib import Path


def is_youtube_url(text: str) -> bool:
    """Return True if the string looks like a YouTube URL."""
    text = text.strip()
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?music\.youtube\.com/watch\?.*v=[\w-]+",
    ]
    return any(re.match(p, text, re.IGNORECASE) for p in patterns)


def download_audio_for_reference(
    url: str,
    progress_callback=None,
    done_callback=None,
    error_callback=None,
) -> None:
    """
    Download the best available audio stream from `url` to a temporary WAV
    file, then call `done_callback(tmp_path, video_title)`.

    All network/disk work is done on a background thread so the UI stays
    responsive.

    Args:
        url:               YouTube URL.
        progress_callback: Called with (percent: float, msg: str).
        done_callback:     Called with (wav_path: str, title: str).
        error_callback:    Called with (error_message: str).
    """
    def _worker():
        try:
            import yt_dlp  # imported here so the rest of the app doesn't break if missing
        except ImportError:
            if error_callback:
                error_callback(
                    "yt-dlp is not installed.\n"
                    "Run: pip install yt-dlp  (or reinstall via run.bat)"
                )
            return

        if progress_callback:
            progress_callback(0, "Fetching video info…")

        # Temp directory — cleaned up by the OS eventually
        tmp_dir = tempfile.mkdtemp(prefix="mastering_ref_")
        out_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")

        video_title = "YouTube Reference"

        def _yt_progress_hook(d):
            if d["status"] == "downloading":
                pct_str = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    pct = float(pct_str)
                except ValueError:
                    pct = 0.0
                speed = d.get("_speed_str", "").strip()
                eta   = d.get("_eta_str", "").strip()
                msg = f"Downloading… {pct:.0f}%"
                if speed:
                    msg += f"  {speed}"
                if eta:
                    msg += f"  ETA {eta}"
                if progress_callback:
                    progress_callback(pct * 0.85, msg)  # reserve last 15% for conversion
            elif d["status"] == "finished":
                if progress_callback:
                    progress_callback(85, "Converting to WAV…")

        ydl_opts = {
            # Best audio quality, prefer lossless/high-bitrate formats
            "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_yt_progress_hook],
            # Post-process: convert to WAV via ffmpeg so soundfile can read it
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "0",  # lossless WAV conversion
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", "YouTube Reference")

        # Find the resulting .wav file
        wav_files = list(Path(tmp_dir).glob("*.wav"))
        if not wav_files:
            if error_callback:
                error_callback(
                    "Download finished but no WAV file was produced.\n"
                    "Make sure ffmpeg is installed and on your PATH."
                )
            return

        wav_path = str(wav_files[0])

        if progress_callback:
            progress_callback(100, "Done!")

        if done_callback:
            done_callback(wav_path, video_title)

    threading.Thread(target=_worker, daemon=True).start()
