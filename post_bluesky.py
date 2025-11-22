# post_bluesky.py
import os
import sys
import requests
from datetime import datetime
import pytz

def generate_default_text():
    """デフォルトの投稿文を生成（改行が先頭に来ないように注意）"""
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")
    
    # 重要：改行は2行目以降に配置（先頭に\nを置かない！）
    return f"【スプラ3】スケジュール更新！\n\n {time_str}\n#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"

def post_to_bluesky(image_path, text):
    HANDLE = os.getenv("BSKY_USER")
    PASSWORD = os.getenv("BSKY_PASS")

    if not HANDLE or not PASSWORD:
        print("Error: Bluesky の認証情報が不足しています")
        sys.exit(1)

    # ====== ① ログイン ======
    login_res = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": PASSWORD}
    )
    if login_res.status_code != 200:
        print("ログイン失敗:", login_res.text)
        sys.exit(1)

    session = login_res.json()
    access_jwt = session["accessJwt"]
    did = session["did"]
    print(f"Bluesky ログイン成功: {did}")

    # ====== ② 画像アップロード ======
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
            print("画像アップロード失敗:", upload_res.text)
            sys.exit(1)

        blob = upload_res.json()["blob"]
        print("Bluesky 画像アップロード成功")
    else:
        print("警告: 画像が見つかりません:", image_path)

    # ====== ③ テキストが空ならデフォルト生成（ここでもガード）======
    if not text or text.strip() == "":
        text = generate_default_text()
        print("テキストが空だったため補完しました →", text.replace("\n", "\\n"))

    # ====== ④ 投稿データ ======
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "langs": ["ja"],
        "createdAt": datetime.now(tz=pytz.utc).isoformat().replace("+00:00", "Z")
    }

    if blob:
        record["embed"] = {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": blob,
                    "alt": "スプラトゥーン3 スケジュール画像"
                }
            ]
        }

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record
    }

    # ====== ⑤ 投稿 ======
    post_res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {access_jwt}"},
        json=payload
    )

    if post_res.status_code != 200:
        print("投稿失敗:", post_res.text)
        sys.exit(1)

    print("Bluesky 投稿成功！")


def main():
    # 環境変数からテキスト取得（空でもOK）
    text = os.getenv("TWEET_TEXT", "").strip()
    
    # 空ならデフォルト生成（mainでも1回ガード）
    if not text:
        text = generate_default_text()
        print("TWEET_TEXTが未設定 → デフォルトテキストを使用")

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")

    post_to_bluesky(image_path, text)


if __name__ == "__main__":
    main()
