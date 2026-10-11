import os, json, urllib.request, html, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
INDEX = ROOT / "articles.json"
ARTICLES.mkdir(exist_ok=True)

key = os.environ.get("GEMINI_API_KEY")
if not key:
    raise SystemExit("ERROR: GEMINI_API_KEY secret missing")

topics = [
    ("earning", "Practical online earning skills for beginners"),
    ("ai", "Useful AI tools and technology explained for beginners"),
    ("mobile", "Useful Android mobile tips and privacy"),
    ("video", "How beginners can create AI videos"),
    ("cricket", "Cricket rules, skills and beginner guides"),
    ("football", "Football rules, skills and beginner guides"),
    ("news", "How to check news and avoid online misinformation")
]

today = datetime.now(timezone.utc).date()
category, topic = topics[today.toordinal() % len(topics)]
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def generate(language):
    if language == "bn":
        instruction = "Write natural, simple Bengali for readers in India."
        langname = "Bengali"
    else:
        instruction = "Write clear, simple English for beginners."
        langname = "English"

    prompt = f"""
Create an original, useful website article in {langname}.
Topic: {topic}
Category: {category}
{instruction}
Write a distinct article for this language, not a translation of another article.
Include a useful title and 5 to 7 informative paragraphs.
Return ONLY valid JSON in this exact format:
{{"title":"Article title","paragraphs":["paragraph 1","paragraph 2","paragraph 3","paragraph 4","paragraph 5"]}}
Do not invent today's news, live scores, match results, statistics, or current events.
For cricket and football, write an evergreen guide, not a fake live score report.
Avoid guaranteed income claims and misleading promises.
"""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1800}
    }).encode()

    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode())

    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    result = json.loads(text)
    if not result.get("title") or not result.get("paragraphs"):
        raise ValueError("Generated article is incomplete")
    return result

try:
    existing = json.loads(INDEX.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    existing = []

for language in ("bn", "en"):
    article = generate(language)
    filename = f"article-{language}-{stamp}.html"
    title = html.escape(str(article["title"]))
    paragraphs = "\n".join(
        "<p>" + html.escape(str(p)) + "</p>"
        for p in article["paragraphs"]
    )
    page = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | AI Path Bangla</title>
<meta name="description" content="{title}">
<style>
body{{font-family:Arial,sans-serif;line-height:1.8;max-width:800px;margin:24px auto;padding:16px;color:#20283a}}
a{{color:#087d61}}article{{background:#fff;padding:18px}}small{{color:#64748b}}
</style>
</head>
<body><a href="../index.html">Home / হোম</a>
<article><h1>{title}</h1>
<small>Category: {html.escape(category)} | Language: {language}</small>
{paragraphs}
</article></body></html>"""
    (ARTICLES / filename).write_text(page, encoding="utf-8")
    existing.insert(0, {
        "title": str(article["title"]),
        "file": filename,
        "lang": language,
        "category": category,
        "date": str(today)
    })
    print("Created:", filename)

# Keep the newest 200 entries; existing older entries are preserved within this limit.
INDEX.write_text(
    json.dumps(existing[:200], ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)
print("Article list updated.")
