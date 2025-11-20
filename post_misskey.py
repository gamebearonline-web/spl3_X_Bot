# post_misskey.py
import os
import requests
from datetime import datetime
import pytz

def post_to_misskey():
    TOKEN = os.getenv("MISSKEY_TOKEN")
    IMAGE_PATH = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")

    if not TOKEN:
        print("Error: MISSKEY_TOKEN が設定されていません")
        return

    # 日本時間で現在時刻文字列作成
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　%-H時更新")

    text = f"【スプラトゥーン3】スケジュール更新！ \n{time_str}\n画像で全ステージ確認してね！\n#スプラ3スケジュール"

    # 画像がある場合はアップロード
    files = {}
    if os.path.exists(IMAGE_PATH):
        files = {"file": open(IMAGE_PATH, "rb")}

    payload = {
        "i": TOKEN,
        "text": text,
        "visibility": "public",   # homeでもOK
        "localOnly": False
    }

    try:
        # misskey.io のエンドポイント（他インスタンスでもほぼ同じ）
        res = requests.post("https://misskey.io/api/notes/create", data=payload, files=files)
        res.raise_for_status()
        print("Misskey 投稿成功！")
        print("→ https://misskey.io/notes/" + res.json()["createdNote"]["id"])
    except Exception as e:
        print("Misskey 投稿失敗:", str(e))
    finally:
        for f in files.values():
            f.close()

if __name__ == "__main__":
    post_to_misskey()
