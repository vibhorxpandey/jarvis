import sys
import time

from config import OWNER_NAME, GREETING, TTS_RATE, TTS_VOLUME, LISTEN_TIMEOUT
from voice_engine import VoiceEngine
from wake_detector import WakeDetector
from command_handler import CommandHandler

_BANNER = r"""
  ____  ____  ____  ____    __    _  _
 ( ___)(  _ \(_  _)(  _ \  /__\  ( \/ )
  )__)  )   / _)(_  )(_) )/(__)\  \  /
 (__)  (_)\_)(____)(____ /(__)(__)  \/

  Female Replacement Intelligent Digital
  Assistant Youth  —  Personal AI to: {}
"""


def main():
    print(_BANNER.format(OWNER_NAME))

    voice = VoiceEngine(rate=TTS_RATE, volume=TTS_VOLUME)
    detector = WakeDetector()
    handler = CommandHandler(voice)

    voice.speak(
        f"F.R.I.D.A.Y. is now online. Good day, {OWNER_NAME}. "
        f"Say my name whenever you need me."
    )

    running = True
    while running:
        try:
            detector.monitor()

            voice.speak(GREETING)
            command = voice.listen(timeout=LISTEN_TIMEOUT)

            if command:
                running = handler.process(command)
            else:
                voice.speak(
                    f"I didn't catch that. "
                    f"Say my name whenever you need me, {OWNER_NAME}."
                )

        except KeyboardInterrupt:
            voice.speak(f"Manual shutdown. Goodbye, {OWNER_NAME}.")
            running = False
        except Exception as exc:
            print(f"  [Error] {exc}")
            time.sleep(0.5)

    detector.cleanup()
    print("\n[FRIDAY offline]\n")


if __name__ == "__main__":
    main()
