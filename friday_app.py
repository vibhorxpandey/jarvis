import threading
import time

from config import OWNER_NAME, GREETING, TTS_RATE, TTS_VOLUME, LISTEN_TIMEOUT
from gui import FridayGUI
from voice_engine import VoiceEngine
from wake_detector import WakeDetector
from command_handler import CommandHandler


class FridayApp:
    def __init__(self):
        self.gui      = FridayGUI()
        self.voice    = VoiceEngine(rate=TTS_RATE, volume=TTS_VOLUME)
        self.detector = WakeDetector()
        self.handler  = CommandHandler(self.voice)

        # Wrap speak() so every response also appears in the GUI log
        _orig = self.voice.speak

        def _speak(text: str):
            self.gui.set_status("SPEAKING")
            self.gui.add_message("FRIDAY", text)
            _orig(text)
            self.gui.set_status("STANDBY")

        self.voice.speak = _speak

        # Give the GUI 500 ms to fully render, then start the logic thread
        self.gui.root.after(500, self._start_thread)

    def _start_thread(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        # ── Step 1: calibrate mic (runs inside the thread, GUI already up) ──
        self.gui.set_status("CALIBRATING")
        self.gui.add_message("FRIDAY", "Calibrating microphone — please stay quiet...")
        self.voice.calibrate()                     # ← sets adaptive thresholds

        # ── Step 2: greet ─────────────────────────────────────────────
        self.voice.speak(
            f"F.R.I.D.A.Y. online. Microphone calibrated. "
            f"Good day, {OWNER_NAME}. Say my name whenever you need me."
        )

        # ── Main loop ─────────────────────────────────────────────────
        running = True
        while running:
            try:
                self.gui.set_status("LISTENING")
                self.detector.monitor()

                self.voice.speak(GREETING)

                self.gui.set_status("LISTENING")
                command = self.voice.listen(
                    timeout=LISTEN_TIMEOUT,
                    level_cb=self.gui.set_audio_level,
                )

                if command:
                    self.gui.add_message(OWNER_NAME, command)
                    self.gui.set_status("PROCESSING")
                    running = self.handler.process(command)
                else:
                    self.voice.speak(
                        f"I didn't catch that, {OWNER_NAME}. "
                        "Say 'voice priority' if I'm having trouble hearing you."
                    )

            except Exception as exc:
                print(f"[Error] {exc}")
                time.sleep(0.5)

        self.gui.root.after(1500, self.gui.root.destroy)

    def run(self):
        self.gui.run()


if __name__ == "__main__":
    FridayApp().run()
