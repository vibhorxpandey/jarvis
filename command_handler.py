from datetime import datetime

from app_launcher import AppLauncher
from news_reader import NewsReader
from config import OWNER_NAME


class CommandHandler:
    def __init__(self, voice):
        self.voice = voice
        self.app_launcher = AppLauncher(voice)
        self.news_reader = NewsReader(voice)

    def process(self, command: str) -> bool:
        """Handle a spoken command. Returns False to shut down."""
        if not command:
            return True

        cmd = command.lower().strip()

        # ── Shutdown ──────────────────────────────────────────────────
        if any(w in cmd for w in ["goodbye", "bye", "exit", "stop", "shut down", "power off", "go to sleep"]):
            self.voice.speak(f"Goodbye, {OWNER_NAME}. Powering down systems. It's been a pleasure.")
            return False

        # ── News ──────────────────────────────────────────────────────
        if any(w in cmd for w in ["news", "headlines", "what's happening", "latest news", "current news"]):
            self.news_reader.read_news()
            return True

        # ── Open app / website ────────────────────────────────────────
        if any(w in cmd for w in ["open", "launch", "start", "run", "show"]):
            self.app_launcher.open_from_command(cmd)
            return True

        # ── Time ──────────────────────────────────────────────────────
        if any(w in cmd for w in ["time", "what time"]):
            now = datetime.now()
            self.voice.speak(f"It is {now.strftime('%I:%M %p')}, {OWNER_NAME}.")
            return True

        # ── Date ──────────────────────────────────────────────────────
        if any(w in cmd for w in ["date", "today", "day is it"]):
            now = datetime.now()
            self.voice.speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")
            return True

        # ── Recalibrate mic ───────────────────────────────────────────────
        if any(w in cmd for w in [
            "recalibrate", "calibrate", "voice priority",
            "tune mic", "adjust mic", "fix mic", "my voice",
        ]):
            self.voice.recalibrate()
            return True

        # ── Help ──────────────────────────────────────────────────────
        if any(w in cmd for w in ["help", "what can you do", "commands"]):
            self.voice.speak(
                "Here is what I can do for you. "
                "Say 'open' followed by any app or website to launch it. "
                "Say 'news' to hear the latest headlines. "
                "Say 'time' or 'date' for the current time and date. "
                "Say 'goodbye' to shut me down."
            )
            return True

        # ── Fallback ──────────────────────────────────────────────────
        self.voice.speak(
            f"I didn't quite catch that, {OWNER_NAME}. "
            "Say 'help' if you'd like a list of what I can do."
        )
        return True
