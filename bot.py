import os
import time
import json
import hashlib
import threading
from datetime import datetime

import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

app = Flask(__name__)

CHECK_TIMES = ["10:00", "15:00", "20:00"]

SEARCH_TARGETS = [
    {
        "name": "Easy Tent",
        "keywords": ["easy tent"],
    },
    {
        "name": "Spectacular Easy Tent",
        "keywords": ["spectacular easy tent"],
    },
    {
        "name": "Supreme Easy Tent",
        "keywords": ["supreme easy tent"],
    },
    {
        "name": "DreamVille Easy Tent",
        "keywords": ["dreamville easy tent"],
    },
]

SITES = [
    {
        "name": "StubHub",
        "url": "https://www.stubhub.com/tomorrowland-tickets/grouping/150299040/",
    },
    {
        "name": "Viagogo",
        "url": "https://www.viagogo.com/Festival-Tickets/International-Festivals/Tomorrowland-Tickets",
    },
    {
        "name": "HelloTickets",
        "url": "https://www.hellotickets.com/tomorrowland-tickets/p-31105",
    },
    {
        "name": "Gigsberg",
        "url": "https://www.gigsberg.com/festival-tickets/international-festivals/tomorrowland-tickets",
    },
]

NEGATIVE_MARKERS = [
    "sold out",
    "unavailable",
    "not available",
    "currently unavailable",
]

SEEN_FILE = "seen_items.json"


def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            return set()
    except Exception:
        return set()


def save_seen(items):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(items)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


SEEN = load_seen()


def send_message(text: str):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text},
            timeout=20,
        )
    except Exception:
        pass


def fetch_html(url: str) -> str:
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=25,
        )
        return r.text.lower()
    except Exception:
        return ""


def page_looks_dead(html: str) -> bool:
    return any(marker in html for marker in NEGATIVE_MARKERS)


def make_item_id(site_name: str, target_name: str, url: str) -> str:
    raw = f"{site_name}|{target_name}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scan_site(site: dict):
    html = fetch_html(site["url"])
    if not html:
        return []

    results = []

    for target in SEARCH_TARGETS:
        matched = any(keyword in html for keyword in target["keywords"])
        if not matched:
            continue

        dead = page_looks_dead(html)

        results.append(
            {
                "site": site["name"],
                "url": site["url"],
                "target": target["name"],
                "dead": dead,
            }
        )

    return results


def check_tickets(manual: bool = False):
    global SEEN

    all_hits = []

    for site in SITES:
        site_hits = scan_site(site)
        all_hits.extend(site_hits)

    live_hits = [hit for hit in all_hits if not hit["dead"]]
    new_hits = []

    for hit in live_hits:
        item_id = make_item_id(hit["site"], hit["target"], hit["url"])
        if item_id not in SEEN:
            SEEN.add(item_id)
            new_hits.append(hit)

    save_seen(SEEN)

    if new_hits:
        send_message("🎟 Нашла новые совпадения по Tomorrowland:")
        for hit in new_hits:
            send_message(
                f"✅ {hit['target']}\n"
                f"Платформа: {hit['site']}\n"
                f"{hit['url']}"
            )
        return

    if manual:
        if live_hits:
            summary = "\n".join(
                f"• {hit['target']} — {hit['site']}" for hit in live_hits[:10]
            )
            send_message(
                "Проверила вручную. Новых совпадений нет, но вижу уже известные:\n"
                f"{summary}"
            )
        else:
            send_message("Проверила вручную: пока ничего подходящего не вижу.")
    else:
        if live_hits:
            send_message("Плановая проверка: ничего нового, но старые совпадения всё ещё есть.")
        else:
            send_message("Плановая проверка: пока ничего подходящего не найдено.")


def scheduler():
    last_run = None
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in CHECK_TIMES and last_run != now:
            send_message("⏰ Запускаю плановую проверку Tomorrowland...")
            check_tickets(manual=False)
            last_run = now
        time.sleep(20)


@app.route("/")
def home():
    return "Bot is running!", 200


def set_webhook():
    if not TOKEN or not RENDER_URL:
        return
    webhook_url = f"{RENDER_URL}/webhook/{TOKEN}"
    telegram_api = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    try:
        requests.get(telegram_api, params={"url": webhook_url}, timeout=20)
    except Exception:
        pass


@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True) or {}
    message = data.get("message", {})
    text = (message.get("text") or "").strip()

    if text == "/start":
        send_message(
            "Бот работает.\n"
            "Я проверяю Tomorrowland в 10:00, 15:00 и 20:00.\n"
            "Команда /check — проверить прямо сейчас.\n"
            "Команда /clear — очистить список уже найденного."
        )

    elif text == "/check":
        send_message("Запускаю ручную проверку...")
        check_tickets(manual=True)

    elif text == "/clear":
        global SEEN
        SEEN = set()
        save_seen(SEEN)
        send_message("Ок, очистила список уже найденных совпадений.")

    return "ok", 200


threading.Thread(target=scheduler, daemon=True).start()
set_webhook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
