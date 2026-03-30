import os
import requests
import time
from datetime import datetime
import threading
from flask import Flask

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_message(text):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=20)

def check_tickets():
    keywords = [
        "Easy Tent",
        "Spectacular Easy Tent",
        "Supreme Easy Tent",
        "DreamVille Easy Tent",
    ]

    sites = [
        "https://www.stubhub.com/tomorrowland-tickets/grouping/150299040/",
        "https://www.viagogo.com/Festival-Tickets/International-Festivals/Tomorrowland-Tickets",
        "https://www.hellotickets.com",
        "https://www.gigsberg.com",
    ]

    found = []

    for site in sites:
        try:
            response = requests.get(
                site,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            ).text.lower()
            for word in keywords:
                if word.lower() in response:
                    found.append(f"🔥 {word} — {site}")
        except Exception:
            pass

    if found:
        for item in found:
            send_message(item)
    else:
        send_message("❌ Easy Tent и выше пока не найдены.")

def scheduler():
    last_run = None
    while True:
        now = datetime.now().strftime("%H:%M")
        if now in ["10:00", "15:00", "20:00"] and last_run != now:
            send_message("⏰ Проверяю билеты Tomorrowland...")
            check_tickets()
            last_run = now
        time.sleep(20)

def run_bot():
    scheduler()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
