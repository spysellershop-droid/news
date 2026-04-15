import json
import os
import urllib.request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_USERNAME = "smtpofficemarket"
NEWS_FILE = "news.json"
STATE_FILE = "last_update_id.txt"

def get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode())

def load_last_update_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_last_update_id(update_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(update_id))

def load_news():
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_news(news):
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

def main():
    last_update_id = load_last_update_id()

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    if last_update_id:
        url += f"?offset={int(last_update_id) + 1}"

    data = get_json(url)

    if not data.get("ok"):
        print("Failed to fetch updates")
        return

    updates = data.get("result", [])
    if not updates:
        print("No new updates")
        return

    news = load_news()

    for upd in updates:
        update_id = upd["update_id"]

        msg = upd.get("channel_post") or upd.get("edited_channel_post")
        if not msg:
            save_last_update_id(update_id)
            continue

        message_id = msg["message_id"]
        text = msg.get("text") or msg.get("caption") or ""
        lines = [x.strip() for x in text.split("\n") if x.strip()]

        item = {
            "id": message_id,
            "title": lines[0] if lines else "Channel Update",
            "text": text[:250],
            "date": msg["date"],
            "url": f"https://t.me/{CHANNEL_USERNAME}/{message_id}"
        }

        news = [x for x in news if x["id"] != message_id]
        news.insert(0, item)
        news = news[:10]

        save_last_update_id(update_id)

    save_news(news)
    print("news.json updated")

if __name__ == "__main__":
    main()
