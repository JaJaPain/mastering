import sys
try:
    import moviepy.editor
    print("Moviepy import successful")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
