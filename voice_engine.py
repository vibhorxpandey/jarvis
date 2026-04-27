import threading
import time
from typing import Callable

import numpy as np
import pyttsx3
import sounddevice as sd
import speech_recognition as sr

_RATE      = 16000
_BLOCK     = 1600          # 0.1 s per callback block — low latency, no gaps
_MIN_SPEECH_BLOCKS = 4     # at least 0.4 s of speech before silence check
_SILENCE_BLOCKS    = 12    # 12 × 0.1 s = 1.2 s of silence → stop


class VoiceEngine:
    def __init__(self, rate=172, volume=1.0):
        self.engine = pyttsx3.init()
        self._setup_voice(rate, volume)
        self.recognizer = sr.Recognizer()
        self._speech_thresh  = 0.025   # overwritten by calibrate()
        self._silence_thresh = 0.008

    # ── Voice ─────────────────────────────────────────────────────────

    def _setup_voice(self, rate, volume):
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        voices = self.engine.getProperty("voices")
        for v in voices:
            if any(n in v.name.lower() for n in ["david", "mark", "george"]):
                self.engine.setProperty("voice", v.id)
                return
        for v in voices:
            if "zira" not in v.name.lower() and "female" not in v.name.lower():
                self.engine.setProperty("voice", v.id)
                return

    # ── Calibration ───────────────────────────────────────────────────

    def calibrate(self) -> float:
        """
        Measure ambient noise floor and set adaptive thresholds.
        Call this once at startup (and whenever the user says 'voice priority').
        """
        print("  [Calibrating — stay quiet for 2 seconds...]")
        buf = sd.rec(int(2 * _RATE), samplerate=_RATE, channels=1, dtype="float32")
        sd.wait()
        ambient = float(np.abs(buf).mean())

        # speech must be clearly louder than the room
        self._speech_thresh  = max(ambient * 6.0, 0.012)
        self._silence_thresh = max(ambient * 2.5, 0.005)

        print(
            f"  [Calibrated]  ambient={ambient:.5f}  "
            f"speech_thresh={self._speech_thresh:.5f}  "
            f"silence_thresh={self._silence_thresh:.5f}"
        )
        return ambient

    def recalibrate(self):
        from config import OWNER_NAME
        self.speak("Recalibrating microphone. Please stay quiet for two seconds.")
        self.calibrate()
        self.speak(f"Done. Tuned to your environment, {OWNER_NAME}. Go ahead.")

    # ── TTS ───────────────────────────────────────────────────────────

    def speak(self, text: str):
        print(f"\n  FRIDAY: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
        time.sleep(0.6)   # let speaker echo die before reopening mic

    # ── STT ───────────────────────────────────────────────────────────

    def listen(
        self,
        timeout: int = 8,
        phrase_limit: int = 12,
        level_cb: Callable[[float], None] | None = None,
    ) -> str | None:
        """
        Stream audio via InputStream (no inter-chunk gaps), detect speech
        with adaptive thresholds, then send the captured audio to Google STT.
        """
        print(
            f"  [Listening...  "
            f"speech={self._speech_thresh:.4f}  "
            f"silence={self._silence_thresh:.4f}]"
        )

        chunks: list[np.ndarray] = []
        speech_blocks  = 0
        silence_blocks = 0
        is_speech      = False
        timed_out      = False
        done           = threading.Event()
        t_start        = time.time()

        def callback(indata: np.ndarray, frames: int, t, status):
            nonlocal is_speech, speech_blocks, silence_blocks, timed_out

            energy = float(np.abs(indata).mean())
            if level_cb:
                level_cb(energy)

            if not is_speech:
                if energy > self._speech_thresh:
                    is_speech = True
                    chunks.append(indata.copy())
                    speech_blocks = 1
                    print(f"  [Speech detected]  energy={energy:.4f}")
                elif time.time() - t_start > timeout:
                    timed_out = True
                    done.set()
            else:
                chunks.append(indata.copy())
                speech_blocks += 1

                if energy < self._silence_thresh:
                    silence_blocks += 1
                    if silence_blocks >= _SILENCE_BLOCKS and speech_blocks >= _MIN_SPEECH_BLOCKS:
                        done.set()
                else:
                    silence_blocks = 0

                if speech_blocks * (_BLOCK / _RATE) >= phrase_limit:
                    done.set()

        with sd.InputStream(
            callback=callback,
            samplerate=_RATE,
            channels=1,
            blocksize=_BLOCK,
            dtype="float32",
        ):
            done.wait(timeout=timeout + 2)

        if timed_out or not chunks:
            print("  [Timeout — no speech detected]")
            return None

        pcm = (np.concatenate(chunks).flatten() * 32767).astype(np.int16)
        audio_data = sr.AudioData(pcm.tobytes(), _RATE, 2)

        try:
            text = self.recognizer.recognize_google(audio_data).lower()
            from config import OWNER_NAME
            print(f"  {OWNER_NAME}: {text}")
            return text
        except sr.UnknownValueError:
            print("  [Not understood — try speaking more clearly or say 'voice priority']")
            return None
        except sr.RequestError as exc:
            print(f"  [API error: {exc}]")
            return None
