"""
Spectral Profile Library
------------------------
Handles saving, loading, and listing of Long-Term Average Spectrum (LTAS)
fingerprints extracted from reference audio tracks.

Profiles are stored as JSON files in the /profiles directory.
Each profile contains the normalized frequency and magnitude data needed to
reconstruct a matching EQ FIR filter without needing the original audio file.
"""

import json
import os
import numpy as np

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "profiles")


def _ensure_dir():
    os.makedirs(PROFILES_DIR, exist_ok=True)


def save_profile(name: str, freqs: np.ndarray, ltas_db: np.ndarray, sample_rate: int, source_file: str = "") -> bool:
    """
    Saves a normalized LTAS fingerprint to a JSON profile file.

    Parameters
    ----------
    name        : Human-readable name for the profile (used as filename).
    freqs       : 1-D array of frequency bins (Hz).
    ltas_db     : 1-D normalized LTAS in dBFS (mean-subtracted so volume is irrelevant).
    sample_rate : Sample rate the spectrum was extracted at.
    source_file : Optional path to the original audio file (for reference only).
    """
    _ensure_dir()
    profile = {
        "name": name,
        "sample_rate": int(sample_rate),
        "source_file": os.path.basename(source_file),
        "freqs": freqs.tolist(),
        "ltas_db": ltas_db.tolist(),
    }
    safe_name = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name).strip()
    path = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    try:
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
        return True
    except Exception as e:
        print(f"[spectral_profiles] Failed to save profile: {e}")
        return False


def load_profile(name_or_path: str) -> dict | None:
    """
    Loads a spectral profile by display name or full path.
    Returns a dict with keys: name, sample_rate, freqs (ndarray), ltas_db (ndarray).
    """
    _ensure_dir()
    # Check if it's a full path already
    if os.path.isfile(name_or_path):
        path = name_or_path
    else:
        safe_name = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name_or_path).strip()
        path = os.path.join(PROFILES_DIR, f"{safe_name}.json")

    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        data["freqs"] = np.array(data["freqs"])
        data["ltas_db"] = np.array(data["ltas_db"])
        return data
    except Exception as e:
        print(f"[spectral_profiles] Failed to load profile: {e}")
        return None


def list_profiles() -> list[str]:
    """Returns a sorted list of profile display names found in /profiles."""
    _ensure_dir()
    names = []
    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith(".json"):
            # Try to read the 'name' field for a clean display name
            try:
                with open(os.path.join(PROFILES_DIR, fname), "r") as f:
                    data = json.load(f)
                names.append(data.get("name", fname.replace(".json", "")))
            except Exception:
                names.append(fname.replace(".json", ""))
    return names


def delete_profile(name: str) -> bool:
    """Deletes a profile file by display name."""
    _ensure_dir()
    safe_name = "".join(c if (c.isalnum() or c in " _-") else "_" for c in name).strip()
    path = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"[spectral_profiles] Failed to delete: {e}")
    return False
