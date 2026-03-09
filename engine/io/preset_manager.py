import json
import os

PRESETS_FILE = os.path.join(os.path.dirname(__file__), "presets.json")

def load_presets():
    """Loads presets from the JSON file."""
    if not os.path.exists(PRESETS_FILE):
        return {}
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load presets: {e}")
        return {}

def save_presets(presets_data):
    """Saves the current presets dictionary to the JSON file."""
    try:
        with open(PRESETS_FILE, "w") as f:
            json.dump(presets_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Failed to save presets: {e}")
        return False
        
def get_preset_names():
    """Returns a list of available preset names."""
    presets = load_presets()
    if "presets" in presets:
        return list(presets["presets"].keys())
    return list(presets.keys())
    
def get_preset(name):
    """Returns the dictionary data for a specific preset."""
    presets = load_presets()
    if "presets" in presets:
        return presets["presets"].get(name, None)
    return presets.get(name, None)
    
def save_custom_preset(name, data):
    """Adds or updates a preset and saves it to disk."""
    presets = load_presets()
    if "presets" in presets:
        presets["presets"][name] = data
    else:
        presets[name] = data
    return save_presets(presets)
