import os
import tweepy
import json

# ==================================================
# 認証情報
# ==================================================
API_KEY = os.environ["TWITTER_API_KEY"]
API_SECRET = os.environ["TWITTER_API_SECRET"]
ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]

# ==================================================
# 投稿文取得
# ==================================================
schedule_json = os.environ.get("SCHEDULE_JSON")

if schedule_json and os.path.exists(schedule_json):
    with open(schedule_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    text = data.get("text", "")
else:
    text = "【テスト投稿】X 文字のみ投稿テスト"

# ==================================================
# X API v1.1（文字のみ）
# ==================================================
auth = tweepy.OAuth1UserHandler(
    API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET
)
api = tweepy.API(auth)

# ★ 画像アップロードは一切しない
api.update_status(status=text)

print("[OK] X 文字のみ投稿 成功")
