# post_misskey.py (2025 Optimized)
import os
import sys
import requests
from datetime import datetime
import pytz


def generate_default_text():
    """X / Bluesky / Misskey 共通の投稿文テンプレート"""
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")

    return (
        f"【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        f"#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )


def misskey_request(url, method="POST", headers=None, data=None, files=None, json=None):
    """Misskey API を安全にラップしてエラーを完全可視化"""
    try:
        res = requests.request(
            method, url, headers=headers, data=data, files=files, json=json
        )
        if res.status_code not in (200, 204):
            print(f"[ERROR] Misskey API error: {url}")
            print(f"status={res.status_code}")
            print(res.text)
            sys.exit(1)
        return res.json() if res.text else {}
    except Exception as e:
        print(f"[ERROR] Misskey request failed: {repr(e)}")
        sys.exit(1)


def post_to_misskey(image_path, text):
    token = os.getenv("MISSKEY_TOKEN")
    if not token:
        print("[ERROR] MISSKEY_TOKEN が設定されていません")
        sys.exit(1)

    MISSKEY_API = "https://misskey.io/api"

    # ======== ① 画像アップロード ========
    file_id = None
    if image_path and os.path.exists(image_path):
        print(f"[INFO] 画像アップロード中 → {image_path}")

        with open(image_path, "rb") as f:
            files = {"file": ("thumbnail.png", f, "image/png")}
            data = {"i": token}

            res = misskey_request(
                f"{MISSKEY_API}/drive/files/create",
                data=data,
                files=files
            )

        file_id = res.get("id")
        print(f"[INFO] Misskey 画像アップロード成功 → file_id={file_id}")
    else:
        print(f"[WARN] 画像ファイルが見つかりません → {image_path}")

    # ======== ② 投稿文補完 ========
    if not text or text.strip() == "":
        text = generate_default_text()
        print("[INFO] 投稿文が空 → デフォルトで補完")

    # ======== ③ 投稿データ ========
    note = {
        "i": token,
        "text": text,
        "visibility": "public"
    }

    if file_id:
        note["fileIds"] = [file_id]

    # ======== ④ 投稿 ========
    print("[INFO] Misskey に投稿中...")
    post_res = misskey_request(
        f"{MISSKEY_API}/notes/create",
        json=note
    )

    note_id = post_res.get("createdNote", {}).get("id", "")
    print(f"[SUCCESS] Misskey 投稿成功！ note_id={note_id}")

    # JST の投稿時刻を表示
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    print("[INFO] 投稿日時(JST):", now.strftime("%Y-%m-%d %H:%M:%S"))
    print("[INFO] 投稿文:\n", text)


def main():
    # 環境変数から取得（空なら補完）
    text = os.getenv("TWEET_TEXT", "").strip()
    if not text:
        text = generate_default_text()
        print("[INFO] TWEET_TEXT 未設定 → デフォルト使用")

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    post_to_misskey(image_path, text)


if __name__ == "__main__":
    main()
