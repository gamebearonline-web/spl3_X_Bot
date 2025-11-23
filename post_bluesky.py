# post_bluesky.py (2025 Optimized & Fixed)
import os
import sys
import requests
from datetime import datetime
import pytz


def generate_default_text():
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")

    return (
        f"【スプラ3】スケジュール更新！\n"
        f"\n"
        f"{time_str}\n"
        f"#スプラ3スケジュール #スプラトゥーン3 #Splatoon3"
    )


# --------------------------------------------------------
# 🔧 Bluesky API 安全版リクエストラッパー（headersを確実に適用）
# --------------------------------------------------------
def bluesky_request(url, method="POST", headers=None, json=None, data=None):
    try:
        res = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            data=data
        )

        if res.status_code not in (200, 201):
            print(f"[ERROR] Bluesky API error ({url}) → {res.status_code}")
            print(res.text)
            sys.exit(1)

        return res.json()

    except Exception as e:
        print(f"[ERROR] Bluesky request 失敗: {url} → {repr(e)}")
        sys.exit(1)


# --------------------------------------------------------
#                 Bluesky 投稿
# --------------------------------------------------------
def post_to_bluesky(image_path, text):
    HANDLE = os.getenv("BSKY_USER")
    PASSWORD = os.getenv("BSKY_PASS")

    if not HANDLE or not PASSWORD:
        print("[ERROR] Bluesky の認証情報が不足しています（BSKY_USER / BSKY_PASS）")
        sys.exit(1)

    # ===== ① ログイン =====
    print("[INFO] Bluesky にログイン中...")
    session = bluesky_request(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": PASSWORD}
    )

    access_jwt = session["accessJwt"]
    did = session["did"]
    print(f"[INFO] ログイン成功: DID = {did}")

    # ===== ② 画像アップロード =====
    blob = None
    if os.path.exists(image_path):
        print(f"[INFO] 画像アップロード中 → {image_path}")
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        upload_res = bluesky_request(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": "image/png"
            },
            data=img_bytes
        )
        blob = upload_res["blob"]
        print("[INFO] 画像アップロード成功")
    else:
        print(f"[WARN] 画像が見つかりません → {image_path}")

    # ===== ③ 投稿文 =====
    if not text.strip():
        text = generate_default_text()
        print("[INFO] 投稿文が空 → デフォルトを使用")

    # ===== ④ レコード作成 =====
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "langs": ["ja"],
        "createdAt": datetime.now(pytz.utc).isoformat().replace("+00:00", "Z")
    }

    if blob:
        record["embed"] = {
            "$type": "app.bsky.embed.images",
            "images": [
                {"image": blob, "alt": "スプラトゥーン3 スケジュール画像"}
            ]
        }

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record
    }

    # ===== ⑤ 投稿 =====
    print("[INFO] Bluesky に投稿中...")
    result = bluesky_request(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {access_jwt}"},
        json=payload
    )

    print("[SUCCESS] Bluesky 投稿成功！")
    print("[INFO] 投稿文:\n" + text)


def main():
    text = os.getenv("TWEET_TEXT", "").strip()
    if not text:
        print("[INFO] TWEET_TEXT 未指定 → デフォルト使用")
        text = generate_default_text()

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    post_to_bluesky(image_path, text)


if __name__ == "__main__":
    main()
