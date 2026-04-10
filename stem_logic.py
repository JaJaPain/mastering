"""
stem_logic.py — Self-contained stem separation module.

Uses Facebook's Demucs via subprocess (no direct torch/demucs imports).
Designed as a zero-coupling "black box": call run_separation(), then poll
the output directory for finished stems.

Stems produced (default htdemucs model):
    vocals.wav | drums.wav | bass.wav | other.wav
"""

import os
import subprocess
import threading
import logging
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
#  Module-level logger — consumers can attach their own handlers if desired
# ---------------------------------------------------------------------------
_log = logging.getLogger("stem_logic")
if not _log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)


class StemWorkerError(Exception):
    """Raised when the Demucs subprocess exits with a non-zero code."""


class StemWorker:
    """
    Launches Demucs in the background to split an audio file into stems.

    Parameters
    ----------
    model : str
        Demucs model name.  Defaults to ``"htdemucs"`` (hybrid transformer).
        Other options include ``"htdemucs_ft"`` (fine-tuned, slower but
        higher quality) and ``"mdx_extra_q"``.
    device : str or None
        Force a compute device (``"cpu"`` or ``"cuda"``).
        ``None`` lets Demucs auto-detect.
    output_format : str
        Stem file format — ``"wav"`` (default), ``"flac"``, or ``"mp3"``.
    shifts : int
        Number of random time shifts for prediction averaging.
        Higher = better quality, slower.  ``1`` is the fast default.
    on_complete : callable or None
        Optional callback invoked with ``(output_dir: str)`` when the
        separation finishes successfully.
    on_error : callable or None
        Optional callback invoked with ``(error: Exception)`` if separation
        fails.

    Example
    -------
    >>> worker = StemWorker(on_complete=lambda p: print(f"Done → {p}"))
    >>> worker.run_separation("song.wav", "./stems")
    """

    DEMUCS_CMD = "demucs"          # must be on PATH or in the active venv
    _DEFAULT_MODEL = "htdemucs"
    _VALID_FORMATS = {"wav", "flac", "mp3"}

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        device: str | None = None,
        output_format: str = "wav",
        shifts: int = 1,
        on_complete=None,
        on_error=None,
    ):
        if output_format not in self._VALID_FORMATS:
            raise ValueError(
                f"output_format must be one of {self._VALID_FORMATS}, "
                f"got '{output_format}'"
            )

        self.model = model
        self.device = device
        self.output_format = output_format
        self.shifts = max(1, shifts)
        self.on_complete = on_complete
        self.on_error = on_error

        # Internal state
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def run_separation(self, input_path: str, output_path: str) -> None:
        """
        Kick off stem separation in a background thread.

        Parameters
        ----------
        input_path : str
            Path to the input audio file (wav, mp3, flac, etc.).
        output_path : str
            Directory where the stems will be written.  The final layout is::

                output_path/
                  vocals.<fmt>
                  drums.<fmt>
                  bass.<fmt>
                  other.<fmt>
        """
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)

        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        os.makedirs(output_path, exist_ok=True)

        self._thread = threading.Thread(
            target=self._worker,
            args=(input_path, output_path),
            daemon=True,
            name="StemWorker-Thread",
        )
        self._thread.start()
        _log.info("Stem separation started in background thread.")

    @property
    def is_running(self) -> bool:
        """Return True if the background separation is still in progress."""
        return self._thread is not None and self._thread.is_alive()

    def wait(self, timeout: float | None = None) -> None:
        """Block until the background separation finishes."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def cancel(self) -> None:
        """Attempt to terminate a running Demucs process."""
        if self._process is not None and self._process.poll() is None:
            _log.warning("Cancelling running Demucs process (PID %d)…", self._process.pid)
            self._process.terminate()

    # ------------------------------------------------------------------
    #  Internal
    # ------------------------------------------------------------------

    def _build_command(self, input_path: str, temp_out: str) -> list[str]:
        """Assemble the Demucs CLI invocation."""
        cmd = [
            self.DEMUCS_CMD,
            "-n", self.model,
            "--out", temp_out,
            "--shifts", str(self.shifts),
            "--clip-mode", "rescale",       # avoid clipping artefacts
        ]

        if self.output_format != "wav":
            cmd += ["--mp3"] if self.output_format == "mp3" else ["--flac"]

        if self.device:
            cmd += ["-d", self.device]

        cmd.append(input_path)
        return cmd

    def _worker(self, input_path: str, output_path: str) -> None:
        """
        Thread target — runs Demucs and relocates stems to *output_path*.

        Demucs writes to ``<temp_out>/<model>/<track_name>/``.
        We flatten that into ``<output_path>/<stem>.<fmt>``.
        """
        # Use a temp staging directory beside the final output to avoid
        # collisions with any existing content.
        staging_dir = os.path.join(output_path, "__demucs_staging__")
        os.makedirs(staging_dir, exist_ok=True)

        cmd = self._build_command(input_path, staging_dir)
        _log.info("Running: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Stream Demucs output to our logger in real time
            for line in self._process.stdout:            # type: ignore[union-attr]
                stripped = line.rstrip()
                if stripped:
                    _log.info("[demucs] %s", stripped)

            return_code = self._process.wait()

            if return_code != 0:
                raise StemWorkerError(
                    f"Demucs exited with code {return_code}"
                )

            # ---- Flatten the nested Demucs output ----
            # Expected structure: <staging_dir>/<model>/<track_stem_name>/
            track_name = Path(input_path).stem
            nested = os.path.join(staging_dir, self.model, track_name)

            if not os.path.isdir(nested):
                raise StemWorkerError(
                    f"Expected stem directory not found: {nested}"
                )

            for stem_file in os.listdir(nested):
                src = os.path.join(nested, stem_file)
                dst = os.path.join(output_path, stem_file)
                shutil.move(src, dst)
                _log.info("  ✓ %s", stem_file)

            # Clean up the staging tree
            shutil.rmtree(staging_dir, ignore_errors=True)

            _log.info("Stem separation complete → %s", output_path)

            if self.on_complete:
                self.on_complete(output_path)

        except Exception as exc:
            _log.error("Stem separation failed: %s", exc)
            shutil.rmtree(staging_dir, ignore_errors=True)
            if self.on_error:
                self.on_error(exc)
