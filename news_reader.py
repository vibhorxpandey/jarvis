import re
import requests
import xml.etree.ElementTree as ET
from html import unescape

from config import NEWS_COUNT, OWNER_NAME

_FEEDS = [
    ("BBC News",  "http://feeds.bbci.co.uk/news/rss.xml"),
    ("Reuters",   "https://feeds.reuters.com/reuters/topNews"),
    ("CNN",       "http://rss.cnn.com/rss/edition.rss"),
]

_TAG_RE = re.compile(r"<[^>]+>")


class NewsReader:
    def __init__(self, voice):
        self.voice = voice

    def read_news(self):
        self.voice.speak(f"Fetching the latest headlines for you, {OWNER_NAME}.")
        headlines = self._fetch()

        if not headlines:
            self.voice.speak(
                "I'm unable to reach the news right now. "
                "Please check your internet connection."
            )
            return

        self.voice.speak(f"Here are today's top {len(headlines)} headlines.")
        for i, (source, title) in enumerate(headlines, 1):
            self.voice.speak(f"Headline {i}: {self._clean(title)}")
        self.voice.speak("That's all the news for now.")

    # ------------------------------------------------------------------

    def _fetch(self) -> list[tuple[str, str]]:
        for name, url in _FEEDS:
            try:
                resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                headlines = []
                for item in items[:NEWS_COUNT]:
                    el = item.find("title")
                    if el is not None and el.text:
                        headlines.append((name, el.text))
                if headlines:
                    print(f"  [News] Loaded {len(headlines)} headlines from {name}")
                    return headlines
            except Exception as exc:
                print(f"  [News] {name} failed: {exc}")
        return []

    @staticmethod
    def _clean(text: str) -> str:
        text = unescape(text)
        text = _TAG_RE.sub("", text)
        return re.sub(r"\s+", " ", text).strip()
