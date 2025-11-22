import os
import sys
import requests
from datetime import datetime
import pytz

def generate_default_text():
    """X / Bluesky と同じ構成の投稿文を生成"""
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")
    return f"【スプラ3】スケジュール更新！\n\n {time_str}\n画像で全ステージ確認してね！"


def post_to_misskey(image_path, text):
    token = os.getenv("MISSKEY_TOKEN")
    if not token:
        print("Error: MISSKEY_TOKEN が設定されていません")
        sys.exit(1)

    MISSKEY_API = "https://misskey.io/api"

    # ========== ① 画像アップロード ==========
    file_id = None
    if image_path and os.path.exists(image_path):

        with open(image_path, "rb") as f:
            files = {
                "file": ("thumbnail.png", f, "image/png")
            }
            data = {
                "i": token
            }

            upload_res = requests.post(
                f"{MISSKEY_API}/drive/files/create",
                data=data,
                files=files
            )

        if upload_res.status_code != 200:
            print("画像アップロード失敗:", upload_res.text)
            sys.exit(1)

        file_id = upload_res.json().get("id")
        print("Misskey 画像アップロード成功:", file_id)

    else:
        print("警告: 画像が見つかりません:", image_path)

    # ========== ② テキスト補完 ==========
    if not text or text.strip() == "":
        text = generate_default_text()
        print("テキストが空だったため補完しました →", text.replace("\n", "\\n"))

    # ========== ③ 投稿データ ==========
    note = {
        "i": token,
        "text": text,
        "visibility": "public"
    }

    if file_id:
        note["fileIds"] = [file_id]

    # ========== ④ 投稿 ==========
    post_res = requests.post(
        f"{MISSKEY_API}/notes/create",
        json=note
    )

    if post_res.status_code != 200:
        print("投稿失敗:", post_res.text)
        sys.exit(1)

    print("Misskey 投稿成功！")


def main():
    text = os.getenv("TWEET_TEXT", "").strip()
    if not text:
        text = generate_default_text()
        print("TWEET_TEXT が無いためデフォルトテキスト使用")

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    post_to_misskey(image_path, text)


if __name__ == "__main__":
    main()
