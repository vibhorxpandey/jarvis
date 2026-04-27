import numpy as np
import sounddevice as sd
import speech_recognition as sr

from config import WAKE_WORD

_RATE = 16000
_CHUNK_SECONDS = 3


class WakeDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def monitor(self):
        """Block until the wake word 'Friday' is heard."""
        print(f"\n  [Ready] Say '{WAKE_WORD.capitalize()}' to activate me.")
        while True:
            audio = sd.rec(int(_CHUNK_SECONDS * _RATE), samplerate=_RATE, channels=1, dtype="int16")
            sd.wait()
            raw = sr.AudioData(audio.flatten().tobytes(), _RATE, 2)
            try:
                text = self.recognizer.recognize_google(raw).lower()
                if WAKE_WORD in text:
                    print(f"  Wake word detected: '{text}'")
                    return
            except Exception:
                pass

    def cleanup(self):
        pass
