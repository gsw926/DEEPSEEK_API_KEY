#!/usr/bin/env python3
"""
TV Industry Daily News Push - Cloud Edition
Google News RSS -> DeepSeek AI -> PushPlus -> WeChat
Runs on GitHub Actions, no local machine needed.
"""

import os
import sys
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import quote, urljoin

import requests

# ==================== Configuration ====================

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
MODEL = "deepseek-chat"
BEIJING_TZ = timezone(timedelta(hours=8))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Search queries: (category, query, language)
SEARCH_QUERIES = [
    ("产品功能", "智能电视 新功能 发布", "zh-CN"),
    ("产品功能", "smart TV new features 2025", "en"),
    ("用户体验", "电视 用户体验 交互 评测", "zh-CN"),
    ("用户体验", "TV user experience interface", "en"),
    ("最新科技", "电视 显示技术 Mini LED OLED MicroLED", "zh-CN"),
    ("最新科技", "TV display technology 2025", "en"),
    ("行业趋势", "电视行业 趋势 市场 数据", "zh-CN"),
    ("行业趋势", "TV industry trends market 2025", "en"),
]

# Category styling: gradient colors
CAT_STYLES = {
    "产品功能": {"grad": "#2563eb,#3b82f6", "color": "#3b82f6"},
    "用户体验": {"grad": "#7c3aed,#a855f7", "color": "#a855f7"},
    "最新科技": {"grad": "#0891b2,#06b6d4", "color": "#06b6d4"},
    "行业趋势": {"grad": "#ea580c,#f97316", "color": "#f97316"},
}

MAX_PER_QUERY = 8
TIMEOUT = 15


# ==================== Step 1: Fetch RSS News ====================

def fetch_rss():
    """Fetch news from Google News RSS for all search queries."""
    articles = []
    seen_titles = set()

    for cat, query, lang in SEARCH_QUERIES:
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

                # Extract source name
                source_elem = item.find("source")
                source = ""
                if source_elem is not None and source_elem.text:
                    source = source_elem.text.strip()

                # Clean title (Google News appends " - Source Name")
                if " - " in title and source and title.endswith(source):
                    title = title[: -len(source) - 3]

                # Strip HTML from description
                clean_desc = re.sub(r"<[^>]+>", "", desc).strip()

                # Deduplicate
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

def resolve_and_get_image(google_news_url):
    """Follow Google News redirect to get real article URL and extract image."""
    real_url = google_news_url
    image_url = None

    try:
        resp = requests.get(google_news_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        real_url = resp.url

        # Only extract images if we reached the actual article page
        if "news.google.com" not in real_url:
            image_url = extract_image(resp.text, real_url)
    except Exception as e:
        print(f"    Resolve error: {e}")

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

def summarize_with_ai(articles):
    """Use DeepSeek API to select and summarize the best articles."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set")
        return None

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
            for a in articles
        ],
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = (
        "你是电视行业每日趋势新闻编辑，擅长从新闻列表中筛选最有价值的信息，"
        "并生成精炼的中文摘要和趋势洞察。"
    )

    user_prompt = f"""请从以下新闻列表中筛选和总结，生成每日电视行业趋势推送。

要求：
1. 去重：同一事件只保留一条
2. 筛选4-6条最有价值的新闻，确保覆盖四个方向：产品功能、用户体验、最新科技、行业趋势
3. 为每条新闻生成中文标题、摘要和趋势洞察
4. summary中的关键数据用<strong>标签加粗，如 <strong>92.8%</strong>
5. original_url必须使用提供的url字段值，不要修改

返回严格JSON格式：
{{
  "articles": [
    {{
      "category": "产品功能",
      "emoji": "与内容相关的emoji",
      "title": "中文标题(15-25字，简洁有力)",
      "source": "来源媒体名称",
      "date": "2026.07 或 2026.07.11",
      "summary": "中文摘要(2-3句话，包含关键数据)",
      "insight": "趋势洞察(1-2句话，分析行业意义)",
      "original_url": "提供的url值"
    }}
  ]
}}

新闻列表：
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
        return selected

    except Exception as e:
        print(f"  DeepSeek API error: {e}")
        if hasattr(resp, "text"):
            print(f"  Response: {resp.text[:500]}")
        return None


# ==================== Step 4: Generate HTML ====================

def _get_date_str():
    now = datetime.now(BEIJING_TZ)
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return now.strftime("%Y年%m月%d日"), weekdays[now.weekday()]


def _count_by_category(articles):
    counts = {}
    for a in articles:
        cat = a.get("category", "")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def generate_html_file(articles):
    """Generate full HTML file with CSS for browser viewing."""
    date_str, weekday = _get_date_str()
    cat_counts = _count_by_category(articles)

    # Stats bar
    stats_items = "".join(
        f'<div class="stats-item" style="background:linear-gradient(135deg,{CAT_STYLES.get(c, CAT_STYLES["行业趋势"])["grad"]});">'
        f'<div class="stats-num">{cnt}</div><div class="stats-label">{c}</div></div>'
        for c, cnt in cat_counts.items()
    )

    # Cards
    cards = ""
    for a in articles:
        cat = a.get("category", "行业趋势")
        s = CAT_STYLES.get(cat, CAT_STYLES["行业趋势"])
        emoji = a.get("emoji", "")
        title = a.get("title", "")
        source = a.get("source", "")
        date = a.get("date", "")
        summary = a.get("summary", "")
        insight = a.get("insight", "")
        url = a.get("original_url", "#")
        img = a.get("image_url", "")

        img_tag = f'<img src="{img}" class="card-img" onerror="this.style.display=\'none\'" />' if img else ""

        cards += f"""
    <div class="card">
      <div class="card-banner" style="background:linear-gradient(90deg,{s['grad']});"></div>
      {img_tag}
      <div class="card-body">
        <div class="card-header">
          <span class="card-emoji">{emoji}</span>
          <span class="card-tag" style="background:{s['color']};">{cat}</span>
          <span class="card-meta">{source} - {date}</span>
        </div>
        <div class="card-title">{title}</div>
        <div class="card-summary">{summary}</div>
        <div class="insight" style="border-left-color:{s['color']};">
          <div class="insight-label" style="color:{s['color']};">趋势洞察</div>
          <div class="insight-text">{insight}</div>
        </div>
        <a href="{url}" target="_blank" class="card-link" style="color:{s['color']};">阅读原文 -></a>
      </div>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日电视行业趋势 - {date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f0f0f5; font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif; color:#1a1a2e; line-height:1.7; }}
.container {{ max-width:680px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#0f0c29,#302b63,#24243e); padding:32px 20px; text-align:center; }}
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
    <div class="header-tag">TV Industry Daily</div>
    <div class="header-title">📺 每日电视行业趋势</div>
    <div class="header-date">{date_str} · {weekday}</div>
  </div>
  <div class="stats">
    <div class="stats-item" style="background:linear-gradient(135deg,#6366f1,#818cf8);"><div class="stats-num">{len(articles)}</div><div class="stats-label">精选要闻</div></div>
    {stats_items}
  </div>
  {cards}
  <div class="footer">
    <div class="footer-line"></div>
    <div>数据来源：Google News RSS · DeepSeek AI 总结</div>
    <div style="margin-top:3px;">由 GitHub Actions 自动生成 · 每日 08:30 推送</div>
  </div>
</div>
</body>
</html>"""


def generate_pushplus_html(articles):
    """Generate inline-styled HTML for PushPlus/WeChat."""
    date_str, weekday = _get_date_str()
    cat_counts = _count_by_category(articles)

    # Stats
    stats_items = "".join(
        f'<div style="flex:1;padding:10px 4px;border-radius:10px;background:linear-gradient(135deg,{CAT_STYLES.get(c, CAT_STYLES["行业趋势"])["grad"]});margin:0 3px;">'
        f'<div style="font-size:20px;font-weight:800;color:#fff;">{cnt}</div>'
        f'<div style="font-size:10px;color:rgba(255,255,255,0.85);">{c}</div></div>'
        for c, cnt in cat_counts.items()
    )

    # Cards
    cards = ""
    for a in articles:
        cat = a.get("category", "行业趋势")
        s = CAT_STYLES.get(cat, CAT_STYLES["行业趋势"])
        emoji = a.get("emoji", "")
        title = a.get("title", "")
        source = a.get("source", "")
        date = a.get("date", "")
        summary = a.get("summary", "")
        insight = a.get("insight", "")
        url = a.get("original_url", "#")
        img = a.get("image_url", "")

        img_tag = f'<img src="{img}" style="width:100%;height:200px;object-fit:cover;display:block;" onerror="this.style.display=\'none\'" />' if img else ""

        cards += f"""
    <div style="background:#fff;margin:10px;border-radius:12px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
      <div style="height:6px;background:linear-gradient(90deg,{s['grad']});"></div>
      {img_tag}
      <div style="padding:16px;">
        <div style="margin-bottom:8px;">
          <span style="font-size:18px;">{emoji}</span>
          <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;color:#fff;background:{s['color']};">{cat}</span>
          <span style="font-size:11px;color:#9ca3af;float:right;">{source} - {date}</span>
        </div>
        <div style="font-size:15px;font-weight:700;color:#1a1a2e;margin-bottom:8px;line-height:1.5;">{title}</div>
        <div style="font-size:13px;color:#4b5563;line-height:1.8;margin-bottom:10px;">{summary}</div>
        <div style="background:#f8fafc;border-left:3px solid {s['color']};border-radius:6px;padding:10px 12px;margin-bottom:10px;">
          <div style="font-size:11px;font-weight:700;color:{s['color']};margin-bottom:3px;">趋势洞察</div>
          <div style="font-size:12px;color:#4b5563;line-height:1.7;">{insight}</div>
        </div>
        <a href="{url}" style="font-size:13px;font-weight:600;color:{s['color']};text-decoration:none;">阅读原文 -></a>
      </div>
    </div>"""

    return f"""<div style="max-width:680px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1a1a2e;line-height:1.7;">
  <div style="background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);padding:32px 20px;text-align:center;border-radius:12px 12px 0 0;">
    <div style="display:inline-block;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:4px 14px;font-size:12px;color:#a5b4fc;margin-bottom:10px;">TV Industry Daily</div>
    <div style="color:#fff;font-size:20px;font-weight:700;">📺 每日电视行业趋势</div>
    <div style="color:#c7d2fe;font-size:13px;margin-top:4px;">{date_str} · {weekday}</div>
  </div>
  <div style="display:flex;text-align:center;background:#fff;padding:12px 8px;">
    <div style="flex:1;padding:10px 4px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#818cf8);margin:0 3px;"><div style="font-size:20px;font-weight:800;color:#fff;">{len(articles)}</div><div style="font-size:10px;color:rgba(255,255,255,0.85);">精选要闻</div></div>
    {stats_items}
  </div>
  {cards}
  <div style="text-align:center;padding:20px 16px 32px;color:#9ca3af;font-size:11px;">
    <div style="width:36px;height:3px;background:linear-gradient(90deg,#6366f1,#a855f7);border-radius:2px;margin:0 auto 8px;"></div>
    <div>数据来源：Google News RSS · DeepSeek AI 总结</div>
    <div style="margin-top:3px;">由 GitHub Actions 自动生成 · 每日 08:30 推送</div>
  </div>
</div>"""


# ==================== Step 5: Push to WeChat ====================

def push_to_wechat(html_content):
    """Push HTML content to WeChat via PushPlus."""
    token = os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        print("ERROR: PUSHPLUS_TOKEN not set")
        return False

    date_str, _ = _get_date_str()

    payload = {
        "token": token,
        "title": f"📺 每日电视行业趋势 · {date_str}",
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

def main():
    print("=" * 60)
    print("📺 TV Industry Daily News Push - Cloud Edition")
    now_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ {now_str} (Beijing Time)")
    print("=" * 60)

    # Step 1: Fetch RSS
    print("\n📡 Step 1: Fetching news from Google News RSS...")
    articles = fetch_rss()
    if not articles:
        print("❌ No articles found. Exiting.")
        sys.exit(1)

    # Step 2: AI Summarization
    print("\n🤖 Step 2: Summarizing with DeepSeek AI...")
    selected = summarize_with_ai(articles)
    if not selected:
        print("❌ AI summarization failed. Exiting.")
        sys.exit(1)

    # Step 3: Resolve URLs & fetch images
    print("\n🖼️ Step 3: Resolving URLs and fetching images...")
    for a in selected:
        url = a.get("original_url", "")
        if url:
            short_title = a.get("title", "")[:30]
            print(f"  Processing: {short_title}...")
            real_url, img = resolve_and_get_image(url)
            a["original_url"] = real_url
            if img:
                a["image_url"] = img
                print(f"    ✅ Image: {img[:80]}")
            else:
                print(f"    ⚠️ No image found")
            time.sleep(0.5)

    # Step 4: Generate HTML
    print("\n📄 Step 4: Generating HTML...")
    html_file = generate_html_file(selected)
    pushplus_html = generate_pushplus_html(selected)

    output_path = "tv-industry-daily-push.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_file)
    print(f"  ✅ HTML saved to {output_path}")

    # Step 5: Push to WeChat
    print("\n📤 Step 5: Pushing to WeChat via PushPlus...")
    push_to_wechat(pushplus_html)

    print("\n" + "=" * 60)
    print("✅ All done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
