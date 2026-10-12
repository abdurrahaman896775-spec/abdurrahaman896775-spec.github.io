import os, json, urllib.request, urllib.error, html, re, time
from urllib.parse import quote
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
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def generate(language, category, topic):
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
Write a distinct article for this language, not a translation.
Include a useful title and 5 to 7 informative paragraphs.
Return ONLY valid JSON in this exact format:
{{"title":"Article title","paragraphs":["paragraph 1","paragraph 2","paragraph 3","paragraph 4","paragraph 5"]}}
Do not invent today's news, live scores, match results, statistics, or current events.
For cricket and football, write an evergreen guide, not a fake live score report.
Avoid guaranteed income claims and misleading promises.
"""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 3000
        }
    }).encode()

    models = [
        "gemini-flash-latest",
        "gemini-3-flash-preview",
        "gemini-3.8-flash"
    ]
    errors = []

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model + ":generateContent"
        )
        for attempt in range(3):
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": key
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    data = json.loads(response.read().decode())

                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
                result = json.loads(text)

                if not result.get("title") or not result.get("paragraphs"):
                    raise ValueError("Generated article is incomplete")

                print("AI model succeeded:", model)
                return result

            except urllib.error.HTTPError as e:
                errors.append(f"{model}: HTTP {e.code}")
                print("AI model error:", model, "HTTP", e.code)

                if e.code in (429, 500, 502, 503, 504):
                    if e.code != 429 and attempt < 2:
                        time.sleep(2 ** (attempt + 1))
                        continue
                break

            except (urllib.error.URLError, TimeoutError) as e:
                errors.append(f"{model}: {e}")
                print("Connection error:", model)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break

            except (KeyError, IndexError, ValueError) as e:
                errors.append(f"{model}: invalid response ({e})")
                print("Invalid AI response:", model)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break

    raise RuntimeError(
        "All Gemini models failed. Check API quota, model access and service status. "
        + "; ".join(errors)
    )


def generate_topic_image(category, topic, stamp):
    image_dir = ARTICLES / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_file = image_dir / f"{category}-{stamp}.jpg"

    fallbacks = {
        "earning": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
        "ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1200&q=80",
        "mobile": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
        "video": "https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?auto=format&fit=crop&w=1200&q=80",
        "cricket": "https://images.unsplash.com/photo-1531415074968-036ba1b575da?auto=format&fit=crop&w=1200&q=80",
        "football": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1200&q=80",
        "news": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80",
    }

    api_key = os.environ.get("POLLINATIONS_API_KEY")
    if api_key:
        prompt = (
            f"Editorial illustration about {topic}, category {category}, "
            "for a helpful beginner blog, clear subject, attractive landscape "
            "composition, no text or letters"
        )
        url = (
            "https://gen.pollinations.ai/image/"
            + quote(prompt, safe="")
            + "?model=flux&width=768&height=512"
        )
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": "Bearer " + api_key}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
            if content_type.startswith("image/") and data:
                image_file.write_bytes(data)
                print("Generated image:", image_file.name)
                return "images/" + image_file.name
            print("Image API returned non-image data; using fallback")
        except Exception as e:
            print("Image generation failed; using fallback:", e)

    return fallbacks.get(category, fallbacks["earning"])

try:
    existing = json.loads(INDEX.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    existing = []

for category, topic in topics:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    topic_image_url = generate_topic_image(category, topic, stamp)

    for language in ("bn", "en"):
        article = generate(language, category, topic)
        filename = f"article-{language}-{stamp}.html"
        title = html.escape(str(article["title"]))
        paragraphs = "\n".join(
            "<p>" + html.escape(str(p)) + "</p>"
            for p in article["paragraphs"]
        )
        image_url = topic_image_url
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
    img.article-image{{display:block;width:100%;height:auto;max-height:420px;object-fit:cover;border-radius:12px;margin:16px 0 22px}}
    </style>
    </head>
    <body><a href="../index.html">Home / হোম</a>
    <article><h1>{title}</h1>
    <img class="article-image" src="{image_url}" alt="{title}" loading="lazy">
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
