import json
import os
import urllib.request
import traceback
from urllib.parse import quote

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_USERNAME = "smtpofficemarket"
NEWS_FILE = "news.json"
STATE_FILE = "last_update_id.txt"
MEDIA_DIR = "media"
SITE_BASE_URL = "https://spysellershop-droid.github.io/news"

os.makedirs(MEDIA_DIR, exist_ok=True)


def get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))


def download_file(url, path):
    with urllib.request.urlopen(url) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)


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
    if msg.get("text"):
        return msg["text"]

    if msg.get("caption"):
        return msg["caption"]

    if msg.get("photo"):
        return "📸 Photo post"

    if msg.get("video"):
        return "🎥 Video post"

    return ""


def get_extension_from_path(file_path, fallback=".bin"):
    _, ext = os.path.splitext(file_path)
    return ext if ext else fallback


def telegram_file_url(file_path):
    safe_path = quote(file_path)
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{safe_path}"


def get_file_path(file_id):
    file_info = get_json(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={quote(file_id)}"
    )
    if not file_info.get("ok"):
        return None
    return file_info["result"].get("file_path")


def save_media_from_file_id(file_id, local_name_prefix, fallback_ext=".bin"):
    file_path = get_file_path(file_id)
    if not file_path:
        return None

    ext = get_extension_from_path(file_path, fallback_ext)
    local_filename = f"{local_name_prefix}{ext}"
    local_path = os.path.join(MEDIA_DIR, local_filename)

    download_file(telegram_file_url(file_path), local_path)

    return f"{SITE_BASE_URL}/{MEDIA_DIR}/{quote(local_filename)}"


def extract_media(msg, message_id):
    try:
        # PHOTO
        if msg.get("photo"):
            file_id = msg["photo"][-1]["file_id"]

            image_url = save_media_from_file_id(
                file_id, f"msg_{message_id}_photo"
            )

            return "photo", image_url, None

        # VIDEO
        if msg.get("video"):
            file_id = msg["video"]["file_id"]

            video_url = None
            image_url = None

            # 🔹 حاول تنزل الفيديو
            try:
                video_url = save_media_from_file_id(
                    file_id, f"msg_{message_id}_video"
                )
            except Exception as e:
                print("VIDEO DOWNLOAD FAILED:", str(e))

            # 🔹 لو الفيديو فشل → هات thumbnail
            if not video_url:
                thumb = msg["video"].get("thumb") or msg["video"].get("thumbnail")

                if thumb:
                    try:
                        image_url = save_media_from_file_id(
                            thumb["file_id"], f"msg_{message_id}_thumb"
                        )
                    except Exception as e:
                        print("THUMB FAILED:", str(e))

            # 🔹 لو عندنا فيديو
            if video_url:
                return "video", None, video_url

            # 🔹 fallback صورة
            if image_url:
                return "photo", image_url, None

            return "none", None, None

        return "none", None, None

    except Exception as e:
        print("MEDIA ERROR:", str(e))
        return "none", None, None


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
        lines = full_text.split("\n") if full_text else []

        media_type, image_url, video_url = extract_media(msg, message_id)

        item = {
            "id": message_id,
            "title": lines[0].strip() if lines and lines[0].strip() else "Channel Update",
            "text": full_text[:1000],
            "date": msg.get("date", 0),
            "url": f"https://t.me/{CHANNEL_USERNAME}/{message_id}",
            "media_type": media_type,
            "image": image_url,
            "video": video_url
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
