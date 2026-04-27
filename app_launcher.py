import os
import re
import subprocess
import webbrowser


# name (lower) → shell command or URL
_APPS: dict[str, str] = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",

    # Windows built-ins
    "notepad": "notepad",
    "calculator": "calc",
    "paint": "mspaint",
    "file explorer": "explorer",
    "explorer": "explorer",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "terminal": "wt",
    "windows terminal": "wt",
    "snipping tool": "snippingtool",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "maps": "bingmaps:",
    "store": "ms-windows-store:",
    "calendar": "outlookcal:",

    # Office (works only if installed)
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "teams",
    "onenote": "onenote",

    # Dev tools
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",

    # Media / comms
    "spotify": "spotify",
    "vlc": "vlc",
    "discord": "discord",
    "telegram": "telegram",
    "whatsapp": "whatsapp",

    # Websites (open in default browser)
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://www.github.com",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "reddit": "https://www.reddit.com",
    "chatgpt": "https://chat.openai.com",
}

_OPEN_VERBS = re.compile(r'\b(open|launch|start|run|show)\b\s*', re.I)


class AppLauncher:
    def __init__(self, voice):
        self.voice = voice

    def open_from_command(self, command: str):
        app_name = _OPEN_VERBS.sub("", command).strip()

        if not app_name:
            self.voice.speak("What would you like me to open?")
            return

        target = self._resolve(app_name)

        if target:
            self._launch(target, app_name)
        else:
            self.voice.speak(f"Searching for {app_name}.")
            subprocess.Popen(f'start "" "{app_name}"', shell=True)

    # ------------------------------------------------------------------

    def _resolve(self, name: str) -> str | None:
        name = name.lower()
        if name in _APPS:
            return _APPS[name]
        for key, val in _APPS.items():
            if key in name or name in key:
                return val
        return None

    def _launch(self, target: str, display_name: str):
        try:
            if target.startswith("http"):
                webbrowser.open(target)
            elif target.endswith(":"):
                subprocess.Popen(f"start {target}", shell=True)
            else:
                subprocess.Popen(target, shell=True)
            self.voice.speak(f"Opening {display_name}.")
        except Exception as exc:
            self.voice.speak(f"I had trouble opening {display_name}.")
            print(f"  [Launch error] {exc}")
