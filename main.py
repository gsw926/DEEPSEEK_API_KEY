#!/usr/bin/env python3
"""
Daily Industry News Push - Cloud Edition (Multi-Topic)
Google News RSS -> DeepSeek AI -> PushPlus -> WeChat
Runs on GitHub Actions, no local machine needed.

Supported topics: tv, design, ai
Set TOPIC env var to choose: TOPIC=tv | design | ai
"""

import os
import sys
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape as html_unescape
from urllib.parse import quote, urljoin

import requests

# ==================== Global Config ====================

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
MODEL = "deepseek-chat"
BEIJING_TZ = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_PER_QUERY = 8
TIMEOUT = 15

# ==================== Topic Configurations ====================

TOPICS = {
    # ---------- TV Industry ----------
    "tv": {
        "emoji": "\U0001F4FA",  # 📺
        "name_cn": "电视行业趋势",
        "name_en": "TV Industry Daily",
        "output_file": "tv-industry-daily-push.html",
        "header_grad": "#0f0c29,#302b63,#24243e",
        "queries": [
            ("\u4ea7\u54c1\u529f\u80fd", "\u667a\u80fd\u7535\u89c6 \u65b0\u529f\u80fd \u53d1\u5e03", "zh-CN"),
            ("\u4ea7\u54c1\u529f\u80fd", "smart TV new features 2025", "en"),
            ("\u7528\u6237\u4f53\u9a8c", "\u7535\u89c6 \u7528\u6237\u4f53\u9a8c \u4ea4\u4e92 \u8bc4\u6d4b", "zh-CN"),
            ("\u7528\u6237\u4f53\u9a8c", "TV user experience interface", "en"),
            ("\u6700\u65b0\u79d1\u6280", "\u7535\u89c6 \u663e\u793a\u6280\u672f Mini LED OLED MicroLED", "zh-CN"),
            ("\u6700\u65b0\u79d1\u6280", "TV display technology 2025", "en"),
            ("\u884c\u4e1a\u8d8b\u52bf", "\u7535\u89c6\u884c\u4e1a \u8d8b\u52bf \u5e02\u573a \u6570\u636e", "zh-CN"),
            ("\u884c\u4e1a\u8d8b\u52bf", "TV industry trends market 2025", "en"),
        ],
        "cat_styles": {
            "\u4ea7\u54c1\u529f\u80fd": {"grad": "#2563eb,#3b82f6", "color": "#3b82f6"},
            "\u7528\u6237\u4f53\u9a8c": {"grad": "#7c3aed,#a855f7", "color": "#a855f7"},
            "\u6700\u65b0\u79d1\u6280": {"grad": "#0891b2,#06b6d4", "color": "#06b6d4"},
            "\u884c\u4e1a\u8d8b\u52bf": {"grad": "#ea580c,#f97316", "color": "#f97316"},
        },
        "system_prompt": "\u4f60\u662f\u7535\u89c6\u884c\u4e1a\u6bcf\u65e5\u8d8b\u52bf\u65b0\u95fb\u7f16\u8f91\uff0c\u64c5\u957f\u4ece\u65b0\u95fb\u5217\u8868\u4e2d\u7b5b\u9009\u6700\u6709\u4ef7\u503c\u7684\u4fe1\u606f\uff0c\u5e76\u751f\u6210\u7cbe\u70bc\u7684\u4e2d\u6587\u6458\u8981\u548c\u8d8b\u52bf\u6d1e\u5bdf\u3002",
        "ai_categories": "\u4ea7\u54c1\u529f\u80fd\u3001\u7528\u6237\u4f53\u9a8c\u3001\u6700\u65b0\u79d1\u6280\u3001\u884c\u4e1a\u8d8b\u52bf",
    },

    # ---------- Design Industry ----------
    "design": {
        "emoji": "\U0001F3A8",  # 🎨
        "name_cn": "设计行业趋势",
        "name_en": "Design Industry Daily",
        "output_file": "design-industry-daily-push.html",
        "header_grad": "#1a1a2e,#16213e,#0f3460",
        "queries": [
            ("\u8bbe\u8ba1\u5de5\u5177", "Figma Adobe Sketch \u65b0\u529f\u80fd \u8bbe\u8ba1\u5de5\u5177", "zh-CN"),
            ("\u8bbe\u8ba1\u5de5\u5177", "design tools new features 2025 Figma Adobe", "en"),
            ("\u7528\u6237\u4f53\u9a8c", "UX UI \u8bbe\u8ba1 \u8d8b\u52bf \u7528\u6237\u4f53\u9a8c", "zh-CN"),
            ("\u7528\u6237\u4f53\u9a8c", "UX UI design trends 2025 user experience", "en"),
            ("\u521b\u610f\u8d8b\u52bf", "\u89c6\u89c9\u8bbe\u8ba1 \u521b\u610f \u8d8b\u52bf \u7075\u611f", "zh-CN"),
            ("\u521b\u610f\u8d8b\u52bf", "graphic design visual trends 2025 creative", "en"),
            ("\u884c\u4e1a\u52a8\u6001", "\u8bbe\u8ba1\u884c\u4e1a \u52a8\u6001 \u65b0\u95fb \u5e74\u5ea6\u62a5\u544a", "zh-CN"),
            ("\u884c\u4e1a\u52a8\u6001", "design industry news awards 2025", "en"),
        ],
        "cat_styles": {
            "\u8bbe\u8ba1\u5de5\u5177": {"grad": "#059669,#10b981", "color": "#10b981"},
            "\u7528\u6237\u4f53\u9a8c": {"grad": "#7c3aed,#a855f7", "color": "#a855f7"},
            "\u521b\u610f\u8d8b\u52bf": {"grad": "#db2777,#ec4899", "color": "#ec4899"},
            "\u884c\u4e1a\u52a8\u6001": {"grad": "#ea580c,#f97316", "color": "#f97316"},
        },
        "system_prompt": "\u4f60\u662f\u8bbe\u8ba1\u884c\u4e1a\u6bcf\u65e5\u8d8b\u52bf\u65b0\u95fb\u7f16\u8f91\uff0c\u64c5\u957f\u4ece\u65b0\u95fb\u5217\u8868\u4e2d\u7b5b\u9009\u6700\u6709\u4ef7\u503c\u7684\u4fe1\u606f\uff0c\u5e76\u751f\u6210\u7cbe\u70bc\u7684\u4e2d\u6587\u6458\u8981\u548c\u8d8b\u52bf\u6d1e\u5bdf\u3002",
        "ai_categories": "\u8bbe\u8ba1\u5de5\u5177\u3001\u7528\u6237\u4f53\u9a8c\u3001\u521b\u610f\u8d8b\u52bf\u3001\u884c\u4e1a\u52a8\u6001",
    },

    # ---------- AI Industry ----------
    "ai": {
        "emoji": "\U0001F916",  # 🤖
        "name_cn": "AI行业趋势",
        "name_en": "AI Industry Daily",
        "output_file": "ai-industry-daily-push.html",
        "header_grad": "#0c0a09,#1c1917,#292524",
        "queries": [
            ("\u6a21\u578b\u4e0e\u6280\u672f", "\u5927\u6a21\u578b \u53d1\u5e03 GPT Claude Gemini \u6280\u672f", "zh-CN"),
            ("\u6a21\u578b\u4e0e\u6280\u672f", "LLM new model release 2025 GPT Claude Gemini", "en"),
            ("\u4ea7\u54c1\u5e94\u7528", "AI \u4ea7\u54c1 \u5e94\u7528 \u53d1\u5e03 2025", "zh-CN"),
            ("\u4ea7\u54c1\u5e94\u7528", "AI product launch features 2025", "en"),
            ("\u884c\u4e1a\u52a8\u6001", "AI \u884c\u4e1a \u8d44\u8bba \u878d\u8d44 \u653f\u7b56", "zh-CN"),
            ("\u884c\u4e1a\u52a8\u6001", "AI industry news funding regulation 2025", "en"),
            ("\u524d\u6cbf\u7814\u7a76", "AI \u7814\u7a76 \u8bba\u6587 \u7a81\u7834 \u57fa\u51c6\u6d4b\u8bd5", "zh-CN"),
            ("\u524d\u6cbf\u7814\u7a76", "AI research paper benchmark breakthrough 2025", "en"),
        ],
        "cat_styles": {
            "\u6a21\u578b\u4e0e\u6280\u672f": {"grad": "#2563eb,#3b82f6", "color": "#3b82f6"},
            "\u4ea7\u54c1\u5e94\u7528": {"grad": "#0d9488,#14b8a6", "color": "#14b8a6"},
            "\u884c\u4e1a\u52a8\u6001": {"grad": "#d97706,#f59e0b", "color": "#f59e0b"},
            "\u524d\u6cbf\u7814\u7a76": {"grad": "#7c3aed,#8b5cf6", "color": "#8b5cf6"},
        },
        "system_prompt": "\u4f60\u662fAI\u4eba\u5de5\u667a\u80fd\u884c\u4e1a\u6bcf\u65e5\u8d8b\u52bf\u65b0\u95fb\u7f16\u8f91\uff0c\u64c5\u957f\u4ece\u65b0\u95fb\u5217\u8868\u4e2d\u7b5b\u9009\u6700\u6709\u4ef7\u503c\u7684\u4fe1\u606f\uff0c\u5e76\u751f\u6210\u7cbe\u70bc\u7684\u4e2d\u6587\u6458\u8981\u548c\u8d8b\u52bf\u6d1e\u5bdf\u3002",
        "ai_categories": "\u6a21\u578b\u4e0e\u6280\u672f\u3001\u4ea7\u54c1\u5e94\u7528\u3001\u884c\u4e1a\u52a8\u6001\u3001\u524d\u6cbf\u7814\u7a76",
    },
}


def get_topic_config():
    """Get topic configuration from TOPIC env var. Defaults to 'all'."""
    topic = os.environ.get("TOPIC", "all").lower().strip()
    if topic == "all":
        return None, "all"
    if topic not in TOPICS:
        print(f"ERROR: Unknown topic '{topic}'. Available: {list(TOPICS.keys())} or 'all'")
        sys.exit(1)
    return TOPICS[topic], topic


def _today_str():
    """Today's date string in Beijing time (YYYY-MM-DD)."""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def check_already_pushed(topic_key):
    """Check if we already pushed today for this topic.
    Uses a marker file committed back via GitHub Actions cache.
    Returns True if already pushed today.
    Force push: set FORCE_PUSH=1 env var to bypass dedup.
    """
    if os.environ.get("FORCE_PUSH", "").strip() == "1":
        print(f"  🔄 FORCE_PUSH enabled, bypassing dedup check for {topic_key}")
        return False
    marker = f".pushed_{topic_key}_{_today_str()}"
    if os.path.exists(marker):
        return True
    return False


def mark_pushed(topic_key):
    """Create a marker file indicating we pushed today."""
    marker = f".pushed_{topic_key}_{_today_str()}"
    with open(marker, "w") as f:
        f.write(datetime.now(BEIJING_TZ).isoformat())


# ==================== Step 1: Fetch RSS News ====================

def fetch_rss(config):
    """Fetch news from Google News RSS for all search queries."""
    articles = []
    seen_titles = set()

    for cat, query, lang in config["queries"]:
        if lang == "zh-CN":
            url = f"https://news.google.com/rss/search?q={quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        else:
            url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en&gl=US&ceid=US:en"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            root = ET.fromstring(resp.content)

            count = 0
            for item in root.findall(".//item"):
                if count >= MAX_PER_QUERY:
                    break

                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")

                source_elem = item.find("source")
                source = ""
                if source_elem is not None and source_elem.text:
                    source = source_elem.text.strip()

                if " - " in title and source and title.endswith(source):
                    title = title[: -len(source) - 3]

                clean_desc = re.sub(r"<[^>]+>", "", desc).strip()

                title_key = title.lower()[:60]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                articles.append({
                    "category_hint": cat,
                    "title": title,
                    "source": source,
                    "url": link,
                    "description": clean_desc[:300],
                    "pub_date": pub_date,
                })
                count += 1

            print(f"  [{cat}] {count} articles from: {query}")
            time.sleep(1)

        except Exception as e:
            print(f"  [{cat}] Error: {e}")

    print(f"\nTotal collected: {len(articles)} articles")
    return articles


# ==================== Step 2: Resolve URLs & Fetch Images ====================

def resolve_google_news_url(google_news_url):
    """Resolve a Google News article URL to the real article URL.

    Google News uses JS-based redirects, so requests.get() can't follow them
    directly. Instead, we fetch the Google News page and parse the HTML for
    the real article URL in data-n-au attribute, meta refresh, or JS redirects.
    """
    try:
        resp = requests.get(google_news_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)

        # Case 1: HTTP redirect already took us to the real article
        if "news.google.com" not in resp.url:
            return resp.url, resp.text

        # Case 2: Still on Google News - parse the HTML for the real URL
        html = resp.text

        # Method A: data-n-au attribute (most common in modern Google News)
        match = re.search(r'data-n-au="([^"]+)"', html)
        if match:
            real_url = html_unescape(match.group(1))
            if real_url.startswith("http") and "news.google.com" not in real_url:
                return real_url, html

        # Method B: data-n-au with &quot; encoding
        match = re.search(r'data-n-au=&quot;([^&]+)&quot;', html)
        if match:
            real_url = html_unescape(match.group(1))
            if real_url.startswith("http") and "news.google.com" not in real_url:
                return real_url, html

        # Method C: meta refresh redirect
        match = re.search(
            r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'>\s]+)',
            html, re.IGNORECASE,
        )
        if match:
            real_url = html_unescape(match.group(1))
            if real_url.startswith("http") and "news.google.com" not in real_url:
                return real_url, html

        # Method D: JavaScript window.location redirect
        match = re.search(
            r'window\.location\.(?:replace|href)\s*=\s*["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        )
        if match:
            real_url = html_unescape(match.group(1))
            if real_url.startswith("http") and "news.google.com" not in real_url:
                return real_url, html

        # Method E: Look for <a> tags with data-n-tl attribute or article links
        for match in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', html):
            candidate = html_unescape(match.group(1))
            if ("news.google.com" not in candidate and
                    "google.com" not in candidate and
                    "gstatic" not in candidate and
                    "googleapis" not in candidate):
                return candidate, html

        # Method F: Try without /rss/ in the URL
        if "/rss/articles/" in google_news_url:
            alt_url = google_news_url.replace("/rss/articles/", "/articles/")
            try:
                resp2 = requests.get(alt_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
                if "news.google.com" not in resp2.url:
                    return resp2.url, resp2.text
                match = re.search(r'data-n-au="([^"]+)"', resp2.text)
                if match:
                    real_url = html_unescape(match.group(1))
                    if real_url.startswith("http") and "news.google.com" not in real_url:
                        return real_url, resp2.text
            except Exception:
                pass

        # Fallback: return the original Google News URL
        return resp.url, html

    except Exception as e:
        print(f"    Resolve error: {e}")
        return google_news_url, ""


def resolve_and_get_image(google_news_url):
    """Follow Google News redirect to get real article URL and extract image."""
    real_url, html_content = resolve_google_news_url(google_news_url)

    image_url = None
    if html_content and "news.google.com" not in real_url:
        image_url = extract_image(html_content, real_url)

    return real_url, image_url


def extract_image(html, base_url):
    """Extract first content image from HTML."""
    patterns = [
        r'data-src="([^"]+\.(?:jpg|jpeg|png|webp))"',
        r'data-original="([^"]+\.(?:jpg|jpeg|png|webp))"',
        r'src="([^"]+\.(?:jpg|jpeg|png|webp))"',
    ]

    skip_kw = [
        "logo", "icon", "avatar", "qr", "pixel", "ad_",
        "banner_ad", "sprite", "blank", "placeholder",
        "loading", "default", "grey", "emoji",
    ]

    for pattern in patterns:
        imgs = re.findall(pattern, html, re.IGNORECASE)
        for img in imgs:
            if any(kw in img.lower() for kw in skip_kw):
                continue
            if not img.startswith("http"):
                img = urljoin(base_url, img)
            return img

    return None


# ==================== Step 3: DeepSeek Summarization ====================

def _deduplicate_ai_articles(articles):
    """Remove duplicate/similar articles from AI output.
    Uses title similarity (first 20 chars + core keywords) to detect duplicates.
    """
    seen = set()
    unique = []
    for a in articles:
        title = a.get("title", "").lower().strip()
        title_clean = re.sub(r"[《》「」【】""''·—– \t\n]", "", title)
        key = title_clean[:20]
        if key in seen:
            print(f"  \U0001f504 Dedup: removing similar article '{a.get('title', '')[:40]}'")
            continue
        seen.add(key)
        unique.append(a)
    return unique


def summarize_with_ai(articles, config):
    """Use DeepSeek API to select and summarize the best articles."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return None

    # Pre-deduplicate: remove articles with very similar titles before sending to AI
    pre_deduped = []
    seen_titles = set()
    for a in articles:
        title_key = a["title"].lower().strip()[:40]
        title_clean = re.sub(r"[《》「」【】""''·—– \t\n]", "", title_key)
        if title_clean[:25] in seen_titles:
            continue
        seen_titles.add(title_clean[:25])
        pre_deduped.append(a)
    print(f"  Pre-dedup: {len(articles)} \u2192 {len(pre_deduped)} articles")

    articles_json = json.dumps(
        [
            {
                "category_hint": a["category_hint"],
                "title": a["title"],
                "source": a["source"],
                "url": a["url"],
                "description": a["description"],
                "pub_date": a["pub_date"],
            }
            for a in pre_deduped
        ],
        ensure_ascii=False,
        indent=2,
    )

    categories = config["ai_categories"]
    system_prompt = config["system_prompt"]

    user_prompt = f"""\u8bf7\u4ece\u4ee5\u4e0b\u65b0\u95fb\u5217\u8868\u4e2d\u7b5b\u9009\u548c\u603b\u7ed3\uff0c\u751f\u6210\u6bcf\u65e5\u884c\u4e1a\u8d8b\u52bf\u63a8\u9001\u3002

\u8981\u6c42\uff1a
1. **\u4e25\u683c\u53bb\u91cd**\uff1a\u540c\u4e00\u4e8b\u4ef8/\u8bdd\u9898\u53ea\u4fdd\u7559\u4e00\u6761\u65b0\u95fb\uff0c\u5373\u4f7f\u6807\u9898\u7565\u6709\u4e0d\u540c\u4e5f\u4e0d\u8981\u91cd\u590d
2. \u7b5b\u90094-6\u6761\u6700\u6709\u4ef7\u503c\u7684\u65b0\u95fb\uff0c\u786e\u4fdd\u8986\u76d6\u56db\u4e2a\u65b9\u5411\uff1a{categories}
3. \u4e3a\u6bcf\u6761\u65b0\u95fb\u751f\u6210\u4e2d\u6587\u6807\u9898\u3001\u6458\u8981\u548c\u8d8b\u52bf\u6d1e\u5bdf
4. summary\u4e2d\u7684\u5173\u952e\u6570\u636e\u7528<strong>\u6807\u7b7e\u52a0\u7c97\uff0c\u5982 <strong>92.8%</strong>
5. original_url\u5fc5\u987b\u4f7f\u7528\u63d0\u4f9b\u7684url\u5b57\u6bb5\u503c\uff0c\u4e0d\u8981\u4fee\u6539

\u8fd4\u56de\u4e25\u683cJSON\u683c\u5f0f\uff1a
{{
  "articles": [
    {{
      "category": "{categories.split("\u3001")[0]}",
      "emoji": "\u4e0e\u5185\u5bb9\u76f8\u5173\u7684emoji",
      "title": "\u4e2d\u6587\u6807\u9898(15-25\u5b57\uff0c\u7b80\u6d01\u6709\u529b)",
      "source": "\u6765\u6e90\u5a92\u4f53\u540d\u79f0",
      "date": "2026.07 \u6216 2026.07.11",
      "summary": "\u4e2d\u6587\u6458\u8981(2-3\u53e5\u8bdd\uff0c\u5305\u542b\u5173\u952e\u6570\u636e)",
      "insight": "\u8d8b\u52bf\u6d1e\u5bdf(1-2\u53e5\u8bdd\uff0c\u5206\u6790\u884c\u4e1a\u610f\u4e49)",
      "original_url": "\u63d0\u4f9b\u7684url\u503c"
    }}
  ]
}}

\u65b0\u95fb\u5217\u8868\uff1a
{articles_json}"""

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)

        selected = result.get("articles", [])
        print(f"  DeepSeek selected {len(selected)} articles")

        # Post-deduplicate: remove similar articles from AI output
        selected = _deduplicate_ai_articles(selected)
        print(f"  Post-dedup: {len(selected)} unique articles")

        return selected

    except Exception as e:
        print(f"  DeepSeek API error: {e}")
        if hasattr(resp, "text"):
            print(f"  Response: {resp.text[:500]}")
        return None


# ==================== Step 4: Generate HTML ====================

def _escape_attr(value):
    """Escape a string for safe use in an HTML attribute value."""
    if not value:
        return ""
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _shorten_url(url, max_len=80):
    """Shorten URL for display."""
    if len(url) <= max_len:
        return url
    return url[:max_len] + "..."


def _get_date_str():
    now = datetime.now(BEIJING_TZ)
    weekdays = ["\u661f\u671f\u4e00", "\u661f\u671f\u4e8c", "\u661f\u671f\u4e09", "\u661f\u671f\u56db", "\u661f\u671f\u4e94", "\u661f\u671f\u516d", "\u661f\u671f\u65e5"]
    return now.strftime("%Y\u5e74%m\u6708%d\u65e5"), weekdays[now.weekday()]


def _count_by_category(articles):
    counts = {}
    for a in articles:
        cat = a.get("category", "")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def generate_html_file(articles, config):
    """Generate full HTML file with CSS for browser viewing."""
    date_str, weekday = _get_date_str()
    cat_counts = _count_by_category(articles)
    cat_styles = config["cat_styles"]
    fallback_style = list(cat_styles.values())[-1]
    emoji = config["emoji"]
    name_cn = config["name_cn"]
    name_en = config["name_en"]
    header_grad = config["header_grad"]

    stats_items = "".join(
        f'<div class="stats-item" style="background:linear-gradient(135deg,{cat_styles.get(c, fallback_style)["grad"]});">'
        f'<div class="stats-num">{cnt}</div><div class="stats-label">{c}</div></div>'
        for c, cnt in cat_counts.items()
    )

    cards = ""
    for a in articles:
        cat = a.get("category", "")
        s = cat_styles.get(cat, fallback_style)
        a_emoji = a.get("emoji", "")
        title = a.get("title", "")
        source = a.get("source", "")
        date = a.get("date", "")
        summary = a.get("summary", "")
        insight = a.get("insight", "")
        url = a.get("original_url", "#")
        img = a.get("image_url", "")

        safe_url = _escape_attr(url)
        safe_img = _escape_attr(img) if img else ""

        url_is_search = a.get("url_is_search", False)
        button_text = "\U0001f50d \u641c\u7d22\u539f\u6587 \u2192" if url_is_search else "\u9605\u8bfb\u539f\u6587 \u2192"

        img_tag = f'<img src="{safe_img}" class="card-img" onerror="this.style.display=&quot;none&quot;" />' if safe_img else ""

        # "一键复制" button + plain text URL for WeChat fallback
        copy_section = ""
        if url and url != "#":
            # Build onclick separately to avoid f-string escape issues in Python 3.12
            onclick_js = "navigator.clipboard.writeText('" + url.replace("'", "\\'") + "').then(function(){this.innerText='已复制!';}.bind(this))"
            btn_style = (
                f"font-size:12px;padding:5px 12px;border-radius:6px;border:1px solid {s['color']};"
                f"background:{s['color']}20;color:{s['color']};cursor:pointer;font-weight:600;"
                f"white-space:nowrap;"
            )
            copy_section = (
                f'<div style="margin-top:8px;display:flex;align-items:center;gap:6px;">'
                f'<button onclick="{onclick_js}" style="{btn_style}">\U0001f4cb 一键复制链接</button>'
                f'</div>'
                f'<div style="margin-top:4px;padding:6px 10px;background:#f3f4f6;border-radius:6px;'
                f'font-size:11px;color:#6b7280;word-break:break-all;line-height:1.5;'
                f'border:1px dashed #d1d5db;">'
                f'\U0001f517 \u957f\u6309\u590d\u5236\uff1a<span style="color:#3b82f6;">{url}</span>'
                f'</div>'
            )

        cards += f"""
    <div class="card">
      <div class="card-banner" style="background:linear-gradient(90deg,{s['grad']});"></div>
      {img_tag}
      <div class="card-body">
        <div class="card-header">
          <span class="card-emoji">{a_emoji}</span>
          <span class="card-tag" style="background:{s['color']};">{cat}</span>
          <span class="card-meta">{source} - {date}</span>
        </div>
        <div class="card-title">{title}</div>
        <div class="card-summary">{summary}</div>
        <div class="insight" style="border-left-color:{s['color']};">
          <div class="insight-label" style="color:{s['color']};">\u8d8b\u52bf\u6d1e\u5bdf</div>
          <div class="insight-text">{insight}</div>
        </div>
        <a href="{safe_url}" target="_blank" rel="noopener" class="card-link" style="color:{s['color']};">{button_text}</a>
        {copy_section}
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>\u6bcf\u65e5{name_cn} - {date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f0f0f5; font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif; color:#1a1a2e; line-height:1.7; }}
.container {{ max-width:680px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,{header_grad}); padding:32px 20px; text-align:center; }}
.header-tag {{ display:inline-block; background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2); border-radius:20px; padding:4px 14px; font-size:12px; color:#a5b4fc; margin-bottom:10px; }}
.header-title {{ color:#fff; font-size:20px; font-weight:700; }}
.header-date {{ color:#c7d2fe; font-size:13px; margin-top:4px; }}
.stats {{ display:flex; text-align:center; background:#fff; padding:12px 8px; }}
.stats-item {{ flex:1; padding:10px 4px; border-radius:10px; margin:0 3px; }}
.stats-num {{ font-size:20px; font-weight:800; color:#fff; }}
.stats-label {{ font-size:10px; color:rgba(255,255,255,0.85); }}
.card {{ background:#fff; margin:10px; border-radius:12px; overflow:hidden; box-shadow:0 1px 6px rgba(0,0,0,0.06); }}
.card-banner {{ height:6px; }}
.card-img {{ width:100%; height:200px; object-fit:cover; display:block; }}
.card-body {{ padding:20px; }}
.card-header {{ margin-bottom:10px; }}
.card-emoji {{ font-size:18px; }}
.card-tag {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; color:#fff; margin-left:4px; }}
.card-meta {{ font-size:11px; color:#9ca3af; float:right; }}
.card-title {{ font-size:15px; font-weight:700; color:#1a1a2e; margin-bottom:8px; line-height:1.5; }}
.card-summary {{ font-size:13px; color:#4b5563; line-height:1.8; margin-bottom:10px; }}
.card-summary strong {{ color:#1a1a2e; }}
.insight {{ background:#f8fafc; border-left:3px solid #ccc; border-radius:6px; padding:10px 12px; margin-bottom:10px; }}
.insight-label {{ font-size:11px; font-weight:700; margin-bottom:3px; }}
.insight-text {{ font-size:12px; color:#4b5563; line-height:1.7; }}
.card-link {{ font-size:13px; font-weight:600; text-decoration:none; }}
.card-link:hover {{ text-decoration:underline; }}
.footer {{ text-align:center; padding:20px 16px 32px; color:#9ca3af; font-size:11px; }}
.footer-line {{ width:36px; height:3px; background:linear-gradient(90deg,#6366f1,#a855f7); border-radius:2px; margin:0 auto 8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-tag">{name_en}</div>
    <div class="header-title">{emoji} \u6bcf\u65e5{name_cn}</div>
    <div class="header-date">{date_str} \u00b7 {weekday}</div>
  </div>
  <div class="stats">
    <div class="stats-item" style="background:linear-gradient(135deg,#6366f1,#818cf8);"><div class="stats-num">{len(articles)}</div><div class="stats-label">\u7cbe\u9009\u8981\u95fb</div></div>
    {stats_items}
  </div>
  {cards}
  <div class="footer">
    <div class="footer-line"></div>
    <div>\u6570\u636e\u6765\u6e90\uff1aGoogle News RSS \u00b7 DeepSeek AI \u603b\u7ed3</div>
    <div style="margin-top:3px;">\u7531 GitHub Actions \u81ea\u52a8\u751f\u6210 \u00b7 \u6bcf\u65e5\u63a8\u9001</div>
  </div>
</div>
</body>
</html>"""


def generate_pushplus_html(articles, config):
    """Generate inline-styled HTML for PushPlus/WeChat."""
    date_str, weekday = _get_date_str()
    cat_counts = _count_by_category(articles)
    cat_styles = config["cat_styles"]
    fallback_style = list(cat_styles.values())[-1]
    emoji = config["emoji"]
    name_cn = config["name_cn"]
    name_en = config["name_en"]
    header_grad = config["header_grad"]

    stats_items = "".join(
        f'<div style="flex:1;padding:10px 4px;border-radius:10px;background:linear-gradient(135deg,{cat_styles.get(c, fallback_style)["grad"]});margin:0 3px;">'
        f'<div style="font-size:20px;font-weight:800;color:#fff;">{cnt}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.85);">{c}</div></div>'
        for c, cnt in cat_counts.items()
    )

    cards = ""
    for a in articles:
        cat = a.get("category", "")
        s = cat_styles.get(cat, fallback_style)
        a_emoji = a.get("emoji", "")
        title = a.get("title", "")
        source = a.get("source", "")
        date = a.get("date", "")
        summary = a.get("summary", "")
        insight = a.get("insight", "")
        url = a.get("original_url", "#")
        img = a.get("image_url", "")

        safe_url = _escape_attr(url)
        safe_img = _escape_attr(img) if img else ""

        img_tag = f'<img src="{safe_img}" style="width:100%;height:200px;object-fit:cover;display:block;" onerror="this.style.display=&quot;none&quot;" />' if safe_img else ""

        url_is_search = a.get("url_is_search", False)
        button_text = "\U0001f50d \u641c\u7d22\u539f\u6587 \u2192" if url_is_search else "\u9605\u8bfb\u539f\u6587 \u2192"

        # "一键复制" button for PushPlus/WeChat
        copy_section = ""
        if url and url != "#":
            onclick_js = "navigator.clipboard.writeText('" + url.replace("'", "\\'") + "').then(function(){this.innerText='✅ 已复制!';}.bind(this))"
            btn_style = (
                f"font-size:12px;padding:5px 12px;border-radius:6px;border:1px solid {s['color']};"
                f"background:{s['color']}20;color:{s['color']};cursor:pointer;font-weight:600;"
                f"white-space:nowrap;"
            )
            copy_section = (
                f'<div style="margin-top:8px;display:flex;align-items:center;gap:6px;">'
                f'<button onclick="{onclick_js}" style="{btn_style}">\U0001f4cb \u4e00\u952e\u590d\u5236\u94fe\u63a5</button>'
                f'</div>'
                f'<div style="margin-top:4px;padding:6px 10px;background:#f3f4f6;border-radius:6px;'
                f'font-size:11px;color:#6b7280;word-break:break-all;line-height:1.5;'
                f'border:1px dashed #d1d5db;">'
                f'\U0001f517 \u957f\u6309\u590d\u5236\uff1a<span style="color:#3b82f6;">{url}</span>'
                f'</div>'
            )

        cards += f"""
    <div style="background:#fff;margin:10px;border-radius:12px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
      <div style="height:6px;background:linear-gradient(90deg,{s['grad']});"></div>
      {img_tag}
      <div style="padding:16px;">
        <div style="margin-bottom:8px;">
          <span style="font-size:18px;">{a_emoji}</span>
          <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;color:#fff;background:{s['color']};">{cat}</span>
          <span style="font-size:11px;color:#9ca3af;float:right;">{source} - {date}</span>
        </div>
        <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:8px;line-height:1.5;">{title}</div>
        <div style="font-size:13px;color:#4b5563;line-height:1.8;margin-bottom:10px;">{summary}</div>
        <div style="background:#f8fafc;border-left:3px solid {s['color']};border-radius:6px;padding:10px 12px;margin-bottom:10px;">
          <div style="font-size:11px;font-weight:700;color:{s['color']};margin-bottom:3px;">\u8d8b\u52bf\u6d1e\u5bdf</div>
          <div style="font-size:12px;color:#4b5563;line-height:1.7;">{insight}</div>
        </div>
        <a href="{safe_url}" style="display:inline-block;font-size:13px;font-weight:600;color:{s['color']};text-decoration:none;padding:6px 14px;border:1px solid {s['color']};border-radius:6px;">{button_text}</a>
        {copy_section}
      </div>
    </div>"""

    return f"""<div style="max-width:680px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1a1a2e;line-height:1.7;">
  <div style="background:linear-gradient(135deg,{header_grad});padding:32px 20px;text-align:center;border-radius:12px 12px 0 0;">
    <div style="display:inline-block;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 14px;font-size:12px;color:#a5b4fc;margin-bottom:10px;">{name_en}</div>
    <div style="color:#fff;font-size:20px;font-weight:700;">{emoji} \u6bcf\u65e5{name_cn}</div>
    <div style="color:#c7d2fe;font-size:13px;margin-top:4px;">{date_str} \u00b7 {weekday}</div>
  </div>
  <div style="display:flex;text-align:center;background:#fff;padding:12px 8px;">
    <div style="flex:1;padding:10px 4px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#818cf8);margin:0 3px;"><div style="font-size:20px;font-weight:800;color:#fff;">{len(articles)}</div><div style="font-size:10px;color:rgba(255,255,255,0.85);">\u7cbe\u9009\u8981\u95fb</div></div>
    {stats_items}
  </div>
  {cards}
  <div style="text-align:center;padding:20px 16px 32px;color:#9ca3af;font-size:11px;">
    <div style="width:36px;height:3px;background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:2px;margin:0 auto 8px;"></div>
    <div>\u6570\u636e\u6765\u6e90\uff1aGoogle News RSS \u00b7 DeepSeek AI \u603b\u7ed3</div>
    <div style="margin-top:3px;">\u7531 GitHub Actions \u81ea\u52a8\u751f\u6210 \u00b7 \u6bcf\u65e5\u63a8\u9001</div>
  </div>
</div>"""


# ==================== Step 5: Push to WeChat ====================

def push_to_wechat(html_content, config):
    """Push HTML content to WeChat via PushPlus."""
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        print("ERROR: PUSHPLUS_TOKEN not set")
        return False

    date_str, _ = _get_date_str()
    emoji = config["emoji"]
    name_cn = config["name_cn"]

    payload = {
        "token": token,
        "title": f"{emoji} 每日{name_cn} · {date_str}",
        "content": html_content,
        "template": "html",
    }

    try:
        resp = requests.post(
            PUSHPLUS_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        result = resp.json()
        if result.get("code") == 200:
            print(f"  Push successful: {result.get('msg', '')}")
            return True
        else:
            print(f"  Push failed: {result}")
            return False
    except Exception as e:
        print(f"  Push error: {e}")
        return False


# ==================== Main ====================

def run_topic(topic_key, config):
    """Run the full pipeline for a single topic."""
    # Dedup: skip if already pushed today
    if check_already_pushed(topic_key):
        print(f"\n\U0001f23ed  {config['emoji']} {config['name_cn']} already pushed today ({_today_str()}). Skipping.")
        return True

    print("\n" + "=" * 60)
    print(f"{config['emoji']} {config['name_cn']} Daily News Push")
    print(f"  Topic: {topic_key}")
    now_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"  Time: {now_str} (Beijing Time)")
    print("=" * 60)

    # Step 1: Fetch RSS
    print("\n\U0001f4e1 Step 1: Fetching news from Google News RSS...")
    articles = fetch_rss(config)
    if not articles:
        print(f"\u274c No articles found for {topic_key}. Skipping.")
        return False

    # Step 2: AI Summarization
    print("\n\U0001f916 Step 2: Summarizing with DeepSeek AI...")
    selected = summarize_with_ai(articles, config)
    if not selected:
        print(f"\u274c AI summarization failed for {topic_key}. Skipping.")
        return False

    # Step 3: Resolve URLs & fetch images
    print("\n\U0001f5bc Step 3: Resolving URLs and fetching images...")
    for a in selected:
        url = a.get("original_url", "")
        if url:
            short_title = a.get("title", "")[:30]
            print(f"  Processing: {short_title}...")
            real_url, img = resolve_and_get_image(url)
            resolved = "news.google.com" not in real_url

            if not resolved:
                title = a.get("title", "")
                source = a.get("source", "")
                search_query = f"{title} {source}".strip() if source else title
                real_url = f"https://www.google.com/search?q={quote(search_query)}"
                a["url_is_search"] = True
                print(f"    \U0001f504 Fallback to Google search: {real_url[:80]}")
            else:
                a["url_is_search"] = False
                print(f"    \u2705 Resolved: {real_url[:80]}")

            a["original_url"] = real_url
            if img:
                a["image_url"] = img
                print(f"    \u2705 Image: {img[:80]}")
            else:
                print(f"    \u26a0\ufe0f No image found")
            time.sleep(0.5)

    # Step 4: Generate HTML
    print("\n\U0001f4c4 Step 4: Generating HTML...")
    html_file = generate_html_file(selected, config)
    pushplus_html = generate_pushplus_html(selected, config)

    output_path = config["output_file"]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_file)
    print(f"  \u2705 HTML saved to {output_path}")

    # Step 5: Push to WeChat
    print("\n\U0001f4e4 Step 5: Pushing to WeChat via PushPlus...")
    success = push_to_wechat(pushplus_html, config)
    if success:
        mark_pushed(topic_key)

    print(f"\n\u2705 {config['name_cn']} done!")
    return success


def main():
    _, topic = get_topic_config()

    if topic == "all":
        print("\U0001f680 Running ALL topics: tv, design, ai")
        results = {}
        for tkey, tconfig in TOPICS.items():
            results[tkey] = run_topic(tkey, tconfig)
        print("\n" + "=" * 60)
        print("\U0001f4ca Summary:")
        for tkey, success in results.items():
            status = "\u2705" if success else "\u274c"
            print(f"  {status} {TOPICS[tkey]['emoji']} {TOPICS[tkey]['name_cn']}")
        print("=" * 60)
    else:
        run_topic(topic, TOPICS[topic])
        print("\n" + "=" * 60)
        print("\u2705 All done!")
        print("=" * 60)


if __name__ == "__main__":
    main()
