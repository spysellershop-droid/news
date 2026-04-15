import json
import os
import urllib.request
import traceback

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_USERNAME = "smtpofficemarket"
NEWS_FILE = "news.json"
STATE_FILE = "last_update_id.txt"

def get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))

def load_last_update_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()
            return int(value) if value else None
    return None

def save_last_update_id(update_id):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(update_id))

def load_news():
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    return []

def save_news(news):
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

def extract_text(msg):
    text = msg.get("text")
    if text:
        return text

    caption = msg.get("caption")
    if caption:
        return caption

    if msg.get("photo"):
        return "Photo post"
    if msg.get("video"):
        return "Video post"
    if msg.get("document"):
        return "Document post"
    if msg.get("audio"):
        return "Audio post"
    if msg.get("voice"):
        return "Voice post"
    if msg.get("sticker"):
        return "Sticker post"

    return "Channel update"

def main():
    last_update_id = load_last_update_id()

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=30"
    if last_update_id is not None:
        url += f"&offset={last_update_id + 1}"

    print("Fetching updates...")
    data = get_json(url)
    print(json.dumps(data, ensure_ascii=False)[:4000])

    if not data.get("ok"):
        raise Exception(f"Telegram API error: {data}")

    updates = data.get("result", [])
    if not updates:
        print("No new updates")
        return

    news = load_news()

    for upd in updates:
        update_id = upd.get("update_id")
        if update_id is None:
            continue

        msg = upd.get("channel_post") or upd.get("edited_channel_post")
        if not msg:
            save_last_update_id(update_id)
            continue

        message_id = msg.get("message_id")
        if message_id is None:
            save_last_update_id(update_id)
            continue

        full_text = extract_text(msg)
        lines = [x.strip() for x in full_text.split("\n") if x.strip()]

        item = {
            "id": message_id,
            "title": lines[0] if lines else "Channel Update",
            "text": full_text[:250],
            "date": msg.get("date", 0),
            "url": f"https://t.me/{CHANNEL_USERNAME}/{message_id}"
        }

        news = [x for x in news if x.get("id") != message_id]
        news.insert(0, item)
        news = news[:10]

        save_last_update_id(update_id)

    save_news(news)
    print("news.json updated")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:")
        print(str(e))
        print(traceback.format_exc())
        raise
