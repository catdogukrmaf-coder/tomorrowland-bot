import os
import time
import threading
from datetime import datetime

import requests
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

app = Flask(__name__)

KEYWORDS = [
    "Easy Tent",
    "Spectacular Easy Tent",
    "Supreme Easy Tent",
    "DreamVille Easy Tent",
]

SITES = [
    "https://www.stubhub.com/tomorrowland-tickets/grouping/150299040/",
    "https://www.viagogo.com/Festival-Tickets/International-Festivals/Tomorrowland-Tickets",
    "https://www.hellotickets.com",
    "https://www.gigsberg.com",
]

def send_message(text: str) -> None:
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

def fetch_url(url: str) -> str:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        return r.text.lower()
    except Exception:
        return ""

def check_tickets(manual: bool = False) -> None:
    found = []

    for site in SITES:
        html = fetch_url(site)
        if not html:
            continue

        for word in KEYWORDS:
            if word.lower() in html:
                found.append(f"🔥 Найдено: {word}\n{site}")

    if found:
        send_message("🎟 Нашла подходящие варианты:")
        for item in found:
            send_message(item)
    else:
        if manual:
            send_message("Проверила вручную: пока ничего нет.")
        else:
            send_message("Плановая проверка: пока ничего нет.")

def scheduler() -> None:
    last_run = None
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in ["10:00", "15:00", "20:00"] and last_run != now:
            send_message("⏰ Запускаю плановую проверку Tomorrowland...")
            check_tickets(manual=False)
            last_run = now
        time.sleep(20)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/check-now")
def check_now():
    check_tickets(manual=True)
    return "Manual check done."

def set_webhook() -> None:
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if not TOKEN or not render_url:
        return

    webhook_url = f"{render_url}/webhook/{TOKEN}"
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
            "Я автоматически проверяю билеты в 10:00, 15:00 и 20:00.\n"
            "Команда /check — проверить прямо сейчас."
        )
    elif text == "/check":
        send_message("Запускаю ручную проверку...")
        check_tickets(manual=True)

    return "ok", 200

def run_scheduler():
    scheduler()

threading.Thread(target=run_scheduler, daemon=True).start()
set_webhook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
