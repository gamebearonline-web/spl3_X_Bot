import os
import sys
import requests
from datetime import datetime
import pytz

def post_to_bluesky(image_path, text):
    HANDLE = os.getenv("BSKY_USER")
    PASSWORD = os.getenv("BSKY_PASS")

    if not HANDLE or not PASSWORD:
        print("Error: Bluesky の認証情報が不足しています")
        sys.exit(1)

    # ① ログイン
    login_res = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": PASSWORD}
    )

    if login_res.status_code != 200:
        print("Bluesky ログイン失敗:", login_res.text)
        sys.exit(1)

    session = login_res.json()
    access_jwt = session["accessJwt"]
    did = session["did"]

    print(f"Bluesky ログイン成功: {did}")

    # ② 画像アップロード
    blob = None
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        upload_res = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": "image/png"
            },
            data=img_bytes
        )

        if upload_res.status_code != 200:
            print("Bluesky 画像アップロード失敗:", upload_res.text)
            sys.exit(1)

        blob = upload_res.json()["blob"]
        print("Bluesky 画像アップロード成功")

    # ③ text が空なら default_text を強制適用
    if not text or text.strip() == "":
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")
        text = f"【スプラ3】スケジュール更新！\n{time_str}"

    # ④ 投稿データ
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "langs": ["ja"],   # ← これが重要！テキスト表示の安定化
        "createdAt": datetime.now(tz=pytz.utc).isoformat().replace("+00:00", "Z")
    }

    # 画像あり
    if blob:
        record["embed"] = {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": blob,
                    "alt": "image"
                }
            ]
        }

    post_payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record
    }

    # ⑤ 投稿
    post_res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {access_jwt}"},
        json=post_payload
    )

    if post_res.status_code != 200:
        print("Bluesky 投稿失敗:", post_res.text)
        sys.exit(1)

    print("Bluesky 投稿成功！")


def main():
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")
    default_text = f"【スプラ3】スケジュール更新！\n{time_str}"

    # 空の場合は main 内でも補完
    text = os.getenv("TWEET_TEXT")
    if not text or text.strip() == "":
        text = default_text

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    if not os.path.exists(image_path):
        print(f"Error: 画像ファイルが見つかりません → {image_path}")
        sys.exit(1)

    post_to_bluesky(image_path, text)


if __name__ == "__main__":
    main()
