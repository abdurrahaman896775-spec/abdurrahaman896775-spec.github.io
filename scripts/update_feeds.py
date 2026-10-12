import json, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "updates.json"

FEEDS = {
    "news": ("India news", "ভারতের খবর"),
    "cricket": ("cricket India", "ভারত ক্রিকেট"),
    "football": ("football India", "ভারত ফুটবল"),
}

all_updates = []

for language in ("bn", "en"):
    for category, queries in FEEDS.items():
        query = queries[0] if language == "en" else queries[1]
        params = urllib.parse.urlencode({
            "q": query + " when:1d",
            "hl": "en-IN" if language == "en" else "bn",
            "gl": "IN",
            "ceid": "IN:en" if language == "en" else "IN:bn",
        })
        url = "https://news.google.com/rss/search?" + params
        req = urllib.request.Request(
            url, headers={"User-Agent": "AI-Path-Bangla/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                root = ET.fromstring(response.read())
            count = 0
            for item in root.findall("./channel/item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                if not title or not link:
                    continue
                all_updates.append({
                    "category": category,
                    "lang": language,
                    "title": title,
                    "url": link,
                    "published": item.findtext("pubDate", "").strip(),
                    "source": item.findtext("source", "Google News").strip(),
                })
                count += 1
                if count >= 10:
                    break
            print(language, category, ":", count, "items")
        except Exception as error:
            print(language, category, "feed failed:", str(error))

OUTPUT.write_text(json.dumps({
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "items": all_updates,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("Saved:", OUTPUT)
print("Total updates:", len(all_updates))
